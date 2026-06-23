from django.db import models


class IssueType(models.TextChoices):
    PLUMBING = "plumbing", "Plumbing"
    WATER_LEAK = "water_leak", "Water Leak"
    DRAIN_CLOG = "drain_clog", "Drain / Clog"
    TOILET = "toilet", "Toilet"

    ELECTRICAL = "electrical", "Electrical"
    POWER_OUTAGE = "power_outage", "Power Outage"
    LIGHTING = "lighting", "Lighting"

    HEATING_COOLING = "heating_cooling", "Heating / Cooling"
    NO_HEAT = "no_heat", "No Heat"
    AIR_CONDITIONING = "air_conditioning", "Air Conditioning"
    VENTILATION = "ventilation", "Ventilation"

    APPLIANCE = "appliance", "Appliance"
    REFRIGERATOR = "refrigerator", "Refrigerator"
    STOVE_OVEN = "stove_oven", "Stove / Oven"
    DISHWASHER = "dishwasher", "Dishwasher"
    WASHER_DRYER = "washer_dryer", "Washer / Dryer"

    DOOR_LOCK = "door_lock", "Door / Lock"
    WINDOW = "window", "Window"
    GARAGE_PARKING = "garage_parking", "Garage / Parking"

    PEST = "pest", "Pest"

    NOISE_SECURITY = "noise_security", "Noise / Security"
    SAFETY_HAZARD = "safety_hazard", "Safety Hazard"

    COMMON_AREA = "common_area", "Common Area"
    EXTERIOR = "exterior", "Exterior"

    FLOORING = "flooring", "Flooring"
    WALLS_CEILING = "walls_ceiling", "Walls / Ceiling"

    GENERAL_MAINTENANCE = "general_maintenance", "General Maintenance"
    OTHER = "other", "Other"


class Priority(models.TextChoices):
    NORMAL = "normal", "Normal"
    URGENT = "urgent", "Urgent"
    EMERGENCY = "emergency", "Emergency"
