from django.db import models
from django.utils.translation import gettext_lazy as _
from .loan import Loan
from .member import Member
from .companyaccount import CompanyAccount


class LoanDisbursement(models.Model):
    METHOD_CHOICES = (
        ("cash", _("Cash")),
        ("bank", _("Conta bancária")),
        ("mobile", _("Carteira móvel")),
    )

    id = models.BigAutoField(primary_key=True)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="disbursements",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="loan_disbursements",
    )
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.PROTECT,
        related_name="loan_disbursements",
    )
    disburse_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    method = models.CharField(max_length=20, default="cash")
    attachment = models.FileField(
        upload_to="loan_disbursements/%Y/%m/",
        null=True,
        blank=True,
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "sl_loan_disbursements"

    def __str__(self):
        return f"Desembolso #{self.id} · Empréstimo {self.loan_id}"
