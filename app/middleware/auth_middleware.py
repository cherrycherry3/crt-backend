from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError

from app.core.jwt import decode_access_token

# -------------------------------------------------
# PUBLIC ROUTES (NO AUTH REQUIRED)
# -------------------------------------------------
PUBLIC_PATHS = (
    "/api/auth",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Global Authentication Middleware

    - Validates JWT access token
    - Attaches authenticated user context to request.state
    - Blocks unauthenticated access to protected routes
    """

    async def dispatch(self, request: Request, call_next):

        path = request.url.path
        method = request.method

        # ------------------------------------------------
        # 1️⃣ ALLOW CORS PREFLIGHT
        # ------------------------------------------------
        if method == "OPTIONS":
            return await call_next(request)

        # ------------------------------------------------
        # 2️⃣ ALLOW PUBLIC ROUTES
        # ------------------------------------------------
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # ------------------------------------------------
        # 3️⃣ READ AUTH HEADER
        # ------------------------------------------------
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header missing"},
            )

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization format"},
            )

        token = auth_header.split(" ", 1)[1].strip()

        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token not provided"},
            )

        # ------------------------------------------------
        # 4️⃣ DECODE & VALIDATE TOKEN
        # ------------------------------------------------
        try:
            payload = decode_access_token(token)
        except JWTError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token payload"},
            )

        user_id = payload.get("sub")
        if not user_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "User identity missing in token"},
            )

        # ------------------------------------------------
        # 5️⃣ ATTACH USER CONTEXT (SINGLE SOURCE OF TRUTH)
        # ------------------------------------------------
        request.state.user = {
            "id": int(user_id),                     # 🔥 IMPORTANT
            "role": payload.get("role", "USER"),
            "permissions": payload.get("permissions", []),
        }

        # ------------------------------------------------
        # 6️⃣ CONTINUE REQUEST
        # ------------------------------------------------
        return await call_next(request)
