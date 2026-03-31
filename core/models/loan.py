from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .member import Member
from .loantype import LoanType
from .interesttype import InterestType
from .companyaccount import CompanyAccount

class Loan(models.Model):
    STATUS_CHOICES = (
        ("pending", _("Pendente")),
        ("approved", _("Aprovado")),
        ("disbursed", _("Desembolsado")),
        ("closed", _("Fechado")),
        ("cancelled", _("Cancelado")),
    )

    PERIOD_TYPE_CHOICES = (
        ("monthly", _("Mensal")),
        ("daily", _("Diário")),
    )

    DISBURSE_METHOD_CHOICES = (
        ("cash", _("Cash")),
        ("company_account", _("Conta da Empresa")),
        ("mobile_wallet", _("Carteira Móvel")),
    )

    id = models.BigAutoField(primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    loan_type = models.ForeignKey(
        LoanType, on_delete=models.PROTECT, related_name="loans", null=True, blank=True
    )
    interest_type = models.ForeignKey(
        InterestType, on_delete=models.PROTECT, related_name="loans"
    )

    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    term_periods = models.PositiveIntegerField()  # nº de meses ou dias
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, default="monthly")

    payment_per_period = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    release_date = models.DateField(null=True, blank=True)
    first_payment_date = models.DateField(null=True, blank=True)

    disburse_method = models.CharField(
        max_length=20, choices=DISBURSE_METHOD_CHOICES, default="cash"
    )
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.PROTECT,
        related_name="disbursed_loans",
        null=True,
        blank=True,
    )

    purpose = models.CharField(max_length=255, null=True, blank=True)
    attachment = models.FileField(upload_to="loans/%Y/%m/", null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_loans",
        null=True,
        blank=True,
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_loans",
        null=True,
        blank=True,
    )


    class Meta:
        managed = False
        db_table = "sl_loans"

    def __str__(self):
        return f"Loan #{self.id} · {self.member}"
