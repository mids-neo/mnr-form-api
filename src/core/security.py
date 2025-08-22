"""
Security configuration and utilities
"""

import secrets
from typing import Dict, Any

class SecuritySettings:
    """Security configuration"""
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # Session settings
    SESSION_TIMEOUT_MINUTES = 30
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # JWT settings
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = "mnr-form-api"
    
    # File security
    ALLOWED_FILE_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    MAX_FILE_SIZE_MB = 50
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW_MINUTES = 15
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < SecuritySettings.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {SecuritySettings.MIN_PASSWORD_LENGTH} characters")
        
        if SecuritySettings.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if SecuritySettings.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if SecuritySettings.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if SecuritySettings.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "strength_score": max(0, 100 - (len(errors) * 20))
        }