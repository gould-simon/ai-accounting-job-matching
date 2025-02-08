"""Script to test database connection."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

def test_connection() -> None:
    """Test the database connection using credentials from .env file."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Successfully connected to the database!")
            print(f"Server version: {connection.dialect.server_version_info}")
            
    except SQLAlchemyError as e:
        print("❌ Database connection failed!")
        print(f"Error: {str(e)}")
    except Exception as e:
        print("❌ An error occurred!")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_connection()
