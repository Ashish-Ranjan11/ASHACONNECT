import os

from fastapi import HTTPException, Request
from clerk_backend_api import (
    authenticate_request,
    AuthenticateRequestOptions,
)


def authenticate_clerk_request(request: Request):
    secret_key = os.getenv("CLERK_SECRET_KEY")
    jwt_key = os.getenv("CLERK_JWT_KEY")

    if not secret_key:
        raise RuntimeError("CLERK_SECRET_KEY is not configured")

    authorized_parties = [
        item.strip()
        for item in os.getenv(
            "CLERK_AUTHORIZED_PARTIES",
            "http://localhost:5173",
        ).split(",")
        if item.strip()
    ]

    state = authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=secret_key,
            jwt_key=jwt_key or None,
            authorized_parties=authorized_parties,
            accepts_token=["session_token"],
        ),
    )

    if not state.is_signed_in:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Clerk session",
        )

    return state
