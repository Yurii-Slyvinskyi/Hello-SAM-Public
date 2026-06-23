import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Building",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("address", models.TextField()),
                (
                    "maintenance_phone_number",
                    models.CharField(max_length=32, unique=True),
                ),
                ("office_phone_number", models.CharField(max_length=32)),
                ("manager_email", models.EmailField(max_length=254)),
                ("manager_phone", models.CharField(max_length=32)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="buildings",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
