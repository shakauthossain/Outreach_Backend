"""
Test script to verify the recommendations screenshot capture functionality
"""
from database import SessionLocal, LeadDB
from pagespeed import capture_recommendations_screenshot

def test_single_lead():
    """Test capturing recommendations screenshot for a single lead"""
    db = SessionLocal()
    try:
        # Get lead with ID 51
        lead = db.query(LeadDB).filter(LeadDB.id == 51).first()
        
        if not lead:
            print("❌ No leads with pagespeed data found")
            return
        
        print(f"Testing lead: {lead.company} - {lead.website_url}")
        print(f"Lead ID: {lead.id}")
        print(f"Mobile Speed: {lead.website_speed_mobile}")
        
        # Capture the screenshot
        screenshot_url = capture_recommendations_screenshot(lead.id, lead.website_url)
        
        if screenshot_url:
            print(f"✅ Screenshot captured successfully!")
            print(f"URL: {screenshot_url}")
            
            # Save to database
            lead.recommendations_screenshot_url = screenshot_url
            db.commit()
            print(f"✅ Saved to database")
        else:
            print(f"❌ Failed to capture screenshot")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_single_lead()
