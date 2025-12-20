"""Speed test endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.services.speedtest_service import SpeedTestService
from app.core.rate_limit import limiter, get_rate_limit
from app.core.security import get_current_user
from app.models.user import User


router = APIRouter()


class SpeedTestResponse(BaseModel):
    """Response for speed test"""
    task_id: str
    status: str
    lead_id: int = None
    message: str = None
    processed: int = None
    failed: int = None
    total: int = None


@router.post("/{lead_id}", response_model=SpeedTestResponse)
@limiter.limit(get_rate_limit("speedtest"))
async def run_speed_test_for_lead(
    request: Request,
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run PageSpeed test for a specific lead.
    
    Args:
        lead_id: ID of the lead to test
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Task information
    """
    try:
        result = await SpeedTestService.run_speed_test(db, lead_id)
        return SpeedTestResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run speed test: {str(e)}"
        )


@router.post("/", response_model=SpeedTestResponse)
@limiter.limit(get_rate_limit("speedtest_bulk"))
async def run_bulk_speed_test(
    request: Request,
    untested_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run PageSpeed test for all leads or untested leads only.
    
    Args:
        untested_only: Only test leads without existing results
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Task information
    """
    try:
        result = await SpeedTestService.run_bulk_speed_test(db, untested_only)
        
        if "message" in result:
            return SpeedTestResponse(
                task_id="",
                status="completed",
                message=result["message"],
                total=result["count"]
            )
        
        return SpeedTestResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run bulk speed test: {str(e)}"
        )
