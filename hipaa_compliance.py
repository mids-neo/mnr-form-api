#!/usr/bin/env python3
"""
HIPAA Compliance Module
=======================

Provides utilities and validation for HIPAA compliance in medical form processing.

Key HIPAA Requirements:
- Access Control: Only authorized users can access PHI
- Audit Controls: Comprehensive logging of all PHI access and modifications
- Integrity: PHI must not be improperly altered or destroyed
- Person or Entity Authentication: Verify identity of users accessing PHI
- Transmission Security: Guard against unauthorized access during transmission
"""

import logging
import os
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class HIPAAValidator:
    """Validates HIPAA compliance requirements"""
    
    REQUIRED_USER_FIELDS = ['user_id', 'user_email', 'user_role']
    REQUIRED_SESSION_FIELDS = ['session_id', 'processing_session']
    REQUIRED_AUDIT_FIELDS = ['audit_enabled']
    
    @classmethod
    def validate_pipeline_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pipeline configuration for HIPAA compliance"""
        validation_result = {
            'is_compliant': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check required user tracking fields
        for field in cls.REQUIRED_USER_FIELDS:
            if not config.get(field):
                validation_result['errors'].append(f"Missing required HIPAA field: {field}")
                validation_result['is_compliant'] = False
        
        # Check session tracking
        for field in cls.REQUIRED_SESSION_FIELDS:
            if not config.get(field):
                validation_result['warnings'].append(f"Missing recommended session field: {field}")
        
        # Check audit controls
        if not config.get('audit_enabled', False):
            validation_result['errors'].append("Audit logging must be enabled for HIPAA compliance")
            validation_result['is_compliant'] = False
        
        # Check encryption
        if not config.get('phi_encryption', False):
            validation_result['warnings'].append("PHI encryption is recommended for enhanced security")
        
        # Validate user role
        user_role = config.get('user_role')
        if user_role and user_role not in ['admin', 'physician', 'nurse', 'technician']:
            validation_result['warnings'].append(f"Unusual user role for PHI access: {user_role}")
        
        return validation_result
    
    @classmethod
    def validate_file_processing(cls, user_id: int, file_info: Dict[str, Any]) -> bool:
        """Validate if user is authorized to process specific file"""
        # In a real implementation, this would check:
        # - User permissions for specific patient data
        # - Patient consent records
        # - Business associate agreements
        # - Access controls based on minimum necessary principle
        
        logger.info(f"🔒 HIPAA: Validating file access for user {user_id}")
        return True  # Simplified for demo
    
    @classmethod
    def log_phi_access(cls, user_id: int, user_email: str, action: str, 
                      phi_identifiers: Optional[Dict[str, Any]] = None):
        """Log PHI access for audit trail"""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'user_email': user_email,
            'action': action,
            'phi_accessed': bool(phi_identifiers),
            'phi_summary': cls._sanitize_phi_for_audit(phi_identifiers) if phi_identifiers else None
        }
        
        # In production, this would go to a secure audit database
        logger.info(f"🔒 HIPAA Audit: {action} by user {user_id}")

    @classmethod
    def _sanitize_phi_for_audit(cls, phi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize PHI data for audit logging (remove actual PHI)"""
        if not phi_data:
            return {}
        
        # Only log metadata, not actual PHI content
        sanitized = {
            'field_count': len(phi_data),
            'has_patient_name': bool(phi_data.get('patient_name')),
            'has_dob': bool(phi_data.get('date_of_birth')),
            'has_mrn': bool(phi_data.get('medical_record_number')),
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return sanitized

class PHIEncryption:
    """Handles encryption/decryption of PHI data"""
    
    def __init__(self, password: Optional[str] = None):
        """Initialize encryption with password or environment variable"""
        self.password = password or os.getenv('PHI_ENCRYPTION_KEY', 'default-key-change-in-production')
        self.key = self._derive_key(self.password)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        password_bytes = password.encode()
        salt = b'hipaa_salt_2024'  # In production, use random salt per record
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def encrypt_phi_data(self, data: Dict[str, Any]) -> str:
        """Encrypt PHI data for storage"""
        json_data = json.dumps(data, sort_keys=True)
        encrypted_data = self.cipher.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_phi_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt PHI data"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())
    
    def hash_phi_identifier(self, identifier: str) -> str:
        """Create hash of PHI identifier for indexing without storing actual value"""
        return hashlib.sha256(f"{identifier}{self.password}".encode()).hexdigest()

class HIPAADataRetention:
    """Manages HIPAA-compliant data retention and purging"""
    
    # HIPAA requires medical records to be retained for 6 years
    DEFAULT_RETENTION_DAYS = 6 * 365  # 6 years
    
    @classmethod
    def should_purge_record(cls, created_date: datetime, 
                           retention_days: int = DEFAULT_RETENTION_DAYS) -> bool:
        """Check if a record should be purged based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return created_date < cutoff_date
    
    @classmethod
    def get_retention_status(cls, created_date: datetime) -> Dict[str, Any]:
        """Get retention status for a record"""
        now = datetime.now(timezone.utc)
        age_days = (now - created_date).days
        days_until_purge = cls.DEFAULT_RETENTION_DAYS - age_days
        
        return {
            'age_days': age_days,
            'retention_period_days': cls.DEFAULT_RETENTION_DAYS,
            'days_until_purge': max(0, days_until_purge),
            'eligible_for_purge': days_until_purge <= 0,
            'retention_category': cls._get_retention_category(days_until_purge)
        }
    
    @classmethod
    def _get_retention_category(cls, days_until_purge: int) -> str:
        """Categorize retention status"""
        if days_until_purge <= 0:
            return 'eligible_for_purge'
        elif days_until_purge <= 30:
            return 'purge_soon'
        elif days_until_purge <= 180:
            return 'nearing_purge'
        else:
            return 'active_retention'

class HIPAAAccessControl:
    """Manages HIPAA access controls and minimum necessary principle"""
    
    USER_PERMISSIONS = {
        'admin': ['read', 'write', 'delete', 'audit', 'user_management'],
        'physician': ['read', 'write', 'audit'],
        'nurse': ['read', 'write'],
        'technician': ['read', 'write'],
        'viewer': ['read'],
        'guest': []
    }
    
    @classmethod
    def check_permission(cls, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        user_permissions = cls.USER_PERMISSIONS.get(user_role, [])
        return required_permission in user_permissions
    
    @classmethod
    def validate_minimum_necessary(cls, user_role: str, requested_data: List[str]) -> Dict[str, Any]:
        """Validate access request against minimum necessary principle"""
        
        # Define what data each role should typically need
        role_data_needs = {
            'physician': ['patient_demographics', 'medical_history', 'diagnoses', 'treatments'],
            'nurse': ['patient_demographics', 'current_medications', 'care_plan'],
            'technician': ['patient_demographics', 'test_orders'],
            'viewer': ['patient_demographics']
        }
        
        necessary_data = role_data_needs.get(user_role, [])
        excessive_access = [data for data in requested_data if data not in necessary_data]
        
        return {
            'compliant': len(excessive_access) == 0,
            'necessary_data': necessary_data,
            'requested_data': requested_data,
            'excessive_access': excessive_access,
            'recommendation': 'Review access request for minimum necessary compliance' if excessive_access else 'Access request is compliant'
        }

# Utility functions for easy access
def validate_hipaa_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for HIPAA validation"""
    return HIPAAValidator.validate_pipeline_config(config)

def encrypt_phi(data: Dict[str, Any], password: Optional[str] = None) -> str:
    """Convenience function for PHI encryption"""
    encryptor = PHIEncryption(password)
    return encryptor.encrypt_phi_data(data)

def decrypt_phi(encrypted_data: str, password: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for PHI decryption"""
    encryptor = PHIEncryption(password)
    return encryptor.decrypt_phi_data(encrypted_data)

def log_phi_access(user_id: int, user_email: str, action: str, 
                  phi_identifiers: Optional[Dict[str, Any]] = None):
    """Convenience function for PHI access logging"""
    return HIPAAValidator.log_phi_access(user_id, user_email, action, phi_identifiers)