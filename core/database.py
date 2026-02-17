# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 



# Library declaration and packages to be installed
import os 
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
load_dotenv()

# Configure according to the deployment method's database url : 
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:

    raise ValueError("DATABASE_URL not found in .env file")

# Creating the thread to connect to the database url and local engine
engine = create_engine(
    DATABASE_URL, 

    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},

    pool_pre_ping=True

)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency to provide a DB session for FastAPI routes.
    Ensures sessions are closed automatically to prevent memory leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()