from django.conf import settings
from django.db import models

from .loan import Loan


class LoanDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    name = models.CharField(max_length=180)
    document_type = models.CharField(max_length=80, null=True, blank=True)
    file = models.FileField(upload_to="loan_documents/%Y/%m/", max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_loan_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "sl_loan_documents"

    def __str__(self):
        return f"{self.name} · Empréstimo {self.loan_id}"
