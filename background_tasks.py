from celery_worker import celery_app
from pagespeed import refresh_speed_for_lead
from database import SessionLocal, LeadDB
from scraping import scrape_and_extract, HookSignals
from punchline import generate_punchlines

def convert_signals_to_evidence(signals: HookSignals) -> list:
    """Convert HookSignals object to evidence format for punchline generation"""
    evidence_list = []
    if signals.hero:
        evidence_list.append({"kind": "hero", "text": signals.hero[0]})
    if signals.awards:
        evidence_list.extend([{"kind": "award", "text": award[0]} for award in signals.awards])
    if signals.clients:
        evidence_list.extend([{"kind": "client", "text": client[0]} for client in signals.clients])
    if signals.recency:
        evidence_list.extend([{"kind": "recency", "text": rec[0]} for rec in signals.recency])
    if signals.niche:
        evidence_list.extend([{"kind": "niche", "text": niche[0]} for niche in signals.niche])
    if signals.standout:
        evidence_list.extend([{"kind": "standout", "text": stand[0]} for stand in signals.standout])
    return evidence_list

@celery_app.task
def run_speed_test(lead_id: int):
    web, mob = refresh_speed_for_lead(lead_id)
    if web is None and mob is None:
        return {"error": "Speed test failed or lead not found"}
    print(f"[Celery] Updated lead {lead_id}: web={web}, mob={mob}")
    return {"message": f"Updated: W-{web}, M-{mob}"}

@celery_app.task
def process_punchlines_for_lead(lead_id: int):
    db = SessionLocal()
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead or not lead.website_url:
        db.close()
        return {"error": "Lead not found or missing website_url"}
    
    # Check if punchlines already exist (to avoid regenerating)
    if lead.punchline1 and lead.punchline2 and lead.punchline3:
        print(f"Lead {lead_id}: Punchlines already exist, skipping generation")
        db.close()
        return {"lead_id": lead_id, "status": "skipped", "reason": "Punchlines already exist"}
    
    retry_count = 0
    max_retries = 5
    base_delay = 2
    
    while retry_count < max_retries:
        try:
            print(f"Lead {lead_id}: Processing punchlines (attempt {retry_count + 1}/{max_retries})")
            
            # Scrape and extract signals
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pages, signals, evidence = loop.run_until_complete(
                scrape_and_extract(lead.website_url, firecrawl_base="https://api.firecrawl.dev", firecrawl_key="fc-135574cccbe141b5bcfe6c1a40d17cb9")
            )
            
            if not evidence:
                print(f"Lead {lead_id}: No evidence found for website: {lead.website_url}")
                db.close()
                return {"error": "No evidence found", "lead_id": lead_id}
            
            company = lead.company if lead.company else "Unknown"
            print(f"Lead {lead_id}: Generating punchlines for company: {company}")
            
            # Convert signals to evidence format for punchline generation
            evidence_list = convert_signals_to_evidence(signals)
            
            ranked_punchlines = generate_punchlines(company, evidence_list)
            
            if not ranked_punchlines or len(ranked_punchlines) == 0:
                print(f"Lead {lead_id}: No punchlines generated")
                retry_count += 1
                
                if retry_count < max_retries:
                    delay = base_delay * (2 ** retry_count)
                    print(f"Lead {lead_id}: Retrying punchline generation in {delay} seconds...")
                    import time
                    time.sleep(delay)
                    continue
                else:
                    db.close()
                    return {"error": "Failed to generate punchlines after max retries", "lead_id": lead_id}
            
            # Update punchlines
            lead.punchline1 = ranked_punchlines[0]["line"] if len(ranked_punchlines) > 0 else None
            lead.punchline2 = ranked_punchlines[1]["line"] if len(ranked_punchlines) > 1 else None
            lead.punchline3 = ranked_punchlines[2]["line"] if len(ranked_punchlines) > 2 else None
            db.commit()
            
            print(f"Lead {lead_id}: Successfully generated {len(ranked_punchlines)} punchlines")
            
            # Wait 2 seconds after successful generation
            import time
            time.sleep(2)
            
            db.close()
            return {"lead_id": lead_id, "status": "success", "punchlines_count": len(ranked_punchlines)}
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for specific API errors
            if "quota exceeded" in error_msg or "rate limit" in error_msg:
                print(f"Lead {lead_id}: Rate limit/quota exceeded error: {e}")
                if retry_count >= 2:
                    print(f"🛑 Persistent quota errors may indicate token exhaustion")
            elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                print(f"Lead {lead_id}: Token limit exceeded error: {e}")
                if retry_count >= 2:
                    print(f"🛑 Persistent token limit errors indicate token exhaustion")
            elif "authentication" in error_msg or "api key" in error_msg:
                print(f"Lead {lead_id}: Authentication error: {e}")
                db.close()
                return {"error": f"Authentication error: {e}", "lead_id": lead_id}
            else:
                print(f"Lead {lead_id}: General error processing punchlines: {e}")
            
            retry_count += 1
            
            if retry_count < max_retries:
                # Longer delay for rate limit/quota errors
                if "quota exceeded" in error_msg or "rate limit" in error_msg:
                    delay = 60 * retry_count  # 1 minute, 2 minutes, etc.
                else:
                    delay = base_delay * (2 ** retry_count)  # Exponential backoff
                
                print(f"Lead {lead_id}: Retrying in {delay} seconds...")
                import time
                time.sleep(delay)
            else:
                print(f"Lead {lead_id}: Max retries ({max_retries}) exceeded. Stopping processing.")
                db.close()
                return {"error": f"Max retries exceeded: {e}", "lead_id": lead_id}
    
    db.close()
    return {"error": "Unexpected end of retry loop", "lead_id": lead_id}

@celery_app.task
def process_punchlines_for_all_leads():
    db = SessionLocal()
    
    # Get all leads that need punchline processing
    leads = db.query(LeadDB).filter(LeadDB.website_url != None).all()
    total_leads = len(leads)
    
    # Filter leads that already have punchlines (optional skip)
    leads_to_process = []
    for lead in leads:
        if not (lead.punchline1 and lead.punchline2 and lead.punchline3):
            leads_to_process.append(lead)
        else:
            print(f"Lead {lead.id}: Already has punchlines, skipping")
    
    print(f"Starting bulk punchline processing: {len(leads_to_process)} leads to process out of {total_leads} total")
    
    processed = 0
    skipped = 0
    errors = []
    token_exhausted = False  # Global flag to stop processing when tokens are exhausted
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    for i, lead in enumerate(leads_to_process, 1):
        # Stop processing if tokens are exhausted
        if token_exhausted:
            print(f"🛑 Token exhaustion detected. Stopping bulk processing.")
            print(f"Remaining {len(leads_to_process) - i + 1} leads will be skipped.")
            break
            
        retry_count = 0
        max_retries = 5
        base_delay = 2
        success = False
        
        print(f"Processing lead {lead.id} ({i}/{len(leads_to_process)})")
        
        while retry_count < max_retries and not success:
            try:
                print(f"Lead {lead.id}: Processing punchlines (attempt {retry_count + 1}/{max_retries})")
                
                pages, signals, evidence = loop.run_until_complete(
                    scrape_and_extract(lead.website_url, firecrawl_base="https://api.firecrawl.dev", firecrawl_key="fc-135574cccbe141b5bcfe6c1a40d17cb9")
                )
                
                if not evidence:
                    print(f"Lead {lead.id}: No evidence found for website: {lead.website_url}")
                    errors.append({"lead_id": lead.id, "reason": "No evidence found"})
                    break  # Don't retry for no evidence
                
                company = lead.company if lead.company else "Unknown"
                print(f"Lead {lead.id}: Generating punchlines for company: {company}")
                
                # Convert signals to evidence format for punchline generation
                evidence_list = convert_signals_to_evidence(signals)
                
                ranked_punchlines = generate_punchlines(company, evidence_list)
                
                if not ranked_punchlines or len(ranked_punchlines) == 0:
                    print(f"Lead {lead.id}: No punchlines generated")
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        delay = base_delay * (2 ** retry_count)
                        print(f"Lead {lead.id}: Retrying punchline generation in {delay} seconds...")
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        errors.append({"lead_id": lead.id, "reason": "Failed to generate punchlines after max retries"})
                        break
                
                # Update punchlines
                lead.punchline1 = ranked_punchlines[0]["line"] if len(ranked_punchlines) > 0 else None
                lead.punchline2 = ranked_punchlines[1]["line"] if len(ranked_punchlines) > 1 else None
                lead.punchline3 = ranked_punchlines[2]["line"] if len(ranked_punchlines) > 2 else None
                db.commit()  # Commit after each lead
                
                processed += 1
                success = True
                print(f"Lead {lead.id}: Successfully generated {len(ranked_punchlines)} punchlines")
                
                # Wait 2 seconds between processing each lead
                import time
                time.sleep(2)
                
            except Exception as e:
                db.rollback()  # Rollback on error
                error_msg = str(e).lower()
                
                # Check for specific API errors
                if "quota exceeded" in error_msg or "rate limit" in error_msg:
                    print(f"Lead {lead.id}: Rate limit/quota exceeded error: {e}")
                    # Check if this is a hard quota limit (tokens exhausted)
                    if "quota exceeded" in error_msg and retry_count >= 2:
                        print(f"🛑 Quota exhaustion detected after {retry_count + 1} attempts. This likely indicates token exhaustion.")
                        print(f"🛑 Stopping bulk processing to prevent further API calls.")
                        token_exhausted = True
                        errors.append({"lead_id": lead.id, "reason": f"Token exhaustion detected: {e}"})
                        break
                elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                    print(f"Lead {lead.id}: Token limit exceeded error: {e}")
                    # Token limit errors after multiple attempts indicate exhaustion
                    if retry_count >= 2:
                        print(f"🛑 Token limit exceeded after {retry_count + 1} attempts. Tokens likely exhausted.")
                        print(f"🛑 Stopping bulk processing to prevent further failures.")
                        token_exhausted = True
                        errors.append({"lead_id": lead.id, "reason": f"Token exhaustion detected: {e}"})
                        break
                elif "authentication" in error_msg or "api key" in error_msg:
                    print(f"Lead {lead.id}: Authentication error: {e}")
                    errors.append({"lead_id": lead.id, "reason": f"Authentication error: {e}"})
                    break  # Don't retry authentication errors
                else:
                    print(f"Lead {lead.id}: General error processing punchlines: {e}")
                
                retry_count += 1
                
                if retry_count < max_retries and not token_exhausted:
                    # Longer delay for rate limit/quota errors
                    if "quota exceeded" in error_msg or "rate limit" in error_msg:
                        delay = 60 * retry_count  # 1 minute, 2 minutes, etc.
                    else:
                        delay = base_delay * (2 ** retry_count)  # Exponential backoff
                    
                    print(f"Lead {lead.id}: Retrying in {delay} seconds...")
                    import time
                    time.sleep(delay)
                else:
                    print(f"Lead {lead.id}: Max retries ({max_retries}) exceeded.")
                    
                    # If max retries exceeded with token/quota errors, likely exhaustion
                    if ("token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg)) or \
                       ("quota exceeded" in error_msg):
                        print(f"🛑 Max retries exceeded with token/quota errors. Tokens likely exhausted.")
                        print(f"🛑 Stopping bulk processing to prevent further failures.")
                        token_exhausted = True
                        errors.append({"lead_id": lead.id, "reason": f"Token exhaustion after max retries: {e}"})
                    else:
                        print(f"Lead {lead.id}: Moving to next lead.")
                        errors.append({"lead_id": lead.id, "reason": f"Max retries exceeded: {e}"})
                    break
    
    skipped = total_leads - len(leads_to_process)
    
    completion_status = "completed"
    if token_exhausted:
        completion_status = "stopped due to token exhaustion"
        print(f"🛑 Bulk punchline processing {completion_status}: {processed} processed, {skipped} skipped, {len(errors)} errors")
        print(f"💡 Recommendation: Check your Gemini API quota and billing status")
    else:
        print(f"✅ Bulk punchline processing {completion_status}: {processed} processed, {skipped} skipped, {len(errors)} errors")
    
    db.close()
    return {
        "total_leads": total_leads,
        "processed": processed, 
        "skipped": skipped,
        "errors": errors,
        "success_rate": f"{(processed/(processed + len(errors)) * 100):.1f}%" if (processed + len(errors)) > 0 else "0%",
        "token_exhausted": token_exhausted,
        "completion_status": completion_status
    }
