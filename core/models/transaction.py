# core/models/transaction.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .companyaccount import CompanyAccount


class Transaction(models.Model):
    TX_TYPE_IN = "IN"
    TX_TYPE_OUT = "OUT"
    TX_TYPE_CHOICES = (
        (TX_TYPE_IN, _("Entrada")),
        (TX_TYPE_OUT, _("Saída")),
    )

    id = models.BigAutoField(primary_key=True)
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    tx_type = models.CharField(max_length=3, choices=TX_TYPE_CHOICES)
    source_type = models.CharField(
        max_length=30,     # aumentei um pouco para caber tranquilo
        blank=True,
        null=True,
        help_text=_("Origem: income, expense, loan_repayment, loan_disbursement, etc."),
    )
    source_id = models.BigIntegerField(blank=True, null=True)
    tx_date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    # NOVO: utilizador que criou o registo
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "sl_transactions"

    def __str__(self):
        return f"{self.tx_date} · {self.company_account.name} · {self.tx_type} {self.amount}"
