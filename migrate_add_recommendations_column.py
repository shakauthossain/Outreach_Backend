"""
Migration script to add recommendations_screenshot_url column to leads table
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def add_recommendations_screenshot_url_column():
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='leads' 
                AND column_name='recommendations_screenshot_url'
            """)
            result = conn.execute(check_query)
            
            if result.fetchone():
                print("✅ Column 'recommendations_screenshot_url' already exists")
                return
            
            # Add the new column
            alter_query = text("""
                ALTER TABLE leads 
                ADD COLUMN recommendations_screenshot_url VARCHAR(500) NULL
            """)
            conn.execute(alter_query)
            conn.commit()
            
            print("✅ Successfully added 'recommendations_screenshot_url' column to leads table")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_recommendations_screenshot_url_column()
