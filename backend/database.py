from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Get database credentials from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# URL encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

# Construct DATABASE_URL with explicit parameters
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Attempting to connect to database: {DB_NAME} on {DB_HOST}:{DB_PORT}")

try:
    # Create SQLAlchemy engine
    engine = create_engine(DATABASE_URL)
    
    # Test the connection
    with engine.connect() as connection:
        logger.info("Successfully connected to the database!")
        
    # Create SessionLocal class
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create Base class
    Base = declarative_base()
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")
    
    # Dependency to get DB session
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
            
except Exception as e:
    logger.error(f"Failed to connect to the database: {str(e)}")
    raise 