from decimal import Decimal
import unittest

from app.allocation import allocate_proportionally


class AllocationTests(unittest.TestCase):
    def test_returns_empty_for_no_positive_creditors(self) -> None:
        applied, allocations = allocate_proportionally(
            [
                {"id": "1", "name": "A", "amount": "0.00"},
                {"id": "2", "name": "B", "amount": "-10.00"},
            ],
            Decimal("100.00"),
        )
        self.assertEqual(applied, Decimal("0.00"))
        self.assertEqual(allocations, [])

    def test_allocates_proportionally_and_sorts_by_name(self) -> None:
        applied, allocations = allocate_proportionally(
            [
                {"id": "b", "name": "Zulu", "amount": "10.00"},
                {"id": "a", "name": "Alpha", "amount": "20.00"},
            ],
            Decimal("10.00"),
        )

        self.assertEqual(applied, Decimal("10.00"))
        self.assertEqual([a.creditor_name for a in allocations], ["Alpha", "Zulu"])
        by_name = {a.creditor_name: a.amount for a in allocations}
        self.assertEqual(by_name["Alpha"], Decimal("6.67"))
        self.assertEqual(by_name["Zulu"], Decimal("3.33"))

    def test_applied_payment_is_capped_by_total_debt(self) -> None:
        applied, allocations = allocate_proportionally(
            [{"id": "1", "name": "Only", "amount": "5.00"}],
            Decimal("100.00"),
        )
        self.assertEqual(applied, Decimal("5.00"))
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0].amount, Decimal("5.00"))

    def test_non_positive_payment_returns_empty(self) -> None:
        applied, allocations = allocate_proportionally(
            [{"id": "1", "name": "Only", "amount": "5.00"}],
            Decimal("0.00"),
        )
        self.assertEqual(applied, Decimal("0.00"))
        self.assertEqual(allocations, [])


if __name__ == "__main__":
    unittest.main()
