import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("buildings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallLog",
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
                ("call_id", models.CharField(db_index=True, max_length=255)),
                ("called_number", models.CharField(max_length=32)),
                ("caller_phone", models.CharField(max_length=32)),
                ("transcript", models.TextField(blank=True)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="call_logs",
                        to="buildings.building",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
