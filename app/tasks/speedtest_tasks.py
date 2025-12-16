"""Speed test background tasks."""

import asyncio
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.integrations.pagespeed import pagespeed_client
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name="speedtest.analyze_single",
    max_retries=3,
    default_retry_delay=60,
)
def analyze_single_speedtest(self, lead_id: int, strategies: list[str] = None):
    """
    Analyze speed test for a single lead.
    
    Args:
        lead_id: Lead ID
        strategies: List of strategies to test (mobile, desktop)
        
    Returns:
        Speed test results
    """
    if strategies is None:
        strategies = ["mobile", "desktop"]
    
    # Update task state
    self.update_state(
        state="PROGRESS",
        meta={"current": 0, "total": len(strategies), "status": "Starting..."}
    )
    
    try:
        # Run async code in event loop
        return asyncio.run(_run_speedtest(self, lead_id, strategies))
    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e)


async def _run_speedtest(task, lead_id: int, strategies: list[str]) -> Dict[str, Any]:
    """
    Internal async function to run speed test.
    
    Args:
        task: Celery task instance
        lead_id: Lead ID
        strategies: Strategies to test
        
    Returns:
        Speed test results
    """
    async with AsyncSessionLocal() as db:
        # Get lead
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        results = {}
        
        # Analyze each strategy
        for i, strategy in enumerate(strategies):
            task.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": len(strategies),
                    "status": f"Analyzing {strategy}...",
                    "url": lead.website_url,
                }
            )
            
            try:
                result = await pagespeed_client.analyze_url(
                    lead.website_url,
                    strategy=strategy
                )
                results[strategy] = result
                
                # Update lead with results
                scores = result.get("scores", {})
                if strategy == "mobile":
                    lead.website_speed_mobile = scores.get("performance", 0)
                    lead.mobile_accessibility_score = scores.get("accessibility", 0)
                    lead.mobile_seo_score = scores.get("seo", 0)
                    lead.mobile_best_practices_score = scores.get("best_practices", 0)
                elif strategy == "desktop":
                    lead.website_speed_web = scores.get("performance", 0)
                    lead.accessibility_score = scores.get("accessibility", 0)
                    lead.seo_score = scores.get("seo", 0)
                    lead.best_practices_score = scores.get("best_practices", 0)
                
            except Exception as e:
                results[strategy] = {"error": str(e)}
        
        # Save lead
        await db.commit()
        
        return {
            "lead_id": lead_id,
            "website_url": lead.website_url,
            "results": results,
            "status": "completed",
        }


@celery_app.task(
    bind=True,
    name="speedtest.analyze_bulk",
    max_retries=1,
)
def analyze_bulk_speedtest(self, lead_ids: list[int], strategies: list[str] = None):
    """
    Analyze speed tests for multiple leads in bulk.
    
    Args:
        lead_ids: List of lead IDs
        strategies: Strategies to test
        
    Returns:
        Batch results
    """
    if strategies is None:
        strategies = ["mobile", "desktop"]
    
    # Update state
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(lead_ids),
            "status": "Starting bulk analysis...",
        }
    )
    
    results = {
        "successful": [],
        "failed": [],
        "total": len(lead_ids),
    }
    
    # Queue individual tasks
    for i, lead_id in enumerate(lead_ids):
        try:
            # Queue task
            task_result = analyze_single_speedtest.apply_async(
                args=[lead_id, strategies],
                countdown=i * 2,  # Stagger requests by 2 seconds
            )
            
            results["successful"].append({
                "lead_id": lead_id,
                "task_id": task_result.id,
            })
            
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(lead_ids),
                    "status": f"Queued {i + 1}/{len(lead_ids)}...",
                }
            )
            
        except Exception as e:
            results["failed"].append({
                "lead_id": lead_id,
                "error": str(e),
            })
    
    return results


@celery_app.task(name="speedtest.get_opportunities")
def get_speedtest_opportunities(lead_id: int, strategy: str = "mobile"):
    """
    Get optimization opportunities for a lead.
    
    Args:
        lead_id: Lead ID
        strategy: Strategy to analyze
        
    Returns:
        Optimization opportunities
    """
    return asyncio.run(_get_opportunities(lead_id, strategy))


async def _get_opportunities(lead_id: int, strategy: str) -> Dict[str, Any]:
    """
    Internal async function to get opportunities.
    
    Args:
        lead_id: Lead ID
        strategy: Strategy to analyze
        
    Returns:
        Opportunities data
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        opportunities = await pagespeed_client.get_opportunities(
            lead.website_url,
            strategy=strategy
        )
        
        return {
            "lead_id": lead_id,
            "website_url": lead.website_url,
            "strategy": strategy,
            "opportunities": opportunities[:10],  # Top 10
            "total_count": len(opportunities),
        }
