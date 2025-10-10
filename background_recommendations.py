from database import SessionLocal, LeadDB
from pagespeed import capture_recommendations_screenshot
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
        
        # Process each lead one by one (default/original behavior)
        print("🚀 Starting default capture (one by one)...")
        success = 0
        failed = 0
        details = []
        for lead in leads:
            print(f"\n� Processing Lead ID {lead.id}: {lead.website_url}")
            url = None
            try:
                url = capture_recommendations_screenshot(lead.id, lead.website_url)
                if url:
                    lead.recommendations_screenshot_url = url
                    db.commit()
                    print(f"✅ Updated Lead ID {lead.id} with screenshot URL")
                    success += 1
                    details.append({"lead_id": lead.id, "status": "success", "url": url})
                else:
                    print(f"❌ Failed to capture screenshot for Lead ID {lead.id}")
                    failed += 1
                    details.append({"lead_id": lead.id, "status": "failed", "error": "No screenshot URL returned"})
            except Exception as e:
                print(f"❌ Exception for Lead ID {lead.id}: {e}")
                failed += 1
                details.append({"lead_id": lead.id, "status": "failed", "error": str(e)})
        print(f"\n📊 Bulk Recommendations Capture Complete!")
        print(f"✅ Success: {success}")
        print(f"❌ Failed: {failed}")
        print(f"📋 Total: {len(leads)}")
        return {"success": success, "failed": failed, "total": len(leads), "details": details}
        
    except Exception as e:
        print(f"❌ Bulk recommendations capture failed: {str(e)}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
