"""
Authentication utilities, JWT handling, and security functions
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
import jwt
from jwt.exceptions import InvalidTokenError
import bcrypt
import secrets
import pyotp
import qrcode
import io
import base64
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..models import get_db, User, UserSession, UserRole, AuditLog, AuditAction
import os
import logging

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"

# JWT Secret Key loaded successfully
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

security = HTTPBearer()

class PasswordHash:
    """Password hashing utilities using bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class JWTManager:
    """JWT token management"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token expired: {e}")
            raise HTTPException(status_code=401, detail="Token has expired")
        except InvalidTokenError as e:
            logger.error(f"Invalid token error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Unexpected JWT decode error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")

class MFAManager:
    """Multi-Factor Authentication using TOTP"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(email: str, secret: str, app_name: str = "Medical Forms App") -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=app_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify a TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=2)  # Allow 2 time windows for clock skew
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate backup codes for MFA recovery"""
        return [secrets.token_hex(4).upper() for _ in range(count)]

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        score = 0
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        elif len(password) >= 12:
            score += 2
        else:
            score += 1
            
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            score += 1
            
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            score += 1
            
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        else:
            score += 1
            
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        else:
            score += 1
            
        strength_levels = {
            0: "Very Weak",
            1: "Weak", 
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong",
            6: "Excellent"
        }
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "strength": strength_levels.get(score, "Very Weak"),
            "score": score
        }

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    try:
        # Decode the JWT token
        payload = JWTManager.decode_token(credentials.credentials)
        
        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Get user ID and session ID from token
        user_id_str: str = payload.get("sub")
        token_id: str = payload.get("jti")
        
        if user_id_str is None or token_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid user ID in token")
        
        # Check if session is still active
        session = db.query(UserSession).filter(
            UserSession.token_id == token_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not session:
            raise HTTPException(status_code=401, detail="Session expired or revoked")
        
        # Get the user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is disabled")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Account is temporarily locked")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        from ..models import has_permission
        
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_checker

def require_role(required_role: UserRole):
    """Decorator to require specific role or higher"""
    role_hierarchy = {
        UserRole.GUEST: 0,
        UserRole.VIEWER: 1,
        UserRole.TECHNICIAN: 2,
        UserRole.NURSE: 3,
        UserRole.PHYSICIAN: 4,
        UserRole.ADMIN: 5
    }
    
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 5)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient role. Required: {required_role.value} or higher"
            )
        return current_user
    
    return role_checker

async def log_audit_event(
    db: Session,
    action: AuditAction,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    contains_phi: bool = False,
    data_classification: str = "internal"
):
    """Log an audit event"""
    
    audit_log = AuditLog(
        user_id=user_id,
        session_id=session_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        endpoint=endpoint,
        method=method,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        success=success,
        error_message=error_message,
        contains_phi=contains_phi,
        data_classification=data_classification
    )
    
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Audit log created: {action.value} by user {user_id}")

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"

def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")