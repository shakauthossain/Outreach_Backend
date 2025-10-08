#!/usr/bin/env python3
"""
Demo script showing the enhanced punchline generation system
This script demonstrates the new features without requiring a full Celery setup
"""

import time
import json
from typing import Dict, Any, Optional

class MockHookSignals:
    """Mock HookSignals for demonstration"""
    def __init__(self):
        self.hero = ("Revolutionary AI-powered solutions for modern businesses", "https://example.com", "home")
        self.awards = [
            ("Winner of TechCrunch Disrupt 2024", "https://example.com/about", "about"),
            ("ISO 27001 Certified Security", "https://example.com/security", "about")
        ]
        self.clients = [
            ("Trusted by Fortune 500 companies", "https://example.com/clients", "clients"),
            ("Serving over 10,000 businesses worldwide", "https://example.com/stats", "home")
        ]
        self.recency = [
            ("Latest product update launched December 2024", "https://example.com/news", "news")
        ]
        self.niche = [
            ("Specialized in enterprise AI automation", "https://example.com/services", "services")
        ]
        self.standout = [
            ("99.9% uptime guarantee with 24/7 support", "https://example.com/features", "features")
        ]

def convert_signals_to_evidence_demo(signals) -> list:
    """Demo version of convert_signals_to_evidence"""
    evidence_list = []
    if hasattr(signals, 'hero') and signals.hero:
        evidence_list.append({"kind": "hero", "text": signals.hero[0]})
    if hasattr(signals, 'awards') and signals.awards:
        evidence_list.extend([{"kind": "award", "text": award[0]} for award in signals.awards])
    if hasattr(signals, 'clients') and signals.clients:
        evidence_list.extend([{"kind": "client", "text": client[0]} for client in signals.clients])
    if hasattr(signals, 'recency') and signals.recency:
        evidence_list.extend([{"kind": "recency", "text": rec[0]} for rec in signals.recency])
    if hasattr(signals, 'niche') and signals.niche:
        evidence_list.extend([{"kind": "niche", "text": niche[0]} for niche in signals.niche])
    if hasattr(signals, 'standout') and signals.standout:
        evidence_list.extend([{"kind": "standout", "text": stand[0]} for stand in signals.standout])
    return evidence_list

def simulate_punchline_generation(company: str, evidence_list: list, lead_id: Optional[int] = None) -> Dict[str, Any]:
    """Simulate punchline generation with retry logic"""
    retry_count = 0
    max_retries = 5
    base_delay = 2
    
    # Mock punchlines that would be generated
    mock_punchlines = [
        {"line": f"Transform {company}'s workflow with our award-winning AI solutions"},
        {"line": f"Join 10,000+ businesses trusting {company} to scale their operations"},
        {"line": f"Experience {company}'s 99.9% uptime guarantee - reliability you can count on"}
    ]
    
    while retry_count <= max_retries:
        try:
            # Log generation attempt
            if lead_id:
                print(f"Lead {lead_id}: Generating punchlines (attempt {retry_count + 1}/{max_retries + 1})")
            else:
                print(f"Generating punchlines (attempt {retry_count + 1}/{max_retries + 1})")
            
            # Simulate processing time
            print(f"Processing {len(evidence_list)} evidence items for company: {company}")
            time.sleep(0.5)  # Simulate API call time
            
            # Simulate occasional failures for demo
            if retry_count == 1:  # Fail on second attempt
                raise Exception("quota exceeded for gemini api")
            
            # Success case
            print(f"Lead {lead_id}: Successfully generated {len(mock_punchlines)} punchlines" if lead_id else f"Successfully generated {len(mock_punchlines)} punchlines")
            
            # Wait 2 seconds after successful generation
            print("Waiting 2 seconds (rate limiting)...")
            time.sleep(2)
            
            return {
                "success": True,
                "punchlines": mock_punchlines,
                "attempts": retry_count + 1,
                "lead_id": lead_id
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for specific API errors
            if "quota exceeded" in error_msg or "rate limit" in error_msg:
                print(f"Lead {lead_id}: Rate limit/quota exceeded error: {e}" if lead_id else f"Rate limit/quota exceeded error: {e}")
            elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                print(f"Lead {lead_id}: Token limit exceeded error: {e}" if lead_id else f"Token limit exceeded error: {e}")
            elif "authentication" in error_msg or "api key" in error_msg:
                print(f"Lead {lead_id}: Authentication error: {e}" if lead_id else f"Authentication error: {e}")
                return {"success": False, "error": "Authentication failed", "attempts": retry_count + 1}
            else:
                print(f"Lead {lead_id}: General error generating punchlines: {e}" if lead_id else f"General error generating punchlines: {e}")
            
            if retry_count < max_retries:
                retry_count += 1
                # Longer delay for rate limit/quota errors
                if "quota exceeded" in error_msg or "rate limit" in error_msg:
                    delay = 60 * retry_count  # 1 minute, 2 minutes, etc. (simulated as seconds for demo)
                    delay = min(delay, 5)  # Cap at 5 seconds for demo
                else:
                    delay = base_delay * (2 ** retry_count)  # Exponential backoff
                
                print(f"Lead {lead_id}: Retrying in {delay} seconds..." if lead_id else f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Lead {lead_id}: Max retries ({max_retries}) exceeded. Stopping punchline generation." if lead_id else f"Max retries ({max_retries}) exceeded. Stopping punchline generation.")
                return {"success": False, "error": f"Max retries exceeded: {e}", "attempts": retry_count + 1}
    
    return {"success": False, "error": "Unexpected end of retry loop", "attempts": retry_count + 1}

def demo_single_lead_processing():
    """Demo single lead processing"""
    print("🔄 Single Lead Processing Demo")
    print("=" * 50)
    
    lead_id = 123
    company = "TechCorp Solutions"
    
    # Check if punchlines already exist (demo: they don't)
    has_punchlines = False
    if has_punchlines:
        print(f"Lead {lead_id}: Punchlines already exist, skipping generation")
        return {"lead_id": lead_id, "status": "skipped", "reason": "Punchlines already exist"}
    
    # Create mock signals and convert to evidence
    signals = MockHookSignals()
    evidence_list = convert_signals_to_evidence_demo(signals)
    
    print(f"Lead {lead_id}: Processing punchlines")
    print(f"Evidence items found: {len(evidence_list)}")
    for i, item in enumerate(evidence_list, 1):
        print(f"  {i}. {item['kind']}: {item['text'][:60]}...")
    
    # Generate punchlines
    result = simulate_punchline_generation(company, evidence_list, lead_id)
    
    if result["success"]:
        print(f"\n✅ Lead {lead_id} completed successfully!")
        print(f"Generated punchlines:")
        for i, punchline in enumerate(result["punchlines"], 1):
            print(f"  {i}. {punchline['line']}")
        return {"lead_id": lead_id, "status": "success", "punchlines_count": len(result["punchlines"])}
    else:
        print(f"\n❌ Lead {lead_id} failed: {result['error']}")
        return {"lead_id": lead_id, "status": "failed", "error": result["error"]}

def demo_bulk_processing():
    """Demo bulk processing"""
    print("\n🚀 Bulk Processing Demo")
    print("=" * 50)
    
    # Mock lead data
    mock_leads = [
        {"id": 201, "company": "DataFlow Inc", "has_punchlines": False},
        {"id": 202, "company": "CloudTech Solutions", "has_punchlines": True},  # Will be skipped
        {"id": 203, "company": "AI Innovations", "has_punchlines": False},
    ]
    
    total_leads = len(mock_leads)
    leads_to_process = [lead for lead in mock_leads if not lead["has_punchlines"]]
    
    print(f"Starting bulk punchline processing: {len(leads_to_process)} leads to process out of {total_leads} total")
    
    processed = 0
    skipped = 0
    errors = []
    
    for i, lead in enumerate(mock_leads, 1):
        print(f"\nProcessing lead {lead['id']} ({i}/{total_leads})")
        
        if lead["has_punchlines"]:
            print(f"Lead {lead['id']}: Already has punchlines, skipping")
            skipped += 1
            continue
        
        # Create mock signals and convert to evidence
        signals = MockHookSignals()
        evidence_list = convert_signals_to_evidence_demo(signals)
        
        # Generate punchlines
        result = simulate_punchline_generation(lead["company"], evidence_list, lead["id"])
        
        if result["success"]:
            processed += 1
        else:
            errors.append({"lead_id": lead["id"], "reason": result["error"]})
    
    success_rate = f"{(processed/(processed + len(errors)) * 100):.1f}%" if (processed + len(errors)) > 0 else "0%"
    
    print(f"\n📊 Bulk processing completed:")
    print(f"  Total leads: {total_leads}")
    print(f"  Processed: {processed}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {len(errors)}")
    print(f"  Success rate: {success_rate}")
    
    return {
        "total_leads": total_leads,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "success_rate": success_rate
    }

def demo_error_categorization():
    """Demo error categorization"""
    print("\n🛠️  Error Categorization Demo")
    print("=" * 50)
    
    test_errors = [
        "quota exceeded for gemini api",
        "rate limit exceeded", 
        "token limit exceeded in request",
        "authentication failed - invalid api key",
        "general network error",
        "Quota exceeded for the current billing account"
    ]
    
    for error in test_errors:
        error_msg = error.lower()
        if "quota exceeded" in error_msg or "rate limit" in error_msg:
            category = "Rate Limit/Quota (60s incremental delays)"
        elif "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
            category = "Token Limit (exponential backoff)"
        elif "authentication" in error_msg or "api key" in error_msg:
            category = "Authentication (no retry)"
        else:
            category = "General (exponential backoff)"
        
        print(f"  Error: '{error}' → {category}")

def main():
    """Run the complete demo"""
    print("🎯 Enhanced Punchline Generation System Demo")
    print("=" * 60)
    print("This demo shows all the new features implemented:")
    print("✅ Comprehensive error handling & retry logic")
    print("✅ Progress tracking & logging") 
    print("✅ Duplicate prevention")
    print("✅ Rate limiting & delays")
    print("✅ Enhanced data flow")
    print("=" * 60)
    
    try:
        # Demo 1: Single lead processing
        demo_single_lead_processing()
        
        # Demo 2: Bulk processing
        demo_bulk_processing()
        
        # Demo 3: Error categorization
        demo_error_categorization()
        
        print("\n🎉 Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  🔄 Retry logic with exponential backoff")
        print("  📊 Comprehensive progress tracking")
        print("  🚫 Duplicate prevention & skipping")
        print("  ⏱️  Rate limiting with 2-second delays")
        print("  🏷️  Error categorization & smart handling")
        print("  📈 Detailed completion statistics")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    main()