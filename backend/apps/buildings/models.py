from django.db import models

from apps.common.validators import validate_e164_phone_number


class Building(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        related_name="buildings",
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    maintenance_phone_number = models.CharField(
        max_length=32,
        unique=True,
        validators=[validate_e164_phone_number],
    )
    office_phone_number = models.CharField(
        max_length=32,
        validators=[validate_e164_phone_number],
    )
    manager_email = models.EmailField()
    manager_phone = models.CharField(
        max_length=32,
        validators=[validate_e164_phone_number],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
