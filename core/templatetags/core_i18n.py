from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template
from django.utils.translation import gettext as _

from core.branding import get_active_brand_preferences


register = template.Library()

SEGMENT_LABELS = {
    "dashboard": _("Dashboard"),
    "members_list": _("Clientes"),
    "member_add": _("Adicionar Membros"),
    "loans_new": _("Novo Empréstimo"),
    "loans_active": _("Empréstimos Activos"),
    "loans_pending": _("Empréstimos Pendentes"),
    "loans_all": _("Todos os Empréstimos"),
    "loan_disbursements": _("Desembolso"),
    "loan_repayments": _("Reembolso"),
    "client_accounts": _("Conta dos Clientes"),
    "company_accounts": _("Conta da Empresa"),
    "interest_calculator": _("Cálculo de Juros"),
    "transactions": _("Transacções"),
    "expenses": _("Despesas"),
    "expense_categories": _("Categoria de Despesas"),
    "incomes": _("Rendimentos"),
    "income_categories": _("Categoria de Rendimentos"),
    "users": _("Utilizadores"),
    "user_permissions": _("Permissões"),
    "account_types": _("Tipos de Contas"),
    "loan_types": _("Tipos de Empréstimos"),
    "interest_types": _("Tipos de Juros"),
    "preferences": _("Preferências"),
    "reports": _("Relatórios"),
}


@register.filter
def segment_label(segment):
    if not segment:
        return SEGMENT_LABELS["dashboard"]

    normalized = str(segment).strip().lower()
    if normalized in SEGMENT_LABELS:
        return SEGMENT_LABELS[normalized]

    return str(segment).replace("_", " ").title()


def _coerce_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _group_digits(value: str, thousands_separator: str) -> str:
    digits = value
    parts: list[str] = []

    while digits:
        parts.append(digits[-3:])
        digits = digits[:-3]

    return thousands_separator.join(reversed(parts)) if parts else "0"


def format_money_value(
    value,
    *,
    include_symbol: bool = False,
    empty_value: str = "",
) -> str:
    decimal_value = _coerce_decimal(value)
    if decimal_value is None:
        return empty_value

    preferences = get_active_brand_preferences()
    decimal_separator = preferences["currency_decimal_separator"]
    thousands_separator = preferences["currency_thousands_separator"]
    currency_symbol = preferences["currency_symbol"]
    symbol_spacing = preferences["currency_symbol_spacing"]

    normalized_value = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if normalized_value < 0 else ""
    absolute_value = abs(normalized_value)
    whole_part, fractional_part = f"{absolute_value:.2f}".split(".")
    grouped_whole_part = _group_digits(whole_part, thousands_separator)
    formatted_value = f"{sign}{grouped_whole_part}{decimal_separator}{fractional_part}"

    if include_symbol:
        return f"{currency_symbol}{symbol_spacing}{formatted_value}"

    return formatted_value


@register.filter
def money(value):
    return format_money_value(value)


@register.filter
def money_with_symbol(value):
    return format_money_value(value, include_symbol=True)
