# ============================================================
# auth/rbac.py — JWT Verification Middleware
# ============================================================
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import JWT_SECRET, JWT_ALGORITHM

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """Decode JWT and return payload. Raises 401 if invalid."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(*allowed_roles: str):
    """Factory: create a dependency that checks role."""
    def _check(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    return _check

# Convenience shortcuts
require_leader    = require_role("leader")
require_admin     = require_role("super_admin", "admin")
require_any_staff = require_role("leader", "super_admin", "admin")
