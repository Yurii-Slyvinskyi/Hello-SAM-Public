from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("maintenance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancerequest",
            name="full_name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="maintenancerequest",
            name="issue_type",
            field=models.CharField(
                choices=[
                    ("plumbing", "Plumbing"),
                    ("water_leak", "Water Leak"),
                    ("drain_clog", "Drain / Clog"),
                    ("toilet", "Toilet"),
                    ("electrical", "Electrical"),
                    ("power_outage", "Power Outage"),
                    ("lighting", "Lighting"),
                    ("heating_cooling", "Heating / Cooling"),
                    ("no_heat", "No Heat"),
                    ("air_conditioning", "Air Conditioning"),
                    ("ventilation", "Ventilation"),
                    ("appliance", "Appliance"),
                    ("refrigerator", "Refrigerator"),
                    ("stove_oven", "Stove / Oven"),
                    ("dishwasher", "Dishwasher"),
                    ("washer_dryer", "Washer / Dryer"),
                    ("door_lock", "Door / Lock"),
                    ("window", "Window"),
                    ("garage_parking", "Garage / Parking"),
                    ("pest", "Pest"),
                    ("noise_security", "Noise / Security"),
                    ("safety_hazard", "Safety Hazard"),
                    ("elevator", "Elevator"),
                    ("common_area", "Common Area"),
                    ("exterior", "Exterior"),
                    ("trash_recycling", "Trash / Recycling"),
                    ("flooring", "Flooring"),
                    ("walls_ceiling", "Walls / Ceiling"),
                    ("cabinets_counters", "Cabinets / Counters"),
                    ("general_maintenance", "General Maintenance"),
                    ("other", "Other"),
                ],
                max_length=64,
            ),
        ),
    ]
