from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def make_verify_token(token: str):
    async def verify_token(
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ):
        if credentials and credentials.credentials == token:
            return credentials.credentials
        raise HTTPException(status_code=401, detail="Unauthorized")

    return verify_token
