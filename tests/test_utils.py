from decimal import Decimal
import unittest

from app.utils import format_datetime_ru, money_to_str, now_iso, percent_of, to_decimal


class UtilsTests(unittest.TestCase):
    def test_to_decimal_uses_half_up_rounding(self) -> None:
        self.assertEqual(to_decimal("1.005"), Decimal("1.01"))
        self.assertEqual(to_decimal("1.004"), Decimal("1.00"))

    def test_money_to_str_formats_two_decimals(self) -> None:
        self.assertEqual(money_to_str("2"), "2.00")
        self.assertEqual(money_to_str(Decimal("2.456")), "2.46")

    def test_now_iso_has_seconds_precision(self) -> None:
        ts = now_iso()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    def test_format_datetime_ru_formats_iso_and_preserves_invalid(self) -> None:
        self.assertEqual(format_datetime_ru("2026-02-23T12:34:56"), "23.02.2026 12:34:56")
        self.assertEqual(format_datetime_ru("not-a-date"), "not-a-date")

    def test_percent_of_handles_zero_and_rounding(self) -> None:
        self.assertEqual(percent_of(Decimal("10"), Decimal("0")), Decimal("0.00"))
        self.assertEqual(percent_of(Decimal("1"), Decimal("3")), Decimal("33.33"))


if __name__ == "__main__":
    unittest.main()
