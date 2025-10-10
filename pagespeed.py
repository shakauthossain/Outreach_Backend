import os
import requests
import base64
from urllib.parse import urlparse
from dotenv import load_dotenv
from database import SessionLocal, LeadDB
from sqlalchemy import or_, and_
from playwright.sync_api import sync_playwright
import time

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_PAGESPEED_KEY")
STATIC_DIR = "static"
FRONTEND_URL = "https://outreach.hellonotionhive.com"
FRONTEND_LOGIN_EMAIL = os.getenv("FRONTEND_LOGIN_EMAIL", "")
FRONTEND_LOGIN_PASSWORD = os.getenv("FRONTEND_LOGIN_PASSWORD", "")


def sanitize_domain(url: str) -> str:
    netloc = urlparse(url).netloc
    return netloc.replace(".", "_").replace(":", "_")


def capture_recommendations_screenshot(lead_id: int, website_url: str) -> str | None:
    """
    Capture a screenshot of the recommendations/diagnostics section
    from the frontend speed details page.
    
    Args:
        lead_id: The ID of the lead
        website_url: The website URL (used for naming the screenshot)
    
    Returns:
        Public URL of the saved screenshot, or None if capture failed
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            # First, check if we need to login
            speed_page_url = f"{FRONTEND_URL}/speed/{lead_id}"
            print(f"📍 Navigating to: {speed_page_url}")
            page.goto(speed_page_url, wait_until="networkidle", timeout=30000)
            
            # Check if we're redirected to login page
            current_url = page.url
            if "/login" in current_url or "login" in page.title().lower():
                print(f"🔐 Login required, attempting authentication...")
                print(f"Current URL: {current_url}")
                
                if not FRONTEND_LOGIN_EMAIL or not FRONTEND_LOGIN_PASSWORD:
                    print(f"❌ No login credentials found. Please set FRONTEND_LOGIN_EMAIL and FRONTEND_LOGIN_PASSWORD in .env")
                    browser.close()
                    return None
                
                try:
                    # Wait a bit for the login form to fully render
                    time.sleep(2)
                    
                    # Try to find ANY input fields on the page to debug
                    all_inputs = page.locator('input').count()
                    print(f"Found {all_inputs} input fields on the page")
                    
                    # Try multiple strategies to find the email/username field
                    email_filled = False
                    email_selectors = [
                        'input[type="email"]',
                        'input[name="email"]',
                        'input[name="username"]',
                        'input[placeholder*="email" i]',
                        'input[placeholder*="Email" i]',
                        'input[id*="email"]',
                        'input.email',
                        '#email',
                        '#username',
                        'input:first-of-type'
                    ]
                    
                    for selector in email_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                print(f"✓ Found email field with selector: {selector}")
                                page.fill(selector, FRONTEND_LOGIN_EMAIL, timeout=5000)
                                email_filled = True
                                break
                        except:
                            continue
                    
                    if not email_filled:
                        print(f"❌ Could not find email input field")
                        # Save screenshot for debugging
                        page.screenshot(path="debug_login_page.png")
                        print(f"💾 Saved login page screenshot to debug_login_page.png")
                        browser.close()
                        return None
                    
                    # Try to find password field
                    password_filled = False
                    password_selectors = [
                        'input[type="password"]',
                        'input[name="password"]',
                        'input[placeholder*="password" i]',
                        'input[id*="password"]',
                        'input.password',
                        '#password'
                    ]
                    
                    for selector in password_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                print(f"✓ Found password field with selector: {selector}")
                                page.fill(selector, FRONTEND_LOGIN_PASSWORD, timeout=5000)
                                password_filled = True
                                break
                        except:
                            continue
                    
                    if not password_filled:
                        print(f"❌ Could not find password input field")
                        page.screenshot(path="debug_login_page.png")
                        print(f"💾 Saved login page screenshot to debug_login_page.png")
                        browser.close()
                        return None
                    
                    # Try to find and click submit button
                    button_selectors = [
                        'button[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Log in")',
                        'button:has-text("Sign in")',
                        'button:has-text("Sign In")',
                        'input[type="submit"]',
                        'button:has-text("Submit")',
                        'form button:first-of-type'
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                print(f"✓ Found submit button with selector: {selector}")
                                page.click(selector, timeout=5000)
                                button_clicked = True
                                break
                        except:
                            continue
                    
                    if not button_clicked:
                        print(f"❌ Could not find submit button, trying form submit")
                        # Try submitting the form directly
                        page.press('input[type="password"]', 'Enter')
                    
                    # Wait for navigation after login - give it more time
                    print(f"⏳ Waiting for login to complete...")
                    try:
                        # Wait for URL to change (redirect after successful login)
                        page.wait_for_url(lambda url: "/login" not in url, timeout=10000)
                        print(f"✅ Login successful - redirected to: {page.url}")
                    except:
                        # If timeout, wait a bit more and check manually
                        time.sleep(3)
                        
                    # Double check if we're still on login page
                    current_url = page.url
                    if "/login" in current_url:
                        print(f"❌ Still on login page after submission")
                        print(f"Checking for error messages...")
                        
                        # Try to find error message on page
                        try:
                            error_text = page.locator("text=/error|invalid|incorrect/i").first.text_content(timeout=2000)
                            print(f"Error message: {error_text}")
                        except:
                            pass
                            
                        page.screenshot(path="debug_after_login.png")
                        print(f"💾 Saved post-login screenshot to debug_after_login.png")
                        browser.close()
                        return None
                    
                    print(f"✅ Login successful, now at: {current_url}")
                    
                    # Navigate to the speed page
                    print(f"📍 Navigating to speed page: {speed_page_url}")
                    page.goto(speed_page_url, wait_until="networkidle", timeout=30000)
                    
                except Exception as login_error:
                    print(f"❌ Login failed: {login_error}")
                    try:
                        page.screenshot(path="debug_login_error.png")
                        print(f"💾 Saved error screenshot to debug_login_error.png")
                    except:
                        pass
                    browser.close()
                    return None
            
            # Wait for the diagnostics section to be loaded
            print("⏳ Waiting for diagnostics section to load...")
            
            # Wait for key elements to ensure page is fully loaded
            try:
                page.wait_for_selector("text=What Can We Fix", timeout=10000)
                print("✓ Found diagnostics section")
            except:
                print("⚠️ Could not find specific section, will capture full page")
            
            # Additional wait to ensure all content is rendered
            time.sleep(2)
            
            # Prepare file path
            domain = sanitize_domain(website_url)
            folder = os.path.join(STATIC_DIR, domain)
            os.makedirs(folder, exist_ok=True)
            filename = f"{domain}-recommendations.png"
            filepath = os.path.join(folder, filename)
            
            # Target the specific Card component from PerformanceDiagnostics.tsx
            screenshot_taken = False
            
            # Try 1: Find by the exact data attribute from the component
            try:
                print("📸 Looking for PerformanceDiagnostics Card component...")
                # Target the Card component that contains "What Can We Fix to Make Your Site Faster?"
                card_selectors = [
                    # By data attribute from the component
                    'div[data-component-name="Card"]:has-text("What Can We Fix to Make Your Site Faster?")',
                    # By class pattern (shadow-lg border-0 bg-white from your HTML)
                    'div.shadow-lg.border-0.bg-white:has-text("What Can We Fix to Make Your Site Faster?")',
                    # By finding the CardHeader and going up to parent Card
                    'div:has(> div[data-component-name="CardHeader"]:has-text("What Can We Fix"))',
                    # Fallback: the rounded-lg card container
                    'div.rounded-lg:has(> div > h3:has-text("What Can We Fix to Make Your Site Faster?"))',
                ]
                
                for selector in card_selectors:
                    try:
                        card_element = page.locator(selector).first
                        if card_element.count() > 0:
                            print(f"✓ Found Card with selector: {selector}")
                            # Scroll the element into view
                            card_element.scroll_into_view_if_needed()
                            time.sleep(1)
                            # Take screenshot of just this Card component
                            card_element.screenshot(path=filepath)
                            screenshot_taken = True
                            print(f"✅ Screenshot captured - Card component only")
                            break
                    except Exception as e:
                        print(f"⚠️ Selector '{selector}' failed: {str(e)[:50]}")
                        continue
            except Exception as e:
                print(f"⚠️ Card targeting failed: {e}")
            
            # Try 2: Find by looking for the title and getting its grandparent Card container
            if not screenshot_taken:
                try:
                    print("📸 Attempting alternate method - finding title's Card parent...")
                    # Find the title element
                    title = page.locator('text=What Can We Fix to Make Your Site Faster?').first
                    # Navigate up to the Card component (usually 2-3 parents up from the title)
                    card = title.locator('xpath=ancestor::div[@class and contains(@class, "rounded-lg")][1]').first
                    
                    if card.count() > 0:
                        card.scroll_into_view_if_needed()
                        time.sleep(1)
                        card.screenshot(path=filepath)
                        screenshot_taken = True
                        print(f"✅ Screenshot captured using title's Card parent")
                except Exception as e:
                    print(f"⚠️ Alternate method failed: {e}")
            
            # Try 3: Fallback - take full page screenshot
            if not screenshot_taken:
                print("📸 Falling back to full page screenshot...")
                try:
                    page.locator('text=What Can We Fix').first.scroll_into_view_if_needed()
                    time.sleep(1)
                except:
                    pass
                
                page.screenshot(path=filepath, full_page=True)
                print(f"✅ Captured full page screenshot as fallback")
            
            browser.close()
            
            # Return public URL
            HF_SPACE_URL = "https://result.hellonotionhive.com"
            screenshot_url = f"{HF_SPACE_URL}/{domain}-recommendations.png"
            
            print(f"✅ Captured recommendations screenshot for {website_url}")
            return screenshot_url
            
    except Exception as e:
        print(f"❌ Error capturing recommendations screenshot for lead {lead_id}: {e}")
        return None


def bulk_capture_recommendations_with_session(leads_data: list) -> dict:
    """
    Optimized bulk capture that logs in once and reuses the browser session.
    
    Args:
        leads_data: List of tuples containing (lead_id, website_url)
    
    Returns:
        Dict with success/failure counts and results for each lead
    """
    results = {
        "success": 0,
        "failed": 0,
        "total": len(leads_data),
        "details": []
    }
    
    if not leads_data:
        print("📊 No leads to process")
        return results
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            # Login once at the beginning
            print("🔐 Logging in to frontend...")
            login_url = f"{FRONTEND_URL}/login"
            page.goto(login_url, wait_until="networkidle", timeout=30000)
            
            try:
                # Fill login form
                time.sleep(2)
                page.fill('input[type="email"]', FRONTEND_LOGIN_EMAIL, timeout=5000)
                page.fill('input[type="password"]', FRONTEND_LOGIN_PASSWORD, timeout=5000)
                page.click('button[type="submit"]', timeout=5000)
                
                # Wait for successful login
                page.wait_for_url(lambda url: "/login" not in url, timeout=10000)
                print("✅ Login successful - session established")
            except Exception as e:
                print(f"❌ Login failed: {e}")
                browser.close()
                results["failed"] = len(leads_data)
                return results
            
            # Now process all leads with the same session
            for lead_id, website_url in leads_data:
                try:
                    print(f"\n🔄 Processing Lead ID {lead_id}: {website_url}")
                    
                    # Parse domain for filename
                    parsed = urlparse(website_url)
                    domain = parsed.netloc.replace("www.", "")
                    domain_safe = domain.replace(".", "_")
                    
                    # Create directories
                    domain_dir = os.path.join(STATIC_DIR, domain_safe)
                    os.makedirs(domain_dir, exist_ok=True)
                    
                    filepath = os.path.join(domain_dir, f"{domain_safe}-recommendations.png")
                    
                    # Navigate to speed details page
                    speed_page_url = f"{FRONTEND_URL}/speed/{lead_id}"
                    page.goto(speed_page_url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for content to load
                    time.sleep(3)
                    
                    # Try to capture the Card component
                    screenshot_taken = False
                    card_selectors = [
                        'div.shadow-lg.border-0.bg-white:has-text("What Can We Fix to Make Your Site Faster?")',
                        'div:has(> div[data-component-name="CardHeader"]:has-text("What Can We Fix"))',
                        'div.rounded-lg:has(> div > h3:has-text("What Can We Fix to Make Your Site Faster?"))',
                    ]
                    
                    for selector in card_selectors:
                        try:
                            card_element = page.locator(selector).first
                            if card_element.count() > 0:
                                card_element.scroll_into_view_if_needed()
                                time.sleep(1)
                                card_element.screenshot(path=filepath)
                                screenshot_taken = True
                                break
                        except:
                            continue
                    
                    if not screenshot_taken:
                        # Fallback to full page
                        page.screenshot(path=filepath, full_page=True)
                    
                    # Generate public URL
                    HF_SPACE_URL = "https://result.hellonotionhive.com"
                    screenshot_url = f"{HF_SPACE_URL}/{domain}-recommendations.png"
                    
                    results["success"] += 1
                    results["details"].append({
                        "lead_id": lead_id,
                        "status": "success",
                        "url": screenshot_url
                    })
                    print(f"✅ Successfully captured screenshot for Lead ID {lead_id}")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "lead_id": lead_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"❌ Failed to capture screenshot for Lead ID {lead_id}: {e}")
            
            browser.close()
            print(f"\n📊 Bulk capture complete: {results['success']} success, {results['failed']} failed")
            
    except Exception as e:
        print(f"❌ Bulk capture failed: {e}")
        results["failed"] = len(leads_data)
    
    return results


def get_pagespeed_score_and_screenshot(url: str, strategy: str) -> tuple[dict | None, str | None, dict | None, dict | None]:
    try:
        api = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy={strategy}&key={GOOGLE_API_KEY}"
        res = requests.get(api).json()

        lighthouse = res.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})

        scores = {
            "performance": int(categories.get("performance", {}).get("score", 0) * 100),
            "accessibility": int(categories.get("accessibility", {}).get("score", 0) * 100),
            "seo": int(categories.get("seo", {}).get("score", 0) * 100),
            "best_practices": int(categories.get("best-practices", {}).get("score", 0) * 100),
        }

        metrics_data = {
            key: {
                "title": audits[key].get("title"),
                "displayValue": audits[key].get("displayValue"),
                "numericValue": audits[key].get("numericValue")
            }
            for key in [
                "first-contentful-paint",
                "largest-contentful-paint",
                "speed-index",
                "total-blocking-time",
                "cumulative-layout-shift"
            ]
            if key in audits
        }

        diagnostics_data = {
            key: audits[key] for key in [
                "diagnostics",
                "network-rtt",
                "mainthread-work-breakdown",
                "bootup-time",
                "uses-rel-preconnect",
                "unminified-css",
                "unminified-javascript",
                "unused-css-rules",
                "uses-webp-images",
                "render-blocking-resources"
            ] if key in audits
        }

        screenshot_data_uri = audits.get("final-screenshot", {}).get("details", {}).get("data")
        screenshot_path = None

        if screenshot_data_uri:
            img_data = base64.b64decode(screenshot_data_uri.split(",")[1])
            domain = sanitize_domain(url)
            
            # Store the file in the 'static' directory under the domain folder
            folder = os.path.join(STATIC_DIR, domain)
            os.makedirs(folder, exist_ok=True)
            filename = f"{domain}-{strategy}-pagespeed.png"
            filepath = os.path.join(folder, filename)
            with open(filepath, "wb") as f:
                f.write(img_data)

            # Public URL structure without '/static/' prefix
            HF_SPACE_URL = "https://result.hellonotionhive.com"
            screenshot_path = f"{HF_SPACE_URL}/{domain}-{strategy}-pagespeed.png"

        return scores, screenshot_path, diagnostics_data, metrics_data

    except Exception as e:
        print(f"Error testing {url} ({strategy}): {e}")
        return None, None, None, None


def test_all_unspeeded_leads():
    db = SessionLocal()
    try:
        leads = db.query(LeadDB).all()
        count = 0

        # (optional) quick visibility while validating
        print(f"[/speedtest] candidates={len(leads)}")

        for lead in leads:
            # Desktop
            scores_web, screenshot_web, _, metrics_web = get_pagespeed_score_and_screenshot(lead.website_url, "desktop")
            # Mobile
            scores_mob, screenshot_mob, diagnostics_mob, metrics_mob = get_pagespeed_score_and_screenshot(lead.website_url, "mobile")

            # Save the data
            if scores_web:
                lead.website_speed_web = scores_web["performance"]
            if scores_mob:
                lead.website_speed_mobile = scores_mob["performance"]
            if screenshot_web:
                lead.screenshot_url_web = screenshot_web
            if screenshot_mob:
                lead.screenshot_url_mobile = screenshot_mob
            if diagnostics_mob:
                lead.pagespeed_diagnostics = diagnostics_mob
            if metrics_web:
                lead.pagespeed_metrics_desktop = metrics_web
            if metrics_mob:
                lead.pagespeed_metrics_mobile = metrics_mob

            # Commit the pagespeed data first to ensure lead.id is available
            if scores_web or scores_mob:
                db.commit()
                
                # Now capture the recommendations screenshot from the frontend page
                recommendations_url = capture_recommendations_screenshot(lead.id, lead.website_url)
                if recommendations_url:
                    lead.recommendations_screenshot_url = recommendations_url
                    db.commit()
                
                count += 1
                print(f"{lead.website_url} → W-{scores_web['performance'] if scores_web else '-'}, "
                      f"M-{scores_mob['performance'] if scores_mob else '-'}")

        return count
    finally:
        db.close()

def refresh_speed_for_lead(lead_id: int) -> tuple[int | None, int | None]:
    db = SessionLocal()
    try:
        lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
        if not lead or not lead.website_url:
            return None, None

        # Fetch scores and screenshot for both desktop and mobile
        scores_web, screenshot_web, _, metrics_web = get_pagespeed_score_and_screenshot(lead.website_url, "desktop")
        scores_mob, screenshot_mob, diagnostics_mob, metrics_mob = get_pagespeed_score_and_screenshot(lead.website_url, "mobile")

        # Save the data
        if scores_web:
            lead.website_speed_web = scores_web["performance"]
        if scores_mob:
            lead.website_speed_mobile = scores_mob["performance"]
        if screenshot_web:
            lead.screenshot_url_web = screenshot_web  # Save desktop screenshot URL
        if screenshot_mob:
            lead.screenshot_url_mobile = screenshot_mob  # Save mobile screenshot URL
        if diagnostics_mob:
            lead.pagespeed_diagnostics = diagnostics_mob
        if metrics_web:
            lead.pagespeed_metrics_desktop = metrics_web
        if metrics_mob:
            lead.pagespeed_metrics_mobile = metrics_mob

        if scores_web or scores_mob:
            db.commit()
            
            # Capture the recommendations screenshot from the frontend page
            recommendations_url = capture_recommendations_screenshot(lead.id, lead.website_url)
            if recommendations_url:
                lead.recommendations_screenshot_url = recommendations_url
                db.commit()
        
        return (
            scores_web["performance"] if scores_web else None,
            scores_mob["performance"] if scores_mob else None
        )
    finally:
        db.close()
