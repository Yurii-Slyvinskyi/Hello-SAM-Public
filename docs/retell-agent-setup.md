# Retell Integration Setup - Hello SAM

This document explains how Hello SAM connects Retell to the Django backend: voice agent setup, tools, phone number routing, inbound webhook context, transfer behavior, and Django building records.

> Public documentation rule: keep fake URLs, phone numbers, emails, and tokens in this file. Replace placeholders with real values only inside private Retell, Render, Postmark, Twilio, and Django Admin environments.
>
> The production SAM conversation prompt is intentionally not included in this public repository. It contains business-specific conversation rules and operational tuning. This document only describes the integration contract between Retell and the backend.

---

## 1. Create the Retell Voice Agent

In the Retell dashboard:

1. Open **Agents**.
2. Click **Create Agent**.
3. Select:
   - **Agent type:** Voice Agent
   - **Prompt mode:** Single prompt
   - **Template:** None
   - **Voice:** Leland
4. Name the agent:

```text
Hello SAM
```

5. Open the agent prompt editor.
6. Add the private SAM conversation prompt from your secure internal source.
7. Save the agent.

---

## 2. Configure Speech Settings

Open the Hello SAM agent and go to **Speech Settings**.

Set:

| Setting | Value |
|---|---|
| Background Sound | None |
| Response Eagerness | 1 |
| Dynamically adjust based on user input | Enabled |
| Interruption Sensitivity | 0.5 |
| Reminder Message Frequency | 6 seconds |
| Maximum Reminder Messages | 1 time |
| Pronunciation | Leave empty initially; add entries only if testing shows a building name or term is pronounced incorrectly |

These values keep SAM patient, allow residents to interrupt naturally, and avoid repeated reminder messages during pauses.

---

## 3. Configure the Private SAM Prompt

Use Retell's **Single Prompt** field for the SAM conversation prompt.

The public repository does not include the full production prompt. At a high level, the prompt should instruct SAM to:

- speak naturally, not like an IVR;
- ask one question at a time;
- collect the resident's full name, unit number, issue, location, follow-up preference, and urgency;
- use the backend's allowed `issue_type` and `ai_priority` values;
- call `create_maintenance_request` only after the request is complete;
- use `transfer_call` when the resident asks for a human;
- trust the backend response after submission.

The backend remains the source of truth for validation, building lookup, priority verification, idempotency, and notification delivery.

---

## 4. Add the Custom Function: `create_maintenance_request`

In the Hello SAM agent:

1. Open **Tools** or **Functions**.
2. Click **Add Tool** / **Add Function**.
3. Select **Custom Function**.
4. Configure it as follows.

### Name

```text
create_maintenance_request
```

### Description

```text
Create a maintenance request after collecting the resident's full name, unit number, issue, location, follow-up phone preference, and urgency. Call this only once when enough reliable information has been collected.
```

### API Endpoint

```text
POST https://hello-sam-demo.example.com/api/voice/maintenance-requests/
```

Replace the fake domain only inside your private Retell configuration.

### Timeout

```text
10000
```

### Headers

```text
X-Voice-Agent-Token: <VOICE_AGENT_TOKEN>
Content-Type: application/json
```

### Parameters JSON Schema

```json
{
  "type": "object",
  "required": [
    "call_id",
    "called_number",
    "caller_phone",
    "full_name",
    "unit_number",
    "use_caller_phone_for_follow_up",
    "follow_up_phone",
    "issue_type",
    "resident_reported_issue",
    "description",
    "location_inside_unit",
    "ai_priority",
    "transcript"
  ],
  "properties": {
    "call_id": {
      "type": "string",
      "const": "{{call_id}}"
    },
    "called_number": {
      "type": "string",
      "const": "{{agent_number}}"
    },
    "caller_phone": {
      "type": "string",
      "const": "{{user_number}}"
    },
    "full_name": {
      "type": "string"
    },
    "unit_number": {
      "type": "string"
    },
    "use_caller_phone_for_follow_up": {
      "type": "boolean"
    },
    "follow_up_phone": {
      "type": "string"
    },
    "issue_type": {
      "type": "string",
      "enum": [
        "plumbing",
        "water_leak",
        "drain_clog",
        "toilet",
        "electrical",
        "power_outage",
        "lighting",
        "heating_cooling",
        "no_heat",
        "air_conditioning",
        "ventilation",
        "appliance",
        "refrigerator",
        "stove_oven",
        "dishwasher",
        "washer_dryer",
        "door_lock",
        "window",
        "garage_parking",
        "pest",
        "noise_security",
        "safety_hazard",
        "common_area",
        "exterior",
        "flooring",
        "walls_ceiling",
        "general_maintenance",
        "other"
      ]
    },
    "resident_reported_issue": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "location_inside_unit": {
      "type": "string"
    },
    "ai_priority": {
      "type": "string",
      "enum": [
        "normal",
        "urgent",
        "emergency"
      ]
    },
    "transcript": {
      "type": "string"
    }
  }
}
```

### Important Validation Rules

- `call_id` must be `{{call_id}}`.
- `called_number` must be `{{agent_number}}`.
- `caller_phone` must be `{{user_number}}`.
- `called_number` must match `Building.maintenance_phone_number` in Django Admin.
- `full_name` is required.
- The backend normalizes `follow_up_phone = caller_phone` when `use_caller_phone_for_follow_up` is `true`.
- Phone numbers in the production flow must use E.164 format.

---

## 5. Add the Transfer Tool: `transfer_call`

In the Hello SAM agent:

1. Open **Tools**.
2. Click **Add Tool**.
3. Select **Transfer Call**.
4. Configure the transfer settings.

### Name

```text
transfer_call
```

### When to Use It

```text
Use this when the resident asks for a human, office, manager, representative, or says they do not want to speak with AI.
```

### Agent Phrase Before Transfer

```text
Sure, I'll transfer you to the office now.
```

### Transfer Settings

| Setting | Value |
|---|---|
| Transfer to | Dynamic Routing |
| Destination | `{{office_phone_number}}` |
| Format | E.164 |
| Transfer behavior | Cold Transfer |
| Displayed Caller ID | Retell Agent's Number |
| Transfer Ring Duration | 20 seconds |

### Transfer Failure Message

```text
I couldn't reach the office right now. I can still create a maintenance request for you, or you can contact the office directly later.
```

### Important

- `{{office_phone_number}}` comes from the Django inbound webhook response.
- It must be a complete E.164 phone number, for example `+12025550103`.
- A value such as `+1` is not valid.

---

## 6. Configure the Retell Phone Number and Inbound Webhook

For each building-specific Retell phone number:

1. Open **Phone Numbers** in Retell.
2. Select the phone number assigned to the building.
3. Set:

| Setting | Value |
|---|---|
| Inbound Call Agent | Hello SAM / Latest |
| Inbound Webhook URL | `https://hello-sam-demo.example.com/api/voice/retell/inbound-call/` |

Replace the fake domain only inside your private Retell configuration.

The inbound webhook runs before the call begins so the backend can identify the building and send building-specific dynamic variables.

### Security

The inbound webhook and the Custom Function use different security mechanisms:

| Request | Security |
|---|---|
| Retell inbound webhook | Retell sends `X-Retell-Signature`; Django verifies it using `RETELL_API_KEY` |
| `create_maintenance_request` Custom Function | Retell sends `X-Voice-Agent-Token`; Django verifies it using `VOICE_AGENT_TOKEN` |

Do not configure `X-Voice-Agent-Token` as the inbound webhook verification mechanism.

### Example Inbound Webhook Request

```json
{
  "event": "call_inbound",
  "call_inbound": {
    "agent_id": "agent_demo",
    "agent_version": 1,
    "from_number": "+12025550101",
    "to_number": "+12025550104"
  }
}
```

The backend resolves:

```text
call_inbound.to_number -> Building.maintenance_phone_number
```

### Example Backend Response

```json
{
  "call_inbound": {
    "dynamic_variables": {
      "office_phone_number": "+12025550103",
      "building_name": "Maple Grove Apartments"
    },
    "metadata": {
      "building_id": "1"
    }
  }
}
```

---

## 7. Configure Each Building in Django Admin

For each building, configure:

| Field | Purpose |
|---|---|
| `maintenance_phone_number` | The Retell number residents call for maintenance |
| `office_phone_number` | The number used when SAM transfers a resident to a person |
| `manager_email` | Recipient of manager email notifications |
| `manager_phone` | Recipient of manager SMS notifications |
| `is_active` | Must be `true` for an active building |

### Public Example

```text
Building: Maple Grove Apartments
Maintenance phone number: +12025550104
Office phone number: +12025550103
Manager email: manager@example.com
Manager phone: +12025550102
Is active: true
```

---

## 8. Configure Backend Environment Variables

Inside the private backend web service environment, configure:

```env
VOICE_AGENT_TOKEN=<secret_for_create_maintenance_request>
RETELL_API_KEY=<retell_api_key_for_inbound_webhook_signature_verification>
```

| Variable | Used For |
|---|---|
| `VOICE_AGENT_TOKEN` | Authentication of the `create_maintenance_request` Custom Function request |
| `RETELL_API_KEY` | Verification of the Retell inbound webhook signature |

Never commit real values to GitHub.

---

## 9. End-to-End Flow

1. A resident calls the building-specific Retell maintenance number.
2. Retell sends the inbound webhook to Django.
3. Django verifies `X-Retell-Signature`.
4. Django identifies the building by `call_inbound.to_number`.
5. Django returns `office_phone_number` and `building_name` as dynamic variables.
6. SAM speaks naturally with the resident and collects a complete maintenance request.
7. SAM calls `create_maintenance_request` exactly once using `X-Voice-Agent-Token`.
8. Django validates the payload, verifies priority, and creates the maintenance request and pending notification logs.
9. Celery asynchronously sends manager email, manager SMS, and resident SMS.
10. If the resident asks for a human, SAM uses `transfer_call` with `{{office_phone_number}}`.
