from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from app.routers import auth, gpus, jobs, wallet, admin, ws
from app.config import get_settings
import os
import asyncio

settings = get_settings()

# ── Rate Limiter Setup ──
def _get_rate_limit_key(request: Request) -> str:
    """
    Key function for rate limiting:
    - If user is authenticated: use user_id (per-user limit)
    - Otherwise: use IP address (per-IP limit)
    """
    # Try to get user from request (set by dependencies)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user-{user_id}"
    # Fallback to IP
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    os.makedirs("uploads", exist_ok=True)
    print("✅ Upload directory ready")
    
    # Auto-create database tables on startup
    from app.database import engine, Base
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        # Create tables with error handling for existing ENUMs
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            # Ignore if types already exist
            if "already exists" not in str(e):
                print(f"⚠️  Database creation warning: {e}")
        
        # Enable UUID extension if not exists
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        except:
            pass  # Extension might already exist or be unavailable
    print("✅ Database tables initialized")
    
    # Initialize Redis rate limiter with REDIS_URL from environment
    from app.redis_rate_limiter import get_rate_limiter
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"🔴 Initializing Redis rate limiter: {redis_url}")
    get_rate_limiter(redis_url)  # Initialize the singleton with proper Redis URL
    print("✅ Redis rate limiter initialized")
    
    # Start background cleanup task for expired GPU locks
    cleanup_task = asyncio.create_task(_cleanup_gpu_locks_background())
    app.state.cleanup_task = cleanup_task
    print("✅ GPU lock cleanup task started")
    
    yield
    
    # ── Shutdown ──
    # Cancel the cleanup task
    if hasattr(app.state, "cleanup_task"):
        app.state.cleanup_task.cancel()
    print("👋 Shutting down UniGPU backend")


async def _cleanup_gpu_locks_background():
    """Periodically clean up expired GPU locks every 60 seconds."""
    from app.database import AsyncSessionLocal
    from app.services.matching import cleanup_expired_locks
    
    while True:
        try:
            await asyncio.sleep(60)  # Run every 60 seconds
            async with AsyncSessionLocal() as session:
                cleaned_count = await cleanup_expired_locks(session)
                if cleaned_count > 0:
                    print(f"🧹 Cleaned up {cleaned_count} expired GPU lock(s)")
        except asyncio.CancelledError:
            print("🧹 GPU lock cleanup task cancelled")
            break
        except Exception as e:
            print(f"⚠️  Error in GPU lock cleanup: {e}")
            # Continue running even if there's an error


# ── Create FastAPI app with conditional docs ──
app = FastAPI(
    title="UniGPU",
    description="Centralized peer-to-peer GPU sharing platform",
    version="0.1.0",
    lifespan=lifespan,
    # Disable Swagger UI, ReDoc, and OpenAPI schema in production
    docs_url=None if not settings.DEBUG else "/docs",
    redoc_url=None if not settings.DEBUG else "/redoc",
    openapi_url=None if not settings.DEBUG else "/openapi.json",
)

# ── CORS ──
# In production, ALLOWED_ORIGINS is set to the actual frontend domain via .env.prod
_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiter State ──
app.state.limiter = limiter


# ── Middleware to extract user ID for per-user rate limiting ──
@app.middleware("http")
async def set_user_id_for_rate_limiting(request: Request, call_next):
    """Extract user ID from JWT token if present, to enable per-user rate limiting."""
    from jose import jwt as jwt_module
    from jose.exceptions import JWTError
    
    request.state.user_id = None
    
    # Try to extract user ID from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header[7:]  # Remove "Bearer "
            payload = jwt_module.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                request.state.user_id = user_id
        except JWTError:
            pass  # Invalid token, will be caught by auth dependency
    
    response = await call_next(request)
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

# ── REST Routers ──
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(gpus.router, prefix="/gpus", tags=["GPUs"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# ── WebSocket ──
app.include_router(ws.router, tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "UniGPU Backend"}
