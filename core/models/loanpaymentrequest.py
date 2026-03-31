from django.db import models
from django.utils.translation import gettext_lazy as _
from .loan import Loan
from .member import Member
from .companyaccount import CompanyAccount

class LoanPaymentRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", _("Pendente")),
        ("paid", _("Pago")),
        ("cancelled", _("Cancelado")),
    )

    id = models.BigAutoField(primary_key=True)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="payment_requests",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="loan_payment_requests",
    )
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loan_payment_requests",
    )
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    attachment = models.FileField(
        upload_to="loan_payments/%Y/%m/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "sl_loan_payment_requests"

    def __str__(self):
        return f"LoanPayment #{self.id} · Loan {self.loan_id}"
