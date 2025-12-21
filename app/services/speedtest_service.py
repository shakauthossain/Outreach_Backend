"""
PageSpeed service for testing website performance.
"""
import os
import asyncio
import httpx
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.lead import Lead
from app.models.task import Task, TaskType, TaskStatus
from app.config import settings


GOOGLE_PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


class SpeedTestService:
    """Service for running PageSpeed tests on leads."""
    
    @staticmethod
    async def run_speed_test(
        db: AsyncSession,
        lead_id: int
    ) -> Dict[str, Any]:
        """
        Run PageSpeed test for a single lead.
        
        Args:
            db: Database session
            lead_id: ID of the lead to test
            
        Returns:
            Task information
        """
        # Get lead
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Generate unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Create task
        task = Task(
            task_id=task_id,
            task_type=TaskType.SPEED_TEST,
            task_name=f"Speed test for lead {lead_id}",
            status=TaskStatus.PENDING,
            metadata={"lead_id": lead_id, "website_url": str(lead.website_url)}
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Queue Celery task for async processing
        try:
            from app.tasks.speedtest_tasks import analyze_single_speedtest
            
            celery_task = analyze_single_speedtest.apply_async(
                args=[lead_id, ["mobile", "desktop"]],
                task_id=task.task_id
            )
            
            # Update task with queued status
            task.status = TaskStatus.PENDING
            task.metadata["celery_task_id"] = celery_task.id
            await db.commit()
            
            return {
                "task_id": task.task_id,
                "celery_task_id": celery_task.id,
                "lead_id": lead_id,
                "status": "queued",
                "message": "Speed test queued for processing"
            }
        except Exception as e:
            # Fallback: If Celery/Redis unavailable, return task for manual processing
            print(f"Celery unavailable: {e}. Task created but not queued.")
            return {
                "task_id": task.task_id,
                "lead_id": lead_id,
                "status": "created",
                "message": "Speed test task created. Background worker required to process."
            }
    
    @staticmethod
    async def run_bulk_speed_test(
        db: AsyncSession,
        untested_only: bool = False
    ) -> Dict[str, Any]:
        """
        Run PageSpeed test for all leads (or untested only).
        
        Args:
            db: Database session
            untested_only: Only test leads without existing results
            
        Returns:
            Task information
        """
        # Get leads
        query = select(Lead)
        if untested_only:
            query = query.where(
                (Lead.website_speed_web.is_(None)) & 
                (Lead.website_speed_mobile.is_(None))
            )
        
        result = await db.execute(query)
        leads = result.scalars().all()
        
        if not leads:
            return {
                "message": "No leads to test",
                "count": 0
            }
        
        # Generate unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Create batch task
        batch_task = Task(
            task_id=task_id,
            task_type=TaskType.BULK_OPERATION,
            task_name="Bulk speed test",
            status=TaskStatus.PENDING,
            metadata={
                "total_leads": len(leads),
                "untested_only": untested_only
            }
        )
        db.add(batch_task)
        await db.commit()
        await db.refresh(batch_task)
        
        # Queue Celery task for async bulk processing
        try:
            from app.tasks.speedtest_tasks import analyze_bulk_speedtest
            
            lead_ids = [lead.id for lead in leads]
            celery_task = analyze_bulk_speedtest.apply_async(
                args=[lead_ids, ["mobile", "desktop"]],
                task_id=batch_task.task_id
            )
            
            # Update task with queued status
            batch_task.status = TaskStatus.PENDING
            batch_task.metadata["celery_task_id"] = celery_task.id
            batch_task.metadata["total_leads"] = len(lead_ids)
            await db.commit()
            
            return {
                "task_id": batch_task.task_id,
                "celery_task_id": celery_task.id,
                "total_leads": len(lead_ids),
                "status": "queued",
                "message": f"Bulk speed test queued for {len(lead_ids)} leads"
            }
        except Exception as e:
            # Fallback: If Celery/Redis unavailable
            print(f"Celery unavailable: {e}. Task created but not queued.")
            lead_ids = [lead.id for lead in leads]
            return {
                "task_id": batch_task.task_id,
                "total_leads": len(lead_ids),
                "status": "created",
                "message": f"Bulk speed test task created for {len(lead_ids)} leads. Background worker required."
            }
    
    @staticmethod
    async def _fetch_pagespeed_data(
        url: str,
        strategy: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch PageSpeed data from Google API.
        
        Args:
            url: Website URL to test
            strategy: "desktop" or "mobile"
            
        Returns:
            Dict with performance scores and screenshot
        """
        api_key = os.getenv("GOOGLE_PAGESPEED_KEY")
        if not api_key:
            print("Warning: GOOGLE_PAGESPEED_KEY not set")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    GOOGLE_PAGESPEED_API,
                    params={
                        "url": url,
                        "strategy": strategy,
                        "key": api_key
                    }
                )
                
                if response.status_code != 200:
                    print(f"PageSpeed API error: {response.status_code}")
                    return None
                
                data = response.json()
                
                # Extract scores
                lighthouse = data.get("lighthouseResult", {})
                categories = lighthouse.get("categories", {})
                
                performance_score = categories.get("performance", {}).get("score", 0) * 100
                accessibility_score = categories.get("accessibility", {}).get("score", 0) * 100
                seo_score = categories.get("seo", {}).get("score", 0) * 100
                best_practices_score = categories.get("best-practices", {}).get("score", 0) * 100
                
                # Extract screenshot
                screenshot_data = lighthouse.get("audits", {}).get("final-screenshot", {})
                screenshot = screenshot_data.get("details", {}).get("data")
                
                # Extract diagnostics (for mobile only)
                diagnostics = None
                if strategy == "mobile":
                    audits = lighthouse.get("audits", {})
                    diagnostics = {
                        "fcp": audits.get("first-contentful-paint", {}).get("displayValue"),
                        "lcp": audits.get("largest-contentful-paint", {}).get("displayValue"),
                        "cls": audits.get("cumulative-layout-shift", {}).get("displayValue"),
                        "speed_index": audits.get("speed-index", {}).get("displayValue")
                    }
                
                return {
                    "performance_score": performance_score,
                    "accessibility_score": accessibility_score,
                    "seo_score": seo_score,
                    "best_practices_score": best_practices_score,
                    "screenshot": screenshot,
                    "diagnostics": diagnostics
                }
                
        except Exception as e:
            print(f"Error fetching PageSpeed data: {e}")
            return None
