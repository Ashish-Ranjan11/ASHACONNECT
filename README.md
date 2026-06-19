# ASHACONNECT

## ASHA Workflow Automation and Management System

ASHACONNECT is a full-stack web-based healthcare workflow automation platform designed to support ASHA workers in managing beneficiaries, clinical records, appointments, immunization schedules, pregnancy records, community events, alerts, and monthly reports.

The project aims to reduce manual paperwork, improve follow-up tracking, support real-time health monitoring, and provide a centralized dashboard for ASHA workers and PHC-level supervision.

---

## Project Overview

ASHA workers play a critical role in India’s rural healthcare system. However, their daily workflow often depends on manual registers, repeated data entry, delayed reporting, and informal communication methods.

ASHACONNECT solves this problem by digitizing core ASHA workflows through a unified platform that includes:

* Beneficiary registration and tracking
* Pregnancy record management
* Immunization scheduling
* Appointment management
* Health event organization
* Notice and reminder system
* Monthly report generation
* Emergency SOS alert support
* Dashboard-based monitoring

---

## Key Features

### Authentication

* Secure ASHA worker login
* JWT-based authentication
* Protected backend APIs

### Dashboard

* Total beneficiaries
* Pregnancy records
* Immunization records
* Upcoming appointments
* Events
* Active alerts
* High-risk pregnancy indicators
* Missed immunization tracking
* Workflow and module overview

### Beneficiary Management

* Add new beneficiaries
* View beneficiary list
* Track category-wise beneficiaries such as pregnant women, children, elderly, and general patients

### Clinical Records

* Pregnancy record creation
* ANC count tracking
* Hemoglobin, blood pressure, weight, and expected delivery date tracking
* High-risk pregnancy status support

### Immunization Records

* Vaccine scheduling
* Dose tracking
* Missed, scheduled, postponed, and given status management

### Appointment Management

* Schedule appointments
* Track appointment status
* Store appointment notes

### Events and Notices

* Create community health events
* Manage awareness drives, vaccination drives, nutrition camps, and checkup events
* Send beneficiary notices and reminders

### Monthly Reports

* Generate monthly performance reports
* Track total patients, pregnancies, immunizations, appointments, and events
* Support PHC-level reporting workflow

### Emergency SOS

* Trigger emergency SOS alerts
* Store worker location and alert status
* Designed for ASHA worker field safety

---

## Tech Stack

### Frontend

* React.js
* Vite
* JavaScript
* CSS

### Backend

* FastAPI
* Python
* SQLAlchemy ORM
* JWT Authentication
* Passlib password hashing

### Database

* SQLite for local development
* MySQL-ready structure for production usage

---

## Folder Structure

```bash
ASHACONNECT-ADVANCED/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── seed.py
│   │   ├── security.py
│   │   ├── db/
│   │   └── routers/
│   │
│   ├── requirements.txt
│   └── awams.db
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── api.js
│   │
│   ├── index.html
│   └── package.json
│
├── README.md
└── .gitignore
```

---

## Backend Setup

Open a terminal and run:

```bash
cd backend

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m app.seed
python -m uvicorn app.main:app --reload
```

Backend will run at:

```bash
http://127.0.0.1:8000
```

FastAPI documentation:

```bash
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Open another terminal and run:

```bash
cd frontend

npm install
npm run dev
```

Frontend will run at:

```bash
http://localhost:5173
```

---

## Demo Login

```bash
Email: asha@example.com
Password: password123
```

---

## API Documentation

Once the backend is running, open:

```bash
http://127.0.0.1:8000/docs
```

This page provides automatic API documentation for all backend routes.

---

## Main Modules

The system is divided into the following core modules:

1. Access Control
2. Dashboard Monitoring
3. Beneficiary Services
4. Clinical Records
5. Pregnancy Tracking
6. Immunization Tracking
7. Appointment Scheduling
8. Event Management
9. Notice and Reminder System
10. Monthly Reporting
11. Emergency SOS

---

## Future Enhancements

* MySQL production database integration
* Role-based dashboards for PHC admins and supervisors
* SMS gateway integration
* Push notification system
* Offline-first Progressive Web App support
* AI-based health advisory module
* Advanced analytics and charts
* Deployment on cloud platforms

---

## Project Purpose

This project is developed as part of the ASHA Workers Workflow Automation initiative. It focuses on improving rural healthcare workflow management through digital transformation, centralized record keeping, automated reminders, and real-time dashboard-based monitoring.

---

## Author

Developed by Ashish Ranjan and team as part of the ASHACONNECT / AWAMS project.
