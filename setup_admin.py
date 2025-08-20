#!/usr/bin/env python3
"""
Admin setup script for Medical Forms API
Creates initial admin user and sets up database
"""
import os
import sys
import getpass
from sqlalchemy.orm import Session
from database import SessionLocal, create_tables, User, UserRole
from auth import PasswordHash, SecurityValidator

def create_initial_admin():
    """Create the initial admin user"""
    
    print("🔧 Medical Forms API - Admin Setup")
    print("=" * 50)
    
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
            response = input("Do you want to create another admin user? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return
        
        print("\n👤 Creating Admin User")
        print("-" * 30)
        
        # Get admin details
        while True:
            email = input("Admin Email: ").strip()
            if not email:
                print("❌ Email is required")
                continue
            
            # Check if email exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                print("❌ User with this email already exists")
                continue
            
            break
        
        full_name = input("Full Name: ").strip()
        if not full_name:
            full_name = "System Administrator"
        
        # Get secure password
        while True:
            password = getpass.getpass("Password: ")
            if not password:
                print("❌ Password is required")
                continue
            
            # Validate password strength
            validation = SecurityValidator.validate_password_strength(password)
            if not validation["is_valid"]:
                print(f"❌ Password validation failed:")
                for error in validation["errors"]:
                    print(f"   - {error}")
                continue
            
            confirm_password = getpass.getpass("Confirm Password: ")
            if password != confirm_password:
                print("❌ Passwords do not match")
                continue
            
            print(f"✅ Password strength: {validation['strength']}")
            break
        
        # Create admin user
        admin_user = User(
            email=email,
            hashed_password=PasswordHash.hash_password(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("\n✅ Admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   Name: {admin_user.full_name}")
        print(f"   Role: {admin_user.role.value}")
        print(f"   Created: {admin_user.created_at}")
        
        # Create sample users for different roles
        create_sample = input("\nDo you want to create sample users for testing? (y/N): ")
        if create_sample.lower() == 'y':
            create_sample_users(db)
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the API server: python main.py")
        print("2. Access API docs: http://localhost:8000/docs")
        print("3. Login with admin credentials")
        print("4. Create additional users via /auth/register endpoint")
        
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

def show_environment_setup():
    """Show required environment variables"""
    
    print("\n🔧 Environment Setup")
    print("-" * 30)
    
    required_vars = {
        "JWT_SECRET_KEY": "Secret key for JWT token signing (auto-generated if not set)",
        "DATABASE_URL": "Database connection URL (defaults to SQLite)",
        "OPENAI_API_KEY": "OpenAI API key for form processing"
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        status = "✅ SET" if value else "❌ NOT SET"
        print(f"{var}: {status}")
        print(f"   {description}")
        if var == "OPENAI_API_KEY" and not value:
            print("   ⚠️  Form processing will use sample data without this key")
        print()

if __name__ == "__main__":
    try:
        print("🚀 Medical Forms API Setup")
        print("=" * 50)
        
        # Show current environment
        show_environment_setup()
        
        # Check if continuing
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  WARNING: OPENAI_API_KEY not set. Form processing will use sample data.")
            response = input("Continue with setup? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled. Please set OPENAI_API_KEY and try again.")
                sys.exit(0)
        
        create_initial_admin()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)