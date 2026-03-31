from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .loan import Loan
from .member import Member
from .companyaccount import CompanyAccount


class LoanRepayment(models.Model):
    METHOD_CHOICES = (
        ("cash", _("Cash")),
        ("bank", _("Conta bancária")),
        ("mobile", _("Carteira móvel")),
    )

    id = models.BigAutoField(primary_key=True)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="repayments",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="loan_repayments",
    )
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.PROTECT,
        related_name="loan_repayments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    principal_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    attachment = models.FileField(
        upload_to="loan_repayments/%Y/%m/",
        null=True,
        blank=True,
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "sl_loan_repayments"

    def __str__(self):
        return f"Reembolso #{self.id} · Loan {self.loan_id}"
