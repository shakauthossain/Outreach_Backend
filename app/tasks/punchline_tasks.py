"""Punchline generation background tasks."""

import asyncio
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name="punchline.generate_single",
    max_retries=3,
)
def generate_single_punchline(self, lead_id: int, style: str = "professional"):
    """
    Generate punchline for a single lead.
    
    Args:
        lead_id: Lead ID
        style: Punchline style
        
    Returns:
        Generated punchline
    """
    self.update_state(
        state="PROGRESS",
        meta={"status": "Generating punchline..."}
    )
    
    try:
        return asyncio.run(_generate_punchline(lead_id, style))
    except Exception as e:
        raise self.retry(exc=e)


async def _generate_punchline(lead_id: int, style: str) -> Dict[str, Any]:
    """
    Internal async function to generate punchline.
    
    Args:
        lead_id: Lead ID
        style: Punchline style
        
    Returns:
        Punchline data
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Build context for punchline generation
        context = {
            "company": lead.company,
            "website_url": lead.website_url,
            "web_speed": lead.website_speed_web,
            "mobile_speed": lead.website_speed_mobile,
            "avg_performance": lead.average_performance_score,
        }
        
        # Generate punchline (placeholder - implement with actual LLM)
        punchline = _generate_punchline_text(context, style)
        
        # Update lead
        lead.punchline = punchline
        await db.commit()
        
        return {
            "lead_id": lead_id,
            "punchline": punchline,
            "style": style,
            "status": "completed",
        }


def _generate_punchline_text(context: Dict[str, Any], style: str) -> str:
    """
    Generate punchline text based on context.
    
    Args:
        context: Lead context
        style: Punchline style
        
    Returns:
        Punchline text
    """
    # Template-based punchline (replace with LLM in production)
    avg = context.get("avg_performance", 0)
    
    if avg < 50:
        return f"Your site could be losing customers every second it takes to load."
    elif avg < 75:
        return f"Small speed improvements can lead to significant conversion increases."
    else:
        return f"Your site performs well, but there's always room for optimization."


@celery_app.task(
    bind=True,
    name="punchline.generate_bulk",
)
def generate_bulk_punchlines(self, lead_ids: list[int], style: str = "professional"):
    """
    Generate punchlines for multiple leads.
    
    Args:
        lead_ids: List of lead IDs
        style: Punchline style
        
    Returns:
        Batch results
    """
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(lead_ids),
            "status": "Starting bulk generation...",
        }
    )
    
    results = {
        "successful": [],
        "failed": [],
        "total": len(lead_ids),
    }
    
    for i, lead_id in enumerate(lead_ids):
        try:
            task_result = generate_single_punchline.apply_async(
                args=[lead_id, style],
                countdown=i,  # Stagger by 1 second
            )
            
            results["successful"].append({
                "lead_id": lead_id,
                "task_id": task_result.id,
            })
            
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
