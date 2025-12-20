"""Punchline generation endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.punchline_service import PunchlineService
from app.core.rate_limit import limiter
from fastapi import Request


router = APIRouter()


@router.post("/{lead_id}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def generate_punchlines_for_lead(
    request: Request,
    lead_id: int,
    k: int = Query(3, ge=1, le=5, description="Number of punchlines to generate"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate personalized punchlines for a specific lead.
    
    Args:
        lead_id: ID of the lead
        k: Number of punchlines to generate (1-5, default 3)
        
    Returns:
        Generated punchlines with scores and metadata
        
    Raises:
        404: Lead not found
        400: Lead missing required data
    """
    try:
        result = await PunchlineService.generate_punchlines(db, lead_id, k)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate punchlines: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def generate_bulk_punchlines(
    request: Request,
    untested_only: bool = Query(
        True,
        description="Only process leads without existing punchlines"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate punchlines for multiple leads in bulk.
    
    This is a long-running operation that processes leads asynchronously.
    
    Args:
        untested_only: If True, only process leads without punchlines
        
    Returns:
        Task information and processing results
    """
    try:
        result = await PunchlineService.generate_bulk_punchlines(db, untested_only)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bulk punchline generation: {str(e)}"
        )
