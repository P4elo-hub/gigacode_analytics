"""Explicit provider capability allow-list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable


@dataclass(frozen=True)
class CapabilityError:
    code: str
    operation: str
    message: str


class UnsupportedCapabilityError(RuntimeError):
    def __init__(self, error: CapabilityError) -> None:
        super().__init__(error.message)
        self.error = error


class CapabilityRegistry:
    """Stores only operations actually enabled for one provider."""

    def __init__(self, operations: Iterable[str] = ()) -> None:
        self._operations: FrozenSet[str] = frozenset(operations)

    @property
    def operations(self) -> FrozenSet[str]:
        return self._operations

    def supports(self, operation: str) -> bool:
        return operation in self._operations

    def require(self, operation: str) -> None:
        if not self.supports(operation):
            raise UnsupportedCapabilityError(
                CapabilityError(
                    code="CAPABILITY_UNAVAILABLE",
                    operation=operation,
                    message=f"provider capability is unavailable: {operation}",
                )
            )
