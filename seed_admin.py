"""
Admin seeding script for PortGuard using SQLAlchemy and bcrypt.
This script inserts a superuser into the users table with proper password hashing.

Usage:
    python seed_admin.py
    
Environment variables (optional):
    ADMIN_EMAIL: Email for admin account (default: admin@portguard.co.za)
    ADMIN_USERNAME: Username for admin account (default: admin_superuser)
    ADMIN_PASSWORD: Password for admin account (default: PortGuard2026!)
"""

import uuid
import sys
import os
from pathlib import Path

# Add the current directory to the system path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.database import SessionLocal, engine, Base
    from models.user import User
    import bcrypt
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt with proper configuration."""
    # Use bcrypt with rounds = 12 (default recommended value)
    # This ensures passwords are properly hashed without truncation
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def seed_admin():
    """Seed a superuser admin account into the database."""
    
    # Configuration
    admin_email = os.getenv("ADMIN_EMAIL", "admin@portguard.co.za")
    admin_username = os.getenv("ADMIN_USERNAME", "admin_superuser")
    admin_password = os.getenv("ADMIN_PASSWORD", "PortGuard2026!")
    
    print("🔐 PortGuard Admin Seeding Script")
    print("=" * 60)
    print(f"Email: {admin_email}")
    print(f"Username: {admin_username}")
    print(f"Role: SUPERUSER")
    print("=" * 60)
    
    try:
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        
        db = SessionLocal()
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(  # type: ignore
            (User.email == admin_email) | (User.username == admin_username)
        ).first()
        
        if existing_admin:
            print(f"⚠️  Admin user already exists:")
            print(f"   Email: {existing_admin.email}")
            print(f"   Username: {existing_admin.username}")
            print(f"   Role: {existing_admin.role}")
            response = input("\nDo you want to update the password? (yes/no): ").strip().lower()
            
            if response == "yes":
                existing_admin.hashed_password = hash_password(admin_password)  # type: ignore
                db.commit()
                print("✅ Admin password updated successfully")
            else:
                print("⏭️  Skipping admin creation")
            
            db.close()
            return True
        
        # Create new admin user
        admin_user = User(
            id=uuid.uuid4(),
            email=admin_email,
            username=admin_username,
            hashed_password=hash_password(admin_password),
            role="SUPERUSER",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ Admin user created successfully!")
        print(f"   ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Role: {admin_user.role}")
        print(f"   Active: {admin_user.is_active}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error seeding admin: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = seed_admin()
    sys.exit(0 if success else 1)
