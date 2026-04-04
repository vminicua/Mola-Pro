from django.db import models
from django.utils.translation import gettext_lazy as _


class LateInterestSetting(models.Model):
    PERIOD_MONTHLY = "monthly"
    PERIOD_DAILY = "daily"

    PERIOD_CHOICES = (
        (PERIOD_MONTHLY, _("Mensal")),
        (PERIOD_DAILY, _("Diário")),
    )

    id = models.BigAutoField(primary_key=True)
    period_type = models.CharField(max_length=10, unique=True)
    rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "sl_late_interest_settings"

    def __str__(self):
        return f"Juros de mora {self.get_period_type_display()}"

    def get_period_type_display(self):
        mapping = {
            self.PERIOD_MONTHLY: _("Mensal"),
            self.PERIOD_DAILY: _("Diário"),
        }
        return mapping.get(self.period_type, self.period_type)
