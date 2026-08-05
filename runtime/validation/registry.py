"""RuleRegistry — the collection of rules a pipeline will run.

Kept separate from the pipeline (which executes) and the validator (which
orchestrates) so each has one reason to change. Registration is explicit rather
than auto-discovered by import side effects: a rule that silently stops running
because a module was not imported is exactly the kind of failure a fail-closed
validator must not have.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence

from runtime.validation.rule import ValidationRule


class DuplicateRuleError(ValueError):
    """Raised when two rules claim the same rule_id."""


class RuleRegistry:
    """An ordered, duplicate-free collection of rules."""

    def __init__(self, rules: Iterable[ValidationRule] | None = None) -> None:
        self._rules: list[ValidationRule] = []
        self._ids: set[str] = set()
        for rule in rules or ():
            self.register(rule)

    def register(self, rule: ValidationRule) -> RuleRegistry:
        if rule.rule_id in self._ids:
            raise DuplicateRuleError(
                f"Rule id {rule.rule_id!r} is already registered. "
                "Rule ids must be unique so CI can reference them stably."
            )
        self._ids.add(rule.rule_id)
        self._rules.append(rule)
        return self

    def register_all(self, rules: Iterable[ValidationRule]) -> RuleRegistry:
        for rule in rules:
            self.register(rule)
        return self

    def without(self, *rule_ids: str) -> RuleRegistry:
        """A copy with the named rules removed (for targeted CI suppression)."""
        excluded = set(rule_ids)
        return RuleRegistry(r for r in self._rules if r.rule_id not in excluded)

    @property
    def rules(self) -> Sequence[ValidationRule]:
        return tuple(self._rules)

    def __iter__(self) -> Iterator[ValidationRule]:
        return iter(tuple(self._rules))

    def __len__(self) -> int:
        return len(self._rules)

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self._ids
