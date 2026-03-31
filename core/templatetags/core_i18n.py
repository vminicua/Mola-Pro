from django import template
from django.utils.translation import gettext as _


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
