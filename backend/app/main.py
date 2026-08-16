from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.mysql import Base, engine
from app.routers import care_automation, security_admin, family_auth, appointments, auth, beneficiaries, dashboard, events, notices, portfolio, records, reports, sos, monitoring, health_records, tasks, family_portfolio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AWAMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(beneficiaries.router)
app.include_router(portfolio.router)
app.include_router(records.router)
app.include_router(appointments.router)
app.include_router(events.router)
app.include_router(notices.router)
app.include_router(reports.router)
app.include_router(sos.router)


@app.get("/")
def root():
    return {"message": "AWAMS Backend Running", "docs": "/docs"}
app.include_router(monitoring.router)
app.include_router(health_records.router)


# ASHACONNECT_LOCAL_DEV_CORS_FIX
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tasks.router)
app.include_router(family_portfolio.router)

app.include_router(security_admin.router)

app.include_router(family_auth.router)

app.include_router(care_automation.router)
