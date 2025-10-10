"""
Test script to verify if login credentials work on the frontend
"""
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import time

load_dotenv()

FRONTEND_URL = "https://outreach.hellonotionhive.com"
FRONTEND_LOGIN_EMAIL = os.getenv("FRONTEND_LOGIN_EMAIL", "")
FRONTEND_LOGIN_PASSWORD = os.getenv("FRONTEND_LOGIN_PASSWORD", "")

def test_login():
    print(f"Testing login with:")
    print(f"Email: {FRONTEND_LOGIN_EMAIL}")
    print(f"Password: {'*' * len(FRONTEND_LOGIN_PASSWORD)}")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Not headless so you can see
        page = browser.new_page()
        
        # Go to login page
        print(f"📍 Navigating to login page...")
        page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
        
        # Wait for form to render
        time.sleep(2)
        
        # Fill email
        print(f"✏️ Filling email field...")
        page.fill('input[placeholder*="email" i]', FRONTEND_LOGIN_EMAIL)
        
        # Fill password
        print(f"✏️ Filling password field...")
        page.fill('input[type="password"]', FRONTEND_LOGIN_PASSWORD)
        
        # Take screenshot before submit
        page.screenshot(path="before_login.png")
        print(f"💾 Saved screenshot: before_login.png")
        
        # Click login
        print(f"🖱️ Clicking login button...")
        page.click('button[type="submit"]')
        
        # Wait for response
        print(f"⏳ Waiting for response...")
        time.sleep(5)
        
        # Check current URL
        current_url = page.url
        print(f"\n📍 Current URL after login: {current_url}")
        
        # Take screenshot after login attempt
        page.screenshot(path="after_login.png")
        print(f"💾 Saved screenshot: after_login.png")
        
        if "/login" in current_url:
            print(f"\n❌ LOGIN FAILED - Still on login page")
            print(f"Possible reasons:")
            print(f"  1. Incorrect email or password")
            print(f"  2. User doesn't exist in the database")
            print(f"  3. Frontend validation error")
            print(f"\nPlease check the screenshots to see any error messages")
        else:
            print(f"\n✅ LOGIN SUCCESSFUL!")
            print(f"Redirected to: {current_url}")
        
        # Keep browser open for 5 seconds so you can see
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    test_login()
