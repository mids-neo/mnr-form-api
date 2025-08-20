"""
Authentication and user management API routes
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
import secrets
import uuid

from database import (
    get_db, User, UserSession, UserRole, AuditLog, AuditAction, 
    FileProcessingLog, has_permission
)
from auth import (
    PasswordHash, JWTManager, MFAManager, SecurityValidator,
    get_current_user, require_permission, require_role,
    log_audit_event, get_client_ip, get_user_agent,
    MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic models for API requests/responses
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[UserRole] = UserRole.GUEST
    
    @validator('password')
    def validate_password(cls, v):
        validation = SecurityValidator.validate_password_strength(v)
        if not validation["is_valid"]:
            raise ValueError(f"Password validation failed: {', '.join(validation['errors'])}")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        validation = SecurityValidator.validate_password_strength(v)
        if not validation["is_valid"]:
            raise ValueError(f"Password validation failed: {', '.join(validation['errors'])}")
        return v

class MFASetup(BaseModel):
    totp_code: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("can_manage_users"))
):
    """Register a new user (Admin only)"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=PasswordHash.hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_verified=True  # Admin-created users are pre-verified
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log audit event
    await log_audit_event(
        db=db,
        action=AuditAction.USER_CREATE,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        endpoint="/auth/register",
        method="POST",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={
            "created_user_email": user.email,
            "created_user_role": user.role.value,
            "created_by": current_user.email
        }
    )
    
    return UserResponse.from_orm(user)

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT tokens"""
    
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        # Log failed login attempt
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN,
            endpoint="/auth/login",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="User not found",
            details={"attempted_email": login_data.email}
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user.id,
            endpoint="/auth/login",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Account locked"
        )
        raise HTTPException(status_code=401, detail="Account is temporarily locked")
    
    # Verify password
    if not PasswordHash.verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        
        # Lock account if too many failures
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            error_message = f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes"
        else:
            error_message = "Invalid credentials"
        
        db.commit()
        
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user.id,
            endpoint="/auth/login",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=error_message,
            details={"failed_attempts": user.failed_login_attempts}
        )
        
        raise HTTPException(status_code=401, detail=error_message)
    
    # Check if account is active
    if not user.is_active:
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user.id,
            endpoint="/auth/login",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Account disabled"
        )
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    # Check MFA if enabled
    if user.mfa_enabled:
        if not login_data.totp_code:
            raise HTTPException(status_code=422, detail="TOTP code required for MFA")
        
        if not MFAManager.verify_totp(user.mfa_secret, login_data.totp_code):
            user.failed_login_attempts += 1
            db.commit()
            
            await log_audit_event(
                db=db,
                action=AuditAction.LOGIN,
                user_id=user.id,
                endpoint="/auth/login",
                method="POST",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="Invalid MFA code"
            )
            
            raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    
    # Create session
    token_id = str(uuid.uuid4())
    session = UserSession(
        user_id=user.id,
        token_id=token_id,
        device_info=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Generate tokens
    token_data = {
        "sub": str(user.id),  # JWT 'sub' must be a string
        "email": user.email,
        "role": user.role.value,
        "jti": token_id
    }
    
    access_token = JWTManager.create_access_token(token_data)
    refresh_token = JWTManager.create_refresh_token(token_data)
    
    # Log successful login
    await log_audit_event(
        db=db,
        action=AuditAction.LOGIN,
        user_id=user.id,
        session_id=session.id,
        endpoint="/auth/login",
        method="POST",
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        details={"session_id": session.id}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,  # 30 minutes
        user=UserResponse.from_orm(user)
    )

@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user and revoke session"""
    
    # Get the authorization header to extract token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = JWTManager.decode_token(token)
        token_id = payload.get("jti")
        
        # Revoke the session
        session = db.query(UserSession).filter(
            UserSession.token_id == token_id,
            UserSession.user_id == current_user.id
        ).first()
        
        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    
    # Log logout
    await log_audit_event(
        db=db,
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        endpoint="/auth/logout",
        method="POST",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not PasswordHash.verify_password(password_data.current_password, current_user.hashed_password):
        await log_audit_event(
            db=db,
            action=AuditAction.PASSWORD_CHANGE,
            user_id=current_user.id,
            endpoint="/auth/change-password",
            method="POST",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False,
            error_message="Invalid current password"
        )
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # Update password
    current_user.hashed_password = PasswordHash.hash_password(password_data.new_password)
    db.commit()
    
    # Log password change
    await log_audit_event(
        db=db,
        action=AuditAction.PASSWORD_CHANGE,
        user_id=current_user.id,
        endpoint="/auth/change-password",
        method="POST",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True
    )
    
    return {"message": "Password changed successfully"}

@router.post("/setup-mfa")
async def setup_mfa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup MFA for user account"""
    
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")
    
    # Generate new secret
    secret = MFAManager.generate_secret()
    qr_code = MFAManager.generate_qr_code(current_user.email, secret)
    backup_codes = MFAManager.generate_backup_codes()
    
    # Store secret temporarily (not committed until verification)
    current_user.mfa_secret = secret
    current_user.backup_codes = backup_codes
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": backup_codes,
        "message": "Complete setup by verifying TOTP code"
    }

@router.post("/verify-mfa")
async def verify_mfa_setup(
    mfa_data: MFASetup,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify and enable MFA"""
    
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")
    
    # Verify TOTP code
    if not MFAManager.verify_totp(current_user.mfa_secret, mfa_data.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Enable MFA
    current_user.mfa_enabled = True
    db.commit()
    
    # Log MFA enable
    await log_audit_event(
        db=db,
        action=AuditAction.MFA_ENABLE,
        user_id=current_user.id,
        endpoint="/auth/verify-mfa",
        method="POST",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"message": "MFA enabled successfully", "backup_codes": current_user.backup_codes}

@router.post("/disable-mfa")
async def disable_mfa(
    password_data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable MFA (requires password confirmation)"""
    
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    
    # Verify password
    if not PasswordHash.verify_password(password_data.get("password", ""), current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.backup_codes = None
    db.commit()
    
    # Log MFA disable
    await log_audit_event(
        db=db,
        action=AuditAction.MFA_DISABLE,
        user_id=current_user.id,
        endpoint="/auth/disable-mfa",
        method="POST",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"message": "MFA disabled successfully"}

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("can_manage_users")),
    db: Session = Depends(get_db)
):
    """List all users (Admin only)"""
    
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.from_orm(user) for user in users]

@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_data: dict,
    request: Request,
    current_user: User = Depends(require_permission("can_manage_users")),
    db: Session = Depends(get_db)
):
    """Update user role (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_role = UserRole(role_data.get("role"))
    old_role = user.role
    
    user.role = new_role
    db.commit()
    
    # Log role change
    await log_audit_event(
        db=db,
        action=AuditAction.ROLE_CHANGE,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user_id),
        endpoint=f"/auth/users/{user_id}/role",
        method="PATCH",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={
            "target_user": user.email,
            "old_role": old_role.value,
            "new_role": new_role.value
        }
    )
    
    return {"message": f"User role updated to {new_role.value}"}

@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[AuditAction] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(require_permission("can_view_audit_logs")),
    db: Session = Depends(get_db)
):
    """Get audit logs (Admin/Physician only)"""
    
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action.value,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "endpoint": log.endpoint,
            "ip_address": log.ip_address,
            "success": log.success,
            "timestamp": log.timestamp,
            "details": log.details
        }
        for log in logs
    ]