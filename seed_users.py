import uuid
import sys
import os

# Add the current directory to the system path so Python can find your files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from services layer instead of core.security
try:
    from core.database import SessionLocal, engine, Base
    from services.auth_service import AuthService
    from models.user import User
    # Import all models to initialize mappers
    from models.booking import Booking
    from models.downtime import Downtime
    from models.cargo import CargoItem
    from models.container import Container
    from models.evidence import ContainerImage
    from models.plan import Plan
    from models.packing import PackingSession
    from models.unpacking import UnpackingSession
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

def seed_test_accounts():
    # Create all tables first
    print("📋 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    db = SessionLocal()
    try:
        # 1. Create the Ground Operator
        operator_email = "operator@portguard.co.za"
        if not db.query(User).filter(User.email == operator_email).first():
            op_user = User(
                id=uuid.uuid4(),
                email=operator_email,
                username="port_operator_01",
                hashed_password=AuthService.get_password_hash("Operator123!"),
                role="OPERATOR",
                is_active=True
            )
            db.add(op_user)
            print(f"✅ Created Operator: {operator_email}")

        # 2. Create the Supervisor (Management)
        supervisor_email = "supervisor@portguard.co.za"
        if not db.query(User).filter(User.email == supervisor_email).first():
            sup_user = User(
                id=uuid.uuid4(),
                email=supervisor_email,
                username="port_supervisor_01",
                hashed_password=AuthService.get_password_hash("Supervisor123!"),
                role="SUPERVISOR",
                is_active=True
            )
            db.add(sup_user)
            print(f"✅ Created Supervisor: {supervisor_email}")

        # 3. Create the Admin User
        admin_email = "admin@portguard.co.za"
        if not db.query(User).filter(User.email == admin_email).first():
            admin_user = User(
                id=uuid.uuid4(),
                email=admin_email,
                username="port_admin_01",
                hashed_password=AuthService.get_password_hash("Admin123!"),
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            print(f"✅ Created Admin: {admin_email}")

        # Seed Bookings for Export Packing
        booking_seed = [
            ("MSC_LIGA_FEB2026", "HULAMIN", "MSC LIGA", "20FT"),
            ("MSC_MARTINA_FEB2026", "PG_BISON", "MSC MARTINA", "40FT"),
            ("CMA_ANTOINE_MAR2026", "HULAMIN", "CMA ANTOINE", "40FT"),
            ("MAERSK_ATLAS_MAR2026", "PG_BISON", "MAERSK ATLAS", "HC"),
            ("ONE_CYGNUS_APR2026", "HULAMIN", "ONE CYGNUS", "20FT"),
        ]
        for ref, client, vessel, ctype in booking_seed:
            if not db.query(Booking).filter(Booking.booking_reference == ref).first():
                db.add(Booking(
                    id=uuid.uuid4(),
                    booking_reference=ref,
                    client=client,
                    vessel_name=vessel,
                    container_type=ctype
                ))
                print(f"✅ Created Booking: {ref} ({client})")

        db.commit()
    except Exception as e:
        print(f"❌ Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_accounts()