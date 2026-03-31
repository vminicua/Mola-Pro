from django.db import models
from .member import Member
from .accounttype import AccountType

class CompanyAccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        related_name="company_accounts",
    )
    name = models.CharField(max_length=150)  # Ex: "Conta BCI MZN - Mola Pro"
    account_identifier = models.CharField(max_length=100)  # nº conta / celular / NIB
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "sl_company_accounts"
