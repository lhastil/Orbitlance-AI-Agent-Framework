"""The ValidationRule abstraction and the contexts rules operate on.

Open/Closed in practice: adding a check means adding a rule class and
registering it. No existing rule, the registry, the pipeline or the validator
is modified. Single Responsibility: one rule answers exactly one question.

Two distinct reasons a rule may not run, kept deliberately separate:

  * It needs a **collaborator** that was not supplied (CoreBundle, Provider
    Registry). Declared via `required_collaborators`; the pipeline enforces it
    generically so no rule re-implements the check. This is a coverage gap.

  * The **data** it inspects is absent, and that absence is already reported by
    another rule. Declared via `is_applicable`. This is not a coverage gap --
    there was nothing to check.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectContext
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation.ports import ProviderRegistryPort


class Collaborator(str, Enum):
    """An external input a rule may require in order to answer its question."""

    CORE_BUNDLE = "core_bundle"
    PROVIDER_REGISTRY = "provider_registry"

    @property
    def description(self) -> str:
        return _COLLABORATOR_DESCRIPTIONS[self]


_COLLABORATOR_DESCRIPTIONS: dict[Collaborator, str] = {
    Collaborator.CORE_BUNDLE: (
        "a loaded CoreBundle (supply one via Validator.validate_project(..., core=...))"
    ),
    Collaborator.PROVIDER_REGISTRY: (
        "a Provider Registry (inject one via Validator(provider_registry=...))"
    ),
}


@runtime_checkable
class RuleContext(Protocol):
    """What the pipeline needs from any rule context.

    Contexts report their own available collaborators, so the pipeline stays
    generic and never type-switches on the concrete context class.
    """

    def available_collaborators(self) -> frozenset[Collaborator]:
        ...


@dataclass(frozen=True, slots=True)
class ProjectRuleContext:
    """Everything a project rule may read.

    `core` and `provider_registry` are optional. Rules that need them declare so
    via `required_collaborators`; they are never silently substituted with a
    permissive stand-in, because a stand-in would turn "not checked" into
    "checked and fine".
    """

    project: ProjectContext
    core: CoreBundle | None = None
    provider_registry: ProviderRegistryPort | None = None

    def available_collaborators(self) -> frozenset[Collaborator]:
        available: set[Collaborator] = set()
        if self.core is not None:
            available.add(Collaborator.CORE_BUNDLE)
        if self.provider_registry is not None:
            available.add(Collaborator.PROVIDER_REGISTRY)
        return frozenset(available)


@dataclass(frozen=True, slots=True)
class CoreRuleContext:
    """Everything a core rule may read."""

    core: CoreBundle

    def available_collaborators(self) -> frozenset[Collaborator]:
        return frozenset({Collaborator.CORE_BUNDLE})


class ValidationRule(ABC):
    """Base class for every validation rule.

    Rules are pure: they read the context and yield issues. They never mutate
    the context, never perform I/O, and never decide activation.
    """

    #: Stable identifier, used for selective enabling/suppression in CI.
    rule_id: str = ""

    #: One-line statement of what this rule guarantees.
    description: str = ""

    #: Collaborators without which this rule cannot answer its question.
    required_collaborators: frozenset[Collaborator] = frozenset()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Guard against the classic failure of a rule that silently never runs
        # because it was registered without an id.
        #
        # Two kinds of subclass are legitimately exempt:
        #   * still-abstract classes (ProjectRule, CoreRule)
        #   * internal shared bases, named with a leading underscore, which
        #     exist only to remove duplication between sibling rules
        #
        # __init_subclass__ runs before ABCMeta populates __abstractmethods__,
        # so that attribute is read defensively rather than assumed present.
        if cls.__name__.startswith("_"):
            return
        if getattr(cls, "__abstractmethods__", None):
            return
        if getattr(cls.evaluate, "__isabstractmethod__", False):
            return
        if not cls.rule_id:
            raise TypeError(f"{cls.__name__} must define a non-empty rule_id")

    def is_applicable(self, context: object) -> bool:  # noqa: ARG002
        """Whether the data this rule inspects is present.

        Return False only when the data is absent *and* that absence is already
        reported by another rule. Never use this to work around a missing
        collaborator -- declare `required_collaborators` instead, so the skip is
        recorded as a coverage gap rather than silently passing.
        """
        return True

    @abstractmethod
    def evaluate(self, context: object) -> Iterable[ValidationIssue]:
        """Yield an issue per problem found. Yield nothing when satisfied."""
        raise NotImplementedError

    # -- helpers shared by all rules ---------------------------------------
    @staticmethod
    def issue(
        *,
        code: str,
        severity: Severity,
        message: str,
        file: str,
        recommendation: str,
        section: str | None = None,
        field_name: str | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            code=code,
            severity=severity,
            message=message,
            file=file,
            recommendation=recommendation,
            section=section,
            field_name=field_name,
        )


class ProjectRule(ValidationRule):
    """A rule that validates a ProjectContext."""

    @abstractmethod
    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        raise NotImplementedError


class CoreRule(ValidationRule):
    """A rule that validates a CoreBundle."""

    @abstractmethod
    def evaluate(self, context: CoreRuleContext) -> Iterable[ValidationIssue]:
        raise NotImplementedError
