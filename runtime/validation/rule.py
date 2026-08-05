"""The ValidationRule abstraction and the contexts rules operate on.

Open/Closed in practice: adding a check means adding a rule class and
registering it. No existing rule, the registry, the pipeline or the validator
is modified. Single Responsibility: one rule answers exactly one question.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectContext
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation.ports import ProviderRegistryPort


@dataclass(frozen=True, slots=True)
class ProjectRuleContext:
    """Everything a project rule may read.

    `core` is optional: authoring-time (CI) validation may run without a loaded
    CoreBundle. Rules that genuinely need Core must declare that by returning
    False from `is_applicable`, rather than assuming it is present.
    """

    project: ProjectContext
    core: CoreBundle | None = None
    provider_registry: ProviderRegistryPort | None = None


@dataclass(frozen=True, slots=True)
class CoreRuleContext:
    """Everything a core rule may read."""

    core: CoreBundle


class ValidationRule(ABC):
    """Base class for every validation rule.

    Rules are pure: they read the context and yield issues. They never mutate
    the context, never perform I/O, and never decide activation.
    """

    #: Stable identifier, used for selective enabling/suppression in CI.
    rule_id: str = ""

    #: One-line statement of what this rule guarantees.
    description: str = ""

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
        """Whether this rule can run against the given context.

        Skipping is not passing — a rule that cannot run yields nothing, and any
        gap that creates is covered by a different rule that *can* run.
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
