"""Lead management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadListQuery,
    LeadStatistics,
    BulkLeadOperation,
    BulkLeadResponse,
)
from app.services.lead_service import LeadService
from app.core.security import get_current_active_user
from app.core.rate_limit import limiter, get_rate_limit
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("/", response_model=LeadListResponse)
@limiter.limit(get_rate_limit("leads_read"))
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    mail_sent: bool = Query(None),
    min_web_speed: float = Query(None, ge=0, le=100),
    max_web_speed: float = Query(None, ge=0, le=100),
    min_mobile_speed: float = Query(None, ge=0, le=100),
    max_mobile_speed: float = Query(None, ge=0, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get paginated list of leads with optional filters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        search: Search term (company, website, email)
        mail_sent: Filter by mail sent status
        min_web_speed: Minimum web speed score
        max_web_speed: Maximum web speed score
        min_mobile_speed: Minimum mobile speed score
        max_mobile_speed: Maximum mobile speed score
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Paginated lead list
    """
    query = LeadListQuery(
        page=page,
        page_size=page_size,
        search=search,
        mail_sent=mail_sent,
        min_web_speed=min_web_speed,
        max_web_speed=max_web_speed,
        min_mobile_speed=min_mobile_speed,
        max_mobile_speed=max_mobile_speed,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    leads, total = await LeadService.list_leads(db, query)
    
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/statistics", response_model=LeadStatistics)
@limiter.limit(get_rate_limit("leads_read"))
async def get_lead_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get lead statistics.
    
    Args:
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Lead statistics
    """
    return await LeadService.get_statistics(db)


@router.get("/{lead_id}", response_model=LeadResponse)
@limiter.limit(get_rate_limit("leads_read"))
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a single lead by ID.
    
    Args:
        lead_id: Lead ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Lead details
        
    Raises:
        NotFoundError: If lead not found
    """
    lead = await LeadService.get_lead_by_id(db, lead_id)
    return LeadResponse.model_validate(lead)


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit("leads_create"))
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new lead.
    
    Args:
        lead_data: Lead creation data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created lead
    """
    lead = await LeadService.create_lead(db, lead_data)
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
@limiter.limit(get_rate_limit("leads_update"))
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a lead.
    
    Args:
        lead_id: Lead ID
        lead_data: Lead update data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated lead
    """
    lead = await LeadService.update_lead(db, lead_id, lead_data)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit("leads_delete"))
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a lead (soft delete).
    
    Args:
        lead_id: Lead ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        No content
    """
    await LeadService.delete_lead(db, lead_id)


@router.post("/bulk", response_model=BulkLeadResponse)
@limiter.limit(get_rate_limit("bulk_operations"))
async def bulk_create_leads(
    leads_data: List[LeadCreate],
    skip_duplicates: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create multiple leads in bulk.
    
    Args:
        leads_data: List of lead creation data
        skip_duplicates: Whether to skip duplicate websites
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Bulk operation result
    """
    created_leads, errors = await LeadService.bulk_create_leads(
        db, leads_data, skip_duplicates
    )
    
    return BulkLeadResponse(
        successful_count=len(created_leads),
        failed_count=len(errors),
        errors=errors,
        created_ids=[lead.id for lead in created_leads],
    )


@router.patch("/bulk", response_model=BulkLeadResponse)
@limiter.limit(get_rate_limit("bulk_operations"))
async def bulk_update_leads(
    operation: BulkLeadOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update multiple leads in bulk.
    
    Args:
        operation: Bulk operation data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Bulk operation result
    """
    updated_count, errors = await LeadService.bulk_update_leads(db, operation)
    
    return BulkLeadResponse(
        successful_count=updated_count,
        failed_count=len(errors),
        errors=errors,
    )
