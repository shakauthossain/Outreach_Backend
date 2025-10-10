from database import SessionLocal, LeadDB
from pagespeed import bulk_capture_recommendations_with_session
from sqlalchemy import or_

def run_bulk_recommendations_capture():
    """Capture recommendations screenshots for all leads with speed data but no recommendations screenshot"""
    db = SessionLocal()
    try:
        # Find leads that have speed data but no recommendations screenshot
        leads = db.query(LeadDB).filter(
            or_(
                LeadDB.website_speed_web.isnot(None),
                LeadDB.website_speed_mobile.isnot(None)
            ),
            LeadDB.recommendations_screenshot_url.is_(None)
        ).all()
        
        print(f"📊 Found {len(leads)} leads with speed data but no recommendations screenshot")
        
        if not leads:
            return {"success": 0, "failed": 0, "total": 0}
        
        # Prepare data for bulk capture (lead_id, website_url)
        leads_data = [(lead.id, lead.website_url) for lead in leads]
        
        # Use optimized bulk capture with single login session
        print("🚀 Starting optimized bulk capture (single login session)...")
        capture_results = bulk_capture_recommendations_with_session(leads_data)
        
        # Update database with successful captures
        print("\n💾 Updating database with captured screenshots...")
        for detail in capture_results["details"]:
            if detail["status"] == "success":
                lead = db.query(LeadDB).filter(LeadDB.id == detail["lead_id"]).first()
                if lead:
                    lead.recommendations_screenshot_url = detail["url"]
                    db.commit()
                    print(f"✅ Updated Lead ID {detail['lead_id']} with screenshot URL")
        
        print(f"\n📊 Bulk Recommendations Capture Complete!")
        print(f"✅ Success: {capture_results['success']}")
        print(f"❌ Failed: {capture_results['failed']}")
        print(f"📋 Total: {capture_results['total']}")
        
        return capture_results
        
    except Exception as e:
        print(f"❌ Bulk recommendations capture failed: {str(e)}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
