# HIU Dashboard - Coding Practices Guide

This document outlines standardized coding patterns and best practices used in the HIU Dashboard project. These patterns ensure consistency, maintainability, and scalability across the codebase.

---

## Table of Contents

1. [Layered Architecture](#layered-architecture)
2. [Request & Response Schemas](#request--response-schemas)
3. [Error Handling](#error-handling)
4. [Dependency Injection](#dependency-injection)
5. [Router Implementation](#router-implementation)
6. [Service Layer](#service-layer)
7. [Repository Pattern](#repository-pattern)
8. [Pagination](#pagination)
9. [Rate Limiting](#rate-limiting)
10. [Authentication & Authorization](#authentication--authorization)
11. [Validation Patterns](#validation-patterns)

---

## Layered Architecture

The application follows a **three-layer architecture** pattern to separate concerns and improve maintainability:

```
Router (HTTP endpoint)
  ↓
Service (business logic)
  ↓
Repository / Client (data access / external calls)
```

### Layer Responsibilities

| Layer | Responsibility | Examples |
|-------|---|---|
| **Router** | HTTP request/response handling, parameter extraction, delegation | `api/routers/*.py` |
| **Service** | Business logic, validation, orchestration, error handling | `api/services/*.py` |
| **Repository** | Database CRUD operations, queries | `api/repositories/*.py` |
| **Client** | External API calls (HPR, HFR, OTP) | `api/common/*_client.py` |

**Key Principle**: Logic flows unidirectionally downward. Each layer depends only on layers below it, never above.

---

## Request & Response Schemas

All API contracts are defined using **Pydantic BaseModel** in `api/schemas/`.

### Request Schema Pattern

Request schemas define the **API contract** and validate all constraints upfront:

```python
from typing import Optional
from pydantic import BaseModel, Field, validator

class SearchFacilityRequest(BaseModel):
    # Optional fields with validation
    ownershipCode: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=2,
        description="Accepted values: G, P, PP"
    )
    stateLGDCode: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=10,
        description="State LGD code"
    )
    
    # Required fields with validation
    page: int = Field(..., ge=1, description="Page number (minimum 1)")
    resultsPerPage: int = Field(..., ge=10, le=100, description="Results per page")

    # Pre-validator: normalize optional text fields
    @validator("ownershipCode", "stateLGDCode", pre=True)
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    # Field-specific validators
    @validator("ownershipCode")
    def validate_ownership_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value.upper() not in {"G", "P", "PP"}:
            raise ValueError("ownershipCode must be one of: G, P, PP")
        return value.upper()
```

### Validation Patterns

#### 1. Max Length Enforcement
Prevents oversized payloads and database constraint violations:
```python
email: str = Field(..., max_length=255)
facility_name: str = Field(..., max_length=200)
```

#### 2. Numeric Range Constraints
```python
page: int = Field(..., ge=1)                           # Minimum 1
results_per_page: int = Field(..., ge=10, le=100)     # 10-100 inclusive
```

#### 3. Reusable Validators
Define validators as module-level functions for reuse across schemas:
```python
def normalize_facility_id(value: Optional[str]) -> str:
    """Normalize facility ID: strip and uppercase."""
    normalized = str(value).strip().upper()
    if not normalized:
        raise ValueError("facilityId is required")
    return normalized

def validate_facility_id_format(value: str) -> str:
    """Validate facility ID: must start with IN and be 12 alphanumeric chars."""
    if not re.fullmatch(r"IN[A-Z0-9]{10}", value):
        raise ValueError("facilityId must be IN + 10 alphanumeric characters")
    return value
```

#### 4. Regex Patterns as Constants
Define patterns at module level for maintainability:
```python
FACILITY_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9\-_.(),/]|(?: [A-Za-z0-9\-_.(),/]))*$"
)
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
WEBSITE_PATTERN = re.compile(
    r"^(?:(?:https?://)|(?:www\.))[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+(?::\d+)?(?:/.*)?$",
    re.IGNORECASE,
)

class FacilityRequest(BaseModel):
    facility_name: str = Field(..., max_length=200)
    
    @validator("facility_name")
    def validate_facility_name(cls, value: str) -> str:
        if not FACILITY_NAME_PATTERN.fullmatch(value):
            raise ValueError("Invalid facility name format")
        return value
```

#### 5. Cross-Field Validation
Validate relationships between multiple fields:
```python
@root_validator
def validate_search_constraints(cls, values: dict) -> dict:
    has_facility_id = bool((values.get("facilityId") or "").strip())
    has_core_fields = bool(
        (values.get("ownershipCode") or "").strip()
        and (values.get("stateLGDCode") or "").strip()
    )
    
    if not has_facility_id and not has_core_fields:
        raise ValueError(
            "Either facilityId OR (ownershipCode + stateLGDCode) must be provided"
        )
    
    return values
```

### Response Schema Pattern

```python
from typing import Optional
from pydantic import BaseModel, Field

class SearchFacilityResponse(BaseModel):
    facilities: list[FacilityItem] = Field(default_factory=list)
    totalFacilities: Optional[int] = None
    numberOfPages: Optional[int] = None
    message: Optional[str] = None

    class Config:
        # Allow extra fields from external APIs (pass-through)
        extra = "allow"
```

**Convention**:
- Response models use `extra = "allow"` to pass through unmapped fields from external APIs
- Optional fields for API responses (external APIs may omit fields)
- Field names must match external API naming exactly (usually camelCase)

---

## Error Handling

### Error Definition Pattern

Errors are centralized in `api/errors/` using immutable `ErrorDefinition` dataclasses:

```python
# api/errors/base.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ErrorDefinition:
    """Immutable error with status code, error code, and message."""
    status_code: int
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"

# api/errors/hfr_errors.py
class HFRErrors:
    HFR_SERVICE_UNAVAILABLE = ErrorDefinition(
        status_code=503,
        error_code="HFR_SERVICE_UNAVAILABLE",
        message="HFR service is currently unavailable",
    )
    
    HFR_INVALID_SEARCH_REQUEST = ErrorDefinition(
        status_code=422,
        error_code="HFR_INVALID_SEARCH_REQUEST",
        message="Invalid HFR facility search request",
    )
    
    HFR_NOT_FOUND = ErrorDefinition(
        status_code=404,
        error_code="HFR_NOT_FOUND",
        message="Resource not found",
    )
```

### Raising Errors

Use `create_error()` factory to raise domain-specific errors with context:

```python
from api.exceptions import create_error

# Simple error raise
raise create_error(HFRErrors.HFR_SERVICE_UNAVAILABLE)

# Error with additional details
raise create_error(
    HFRErrors.HFR_INVALID_SEARCH_REQUEST,
    details={"field": "ownershipCode", "reason": "Invalid value"}
)

# Error with HTTP exception conversion
raise create_error(
    CaregiverErrors.CAREGIVER_NOT_FOUND,
    details={"cg_id": str(caregiver_id)}
)
```

### Error Response Format

Exceptions are caught by global exception handlers and converted to JSON:

```json
{
  "status_code": 422,
  "error_code": "HFR_INVALID_SEARCH_REQUEST",
  "message": "Invalid HFR facility search request",
  "details": {
    "field": "ownershipCode",
    "reason": "Invalid value"
  }
}
```

**Best Practices**:
- Define one error domain per module (`hfr_errors.py`, `caregiver_errors.py`, etc.)
- Use descriptive error codes (SCREAMING_SNAKE_CASE)
- Always provide appropriate HTTP status codes
- Include context via `details` parameter for debugging
- Never expose internal implementation details in error messages

---

## Dependency Injection

FastAPI dependencies are defined in `api/dependencies.py` and follow a **composition pattern**.

### App-Scoped Dependencies

These are initialized once during application startup and stored in `app.state`:

```python
# api/dependencies.py

def get_redis_client(request: Request) -> Redis:
    """Provide shared Redis client from app.state."""
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise RuntimeError("Redis client not configured on app state")
    return redis_client

def get_jwt_service(request: Request) -> JwtService:
    """Provide shared JWT service from app.state."""
    jwt_service = getattr(request.app.state, "jwt_service", None)
    if jwt_service is None:
        raise RuntimeError("JWT service not configured on app state")
    return jwt_service

def get_otp_client(request: Request) -> OtpClient:
    """Provide shared OTP client with fallback creation."""
    otp_client = getattr(request.app.state, "otp_client", None)
    if otp_client is None:
        fallback = getattr(request.app.state, "_otp_client_fallback", None)
        if fallback is None or fallback.is_closed:
            fallback = httpx.AsyncClient(timeout=settings.REMOTE_API_TIMEOUT_SECONDS)
            request.app.state._otp_client_fallback = fallback
        otp_client = OtpClient(fallback)
        request.app.state.otp_client = otp_client
    return otp_client
```

### Composed Dependencies

Compose app-scoped dependencies to create request-specific instances:

```python
def get_hfr_client(
    client: httpx.AsyncClient = Depends(get_http_client),
    abdm_tm: ABDMTokenManager = Depends(get_abdm_token_manager),
) -> HFRClient:
    """Return new HFRClient initialized with shared http client and token manager."""
    return HFRClient(
        client=client,
        token_manager=abdm_tm,
        base_url=settings.HFR_BASE_URL
    )

def get_hpr_client(
    client: httpx.AsyncClient = Depends(get_http_client),
    abdm_tm: ABDMTokenManager = Depends(get_abdm_token_manager),
) -> HPRClient:
    """Return new HPRClient initialized with shared http client and token manager."""
    return HPRClient(
        client=client,
        token_manager=abdm_tm,
        base_url=settings.HPR_BASE_URL
    )
```

### Authentication Dependencies

Extract and validate authentication context:

```python
def get_token_payload(
    request: Request,
    jwt_service: JwtService = Depends(get_jwt_service),
) -> TokenPayload:
    """Extract and validate token from request (Authorization header or cookies)."""
    token = _extract_token_from_request(request)
    
    if not token:
        raise create_error(AuthErrors.MISSING_TOKEN)
    
    payload_dict = jwt_service.decode_token(token)
    if payload_dict is None:
        raise create_error(AuthErrors.INVALID_TOKEN)
    
    return TokenPayload.from_dict(payload_dict)

def get_caregiver_id(
    payload: TokenPayload = Depends(get_token_payload),
) -> UUID:
    """Extract caregiver ID from validated token."""
    if payload.persona != PersonaEnum.caregiver.value:
        raise create_error(AuthErrors.INVALID_ROLE)
    
    cg_id = payload.claims.get("cg_id")
    if not cg_id:
        raise create_error(AuthErrors.INVALID_TOKEN)
    
    return UUID(str(cg_id))

def get_health_professional_id(
    payload: TokenPayload = Depends(get_token_payload),
) -> UUID:
    """Extract health professional ID from validated token."""
    if payload.persona != PersonaEnum.hp.value:
        raise create_error(AuthErrors.INVALID_ROLE)
    
    hp_id = payload.claims.get("hp_id")
    if not hp_id:
        raise create_error(AuthErrors.INVALID_TOKEN)
    
    return UUID(str(hp_id))

def get_current_caregiver(
    cg_id: UUID = Depends(get_caregiver_id),
    db: Session = Depends(get_db),
) -> Caregiver:
    """Return authenticated caregiver from database."""
    caregiver = db.query(Caregiver).filter(Caregiver.cg_id == cg_id).first()
    if not caregiver:
        raise create_error(CaregiverErrors.CAREGIVER_NOT_FOUND)
    return caregiver
```

### Router-Level Dependency

Apply dependencies at router level to protect all routes:

```python
# api/routers/healthprofessional.py

router = APIRouter(
    prefix="/health-professionals",
    tags=["Health Professionals"],
    dependencies=[Depends(require_valid_hp_access_token_for_non_auth_routes)],
)

def require_valid_hp_access_token_for_non_auth_routes(
    request: Request,
    jwt_service: JwtService = Depends(get_jwt_service),
) -> None:
    """Require valid HP access token except on auth routes."""
    route_path = getattr(request.scope.get("route"), "path", request.url.path)
    if "/auth/" in route_path:
        return
    
    token = request.cookies.get(settings.HP_ACCESS_COOKIE_NAME)
    payload = _decode_token_payload(token, jwt_service)
```

**Best Practices**:
- Use router-level dependencies to protect groups of routes
- Extract dependencies to separate functions for reusability
- Always validate extracted values and raise appropriate errors
- Use composition to build complex dependencies from simpler ones

---

## Router Implementation

Routers are defined in `api/routers/` and must remain **thin and focused** on HTTP concerns.

### Thin Router Pattern

Routers handle only HTTP contract mapping, delegating all logic to services:

```python
# api/routers/hfr.py
from fastapi import APIRouter, Body, Depends, Query

router = APIRouter(prefix="/hfr", tags=["HFR"])

@router.post(
    "/facility/search",
    response_model=SearchFacilityResponse,
    summary="Search HFR facilities",
)
async def search_facility(
    request: SearchFacilityRequest = Body(...),
    hfr_client: HFRClient = Depends(get_hfr_client),
):
    """Search facilities via HFR API."""
    # Route stays thin—delegates to service
    return await search_facility_service(request=request, hfr_client=hfr_client)
```

### Request Parameter Extraction

Use FastAPI parameter types to extract and validate:

```python
# Query parameters with validation
@router.get("/masters/data")
async def get_master_data(
    type: str = Query(..., min_length=1, max_length=50, description="Master data type"),
    hfr_client: HFRClient = Depends(get_hfr_client),
):
    return await get_master_data_service(master_type=type, hfr_client=hfr_client)

# Body parameters
@router.post("/facility/search")
async def search_facility(
    request: SearchFacilityRequest = Body(...),
    hfr_client: HFRClient = Depends(get_hfr_client),
):
    return await search_facility_service(request=request, hfr_client=hfr_client)

# Header parameters
@router.get("/data")
async def get_data(
    x_request_id: str = Header(..., description="Request ID"),
):
    return {"request_id": x_request_id}

# Combined: Pydantic model with Query
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)

@router.get("/items")
async def list_items(
    params: PaginationParams = Depends(),
):
    pass
```

### Response Status Codes

Explicitly set response status codes:

```python
@router.post("/auth/signup", response_model=SignupResponse, status_code=201)
async def signup(request: SignupRequest):
    """Created (201) for resource creation."""
    pass

@router.post("/auth/login", response_model=LoginResponse, status_code=200)
async def login(request: LoginRequest):
    """OK (200) for successful operation."""
    pass

@router.delete("/resource/{id}", status_code=204)
async def delete_resource(id: UUID):
    """No Content (204) for successful deletion."""
    pass
```

### Cookie and Response Management

```python
def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set secure HTTP-only cookies for token storage."""
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,          # Prevent JS access
        secure=settings.COOKIE_SECURE,  # HTTPS only in production
        samesite=settings.COOKIE_SAMESITE,  # CSRF protection
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_MAX_AGE,
    )

@router.post("/auth/login", response_model=LoginResponse)
async def login(
    response: Response,
    login_request: LoginRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService()
    result = auth_service.login(db=db, request=login_request)
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return LoginResponse(user=result.user)
```

**Best Practices**:
- Routes should be one-liners when possible
- Use descriptive summaries and docstrings
- Extract parameters using FastAPI types (Query, Body, Header, Path)
- Delegate all logic to service layer
- Set explicit response status codes
- Use type hints consistently

---

## Service Layer

Services implement business logic and are located in `api/services/`.

### Service Pattern

Services validate business rules, orchestrate lower layers, and handle errors:

```python
# api/services/hfr_service.py
from api.exceptions import create_error
from api.errors.hfr_errors import HFRErrors

async def search_facility_service(
    request: SearchFacilityRequest,
    hfr_client: HFRClient,
) -> dict:
    """
    Validate business rules and delegate to client.
    
    Business Validation:
    - Either facilityId OR core fields (ownershipCode, stateLGDCode) must be provided
    """
    # Validate business semantics
    has_facility_id = bool((request.facilityId or "").strip())
    has_core_fields = bool(
        (request.ownershipCode or "").strip()
        and (request.stateLGDCode or "").strip()
    )
    
    if not has_facility_id and not has_core_fields:
        raise create_error(
            HFRErrors.HFR_INVALID_SEARCH_REQUEST,
            details={
                "message": "Either facilityId OR (ownershipCode + stateLGDCode) required"
            },
        )
    
    # Delegate to client
    return await hfr_client.search_facility(request)
```

### Service with Database Access

Services that need data access combine repository and business logic:

```python
# api/services/healthprofessional_service.py
from sqlalchemy.orm import Session
from api.repositories import healthprofessional_repo

def get_health_professional_details(
    hp_id: UUID,
    db: Session,
) -> HealthProfessionalDetailsResponse:
    """Fetch and format health professional details."""
    # Repository call
    hp = healthprofessional_repo.get_by_id(db, hp_id)
    
    # Business logic
    if not hp:
        raise create_error(HFRErrors.HEALTH_PROFESSIONAL_NOT_FOUND)
    
    if not hp.hpr_id:
        raise create_error(HFRErrors.HEALTH_PROFESSIONAL_HPR_ID_MISSING)
    
    # Format response
    return HealthProfessionalDetailsResponse(
        hp_id=hp.hp_id,
        hpr_id=hp.hpr_id,
        full_name=hp.full_name,
    )
```

### Service Composition

Services can orchestrate multiple lower-layer calls:

```python
# api/services/basic_information_service.py

async def basic_information_service(
    request: HFRBasicInformationRequest,
    supervisor_hp_id: UUID,
    hfr_client: HFRClient,
    db: Session,
) -> dict:
    """Create/update facility basic information with supervisor validation."""
    # Step 1: Validate supervisor exists and has HPR ID
    hp = healthprofessional_repo.get_by_id(db, supervisor_hp_id)
    if not hp:
        raise create_error(HFRErrors.HEALTH_PROFESSIONAL_NOT_FOUND)
    if not hp.hpr_id:
        raise create_error(HFRErrors.HEALTH_PROFESSIONAL_HPR_ID_MISSING)
    
    # Step 2: Validate facility business rules
    if not request.facility_name or len(request.facility_name) < 3:
        raise create_error(HFRErrors.HFR_INVALID_REQUEST)
    
    # Step 3: Delegate to client
    return await hfr_client.basic_information(request, hpr_id=hp.hpr_id)
```

### Service Error Handling

Always catch and re-raise with appropriate domain errors:

```python
async def submit_facility_service(
    request: HFRSubmitFacilityRequest,
    hfr_client: HFRClient,
) -> dict:
    """Submit facility and handle errors gracefully."""
    try:
        return await hfr_client.submit_facility(request)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            raise create_error(HFRErrors.HFR_SERVICE_UNAVAILABLE) from exc
        else:
            raise create_error(
                HFRErrors.HFR_SUBMIT_FACILITY_FAILED,
                details={"status": exc.response.status_code}
            ) from exc
    except Exception as exc:
        raise create_error(HFRErrors.HFR_CLIENT_ERROR) from exc
```

**Best Practices**:
- Validate all business rules before delegating
- Never expose internal errors to clients
- Always provide context in error details
- Compose multiple operations into logical workflows
- Keep services focused on a single domain

---

## Repository Pattern

Repositories handle all database operations in `api/repositories/`.

### Repository CRUD Operations

```python
# api/repositories/healthprofessional_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api.models.professionals import HealthProfessional
from uuid import UUID

class HealthProfessionalRepository:
    @staticmethod
    def get_by_id(db: Session, hp_id: UUID) -> HealthProfessional | None:
        """Fetch by primary key."""
        return db.query(HealthProfessional).filter(
            HealthProfessional.hp_id == hp_id
        ).first()
    
    @staticmethod
    def get_by_hpr_id(db: Session, hpr_id: str) -> HealthProfessional | None:
        """Fetch by HPR ID."""
        return db.query(HealthProfessional).filter(
            HealthProfessional.hpr_id == hpr_id
        ).first()
    
    @staticmethod
    def create(db: Session, **kwargs) -> HealthProfessional:
        """Create new health professional."""
        hp = HealthProfessional(**kwargs)
        db.add(hp)
        db.commit()
        db.refresh(hp)
        return hp
    
    @staticmethod
    def update(db: Session, hp_id: UUID, **kwargs) -> HealthProfessional | None:
        """Update existing record."""
        hp = db.query(HealthProfessional).filter(
            HealthProfessional.hp_id == hp_id
        ).first()
        
        if not hp:
            return None
        
        for key, value in kwargs.items():
            if hasattr(hp, key):
                setattr(hp, key, value)
        
        db.commit()
        db.refresh(hp)
        return hp
    
    @staticmethod
    def delete(db: Session, hp_id: UUID) -> bool:
        """Delete record."""
        hp = db.query(HealthProfessional).filter(
            HealthProfessional.hp_id == hp_id
        ).first()
        
        if not hp:
            return False
        
        db.delete(hp)
        db.commit()
        return True
```

### Complex Queries

```python
@staticmethod
def find_by_criteria(
    db: Session,
    state_id: Optional[int] = None,
    hpr_id: Optional[str] = None,
    name_pattern: Optional[str] = None,
) -> list[HealthProfessional]:
    """Complex query with multiple filters."""
    query = db.query(HealthProfessional)
    
    if state_id:
        query = query.filter(HealthProfessional.state_id == state_id)
    
    if hpr_id:
        query = query.filter(HealthProfessional.hpr_id == hpr_id)
    
    if name_pattern:
        query = query.filter(
            HealthProfessional.full_name.ilike(f"%{name_pattern}%")
        )
    
    return query.all()
```

**Best Practices**:
- Repositories handle only database operations (no business logic)
- Use type hints for clarity
- Return None instead of raising exceptions for not-found queries
- Encapsulate complex queries in dedicated methods
- Always commit/refresh after modifications

---

## Pagination

Implement cursor-based and offset-based pagination consistently.

### Pagination Models

```python
# api/common/pagination.py
from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional

T = TypeVar("T")

class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(10, ge=1, le=100, description="Results per page")

class Page(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.pages
    
    @property
    def has_previous(self) -> bool:
        return self.page > 1
```

### Service Pagination

```python
# api/services/healthprofessional_service.py
from api.common.pagination import PaginationParams, Page

def list_verification_requests_paginated(
    db: Session,
    supervisor_hp_id: UUID,
    facility_id: str,
    status: Optional[VerificationStatusEnum],
    pagination: PaginationParams,
) -> Page[HealthProfessionalVerificationRequestItem]:
    """Fetch paginated verification requests."""
    # Build query
    query = db.query(VerificationRequest).filter(
        and_(
            VerificationRequest.supervisor_hp_id == supervisor_hp_id,
            VerificationRequest.facility_id == facility_id,
        )
    )
    
    if status:
        query = query.filter(VerificationRequest.status == status)
    
    # Total count
    total = query.count()
    
    # Paginate
    offset = (pagination.page - 1) * pagination.limit
    items = query.offset(offset).limit(pagination.limit).all()
    
    # Format response
    pages = (total + pagination.limit - 1) // pagination.limit
    return Page(
        items=[HealthProfessionalVerificationRequestItem.from_orm(item) for item in items],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        pages=pages,
    )
```

### Router Pagination

```python
# api/routers/healthprofessional.py
@router.get(
    "/verification-requests",
    response_model=Page[HealthProfessionalVerificationRequestItem],
)
def get_verification_requests(
    supervisor_hp_id: UUID = Depends(get_health_professional_id_from_cookie),
    facility_id: str = Query(..., description="Facility ID filter"),
    status: Optional[VerificationStatusEnum] = Query(VerificationStatusEnum.submitted),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    """List verification requests with pagination."""
    return list_verification_requests_paginated(
        db=db,
        supervisor_hp_id=supervisor_hp_id,
        facility_id=facility_id,
        status=status,
        pagination=pagination,
    )
```

---

## Rate Limiting

Implement rate limiting to protect APIs from abuse.

### Rate Limit Dependencies

```python
# api/dependencies.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# In main.py
app.state.limiter = limiter
```

### Applied Rate Limits

```python
# api/routers/auth.py
@router.post("/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # 5 login attempts per minute
async def login(request: Request, login_request: LoginRequest, db: Session = Depends(get_db)):
    pass

# api/routers/hfr.py
@router.post("/facility/search", response_model=SearchFacilityResponse)
@limiter.limit("100/hour")  # 100 searches per hour
async def search_facility(request: SearchFacilityRequest):
    pass
```

**Rate Limit Strategies**:
- **Auth Endpoints**: 5-10 requests per minute (brute force protection)
- **Search/Get Endpoints**: 100-1000 per hour (data retrieval)
- **Write Endpoints**: 10-50 per minute (data modification)

---

## Authentication & Authorization

### Token Structure

Tokens encode identity and permissions via JWT claims:

```python
# api/common/jwt_service.py
from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class TokenPayload:
    """Structured JWT token payload."""
    sub: str                        # User Auth ID
    entity_type: str               # EntityTypeEnum (caregiver, hp, admin, etc.)
    persona: str                   # PersonaEnum (caregiver, hp, admin, etc.)
    jti: Optional[str]             # JWT ID (for token revocation)
    exp: int                       # Expiry timestamp
    claims: Dict[str, Any]         # Extra claims (cg_id, hp_id, etc.)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.sub,
            "entity_type": self.entity_type,
            "persona": self.persona,
            "jti": self.jti,
            "exp": self.exp,
            **self.claims,  # Spread extra claims into token
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "TokenPayload":
        return TokenPayload(
            sub=payload["sub"],
            entity_type=payload["entity_type"],
            persona=payload["persona"],
            jti=payload.get("jti"),
            exp=payload["exp"],
            claims={k: v for k, v in payload.items() 
                   if k not in {"sub", "entity_type", "persona", "jti", "exp"}},
        )
```

### Creating Access Tokens

```python
class JwtService:
    def create_access_token(
        self,
        user_auth_id: str,
        entity_type: str,
        persona: str,
        expires_in_minutes: Optional[int] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create access token with structured payload.
        
        Example:
            token = jwt_service.create_access_token(
                user_auth_id=str(user_auth.id),
                entity_type=EntityTypeEnum.caregiver,
                persona=PersonaEnum.caregiver,
                extra_claims={"cg_id": str(caregiver.cg_id)},
            )
        """
        if expires_in_minutes is None:
            expires_in_minutes = self.access_token_expire_minutes
        
        expire = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        payload = {
            "sub": user_auth_id,
            "entity_type": entity_type,
            "persona": persona,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            **(extra_claims or {}),
        }
        
        encoded = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded
```

### Mobile Verification Flow

Before signup, verify mobile via OTP:

```python
# api/dependencies.py

def get_verified_mobile(request: Request) -> str:
    """Validate mobile-verification cookie and return verified mobile number."""
    mobile_verification_token = request.cookies.get(settings.MOBILE_VERIFICATION_COOKIE_NAME)
    
    if not mobile_verification_token:
        raise create_error(OtpErrors.MOBILE_VERIFICATION_COOKIE_NOT_FOUND)
    
    try:
        payload = jwt.decode(
            mobile_verification_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.InvalidTokenError as exc:
        raise create_error(OtpErrors.INVALID_VERIFICATION_TOKEN) from exc
    
    if payload.get("purpose") != "mobile_verification":
        raise create_error(OtpErrors.INVALID_VERIFICATION_TOKEN)
    
    if payload.get("verified") is not True:
        raise create_error(OtpErrors.MOBILE_NOT_VERIFIED)
    
    mobile = payload.get("mobile")
    if not mobile:
        raise create_error(OtpErrors.INVALID_VERIFICATION_TOKEN)
    
    return mobile

# Usage in signup
@router.post("/auth/signup", response_model=SignupResponse, status_code=201)
async def signup(
    response: Response,
    signup_request: HealthProfessionalSignupRequest,
    db: Session = Depends(get_db),
    jwt_service: JwtService = Depends(get_jwt_service),
    verified_mobile: str = Depends(get_verified_mobile),
):
    """Signup requires pre-verified mobile number."""
    auth_service = AuthService(jwt_service)
    result = auth_service.signup(
        db=db,
        signup_request=signup_request,
        mobile=verified_mobile,
    )
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return SignupResponse(user=result.user)
```

### Role-Based Access Control

```python
# Enums for structured roles
# api/enums/auth.py
from enum import Enum

class EntityTypeEnum(str, Enum):
    """Entity types (who you are)."""
    caregiver = "caregiver"
    health_professional = "health_professional"
    admin = "admin"

class PersonaEnum(str, Enum):
    """Personas (what you can do)."""
    caregiver = "caregiver"
    hp = "hp"
    admin = "admin"

# Validate roles in dependencies
def _get_health_professional_id_from_payload(payload: TokenPayload) -> UUID:
    """Extract HP ID with persona validation."""
    if payload.persona != PersonaEnum.hp.value:
        raise create_error(AuthErrors.INVALID_ROLE)
    
    if payload.entity_type != EntityTypeEnum.health_professional.value:
        raise create_error(AuthErrors.INVALID_ROLE)
    
    hp_id = payload.claims.get("hp_id")
    if not hp_id:
        raise create_error(AuthErrors.INVALID_TOKEN)
    
    return UUID(str(hp_id))
```

### Cookie Management

```python
# Secure cookie settings
@dataclass(frozen=True)
class CookieConfig:
    """Immutable cookie configuration."""
    name: str
    max_age: int
    httponly: bool = True
    secure: bool = True      # HTTPS only
    samesite: str = "Strict"  # CSRF protection

# In main.py
HP_ACCESS_COOKIE_CONFIG = CookieConfig(
    name="hp_access_token",
    max_age=settings.HP_ACCESS_COOKIE_MAX_AGE,
    secure=settings.COOKIE_SECURE,
)

# In route handler
def _set_health_professional_auth_cookies(
    response: Response, 
    access_token: str, 
    refresh_token: str
) -> None:
    response.set_cookie(
        key=settings.HP_ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=_hp_access_cookie_max_age(),
    )
    response.set_cookie(
        key=settings.HP_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.HP_REFRESH_COOKIE_MAX_AGE,
    )
```

---

## Validation Patterns

### Pre-Validator: Normalize Input

```python
class SearchFacilityRequest(BaseModel):
    facilityId: Optional[str] = None
    facilityName: Optional[str] = None
    pincode: Optional[str] = None
    
    # Pre-validators run before other validators
    @validator("facilityId", "facilityName", "pincode", pre=True)
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Trim whitespace and convert empty strings to None."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
```

### Field-Specific Validators

```python
@validator("pincode")
def validate_pincode(cls, value: Optional[str]) -> Optional[str]:
    """Validate 6-digit pincode format."""
    if value is None:
        return value
    if not re.fullmatch(r"\d{6}", value):
        raise ValueError("Pincode must be a 6-digit number")
    return value

@validator("ownershipCode")
def validate_ownership_code(cls, value: Optional[str]) -> Optional[str]:
    """Validate ownership code is one of allowed values."""
    if value is None:
        return value
    if value.upper() not in {"G", "P", "PP"}:
        raise ValueError("ownershipCode must be one of: G, P, PP")
    return value.upper()
```

### Cross-Field Validation

```python
@root_validator
def validate_search_constraints(cls, values: dict) -> dict:
    """Ensure required fields are provided together."""
    has_facility_id = bool((values.get("facilityId") or "").strip())
    has_core_fields = bool(
        (values.get("ownershipCode") or "").strip()
        and (values.get("stateLGDCode") or "").strip()
    )
    
    if not has_facility_id and not has_core_fields:
        raise ValueError(
            "Either facilityId OR (ownershipCode + stateLGDCode) must be provided"
        )
    
    return values
```

### File Upload Validation

```python
class DocumentUploadRequest(BaseModel):
    file_name: str = Field(..., max_length=200)
    file_content: str = Field(..., max_length=6_000_000)  # ~5MB base64
    file_type: str = Field(..., pattern="^(jpg|jpeg|png|pdf)$")
    
    @validator("file_content")
    def validate_file_content(cls, value: str) -> str:
        """Validate base64 encoding and size."""
        try:
            decoded = base64.b64decode(value, validate=True)
            if len(decoded) > 5_000_000:  # 5MB limit
                raise ValueError("File exceeds 5MB limit")
            return value
        except (TypeError, binascii.Error):
            raise ValueError("Invalid base64 encoding")
```

### Email Validation

```python
from pydantic import EmailStr

class RegistrationRequest(BaseModel):
    email: EmailStr  # Automatic RFC 5322 validation
    mobile: str = Field(..., regex=r"^\d{10}$")  # 10-digit mobile
    website: Optional[str] = Field(None, regex=WEBSITE_PATTERN.pattern)
```

---

## Configuration Management

Configuration is centralized in environment variables accessed via settings:

```python
# api/config/settings.py
import os
from typing import Optional

class Settings:
    @staticmethod
    def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
        """Read and validate environment variable."""
        value = os.getenv(name, default)
        if required and not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value
    
    def __init__(self):
        # Auth
        self.SECRET_KEY = self._get_env("SECRET_KEY", required=True)
        self.ALGORITHM = self._get_env("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(self._get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        
        # Database
        self.DATABASE_URL = self._get_env("DATABASE_URL", required=True)
        
        # Redis
        self.REDIS_URL = self._get_env("REDIS_URL", required=True)
        
        # API URLs
        self.HPR_BASE_URL = self._get_env("HPR_BASE_URL", required=True)
        self.HFR_BASE_URL = self._get_env("HFR_BASE_URL", required=True)
        
        # Cookies
        self.ACCESS_COOKIE_NAME = self._get_env("ACCESS_COOKIE_NAME", "access_token")
        self.COOKIE_SECURE = self._get_env("COOKIE_SECURE", "true").lower() == "true"
        self.COOKIE_SAMESITE = self._get_env("COOKIE_SAMESITE", "Strict")

settings = Settings()
```

---

## Summary: Best Practices Checklist

✅ **Architecture**
- [ ] Keep routers thin—logic belongs in services
- [ ] Validate in schemas, not in routes
- [ ] Use dependency injection for all external services
- [ ] Handle errors at appropriate layers (services, not routes)

✅ **Schemas**
- [ ] Use pre-validators for normalization
- [ ] Use field validators for single-field rules
- [ ] Use root validators for cross-field rules
- [ ] Define regex patterns as module-level constants
- [ ] Set max_length on all string fields

✅ **Error Handling**
- [ ] Define errors in `api/errors/` using `ErrorDefinition`
- [ ] Always raise with `create_error()` factory
- [ ] Include contextual details in error responses
- [ ] Never expose internal implementation details

✅ **Dependencies**
- [ ] Extract dependencies to `api/dependencies.py`
- [ ] Use app.state for singletons
- [ ] Compose dependencies to build complex ones
- [ ] Validate extracted values and raise appropriate errors

✅ **Repositories**
- [ ] Handle only database operations
- [ ] Return None for not-found queries (not exceptions)
- [ ] Encapsulate complex queries in dedicated methods
- [ ] Always commit/refresh after modifications

✅ **Authentication**
- [ ] Use JWT for stateless token-based auth
- [ ] Store tokens in HTTP-only cookies
- [ ] Validate personas and entity types in dependencies
- [ ] Use role-based access control dependencies

✅ **Configuration**
- [ ] Centralize all configuration in settings
- [ ] Use environment variables for all secrets
- [ ] Validate required settings on startup
- [ ] Never hardcode config values
