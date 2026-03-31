from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AccountType(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.CharField(  # cash / mobile / bank
        max_length=20
    )
    name = models.CharField(max_length=100)  # Nome do tipo de conta
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "sl_account_types"

    def __str__(self):
        return f"{self.get_category_display()} · {self.name}"

    def get_category_display(self):
        mapping = {
            "cash": _("Cash"),
            "mobile": _("Carteira móvel"),
            "bank": _("Conta bancária"),
        }
        return mapping.get(self.category, self.category)
