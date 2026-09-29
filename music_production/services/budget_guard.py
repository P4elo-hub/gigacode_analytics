"""Reservation-based accounting for creative generation budgets."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple
from uuid import uuid4


class BudgetDecisionCode(str, Enum):
    APPROVED = "APPROVED"
    REVISION_ESCALATION = "REVISION_ESCALATION"


@dataclass(frozen=True)
class BudgetLimits:
    max_batch: int
    max_defect_fix_attempts: int
    max_iterations: int
    max_api_wait_seconds: int
    max_cost: Decimal

    def __post_init__(self) -> None:
        _validate_non_negative_usage(
            BudgetUsage(
                generation_batches=self.max_batch,
                defect_fix_attempts=self.max_defect_fix_attempts,
                iterations=self.max_iterations,
                api_wait_seconds=self.max_api_wait_seconds,
                cost=self.max_cost,
            )
        )


@dataclass(frozen=True)
class BudgetUsage:
    generation_batches: int = 0
    defect_fix_attempts: int = 0
    iterations: int = 0
    api_wait_seconds: int = 0
    cost: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if isinstance(self.cost, float):
            raise TypeError("money must use Decimal, not float")
        if not isinstance(self.cost, Decimal):
            raise TypeError("cost must be Decimal")
        _validate_non_negative_usage(self)

    def __add__(self, other: "BudgetUsage") -> "BudgetUsage":
        return BudgetUsage(
            generation_batches=self.generation_batches + other.generation_batches,
            defect_fix_attempts=self.defect_fix_attempts + other.defect_fix_attempts,
            iterations=self.iterations + other.iterations,
            api_wait_seconds=self.api_wait_seconds + other.api_wait_seconds,
            cost=self.cost + other.cost,
        )

    def __sub__(self, other: "BudgetUsage") -> "BudgetUsage":
        return BudgetUsage(
            generation_batches=self.generation_batches - other.generation_batches,
            defect_fix_attempts=self.defect_fix_attempts - other.defect_fix_attempts,
            iterations=self.iterations - other.iterations,
            api_wait_seconds=self.api_wait_seconds - other.api_wait_seconds,
            cost=self.cost - other.cost,
        )


def _validate_non_negative_usage(usage: BudgetUsage) -> None:
    values = (
        usage.generation_batches,
        usage.defect_fix_attempts,
        usage.iterations,
        usage.api_wait_seconds,
        usage.cost,
    )
    if any(value < 0 for value in values):
        raise ValueError("budget values cannot be negative")


@dataclass(frozen=True)
class BudgetDecision:
    code: BudgetDecisionCode
    exceeded_limits: Tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.code == BudgetDecisionCode.APPROVED


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    requested: BudgetUsage


@dataclass(frozen=True)
class ReservationResult:
    decision: BudgetDecision
    reservation: Optional[BudgetReservation] = None


class UnknownReservationError(KeyError):
    pass


class BudgetGuard:
    """Check, reserve, commit, or release one creative attempt."""

    def __init__(self, limits: BudgetLimits) -> None:
        self.limits = limits
        self.committed = BudgetUsage()
        self._reservations: Dict[str, BudgetUsage] = {}

    @property
    def reserved(self) -> BudgetUsage:
        total = BudgetUsage()
        for usage in self._reservations.values():
            total = total + usage
        return total

    @property
    def remaining(self) -> BudgetUsage:
        used = self.committed + self.reserved
        return BudgetUsage(
            generation_batches=self.limits.max_batch - used.generation_batches,
            defect_fix_attempts=(
                self.limits.max_defect_fix_attempts - used.defect_fix_attempts
            ),
            iterations=self.limits.max_iterations - used.iterations,
            api_wait_seconds=(
                self.limits.max_api_wait_seconds - used.api_wait_seconds
            ),
            cost=self.limits.max_cost - used.cost,
        )

    def check(self, requested: BudgetUsage) -> BudgetDecision:
        projected = self.committed + self.reserved + requested
        exceeded = []
        comparisons = (
            ("max_batch", projected.generation_batches, self.limits.max_batch),
            (
                "max_defect_fix_attempts",
                projected.defect_fix_attempts,
                self.limits.max_defect_fix_attempts,
            ),
            ("max_iterations", projected.iterations, self.limits.max_iterations),
            (
                "max_api_wait_seconds",
                projected.api_wait_seconds,
                self.limits.max_api_wait_seconds,
            ),
            ("max_cost", projected.cost, self.limits.max_cost),
        )
        for name, value, limit in comparisons:
            if value > limit:
                exceeded.append(name)
        if exceeded:
            return BudgetDecision(
                BudgetDecisionCode.REVISION_ESCALATION,
                tuple(exceeded),
            )
        return BudgetDecision(BudgetDecisionCode.APPROVED)

    def reserve(self, requested: BudgetUsage) -> ReservationResult:
        decision = self.check(requested)
        if not decision.allowed:
            return ReservationResult(decision=decision)
        reservation = BudgetReservation(str(uuid4()), requested)
        self._reservations[reservation.reservation_id] = requested
        return ReservationResult(decision=decision, reservation=reservation)

    def commit(
        self,
        reservation_id: str,
        actual: Optional[BudgetUsage] = None,
    ) -> None:
        requested = self._pop_reservation(reservation_id)
        actual_usage = actual if actual is not None else requested
        if _usage_exceeds(actual_usage, requested):
            self._reservations[reservation_id] = requested
            raise ValueError("actual usage cannot exceed the reservation")
        self.committed = self.committed + actual_usage

    def release(self, reservation_id: str) -> None:
        self._pop_reservation(reservation_id)

    def _pop_reservation(self, reservation_id: str) -> BudgetUsage:
        try:
            return self._reservations.pop(reservation_id)
        except KeyError as exc:
            raise UnknownReservationError(reservation_id) from exc


def _usage_exceeds(actual: BudgetUsage, reserved: BudgetUsage) -> bool:
    return any(
        actual_value > reserved_value
        for actual_value, reserved_value in (
            (actual.generation_batches, reserved.generation_batches),
            (actual.defect_fix_attempts, reserved.defect_fix_attempts),
            (actual.iterations, reserved.iterations),
            (actual.api_wait_seconds, reserved.api_wait_seconds),
            (actual.cost, reserved.cost),
        )
    )
