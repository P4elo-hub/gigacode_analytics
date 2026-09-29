#!/usr/bin/env python3
"""Reservation and typed escalation behavior for BudgetGuard."""

from __future__ import annotations

import unittest
from decimal import Decimal

from music_production.services.budget_guard import (
    BudgetDecisionCode,
    BudgetGuard,
    BudgetLimits,
    BudgetUsage,
)


def limits() -> BudgetLimits:
    return BudgetLimits(
        max_batch=2,
        max_defect_fix_attempts=3,
        max_iterations=4,
        max_api_wait_seconds=120,
        max_cost=Decimal("10.00"),
    )


class BudgetGuardTest(unittest.TestCase):
    def test_reserve_commit_and_release(self) -> None:
        guard = BudgetGuard(limits())
        usage = BudgetUsage(
            generation_batches=1,
            iterations=1,
            api_wait_seconds=30,
            cost=Decimal("2.50"),
        )
        first = guard.reserve(usage)
        self.assertTrue(first.decision.allowed)
        self.assertEqual(guard.reserved, usage)
        guard.commit(first.reservation.reservation_id)
        self.assertEqual(guard.committed, usage)
        self.assertEqual(guard.reserved, BudgetUsage())

        second = guard.reserve(BudgetUsage(defect_fix_attempts=1))
        guard.release(second.reservation.reservation_id)
        self.assertEqual(guard.reserved, BudgetUsage())
        self.assertEqual(guard.committed, usage)

    def test_each_limit_returns_revision_escalation(self) -> None:
        cases = (
            ("max_batch", BudgetUsage(generation_batches=3)),
            ("max_defect_fix_attempts", BudgetUsage(defect_fix_attempts=4)),
            ("max_iterations", BudgetUsage(iterations=5)),
            ("max_api_wait_seconds", BudgetUsage(api_wait_seconds=121)),
            ("max_cost", BudgetUsage(cost=Decimal("10.01"))),
        )
        for expected, usage in cases:
            with self.subTest(limit=expected):
                decision = BudgetGuard(limits()).check(usage)
                self.assertEqual(
                    decision.code,
                    BudgetDecisionCode.REVISION_ESCALATION,
                )
                self.assertIn(expected, decision.exceeded_limits)

    def test_reservations_prevent_overbooking(self) -> None:
        guard = BudgetGuard(limits())
        first = guard.reserve(BudgetUsage(generation_batches=2))
        self.assertIsNotNone(first.reservation)
        second = guard.reserve(BudgetUsage(generation_batches=1))
        self.assertFalse(second.decision.allowed)
        self.assertIsNone(second.reservation)

    def test_values_cannot_be_negative(self) -> None:
        with self.assertRaises(ValueError):
            BudgetUsage(iterations=-1)
        with self.assertRaises(ValueError):
            BudgetLimits(1, 1, 1, 1, Decimal("-0.01"))

    def test_money_must_not_be_float(self) -> None:
        with self.assertRaises(TypeError):
            BudgetUsage(cost=1.5)  # type: ignore[arg-type]

    def test_commit_can_charge_less_but_not_more_than_reservation(self) -> None:
        guard = BudgetGuard(limits())
        result = guard.reserve(
            BudgetUsage(generation_batches=1, cost=Decimal("3.00"))
        )
        guard.commit(
            result.reservation.reservation_id,
            BudgetUsage(generation_batches=1, cost=Decimal("2.25")),
        )
        self.assertEqual(guard.committed.cost, Decimal("2.25"))

        result = guard.reserve(BudgetUsage(cost=Decimal("1.00")))
        with self.assertRaises(ValueError):
            guard.commit(
                result.reservation.reservation_id,
                BudgetUsage(cost=Decimal("1.01")),
            )
        self.assertEqual(guard.reserved.cost, Decimal("1.00"))


if __name__ == "__main__":
    unittest.main()
