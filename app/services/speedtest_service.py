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
        
        # Create task
        task = Task(
            lead_id=lead_id,
            task_type=TaskType.SPEEDTEST,
            status=TaskStatus.PENDING,
            metadata={"website_url": str(lead.website_url)}
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # TODO: Queue Celery task instead of running synchronously
        # For now, run synchronously
        try:
            task.status = TaskStatus.RUNNING
            await db.commit()
            
            # Run tests
            desktop_data = await SpeedTestService._fetch_pagespeed_data(
                str(lead.website_url), "desktop"
            )
            mobile_data = await SpeedTestService._fetch_pagespeed_data(
                str(lead.website_url), "mobile"
            )
            
            # Update lead with results
            if desktop_data:
                lead.website_speed_web = desktop_data.get("performance_score")
                lead.accessibility_score = desktop_data.get("accessibility_score")
                lead.seo_score = desktop_data.get("seo_score")
                lead.best_practices_score = desktop_data.get("best_practices_score")
                lead.screenshot_url_web = desktop_data.get("screenshot")
            
            if mobile_data:
                lead.website_speed_mobile = mobile_data.get("performance_score")
                lead.screenshot_url_mobile = mobile_data.get("screenshot")
                lead.recommendations = mobile_data.get("diagnostics")
            
            lead.updated_at = datetime.utcnow()
            task.status = TaskStatus.COMPLETED
            task.result = {"desktop": desktop_data, "mobile": mobile_data}
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            raise
        finally:
            await db.commit()
        
        return {
            "task_id": str(task.task_id),
            "status": task.status.value,
            "lead_id": lead_id
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
        
        # Create batch task
        batch_task = Task(
            task_type=TaskType.BULK_SPEEDTEST,
            status=TaskStatus.PENDING,
            metadata={
                "total_leads": len(leads),
                "untested_only": untested_only
            }
        )
        db.add(batch_task)
        await db.commit()
        await db.refresh(batch_task)
        
        # TODO: Queue Celery task for async processing
        # For now, process sequentially (not recommended for production)
        batch_task.status = TaskStatus.RUNNING
        await db.commit()
        
        processed = 0
        failed = 0
        
        for lead in leads:
            try:
                await SpeedTestService.run_speed_test(db, lead.id)
                processed += 1
            except Exception as e:
                failed += 1
                print(f"Failed to test lead {lead.id}: {e}")
        
        batch_task.status = TaskStatus.COMPLETED
        batch_task.result = {
            "processed": processed,
            "failed": failed,
            "total": len(leads)
        }
        await db.commit()
        
        return {
            "task_id": str(batch_task.task_id),
            "status": batch_task.status.value,
            "processed": processed,
            "failed": failed,
            "total": len(leads)
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
