#!/usr/bin/env python3
"""
Automated admin setup script for Medical Forms API
"""
import os
import sys
from sqlalchemy.orm import Session
from database import SessionLocal, create_tables, User, UserRole
from auth import PasswordHash

def create_admin_automatically():
    """Create the initial admin user automatically"""
    
    print("🔧 Medical Forms API - Automated Admin Setup")
    print("=" * 50)
    
    # Set environment variables if not set
    if not os.getenv('JWT_SECRET_KEY'):
        os.environ['JWT_SECRET_KEY'] = 'aNzcN4DuxkQfQRa_7Rp7qajI3p4pKQJYFmXwk12Ccro'
    
    if not os.getenv('DATABASE_URL'):
        os.environ['DATABASE_URL'] = 'sqlite:///./medical_forms.db'
    
    # Create database tables
    print("📊 Creating database tables...")
    create_tables()
    print("✅ Database tables created successfully")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check if any admin users exist
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        
        if existing_admin:
            print(f"⚠️  Admin user already exists: {existing_admin.email}")
            return existing_admin
        
        print("\n👤 Creating Admin User")
        print("-" * 30)
        
        # Create admin user with default credentials
        admin_email = "admin@medicaldocai.com"
        admin_password = "Admin123!"
        admin_name = "System Administrator"
        
        # Create admin user
        admin_user = User(
            email=admin_email,
            hashed_password=PasswordHash.hash_password(admin_password),
            full_name=admin_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: {admin_password}")
        print(f"   Name: {admin_user.full_name}")
        print(f"   Role: {admin_user.role.value}")
        print(f"   Created: {admin_user.created_at}")
        
        # Create sample users for different roles
        create_sample_users(db)
        
        print("\n🎉 Setup completed successfully!")
        print("\nAdmin Login Credentials:")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print("\nNext steps:")
        print("1. Start the API server: python main.py")
        print("2. Access API docs: http://localhost:8000/docs")
        print("3. Login with admin credentials")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

def create_sample_users(db: Session):
    """Create sample users for different roles"""
    
    sample_users = [
        {
            "email": "physician@medicaldocai.com",
            "full_name": "Dr. Sarah Johnson",
            "role": UserRole.PHYSICIAN,
            "password": "Physician123!"
        },
        {
            "email": "nurse@medicaldocai.com", 
            "full_name": "Nurse Mary Smith",
            "role": UserRole.NURSE,
            "password": "Nurse123!"
        },
        {
            "email": "technician@medicaldocai.com",
            "full_name": "Tech John Doe",
            "role": UserRole.TECHNICIAN,
            "password": "Tech123!"
        },
        {
            "email": "viewer@medicaldocai.com",
            "full_name": "Viewer Jane Wilson",
            "role": UserRole.VIEWER,
            "password": "Viewer123!"
        }
    ]
    
    print("\n👥 Creating sample users...")
    
    for user_data in sample_users:
        # Check if user already exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"   ⚠️  User {user_data['email']} already exists, skipping")
            continue
        
        user = User(
            email=user_data["email"],
            hashed_password=PasswordHash.hash_password(user_data["password"]),
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
        print(f"   ✅ Created {user_data['role'].value}: {user_data['email']}")
    
    db.commit()
    
    print("\n📋 Sample User Credentials:")
    print("-" * 40)
    for user_data in sample_users:
        print(f"Role: {user_data['role'].value.title()}")
        print(f"Email: {user_data['email']}")
        print(f"Password: {user_data['password']}")
        print(f"Name: {user_data['full_name']}")
        print("-" * 40)

if __name__ == "__main__":
    create_admin_automatically()