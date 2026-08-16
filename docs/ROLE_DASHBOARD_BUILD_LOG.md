# ASHACONNECT Role-Based Dashboard Build Log

## Current Security Status

The backend now supports JWT-based authentication, password hashing, staff login, family login, role-based access control, audit logs and access scopes.

## Roles

### ASHA Worker
- Can access own care queue.
- Can access own assigned records.
- Cannot access worker management.
- Cannot access admin audit logs.

### PHC Admin
- Can access PHC-level worker management.
- Can access audit logs.
- Can monitor PHC risk summary.
- Can view high-risk cases and SOS activity.

### Supervisor
- Can access village-wise monitoring.
- Can access ASHA worker performance.
- Can access supervision alerts.
- Can view PHC-scoped risk.

### Family / Beneficiary
- Can login using family portal.
- Can only view mapped family portfolio.
- Cannot access staff routes.

## Frontend Additions

Added:

- `frontend-redesigned/src/role-workspace.jsx`
- `frontend-redesigned/src/role-workspace.css`

The frontend now detects token role and shows a different premium workspace for each login type.

## Working Demo Accounts

ASHA Worker:
- Email: asha@ashaconnect.in
- Password: Asha@123

PHC Admin:
- Email: phc.admin@ashaconnect.in
- Password: Admin@123

Supervisor:
- Email: supervisor@ashaconnect.in
- Password: Supervisor@123

Family:
- Email: family.demo@ashaconnect.in
- Password: Family@123
- Mapped family: Kunda Chettri Family

## Next Build Targets

1. Add frontend worker creation form for PHC Admin.
2. Add audit log viewer with filters.
3. Add family login button into main login page.
4. Hide/show dashboard navigation based on role.
5. Add server-side ownership checks to every beneficiary, appointment, pregnancy and immunization route.
6. Add production database migration from SQLite to PostgreSQL.

## Product Direction Update

Family / beneficiary login remains available in backend for future expansion, but it has been removed from the visible frontend for now.

Reason:
- Current product focus is ASHA Worker Workflow Automation.
- The frontend should not confuse users by showing beneficiary/family portal access during the ASHA operations workflow.
- Family portal can be reintroduced later as a separate product view, similar to an e-campus system with multiple portals.

Current frontend focus:
- ASHA Worker
- PHC Admin
- Supervisor
- Operations Hub
- Role-based staff workspace

## Care Automation Build

Added smart ASHA workflow automation for reports and reminders.

### New backend router

`backend/app/routers/care_automation.py`

### Backend features

- Individual beneficiary report generation
- Family health report generation
- All-families PHC summary generation
- PDF export using ReportLab
- Report history table
- Outbound WhatsApp-style message queue
- Reminder settings table
- Reminder scan for appointments and immunization schedules
- Audit log entries for generated reports and reminder scans

### New database tables

- generated_reports
- outbound_messages
- reminder_settings
- reminder_events

### New frontend module

`frontend-redesigned/src/care-automation.jsx`

### Frontend features

- Care Automation premium workspace button
- Report Generation tab
- Reminder Settings tab
- Message Queue tab
- Report History tab

### Product note

WhatsApp delivery is currently implemented as a message queue with WhatsApp-ready links. This makes the feature demo-ready without requiring paid API credentials. In production, the outbound queue can be connected to WhatsApp Cloud API, Twilio, Gupshup or another provider.

## Automatic Reminder Scheduler Build

Added backend automatic reminder scheduler.

### New file
- `backend/app/services/reminder_engine.py`

### New backend endpoints
- `POST /api/care-automation/reminders/auto-run-now`
- `GET /api/care-automation/reminders/scheduler/status`

### Scheduler behavior
- Starts automatically when FastAPI starts.
- Runs every 3600 seconds by default.
- Scans appointment reminders.
- Scans immunization reminders.
- Scans pregnancy expected/follow-up reminders.
- Creates one-day-before reminders.
- Creates same-day/few-hours-before reminders.
- Prevents duplicate reminders through `reminder_events`.
- Stores outbound messages in `outbound_messages`.

### Environment controls
- `ASHACONNECT_REMINDER_SCHEDULER=1`
- `ASHACONNECT_REMINDER_INTERVAL_SECONDS=3600`

### Product note
This is currently an in-app scheduler suitable for local/demo deployment. In production, this can be moved to Celery, cron jobs, Redis Queue or a cloud background worker.

## Reminder Settings UX Fix

Fixed reminder template editing issue.

Previous behavior:
- Reminder template saved on every keystroke.
- API refresh happened after each letter.
- Textarea lost cursor position.

Updated behavior:
- Reminder settings now use local draft state.
- User can type normally.
- Backend saves only when "Save Setting" is clicked.

## Care Automation UX Simplification

Removed visible Reminder Settings from the frontend.

Reason:
- ASHA worker should not manually edit technical reminder templates.
- The product goal is one-click workflow automation.
- Reminder automation should feel like: click once, scan due records, prepare messages.

Updated frontend tabs:
- Generate Reports
- Send Reminders
- Message Queue
- Report History

Updated reminder behavior:
- One click checks due appointments, immunization and pregnancy follow-ups.
- Messages are added to the Message Queue.
- ASHA worker sees clear status after the action.
- Standard ASHA reminder templates are used in backend.

## Care Events Scheduling Foundation

Added a unified `care_events` table.

Purpose:
- Store appointments, vaccination due dates, routine checkups and follow-ups in one reliable place.
- Make reminder automation independent of older fragmented tables.
- Allow ASHA worker scheduling features to be added later without breaking reminders.

New endpoints:
- `GET /api/care-automation/events`
- `POST /api/care-automation/events`
- `POST /api/care-automation/events/seed-demo`

Reminder engine update:
- Reminder scanner now checks `care_events`.
- Today events create same-day reminders.
- Tomorrow events create one-day-before reminders.
- Duplicate reminders are prevented through `reminder_events`.

Product note:
This is a backend foundation. UI can later expose this as simple ASHA actions like "Add Appointment", "Add Vaccine Date", and "Send Reminder".

## Premium Responsive Website Redesign Phase 1

Updated frontend direction:
- ASHACONNECT remains a responsive website, not a separate app.
- The site must work properly in mobile browsers for ASHA workers.
- Desktop/tablet views should feel like premium healthcare SaaS.
- ASHA worker screens should stay simple, large, readable and touch-friendly.

Phase 1 frontend changes:
- Added `frontend-redesigned/src/premium-responsive-theme.css`
- Replaced emoji navigation icons with professional short labels.
- Improved global cards, forms, buttons, sidebar, floating action dock and mobile responsiveness.
- Kept backend and feature logic untouched.

Next redesign phase:
- Replace short-label icons with SVG icon components.
- Build reusable design components.
- Simplify ASHA flow for low-literacy field use.
- Add multilingual labels.
