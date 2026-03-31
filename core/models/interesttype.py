from django.db import models
from django.utils.translation import gettext_lazy as _

class InterestType(models.Model):
    PERIOD_MONTHLY = "monthly"
    PERIOD_DAILY = "daily"

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)              # Ex: Juros Mensais 3%
    description = models.CharField(max_length=255, blank=True, null=True)
    rate = models.DecimalField(max_digits=7, decimal_places=4)  # Ex: 3.0000 (% por período)
    period_type = models.CharField(                      # monthly / daily
        max_length=10
    )
    calculation_method = models.CharField(               # flat / (futuro: reducing, etc.)
        max_length=20,
        default="flat",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "sl_interest_types"

    def __str__(self):
        return self.name

    def get_period_type_display(self):
        mapping = {
            "monthly": _("Mensal"),
            "daily": _("Diário"),
        }
        return mapping.get(self.period_type, self.period_type)
