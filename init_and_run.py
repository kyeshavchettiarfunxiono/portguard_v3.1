#!/usr/bin/env python3
"""Initialize database with test users and start the server"""

import uuid
import sys
import os
from pathlib import Path
from sqlalchemy import and_, or_

# Add the current directory to the system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core components
try:
    from core.database import SessionLocal, engine, Base
    from services.auth_service import AuthService
    from models.user import User
    from models.booking import Booking
    # Import ALL models to ensure mapper initialization
    from models.container import Container, ContainerStatus
    from models.cargo import CargoItem
    from models.evidence import ContainerImage
    from models.plan import Plan
    from models.packing import PackingSession
    from models.unpacking import UnpackingSession
    from models.downtime import Downtime
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def seed_database():
    """Create tables and seed test data"""
    print("\n" + "="*50)
    print("🌱 SEEDING DATABASE")
    print("="*50)
    
    # Create tables
    print("📋 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    db = SessionLocal()
    try:
        # Check if users already exist
        admin_exists = db.query(User).filter(User.email == "admin@portguard.co.za").first()  # type: ignore
        
        if admin_exists:
            print("✅ Test users already exist - skipping seed")
            db.close()
            return

        # Create test users
        print("\n👥 Creating test users...")
        
        # Operator
        op_user = User(
            id=uuid.uuid4(),
            email="operator@portguard.co.za",
            username="port_operator_01",
            hashed_password=AuthService.get_password_hash("Operator123!"),
            role="OPERATOR",
            is_active=True
        )
        db.add(op_user)
        print(f"   ✅ Operator: operator@portguard.co.za / Operator123!")

        # Supervisor
        sup_user = User(
            id=uuid.uuid4(),
            email="supervisor@portguard.co.za",
            username="port_supervisor_01",
            hashed_password=AuthService.get_password_hash("Supervisor123!"),
            role="SUPERVISOR",
            is_active=True
        )
        db.add(sup_user)
        print(f"   ✅ Supervisor: supervisor@portguard.co.za / Supervisor123!")

        # Admin
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@portguard.co.za",
            username="port_admin_01",
            hashed_password=AuthService.get_password_hash("Admin123!"),
            role="ADMIN",
            is_active=True
        )
        db.add(admin_user)
        print(f"   ✅ Admin: admin@portguard.co.za / Admin123!")

        # Create test bookings
        print("\n📦 Creating test bookings...")
        bookings = [
            ("MSC_LIGA_FEB2026", "HULAMIN", "MSC LIGA", "20FT"),
            ("MSC_MARTINA_FEB2026", "PG_BISON", "MSC MARTINA", "40FT"),
            ("CMA_ANTOINE_MAR2026", "HULAMIN", "CMA ANTOINE", "40FT"),
        ]
        
        for ref, client, vessel, ctype in bookings:
            if not db.query(Booking).filter(Booking.booking_reference == ref).first():  # type: ignore
                db.add(Booking(
                    id=uuid.uuid4(),
                    booking_reference=ref,
                    client=client,
                    vessel_name=vessel,
                    container_type=ctype
                ))
                print(f"   ✅ {ref} ({client})")

        db.commit()
        print("\n✅ Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def start_server():
    """Start the FastAPI server"""
    print("\n" + "="*50)
    print("🚀 STARTING FASTAPI SERVER")
    print("="*50)
    print("\n📍 Server: http://localhost:8000")
    print("🔧 Dashboard: http://localhost:8000/operator-dashboard")
    print("\n✅ Use credentials from seeded database above\n")
    
    from main import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # First seed the database
    seed_database()
    
    # Then start the server
    start_server()
