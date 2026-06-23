from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationlog",
            name="purpose",
            field=models.CharField(
                blank=True,
                choices=[
                    ("manager_email", "Manager email"),
                    ("manager_sms", "Manager SMS"),
                    ("resident_sms", "Resident SMS"),
                ],
                default="",
                max_length=32,
            ),
        ),
    ]
