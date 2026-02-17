#!/usr/bin/env python3
"""Quick diagnostic test"""
import sys
import traceback

def run_diagnostics() -> None:
    try:
        print("1. Importing database...")
        from core.database import SessionLocal, engine, Base
        print("   ✅ Database imported")
        
        print("2. Importing models...")
        from models.user import User
        from models.booking import Booking
        from models.downtime import Downtime
        from models.cargo import CargoItem
        from models.container import Container
        from models.evidence import ContainerImage
        from models.plan import Plan
        from models.packing import PackingSession
        from models.unpacking import UnpackingSession
        from models.truck_offloading import TruckOffloading
        from models.backload_truck import BackloadTruck
        print("   ✅ All models imported")
        
        print("3. Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created/verified")
        
        print("4. Connecting to database...")
        db = SessionLocal()
        print("   ✅ Database connection successful")
        
        print("5. Checking existing users...")
        users = db.query(User).all()
        print(f"   ✅ Found {len(users)} users")
        for user in users:
            print(f"      - {user.email} ({user.role})")
        
        db.close()
        print("\n✅ All diagnostics passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostics()
