# ASHACONNECT / AWAMS Advanced UI

Advanced full-stack AWAMS starter for ASHA Workflow Automation and Management System.

## What changed

- Premium React UI with command-center dashboard
- Dashboard summary based on beneficiaries, pregnancies, immunization, appointments, events, notices, monthly reports, and SOS
- UML-aligned module section: Access Control, Beneficiary Services, Clinical Records, Outreach & Safety
- Architecture layer cards: ASHA UI, Backend API, relational database, notification gateway, emergency services
- Better data seed with realistic records and dashboard alerts
- Fixed backend bcrypt issue by pinning bcrypt==4.0.1
- Node 18 compatible Vite setup

## Backend run

```bash
cd backend
rm -rf venv awams.db
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.seed
python -m uvicorn app.main:app --reload
```

Backend docs:

```txt
http://127.0.0.1:8000/docs
```

## Frontend run

Open another terminal:

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

Frontend:

```txt
http://localhost:5173
```

## Demo login

```txt
email: asha@example.com
password: password123
```

## Existing folder update

If you already have ASHACONNECT open, replace these files/folders from this package:

- `frontend/src/main.jsx`
- `frontend/src/styles.css`
- `frontend/package.json`
- `backend/app/routers/dashboard.py`
- `backend/app/seed.py`
- `backend/requirements.txt`

Then run backend seed again after deleting `awams.db`.
# ASHACONNECT
# ASHACONNECT
