# Product Specification

## Product Summary

Hello SAM is an AI-powered maintenance phone intake system for apartment and building management teams.

The product turns an unstructured resident phone call into a validated maintenance request with building context, priority verification, call logging, manager notifications, resident confirmation, and optional human transfer.

The MVP is intentionally narrow: one high-value operational workflow, implemented with production-oriented backend patterns instead of demo-only shortcuts.

## Product Positioning

Hello SAM is not a phone tree, chatbot demo, or generic ticket form.

It is a voice-first maintenance intake backend designed around the real operational constraints of property management:

- residents often call outside office hours;
- maintenance reports are incomplete unless guided;
- managers need structured, actionable summaries;
- urgent and emergency issues need consistent handling;
- multiple buildings need separate routing without duplicating agents;
- phone calls can be retried, dropped, duplicated, or escalated to a human.

The backend owns the critical decisions. The AI agent collects information, but the system validates, normalizes, prioritizes, stores, and notifies.

## Core Goals

- Let residents report maintenance issues naturally by phone.
- Route one shared Retell agent across multiple buildings using called-number lookup.
- Create structured maintenance tickets from voice conversations.
- Store call payload and transcript context for operational review.
- Notify managers through email and SMS.
- Confirm submission to residents through SMS.
- Support transfer to the correct building office when a resident asks for a human.
- Keep data quality and safety safeguards in backend code rather than relying only on AI behavior.

## Non-Goals

The MVP does not include:

- Resident account profiles.
- Public frontend or resident portal.
- Scheduling or technician assignment.
- Payment, lease, or rent workflows.
- Automated repair diagnosis.
- Multi-provider notification routing beyond Postmark and Twilio.
- Full property-management-system integration.

## System Boundary

Hello SAM owns:

- building lookup;
- maintenance request creation;
- call logging;
- priority verification;
- notification intent creation;
- async notification delivery state;
- retry visibility;
- voice endpoint security;
- admin verification and operations.

External systems own:

- live voice conversation runtime through Retell;
- email delivery through Postmark;
- SMS delivery through Twilio;
- hosting/runtime infrastructure;
- final human office response after transfer.

## Building Routing

Each building has:

- `maintenance_phone_number`: the Retell number residents call.
- `office_phone_number`: the number used for human transfer.
- `manager_email`: email notification recipient.
- `manager_phone`: SMS notification recipient.

The backend maps:

```text
called_number -> Building.maintenance_phone_number
```

This lets one Retell agent serve multiple buildings without asking the resident which property they are calling from.

## Voice Request Data

The voice maintenance request endpoint requires:

- `call_id`
- `called_number`
- `caller_phone`
- `full_name`
- `unit_number`
- `use_caller_phone_for_follow_up`
- `follow_up_phone`
- `issue_type`
- `resident_reported_issue`
- `description`
- `location_inside_unit`
- `ai_priority`
- `transcript`

The backend normalizes `follow_up_phone` to `caller_phone` when `use_caller_phone_for_follow_up` is `true`.

## Issue Types

Supported issue types:

```text
plumbing
water_leak
drain_clog
toilet
electrical
power_outage
lighting
heating_cooling
no_heat
air_conditioning
ventilation
appliance
refrigerator
stove_oven
dishwasher
washer_dryer
door_lock
window
garage_parking
pest
noise_security
safety_hazard
common_area
exterior
flooring
walls_ceiling
general_maintenance
other
```

## Priority Handling

Priority values:

- `normal`
- `urgent`
- `emergency`

Retell submits `ai_priority` as a suggestion. The backend independently scans maintenance text and calculates `backend_priority`. The saved `final_priority` is the highest severity between the AI suggestion and backend detection.

Notifications use `final_priority`.

This prevents the system from blindly trusting a model-generated priority for operationally important decisions.

## Security Model

Two voice-facing endpoints use separate security mechanisms:

- Retell inbound webhook: `X-Retell-Signature`, verified with `RETELL_API_KEY` and the raw request body.
- Retell Custom Function: `X-Voice-Agent-Token`, verified against `VOICE_AGENT_TOKEN`.

No Django user authentication, JWT, OAuth, or session auth is used for these machine-to-machine voice endpoints.

## Data Quality Safeguards

The MVP includes backend-side safeguards for:

- active building validation;
- unique `maintenance_phone_number`;
- unique `call_id`;
- E.164 phone validation;
- follow-up phone normalization;
- placeholder phone rejection;
- deterministic priority detection;
- duplicate request prevention;
- duplicate notification intent prevention.

These safeguards are intentionally implemented server-side because voice AI output can be inconsistent.

## Notification Flow

For a new maintenance request, the backend creates three notification intents:

- Manager email.
- Manager SMS.
- Resident SMS confirmation.

Notifications are sent asynchronously by Celery through:

- Postmark for email.
- Twilio for SMS.

`NotificationLog` tracks:

- recipient;
- purpose;
- status;
- provider message ID;
- error message;
- attempt count;
- last attempt time;
- sent time.

## Notification Reliability

The reliability design includes:

- Celery enqueue after database commit with `transaction.on_commit`.
- Pending notification logs remain recoverable if Redis/Celery enqueue fails.
- Status flow: `pending -> processing -> sent` and `pending -> processing -> failed`.
- Normal processing only handles `pending` logs.
- Admin retry handles selected `pending` or `failed` logs.
- `sent` and `processing` logs are skipped by retry.
- A database constraint prevents duplicate `(maintenance_request, purpose)` notification intents.

External provider delivery is not guaranteed exactly once. If Postmark or Twilio accepts a message and the worker crashes before saving `sent`, a later manual retry may duplicate that external provider delivery.

The system is designed to reduce normal duplicate sends, surface failed delivery, and keep recovery explicit.

## Admin Operations

Django Admin is the MVP operations console.

It supports review and management of:

- companies;
- buildings;
- maintenance requests;
- call logs;
- notification logs.

Admin also provides a retry action for selected pending or failed notifications.

## Runtime Architecture

The MVP is designed to run as:

- Django API web process.
- Celery worker process.
- PostgreSQL database.
- Redis broker.
- Retell voice integration.
- Postmark email provider.
- Twilio SMS provider.
- Sentry/logging monitoring layer.

The repository supports Docker-based local development and CI validation.

## Why This Is Portfolio-Relevant

Hello SAM demonstrates production backend engineering beyond CRUD:

- external webhook security;
- service-layer business logic;
- async job orchestration;
- idempotent request handling;
- provider abstraction;
- stateful notification delivery;
- database constraints for business invariants;
- deterministic safeguards around AI-generated data;
- practical admin operations;
- Dockerized local workflow and testable integrations.

## Public Documentation Source of Truth

Implementation source of truth:

- API routes: Django URL configuration and views.
- Payload fields: DRF serializers.
- Issue type values: backend `IssueType` choices.
- Priority behavior: backend priority service.
- Notification behavior: notification services, tasks, models, and tests.
- Runtime behavior: Dockerfile, entrypoint, Compose, and GitHub Actions workflow.
