"""Base abstractions for modular licensing criteria."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CriterionResult:
    """Outcome of validating a single licensing criterion."""

    name: str
    passed: bool
    enabled: bool
    current: int | None = None
    limit: int | None = None
    message: str = ""


@runtime_checkable
class LicenseCriterion(Protocol):
    """Interface for evaluating a single licensing criterion."""

    name: str

    def validate(self) -> CriterionResult:
        """Evaluate the criterion.

        Returns:
            CriterionResult indicating status.

        Raises:
            LicenseError: If evaluation fails or limit is exceeded.
        """
        ...
