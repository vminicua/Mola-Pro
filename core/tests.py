from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from core.loan_installment_schedule import (
    allocate_amount_to_installments,
    build_loan_installment_schedule,
)
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.branding import (
    USER_CURRENCY_FORMAT_SESSION_KEY,
    USER_LANGUAGE_SESSION_KEY,
    load_brand_preferences,
    reset_active_brand_preferences,
    save_brand_preferences,
    set_active_brand_preferences,
)
from core.loan_repayment_logic import RepaymentAllocationError, add_period, allocate_repayment
from core.templatetags.core_i18n import format_money_value
from core.views.preferences_view import update_user_currency_format, update_user_language


class DummyAuthenticatedUser:
    is_authenticated = True


class BrandPalettePreferenceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.media_root = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name, MEDIA_URL="/media/")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media_root.cleanup)
        self.request_factory = RequestFactory()

    def _preferences_path(self) -> Path:
        return Path(self.media_root.name) / "preferences" / "branding.json"

    def _write_preferences(self, data: dict[str, str]) -> None:
        preferences_path = self._preferences_path()
        preferences_path.parent.mkdir(parents=True, exist_ok=True)
        preferences_path.write_text(json.dumps(data), encoding="utf-8")

    def test_load_brand_preferences_maps_legacy_primary_color_to_matching_palette(self) -> None:
        self._write_preferences(
            {
                "language": "en",
                "primary_color": "#42A5F5",
            }
        )

        preferences = load_brand_preferences()

        self.assertEqual(preferences["palette_key"], "ocean")
        self.assertEqual(preferences["primary_color"], "#42A5F5")
        self.assertEqual(preferences["palette"]["label"], "Atlantic Blue")

    def test_save_brand_preferences_persists_palette_key_and_primary_color(self) -> None:
        preferences = save_brand_preferences(
            palette_key="graphite",
            language="en",
            currency_format="intl",
        )
        stored_preferences = json.loads(self._preferences_path().read_text(encoding="utf-8"))

        self.assertEqual(preferences["palette_key"], "graphite")
        self.assertEqual(preferences["primary_color"], "#334155")
        self.assertEqual(preferences["default_currency_format"], "intl")
        self.assertEqual(stored_preferences["palette_key"], "graphite")
        self.assertEqual(stored_preferences["primary_color"], "#334155")
        self.assertEqual(stored_preferences["currency_format"], "intl")
        self.assertEqual(stored_preferences["language"], "en")

    def test_save_brand_preferences_rejects_unknown_palette(self) -> None:
        with self.assertRaisesMessage(ValueError, "Paleta inválida"):
            save_brand_preferences(palette_key="unknown-palette")

    def test_load_brand_preferences_supports_session_language_override(self) -> None:
        self._write_preferences(
            {
                "currency_format": "mz",
                "language": "pt-mz",
                "palette_key": "emerald",
            }
        )

        preferences = load_brand_preferences(language_override="en")

        self.assertEqual(preferences["language"], "en")
        self.assertEqual(preferences["default_language"], "pt-mz")
        self.assertTrue(preferences["is_language_overridden"])
        self.assertEqual(preferences["palette"]["label"], "Mola Green")

    def test_load_brand_preferences_defaults_to_mozambique_currency_format(self) -> None:
        preferences = load_brand_preferences()

        self.assertEqual(preferences["currency_format"], "mz")
        self.assertEqual(preferences["default_currency_format"], "mz")
        self.assertEqual(preferences["currency_example"], "100.000,00")

    def test_load_brand_preferences_supports_session_currency_override(self) -> None:
        self._write_preferences(
            {
                "currency_format": "mz",
                "language": "en",
                "palette_key": "emerald",
            }
        )

        preferences = load_brand_preferences(currency_format_override="intl")

        self.assertEqual(preferences["currency_format"], "intl")
        self.assertEqual(preferences["default_currency_format"], "mz")
        self.assertTrue(preferences["is_currency_format_overridden"])
        self.assertEqual(preferences["currency_thousands_separator"], ",")
        self.assertEqual(preferences["currency_decimal_separator"], ".")

    def test_format_money_value_uses_active_currency_format(self) -> None:
        preferences = load_brand_preferences(currency_format_override="intl")
        token = set_active_brand_preferences(preferences)
        self.addCleanup(reset_active_brand_preferences, token)

        self.assertEqual(format_money_value("100000.00"), "100,000.00")

    def test_update_user_language_stores_session_override(self) -> None:
        request = self.request_factory.post("/preferences/language/update/", {"language": "en"})
        SessionMiddleware(lambda _: None).process_request(request)
        request.user = DummyAuthenticatedUser()

        response = update_user_language(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session[USER_LANGUAGE_SESSION_KEY], "en")
        self.assertEqual(payload["language"], "en")

    def test_update_user_currency_format_stores_session_override(self) -> None:
        request = self.request_factory.post(
            "/preferences/currency-format/update/",
            {"currency_format": "intl"},
        )
        SessionMiddleware(lambda _: None).process_request(request)
        request.user = DummyAuthenticatedUser()

        response = update_user_currency_format(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session[USER_CURRENCY_FORMAT_SESSION_KEY], "intl")
        self.assertEqual(payload["currency_format"], "intl")


class LoanRepaymentLogicTests(SimpleTestCase):
    def test_add_period_uses_the_loan_period_type(self) -> None:
        self.assertEqual(add_period(date(2026, 1, 31), "monthly"), date(2026, 2, 28))
        self.assertEqual(add_period(date(2026, 4, 3), "daily"), date(2026, 4, 4))

    def test_partial_repayment_splits_interest_then_principal(self) -> None:
        allocation = allocate_repayment(
            amount=Decimal("80.00"),
            interest_remaining=Decimal("30.00"),
            outstanding_principal=Decimal("200.00"),
            repayment_type="partial",
        )

        self.assertEqual(allocation.interest_amount, Decimal("30.00"))
        self.assertEqual(allocation.principal_amount, Decimal("50.00"))
        self.assertEqual(allocation.principal_balance_after, Decimal("150.00"))

    def test_partial_repayment_requires_a_real_principal_reduction(self) -> None:
        with self.assertRaises(RepaymentAllocationError) as context:
            allocate_repayment(
                amount=Decimal("30.00"),
                interest_remaining=Decimal("30.00"),
                outstanding_principal=Decimal("200.00"),
                repayment_type="partial",
            )

        self.assertEqual(context.exception.code, "partial_must_reduce_principal")

    def test_partial_repayment_rejects_values_that_close_the_loan(self) -> None:
        with self.assertRaises(RepaymentAllocationError) as context:
            allocate_repayment(
                amount=Decimal("230.00"),
                interest_remaining=Decimal("30.00"),
                outstanding_principal=Decimal("200.00"),
                repayment_type="partial",
            )

        self.assertEqual(context.exception.code, "partial_must_be_less_than_total_due")

    def test_full_repayment_closes_the_loan(self) -> None:
        allocation = allocate_repayment(
            amount=Decimal("230.00"),
            interest_remaining=Decimal("30.00"),
            outstanding_principal=Decimal("200.00"),
            repayment_type="full",
        )

        self.assertEqual(allocation.interest_amount, Decimal("30.00"))
        self.assertEqual(allocation.principal_amount, Decimal("200.00"))
        self.assertEqual(allocation.principal_balance_after, Decimal("0.00"))


class LoanInstallmentScheduleTests(SimpleTestCase):
    def _build_loan(self):
        return SimpleNamespace(
            principal_amount=Decimal("100000.00"),
            term_periods=3,
            period_type="monthly",
            payment_per_period=None,
            first_payment_date=date(2026, 5, 3),
            release_date=date(2026, 4, 3),
            interest_type=SimpleNamespace(rate=Decimal("30.00")),
        )

    def test_schedule_exposes_all_installments_and_locks_future_rows(self) -> None:
        _, rows, summary = build_loan_installment_schedule(self._build_loan(), [])

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["due_date"], date(2026, 5, 3))
        self.assertEqual(rows[1]["due_date"], date(2026, 6, 3))
        self.assertEqual(rows[2]["due_date"], date(2026, 7, 3))
        self.assertEqual(rows[0]["expected_payment"], Decimal("63333.33"))
        self.assertEqual(rows[1]["expected_payment"], Decimal("63333.33"))
        self.assertEqual(rows[2]["expected_payment"], Decimal("63333.34"))
        self.assertEqual(rows[0]["status"], "current")
        self.assertEqual(rows[1]["status"], "locked")
        self.assertEqual(rows[2]["status"], "locked")
        self.assertEqual(summary["remaining_total"], Decimal("190000.00"))
        self.assertEqual(summary["remaining_principal"], Decimal("100000.00"))
        self.assertEqual(summary["active_installment"]["installment_number"], 1)

    def test_underpayment_keeps_same_installment_active_and_future_rows_locked(self) -> None:
        repayments = [
            {
                "id": 1,
                "payment_date": date(2026, 5, 3),
                "amount": Decimal("50000.00"),
            }
        ]

        _, rows, summary = build_loan_installment_schedule(self._build_loan(), repayments)

        self.assertEqual(rows[0]["status"], "partial")
        self.assertEqual(rows[0]["paid_interest"], Decimal("30000.00"))
        self.assertEqual(rows[0]["paid_principal"], Decimal("20000.00"))
        self.assertEqual(rows[0]["remaining_total"], Decimal("13333.33"))
        self.assertEqual(rows[0]["remaining_principal_component"], Decimal("13333.33"))
        self.assertEqual(rows[1]["status"], "locked")
        self.assertEqual(rows[2]["status"], "locked")
        self.assertEqual(summary["active_installment"]["installment_number"], 1)
        self.assertEqual(summary["remaining_total"], Decimal("140000.00"))
        self.assertEqual(summary["remaining_principal"], Decimal("80000.00"))

    def test_overpayment_flows_into_next_installment(self) -> None:
        repayments = [
            {
                "id": 1,
                "payment_date": date(2026, 5, 3),
                "amount": Decimal("70000.00"),
            }
        ]

        _, rows, summary = build_loan_installment_schedule(self._build_loan(), repayments)

        self.assertEqual(rows[0]["status"], "paid")
        self.assertEqual(rows[1]["status"], "partial")
        self.assertEqual(rows[1]["paid_total"], Decimal("6666.67"))
        self.assertEqual(rows[1]["paid_interest"], Decimal("6666.67"))
        self.assertEqual(rows[1]["remaining_interest"], Decimal("23333.33"))
        self.assertEqual(rows[1]["remaining_total"], Decimal("56666.66"))
        self.assertEqual(rows[2]["status"], "locked")
        self.assertEqual(summary["active_installment"]["installment_number"], 2)
        self.assertEqual(summary["remaining_total"], Decimal("120000.00"))
        self.assertEqual(summary["remaining_principal"], Decimal("66666.67"))

    def test_allocate_amount_to_installments_distributes_in_sequence(self) -> None:
        _, rows, _ = build_loan_installment_schedule(self._build_loan(), [])

        allocation = allocate_amount_to_installments(rows, Decimal("70000.00"))

        self.assertEqual(allocation["interest_amount"], Decimal("36666.67"))
        self.assertEqual(allocation["principal_amount"], Decimal("33333.33"))
        self.assertEqual(allocation["total_applied"], Decimal("70000.00"))
        self.assertEqual(allocation["unallocated_amount"], Decimal("0.00"))
        self.assertEqual(allocation["touched_installments"], [1, 2])
