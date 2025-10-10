"""
Create a test user for screenshot automation
"""
from database import SessionLocal
from auth.models import User
from auth.utils import hash_password
import os
from dotenv import load_dotenv

load_dotenv()

def create_test_user():
    email = os.getenv("FRONTEND_LOGIN_EMAIL", "testing1@gmail.com")
    password = os.getenv("FRONTEND_LOGIN_PASSWORD", "admin123")
    
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            print(f"✅ User {email} already exists")
            # Update password just in case
            existing_user.hashed_password = hash_password(password)
            db.commit()
            print(f"✅ Updated password for {email}")
        else:
            # Create new user
            new_user = User(
                email=email,
                hashed_password=hash_password(password)
            )
            db.add(new_user)
            db.commit()
            print(f"✅ Created new user: {email}")
            
        print(f"\n📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"\nYou can now use these credentials for screenshot automation!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
