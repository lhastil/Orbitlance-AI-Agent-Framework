"""Prompt Assembler — Runtime Module 4.

Implements module 4 of docs/runtime-specification.md:

    assemble(resolved_context, workflow_state, conversation_context) -> PromptBundle

Builds the static `PromptBundle` from a `ResolvedContext`, in the frozen
assembly order.

**Why `CoreBundle` is constructor-injected.** Rule 6 fixes the public interface
at three parameters, none of which carries Core content, yet six of the nine
slots are sourced from Core. A fourth parameter would break the frozen
signature. Core Loader rule 6 offers `getCoreBundle()` cached *"for the process
lifetime"*, so a long-lived injected bundle is the shape the specification
already implies — the same split the Validation Layer uses for its long-lived
provider registry.

**What this module refuses to do**, per rule 3 and the surrounding architecture:
it never calls a provider, never counts tokens, never chooses the active
workflow, never touches the filesystem, never parses Markdown, never executes a
tool, never decides activation, and never re-decides a fallback the Resolver
already decided. It renders what it is given, in the order it was given.

It is a pure function of its inputs: identical inputs produce an equal bundle,
and nothing it receives is mutated.
"""

from __future__ import annotations

from collections.abc import Mapping

from runtime.assembler import core_slots as slots
from runtime.assembler.errors import PlaybookLeakError, UnknownWorkflowError
from runtime.assembler.ports import TokenBudgetPort
from runtime.models.budget import (
    BudgetRequest,
    BudgetSelection,
    KnowledgeCandidate,
    SectionRef,
)
from runtime.models.conversation import ConversationContext, Turn, WorkflowState
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectDocument, Section
from runtime.models.prompt_bundle import (
    ASSEMBLY_ORDER,
    PromptBundle,
    PromptSection,
    PromptSlot,
)
from runtime.models.resolved_context import ResolvedContext

_SEPARATOR = "\n\n"


def _render_section(section: Section) -> str:
    """One Knowledge section as prompt text: its heading, then its body.

    The heading marker is rebuilt from `heading_level` because the assembled
    prompt has always carried Markdown headings — the previous renderer emitted
    `raw_text` verbatim. Reproducing the marker plus the original heading text
    preserves that exactly; the heading text itself is never regenerated,
    normalised or invented.
    """
    heading = f"{'#' * section.heading_level} {section.heading_text}".strip()
    body = section.body.strip()
    return f"{heading}{_SEPARATOR}{body}" if body else heading


def _knowledge_candidates(context: ResolvedContext) -> tuple[KnowledgeCandidate, ...]:
    """Render every Knowledge section once, in document order.

    Phase 1 is all-or-nothing, so the candidate set is the whole set. Rendering
    here — before the budget manager is consulted — is what lets it count the
    exact text that will ship, and the same strings are reused when the slot is
    assembled. Empty renders are dropped so a candidate always carries content.
    """
    candidates: list[KnowledgeCandidate] = []
    for name, document in context.knowledge.items():
        if not document.exists or document.is_empty:
            continue
        for section in document.sections:
            rendered = _render_section(section)
            if rendered:
                candidates.append(KnowledgeCandidate(name, section.ordinal, rendered))
    return tuple(candidates)


def _provenance(
    document: ProjectDocument, fallback: str, project_id: str | None = None
) -> str:
    """Where this text actually came from, as the Loader recorded it.

    `ProjectDocument.relative_path` is set by whichever Loader read the file, so
    it is evidence about the text's origin rather than a label the assembler
    invented for the slot it was filling. Core documents already carry a
    repository-relative path (`core/prompts/02_mission.md`); project documents
    carry a project-relative one (`knowledge/01_company.md`), which is prefixed
    here so both live in one namespace.

    `fallback` applies when a document records no usable path — either empty or
    a bare filename, which carries no directory and therefore no provenance. It
    names the slot's expected location, so provenance is unverified for that
    document, which is precisely why a fallback can never be a playbook path.

    This does not prove content origin. See PA-6 for what it does and does not
    establish.
    """
    path = (document.relative_path or "").replace("\\", "/").strip()
    if not path or "/" not in path:
        return fallback
    if path.startswith(("core/", "projects/")):
        return path
    return f"projects/{project_id}/{path}" if project_id else path


class PromptAssembler:
    """Assembles a `PromptBundle`. Stateless apart from its injected collaborators."""

    __slots__ = ("_core", "_budget")

    def __init__(self, core: CoreBundle, *, token_budget: TokenBudgetPort | None = None):
        self._core = core
        self._budget = token_budget

    # --- public interface ---------------------------------------------------
    def assemble(
        self,
        resolved_context: ResolvedContext,
        workflow_state: WorkflowState,
        conversation_context: ConversationContext,
    ) -> PromptBundle:
        """Build this turn's bundle.

        Missing Knowledge takes the degraded path (rule 9) as defence in depth,
        even though the Runtime Engine should already have refused activation.
        """
        if resolved_context.knowledge_incomplete:
            sections = self._degraded_sections()
            history: tuple[Turn, ...] = conversation_context.history
            degraded = True
        else:
            sections, history = self._normal_sections(
                resolved_context, workflow_state, conversation_context
            )
            degraded = False

        self._assert_no_playbook_content(sections)

        return PromptBundle(
            project_id=resolved_context.project_id,
            conversation_id=conversation_context.conversation_id,
            static_sections=sections,
            conversation_history_window=history,
            latest_message=conversation_context.latest_user_message,
            degraded=degraded,
        )

    # --- normal assembly ----------------------------------------------------
    def _normal_sections(
        self,
        context: ResolvedContext,
        state: WorkflowState,
        conversation: ConversationContext,
    ) -> tuple[tuple[PromptSection, ...], tuple[Turn, ...]]:
        """The nine frozen slots, in order. Empty slots are omitted, not faked.

        Every fixed slot is rendered **before** the budget manager is consulted,
        so it counts the real text rather than an estimate of it. Only the
        Knowledge slot depends on that answer, so only it is built afterwards.
        The build order differs from `ASSEMBLY_ORDER`; the output order does not.
        """
        builders = {
            PromptSlot.GUARDRAILS: self._guardrails,
            PromptSlot.BRANDING: lambda: self._branding(context),
            PromptSlot.WORKFLOW: lambda: self._workflow(context, state),
        }
        fixed: dict[PromptSlot, PromptSection] = {}
        for slot in ASSEMBLY_ORDER:
            if slot is PromptSlot.KNOWLEDGE:
                continue
            build = builders.get(slot)
            section = build() if build else self._core_prompt(slot)
            if section is not None:
                fixed[slot] = section

        candidates = _knowledge_candidates(context)
        selection = self._select(
            context, conversation, tuple(fixed.values()), candidates
        )
        knowledge = self._knowledge(context, candidates, selection.knowledge_sections)

        rendered = dict(fixed)
        if knowledge is not None:
            rendered[PromptSlot.KNOWLEDGE] = knowledge
        ordered = tuple(rendered[slot] for slot in ASSEMBLY_ORDER if slot in rendered)
        return ordered, selection.history_window

    def _core_prompt(self, slot: PromptSlot) -> PromptSection | None:
        """A slot sourced from a single `core/prompts/` file."""
        filename = slots.CORE_PROMPT_FILES[slot]
        document = self._core.prompts.get(filename)
        if document is None or not document.exists or document.is_empty:
            return None
        return PromptSection(
            slot=slot,
            sources=(_provenance(document, f"core/prompts/{filename}"),),
            content=document.raw_text.strip(),
        )

    def _guardrails(self) -> PromptSection | None:
        """The atomic Safety + Escalation + Compliance bundle.

        `core/prompts/08_guardrails.md` is never rendered — it marks where these
        rules go rather than containing them.
        """
        parts: list[str] = []
        rendered: list[str] = []
        for filename in slots.GUARDRAIL_FILES:
            document = self._core.guardrails.get(filename)
            if document is None or not document.exists or document.is_empty:
                continue
            parts.append(document.raw_text.strip())
            rendered.append(_provenance(document, f"core/guardrails/{filename}"))
        if not parts:
            return None
        return PromptSection(
            slot=PromptSlot.GUARDRAILS,
            sources=tuple(rendered),
            content=_SEPARATOR.join(parts),
        )

    @staticmethod
    def _branding(context: ResolvedContext) -> PromptSection | None:
        """The project's branding overlay.

        An empty overlay means Core's neutral default voice already applies —
        the Resolver decided that and recorded it (R3-3). The assembler must not
        substitute Core Personality here: it is already emitted in its own slot,
        and copying it would send the same text twice.
        """
        return PromptAssembler._documents_section(
            PromptSlot.BRANDING, context.branding, context.project_id
        )

    def _knowledge(
        self,
        context: ResolvedContext,
        candidates: tuple[KnowledgeCandidate, ...],
        selected: tuple[SectionRef, ...],
    ) -> PromptSection | None:
        """Assemble the Knowledge slot from the **already-rendered** candidates.

        Nothing is rendered a second time here. Each candidate was rendered once,
        handed to the budget manager to count, and the identical string is reused
        now — so what was counted and what ships cannot diverge. Re-rendering,
        even with the same function, would reopen that gap the moment the two
        paths differed.

        `raw_text` is never consulted, and `section_body(title)` is unusable
        anyway: it is first-occurrence lookup and cannot address the second
        `Category` in a document that has five. An unresolvable reference is
        skipped rather than invented.
        """
        by_ref = {candidate.ref: candidate for candidate in candidates}
        parts: list[str] = []
        sources: list[str] = []
        for ref in selected:
            candidate = by_ref.get(ref)
            if candidate is None or not candidate.rendered_text:
                continue
            document = context.knowledge.get(candidate.document_name)
            if document is None:
                continue
            parts.append(candidate.rendered_text)
            base = _provenance(
                document,
                f"projects/{context.project_id}/{candidate.document_name}",
                context.project_id,
            )
            sources.append(f"{base}#{candidate.ordinal}")
        if not parts:
            return None
        return PromptSection(
            slot=PromptSlot.KNOWLEDGE,
            sources=tuple(sources),
            content=_SEPARATOR.join(parts),
        )

    def _select(
        self,
        context: ResolvedContext,
        conversation: ConversationContext,
        fixed: tuple[PromptSection, ...],
        candidates: tuple[KnowledgeCandidate, ...],
    ) -> BudgetSelection:
        """Ask the budget manager what fits, handing it the real rendered text.

        Both halves cross the seam already rendered — fixed sections and
        Knowledge candidates alike — so the budget manager counts literal
        strings and never models this module's formatting.
        """
        if self._budget is None:
            return BudgetSelection(
                # Phase 1: all of them.
                knowledge_sections=tuple(c.ref for c in candidates),
                history_window=conversation.history,
            )
        return self._budget.select(
            BudgetRequest(
                project_id=context.project_id,
                fixed_sections=fixed,
                latest_message=conversation.latest_user_message,
                knowledge_candidates=candidates,
                conversation=conversation,
            )
        )

    def _workflow(
        self, context: ResolvedContext, state: WorkflowState
    ) -> PromptSection | None:
        """The active workflow expanded; every other enabled workflow indexed."""
        enabled = context.config.enabled_workflows
        active = state.active_workflow
        if active is None:
            return None

        document = self._core.workflows.get(f"{active}.md")
        if document is None or not document.exists:
            raise UnknownWorkflowError(
                f"Active workflow {active!r} does not exist in core/workflows/. "
                "The Workflow Router must never route to an undefined workflow."
            )

        others = tuple(name for name in enabled if name != active)
        content = document.raw_text.strip()
        if others:
            content += _SEPARATOR + (
                "Other workflows available for this project (not active now; "
                "listed so you know they exist, do not follow them): "
                + ", ".join(others)
                + "."
            )
        return PromptSection(
            slot=PromptSlot.WORKFLOW,
            sources=(_provenance(document, f"core/workflows/{active}.md"),),
            content=content,
        )

    @staticmethod
    def _documents_section(
        slot: PromptSlot,
        documents: Mapping[str, ProjectDocument],
        project_id: str,
    ) -> PromptSection | None:
        """Render live documents, recording provenance for exactly those.

        Sources are derived from the documents actually rendered, never from the
        full candidate list — an earlier revision listed empty documents it had
        skipped, overstating provenance (PA-7).
        """
        parts: list[str] = []
        sources: list[str] = []
        for name, doc in documents.items():
            if not doc.exists or doc.is_empty:
                continue
            parts.append(doc.raw_text.strip())
            sources.append(_provenance(doc, f"projects/{project_id}/{name}", project_id))
        if not parts:
            return None
        return PromptSection(
            slot=slot, sources=tuple(sources), content=_SEPARATOR.join(parts)
        )

    # --- degraded assembly (rule 9) -----------------------------------------
    def _degraded_sections(self) -> tuple[PromptSection, ...]:
        """A minimal, honest bundle that explains the agent is not configured.

        No Knowledge, no Branding, no Workflow, no Tool Instructions, no
        Mission: there is no configured business to represent. Nothing about the
        client is invented — the notice is fixed framework text.
        """
        sections: list[PromptSection] = []
        for slot in slots.DEGRADED_SLOTS:
            if slot is PromptSlot.DEGRADED_NOTICE:
                sections.append(
                    PromptSection(
                        slot=slot,
                        sources=("runtime/assembler/core_slots.py",),
                        content=slots.DEGRADED_NOTICE,
                    )
                )
            elif slot is PromptSlot.GUARDRAILS:
                guardrails = self._guardrails()
                if guardrails is not None:
                    sections.append(guardrails)
            else:
                section = self._core_prompt(slot)
                if section is not None:
                    sections.append(section)
        return tuple(sections)

    # --- rule 10: hard playbook assertion -----------------------------------
    @staticmethod
    def _assert_no_playbook_content(sections: tuple[PromptSection, ...]) -> None:
        """No assembled section may originate under `core/industry_playbooks/`.

        Provenance, not substring, and **every** source is inspected — an
        earlier revision joined sources into one string and tested it with
        `startswith`, so only the first path was ever checked (PA-5).

        A substring check would be wrong regardless: several assembled files
        legitimately *mention* Industry Playbooks. `core/guardrails/safety.md`,
        `compliance.md` and `escalation.md` all defer industry specifics to
        them, and `core/workflows/discovery.md` and `recommendation.md` state
        that playbooks never load at runtime. Nine such mentions appear in a
        real assembled bundle, so a text search would reject valid output.

        **What this cannot establish (PA-6).** Provenance comes from
        `ProjectDocument.relative_path` — what the Loader recorded about where
        the text was read. That catches the realistic Core Loader defect: a
        playbook document misfiled into a prompt slot while still carrying its
        true path. It cannot catch a document carrying playbook *text* under a
        falsified path, because `CoreBundle` holds no content-origin metadata
        and no playbook text to compare against. That case is covered at the
        test boundary by the spec's own rule-12(b) fixture test, which checks
        real assembled output against real playbook strings.
        """
        for section in sections:
            if section.is_from_playbook:
                raise PlaybookLeakError(
                    f"Section {section.slot.value!r} is sourced from "
                    f"{section.source!r}. Industry Playbooks are reference-only "
                    "and must never reach an assembled prompt."
                )

