"""Speed test background tasks."""

import asyncio
import json
from typing import Dict, Any
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.integrations.pagespeed import pagespeed_client
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.models.task import Task, TaskStatus
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
        # Update Task record in database - mark as started
        task_record = None
        if hasattr(task, 'request') and task.request.id:
            stmt = select(Task).where(Task.task_id == task.request.id)
            result = await db.execute(stmt)
            task_record = result.scalar_one_or_none()
            
            if task_record:
                task_record.status = TaskStatus.STARTED
                task_record.started_at = datetime.utcnow()
                task_record.progress = 0
                await db.commit()
        
        # Get lead
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            # Update task as failed
            if task_record:
                task_record.status = TaskStatus.FAILURE
                task_record.error = f"Lead {lead_id} not found"
                task_record.completed_at = datetime.utcnow()
                await db.commit()
            raise ValueError(f"Lead {lead_id} not found")
        
        results = {}
        
        # Analyze each strategy
        for i, strategy in enumerate(strategies):
            # Update Celery state
            task.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": len(strategies),
                    "status": f"Analyzing {strategy}...",
                    "url": lead.website_url,
                }
            )
            
            # Update Task record progress
            if task_record:
                task_record.progress = int((i / len(strategies)) * 100)
                task_record.current_step = f"Analyzing {strategy}"
                task_record.processed_items = i
                task_record.total_items = len(strategies)
                await db.commit()
            
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
                    # Store mobile-specific scores if needed in the future
                    # For now, use desktop scores for all metrics
                elif strategy == "desktop":
                    lead.website_speed_web = scores.get("performance", 0)
                    lead.accessibility_score = scores.get("accessibility", 0)
                    lead.seo_score = scores.get("seo", 0)
                    lead.best_practices_score = scores.get("best_practices", 0)
                
                # Capture screenshot from raw data if available
                raw_data = result.get("raw_data", {})
                lighthouse = raw_data.get("lighthouseResult", {})
                audits = lighthouse.get("audits", {})
                screenshot_audit = audits.get("final-screenshot", {})
                screenshot_data = screenshot_audit.get("details", {}).get("data", "")
                
                if screenshot_data:
                    # Store full screenshot data URL (base64 encoded)
                    if strategy == "mobile":
                        lead.screenshot_url_mobile = screenshot_data
                    elif strategy == "desktop":
                        lead.screenshot_url_web = screenshot_data
                
                # Store detailed PageSpeed metrics for Performance Diagnostics
                # Extract audit data for FCP, LCP, TBT, CLS, Speed Index
                metrics_to_store = {}
                metric_keys = [
                    "first-contentful-paint",
                    "largest-contentful-paint", 
                    "total-blocking-time",
                    "cumulative-layout-shift",
                    "speed-index"
                ]
                
                for metric_key in metric_keys:
                    if metric_key in audits:
                        audit_data = audits[metric_key]
                        metrics_to_store[metric_key] = {
                            "displayValue": audit_data.get("displayValue"),
                            "numericValue": audit_data.get("numericValue"),
                            "score": audit_data.get("score")
                        }
                
                # Store metrics as JSON string
                if metrics_to_store:
                    metrics_json = json.dumps(metrics_to_store)
                    if strategy == "mobile":
                        lead.pagespeed_metrics_mobile = metrics_json
                    elif strategy == "desktop":
                        lead.pagespeed_metrics_desktop = metrics_json
                
            except Exception as e:
                error_msg = str(e)
                results[strategy] = {"error": error_msg}
                print(f"Error testing {lead.website_url} ({strategy}): {error_msg}")
                
                # Don't update scores if there's an error - keep existing values
                # This prevents overwriting good scores with 0
        
        # Save lead (even if some strategies failed)
        await db.commit()
        
        # Update Task record as completed
        if task_record:
            task_record.status = TaskStatus.SUCCESS
            task_record.progress = 100
            task_record.current_step = "Completed"
            task_record.completed_at = datetime.utcnow()
            task_record.processed_items = len(strategies)
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
