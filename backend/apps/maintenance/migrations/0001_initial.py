import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("buildings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceRequest",
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
                ("call_id", models.CharField(max_length=255, unique=True)),
                ("caller_phone", models.CharField(max_length=32)),
                ("follow_up_phone", models.CharField(blank=True, max_length=32)),
                (
                    "use_caller_phone_for_follow_up",
                    models.BooleanField(default=True),
                ),
                ("unit_number", models.CharField(max_length=64)),
                (
                    "issue_type",
                    models.CharField(
                        choices=[
                            ("plumbing", "Plumbing"),
                            ("electrical", "Electrical"),
                            ("heating_cooling", "Heating/Cooling"),
                            ("appliance", "Appliance"),
                            ("door_lock", "Door/Lock"),
                            ("pest", "Pest"),
                            ("noise_security", "Noise/Security"),
                            ("general_maintenance", "General Maintenance"),
                            ("other", "Other"),
                        ],
                        max_length=64,
                    ),
                ),
                ("resident_reported_issue", models.TextField()),
                ("description", models.TextField()),
                ("location_inside_unit", models.CharField(max_length=255)),
                (
                    "ai_priority",
                    models.CharField(
                        choices=[
                            ("normal", "Normal"),
                            ("urgent", "Urgent"),
                            ("emergency", "Emergency"),
                        ],
                        default="normal",
                        max_length=16,
                    ),
                ),
                (
                    "backend_priority",
                    models.CharField(
                        choices=[
                            ("normal", "Normal"),
                            ("urgent", "Urgent"),
                            ("emergency", "Emergency"),
                        ],
                        default="normal",
                        max_length=16,
                    ),
                ),
                (
                    "final_priority",
                    models.CharField(
                        choices=[
                            ("normal", "Normal"),
                            ("urgent", "Urgent"),
                            ("emergency", "Emergency"),
                        ],
                        default="normal",
                        max_length=16,
                    ),
                ),
                ("is_emergency", models.BooleanField(default=False)),
                ("emergency_reason", models.TextField(blank=True)),
                ("transcript", models.TextField()),
                ("status", models.CharField(default="new", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="maintenance_requests",
                        to="buildings.building",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
