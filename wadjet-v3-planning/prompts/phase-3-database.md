# Phase 3 — Database & Authentication Foundation

## Goal
Add the SaaS foundation: a database layer (SQLite for beta, PostgreSQL-ready) and JWT-based authentication. This transforms Wadjet from a stateless demo into a product that remembers its users.

## Bugs Fixed
- **M16**: In-memory-only sessions → state lost on restart

## New Features
- SQLite database via aiosqlite + SQLAlchemy 2.0 async
- Alembic migrations (PostgreSQL-ready schema)
- User registration + login (email/password)
- JWT access tokens (30min) + refresh tokens (7d, httpOnly cookie)
- Guest mode preserved (all features work without login)
- Auth dependency injection (`get_current_user`, `get_optional_user`)

## Files Created/Modified

### New Files
- `app/db/__init__.py`
- `app/db/database.py` — async engine, session factory
- `app/db/models.py` — SQLAlchemy ORM models
- `app/db/schemas.py` — Pydantic request/response schemas
- `app/db/crud.py` — database operations
- `app/auth/__init__.py`
- `app/auth/jwt.py` — token creation, validation
- `app/auth/password.py` — bcrypt hashing
- `app/auth/dependencies.py` — FastAPI dependencies
- `app/api/auth.py` — register, login, refresh, logout endpoints
- `app/api/user.py` — profile, history, progress endpoints
- `alembic.ini` — migration config
- `alembic/` — migration folder
- `data/wadjet.db` — SQLite database file (auto-created)

### Modified Files
- `requirements.txt` — add sqlalchemy[asyncio], aiosqlite, alembic, python-jose, bcrypt, pydantic[email]
- `app/config.py` — add DATABASE_URL, JWT_SECRET, JWT_ALGORITHM settings
- `app/main.py` — add startup DB init, auth router mount
- `app/templates/base.html` — add login/signup modal trigger in nav

## Implementation Steps

### Step 1: Install dependencies
```
# Add to requirements.txt:
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20.0
alembic>=1.14
python-jose[cryptography]>=3.3
bcrypt>=4.0
pydantic[email]>=2.0
```

### Step 2: Database setup (app/db/database.py)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        yield session
```

### Step 3: User model (app/db/models.py)
```python
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    preferred_lang = Column(String, default="en")
    tier = Column(String, default="free")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ScanHistory(Base):
    __tablename__ = "scan_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    results_json = Column(Text)
    confidence_avg = Column(Float)
    glyph_count = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

class StoryProgress(Base):
    __tablename__ = "story_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    story_id = Column(String, nullable=False)
    chapter_index = Column(Integer, default=0)
    glyphs_learned = Column(Text, default="[]")
    score = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "story_id"),)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_type = Column(String, nullable=False)  # 'landmark', 'glyph', 'story'
    item_id = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id"),)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

### Step 4: Auth utilities (app/auth/password.py + jwt.py)
```python
# password.py
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

```python
# jwt.py
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.config import settings

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.jwt_secret, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": user_id, "exp": expire, "type": "refresh"}, settings.jwt_secret, algorithm="HS256")

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None
```

### Step 5: Auth dependencies (app/auth/dependencies.py)
```python
from fastapi import Depends, HTTPException, Request
from app.auth.jwt import decode_token
from app.db.database import get_db
from app.db.crud import get_user_by_id

async def get_current_user(request: Request, db=Depends(get_db)):
    """Require authentication. Returns User or raises 401."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_optional_user(request: Request, db=Depends(get_db)):
    """Optional auth. Returns User or None (for guest mode)."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return await get_user_by_id(db, payload["sub"])
```

### Step 6: Auth router (app/api/auth.py)
```python
# POST /api/auth/register — email + password → user + tokens
# POST /api/auth/login — email + password → tokens
# POST /api/auth/refresh — refresh cookie → new access token
# POST /api/auth/logout — invalidate refresh token
```

### Step 7: Config additions
```python
# app/config.py additions:
database_url: str = "sqlite+aiosqlite:///data/wadjet.db"
jwt_secret: str = "change-me-in-production"  # from .env
csrf_secret: str = "change-me-in-production"  # from .env
```

### Step 8: UI integration
- Add "Sign In" / "Sign Up" link in nav (desktop + mobile)
- Auth modals using Alpine.js (no new pages needed)
- After login, show user avatar/name in nav, "Sign Out" option
- Guest mode: everything works, but "Sign in to save progress" prompts appear

## Testing Checklist
- [ ] `data/wadjet.db` auto-created on first start
- [ ] POST /api/auth/register with valid email+password → 201, user created
- [ ] POST /api/auth/register with duplicate email → 409 Conflict
- [ ] POST /api/auth/register with weak password (<8 chars) → 400
- [ ] POST /api/auth/login with valid creds → 200, access_token + refresh cookie
- [ ] POST /api/auth/login with wrong password → 401
- [ ] GET /api/user/profile with valid access token → 200, user data
- [ ] GET /api/user/profile with expired token → 401
- [ ] POST /api/auth/refresh with valid refresh cookie → new access token
- [ ] POST /api/auth/logout → refresh token invalidated
- [ ] All existing features work WITHOUT auth (guest mode preserved)
- [ ] Password stored as bcrypt hash (not plaintext) in DB
- [ ] JWT tokens contain no sensitive data (just user_id + exp)
- [ ] Restart server → user data persists (SQLite file)

## Git Commit
```
[Phase 3] Database & auth foundation — SQLite, SQLAlchemy, JWT auth, user model
```
