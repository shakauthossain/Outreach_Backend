"""Lead service containing business logic for lead operations."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadListQuery,
    LeadStatistics,
    BulkLeadOperation,
)
from app.core.exceptions import NotFoundError, DuplicateError, ValidationError
from app.core.cache import cache_manager, CacheTTL, CacheKeys, generate_cache_key


class LeadService:
    """Service for lead-related business logic."""
    
    @staticmethod
    async def get_lead_by_id(db: AsyncSession, lead_id: int) -> Lead:
        """
        Get a single lead by ID.
        
        Args:
            db: Database session
            lead_id: Lead ID
            
        Returns:
            Lead instance
            
        Raises:
            NotFoundError: If lead not found
        """
        # Check cache first
        cache_key = generate_cache_key("lead", lead_id, prefix="leads:detail")
        cached = await cache_manager.get(cache_key)
        if cached:
            # Return cached lead (need to reconstruct as model)
            result = await db.execute(select(Lead).where(Lead.id == lead_id))
            return result.scalar_one_or_none()
        
        result = await db.execute(
            select(Lead).where(
                and_(
                    Lead.id == lead_id,
                    Lead.deleted_at.is_(None)
                )
            )
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise NotFoundError(f"Lead with ID {lead_id} not found")
        
        # Cache the result
        await cache_manager.set(cache_key, lead.id, CacheTTL.DETAIL)
        
        return lead
    
    @staticmethod
    async def get_lead_by_website(db: AsyncSession, website_url: str) -> Optional[Lead]:
        """
        Get a lead by website URL.
        
        Args:
            db: Database session
            website_url: Website URL
            
        Returns:
            Lead instance or None
        """
        result = await db.execute(
            select(Lead).where(
                and_(
                    Lead.website_url == website_url,
                    Lead.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_leads(
        db: AsyncSession,
        query: LeadListQuery,
    ) -> tuple[List[Lead], int]:
        """
        Get paginated list of leads with filters.
        
        Args:
            db: Database session
            query: Query parameters with filters and pagination
            
        Returns:
            Tuple of (leads list, total count)
        """
        # Build base query
        stmt = select(Lead).where(Lead.deleted_at.is_(None))
        
        # Apply search filter
        if query.search:
            search_term = f"%{query.search}%"
            stmt = stmt.where(
                or_(
                    Lead.company.ilike(search_term),
                    Lead.website_url.ilike(search_term),
                    Lead.email.ilike(search_term),
                )
            )
        
        # Apply mail_sent filter
        if query.mail_sent is not None:
            stmt = stmt.where(Lead.mail_sent == query.mail_sent)
        
        # Apply score filters
        if query.min_web_speed is not None:
            stmt = stmt.where(Lead.website_speed_web >= query.min_web_speed)
        if query.max_web_speed is not None:
            stmt = stmt.where(Lead.website_speed_web <= query.max_web_speed)
        
        if query.min_mobile_speed is not None:
            stmt = stmt.where(Lead.website_speed_mobile >= query.min_mobile_speed)
        if query.max_mobile_speed is not None:
            stmt = stmt.where(Lead.website_speed_mobile <= query.max_mobile_speed)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply sorting
        if query.sort_by:
            sort_column = getattr(Lead, query.sort_by, Lead.created_at)
            if query.sort_order == "desc":
                stmt = stmt.order_by(sort_column.desc())
            else:
                stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(Lead.created_at.desc())
        
        # Apply pagination
        stmt = stmt.offset(query.skip).limit(query.limit)
        
        # Execute query
        result = await db.execute(stmt)
        leads = result.scalars().all()
        
        return list(leads), total
    
    @staticmethod
    async def create_lead(db: AsyncSession, lead_data: LeadCreate) -> Lead:
        """
        Create a new lead.
        
        Args:
            db: Database session
            lead_data: Lead creation data
            
        Returns:
            Created lead instance
            
        Raises:
            DuplicateError: If lead with same website already exists
        """
        # Check for duplicate website
        existing = await LeadService.get_lead_by_website(db, lead_data.website_url)
        if existing:
            raise DuplicateError(
                f"Lead with website {lead_data.website_url} already exists"
            )
        
        # Create lead
        lead = Lead(**lead_data.model_dump())
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        # Invalidate list cache
        await cache_manager.delete_pattern(CacheKeys.LEAD_LIST)
        await cache_manager.delete(CacheKeys.LEAD_STATS)
        
        return lead
    
    @staticmethod
    async def update_lead(
        db: AsyncSession,
        lead_id: int,
        lead_data: LeadUpdate,
    ) -> Lead:
        """
        Update a lead.
        
        Args:
            db: Database session
            lead_id: Lead ID
            lead_data: Lead update data
            
        Returns:
            Updated lead instance
            
        Raises:
            NotFoundError: If lead not found
            DuplicateError: If updating to a duplicate website URL
        """
        lead = await LeadService.get_lead_by_id(db, lead_id)
        
        # Check for duplicate website if updating URL
        if lead_data.website_url and lead_data.website_url != lead.website_url:
            existing = await LeadService.get_lead_by_website(db, lead_data.website_url)
            if existing:
                raise DuplicateError(
                    f"Lead with website {lead_data.website_url} already exists"
                )
        
        # Update fields
        update_data = lead_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)
        
        lead.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(lead)
        
        # Invalidate caches
        cache_key = generate_cache_key("lead", lead_id, prefix="leads:detail")
        await cache_manager.delete(cache_key)
        await cache_manager.delete_pattern(CacheKeys.LEAD_LIST)
        await cache_manager.delete(CacheKeys.LEAD_STATS)
        
        return lead
    
    @staticmethod
    async def delete_lead(db: AsyncSession, lead_id: int) -> Lead:
        """
        Soft delete a lead.
        
        Args:
            db: Database session
            lead_id: Lead ID
            
        Returns:
            Deleted lead instance
            
        Raises:
            NotFoundError: If lead not found
        """
        lead = await LeadService.get_lead_by_id(db, lead_id)
        
        # Soft delete
        lead.deleted_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(lead)
        
        # Invalidate caches
        cache_key = generate_cache_key("lead", lead_id, prefix="leads:detail")
        await cache_manager.delete(cache_key)
        await cache_manager.delete_pattern(CacheKeys.LEAD_LIST)
        await cache_manager.delete(CacheKeys.LEAD_STATS)
        
        return lead
    
    @staticmethod
    async def get_statistics(db: AsyncSession) -> LeadStatistics:
        """
        Get lead statistics.
        
        Args:
            db: Database session
            
        Returns:
            Lead statistics
        """
        # Check cache
        cached = await cache_manager.get(CacheKeys.LEAD_STATS)
        if cached:
            return LeadStatistics(**cached)
        
        # Query statistics
        result = await db.execute(
            select(
                func.count(Lead.id).label("total"),
                func.count(Lead.id).filter(Lead.mail_sent == True).label("mail_sent_count"),
                func.avg(Lead.website_speed_web).label("avg_web_speed"),
                func.avg(Lead.website_speed_mobile).label("avg_mobile_speed"),
            ).where(Lead.deleted_at.is_(None))
        )
        row = result.one()
        
        stats = LeadStatistics(
            total_leads=row.total or 0,
            mail_sent_count=row.mail_sent_count or 0,
            average_web_speed=round(row.avg_web_speed or 0, 2),
            average_mobile_speed=round(row.avg_mobile_speed or 0, 2),
        )
        
        # Cache for 5 minutes
        await cache_manager.set(
            CacheKeys.LEAD_STATS,
            stats.model_dump(),
            CacheTTL.LIST
        )
        
        return stats
    
    @staticmethod
    async def bulk_create_leads(
        db: AsyncSession,
        leads_data: List[LeadCreate],
        skip_duplicates: bool = True,
    ) -> tuple[List[Lead], List[str]]:
        """
        Create multiple leads in bulk.
        
        Args:
            db: Database session
            leads_data: List of lead creation data
            skip_duplicates: Whether to skip duplicate websites
            
        Returns:
            Tuple of (created leads, error messages)
        """
        created_leads = []
        errors = []
        
        for lead_data in leads_data:
            try:
                # Check for duplicate
                existing = await LeadService.get_lead_by_website(db, lead_data.website_url)
                if existing:
                    if skip_duplicates:
                        errors.append(
                            f"Skipped duplicate: {lead_data.website_url}"
                        )
                        continue
                    else:
                        errors.append(
                            f"Duplicate website: {lead_data.website_url}"
                        )
                        continue
                
                # Create lead
                lead = Lead(**lead_data.model_dump())
                db.add(lead)
                created_leads.append(lead)
                
            except Exception as e:
                errors.append(
                    f"Error creating lead {lead_data.website_url}: {str(e)}"
                )
        
        # Commit all at once
        if created_leads:
            await db.commit()
            
            # Refresh all created leads
            for lead in created_leads:
                await db.refresh(lead)
            
            # Invalidate caches
            await cache_manager.delete_pattern(CacheKeys.LEAD_LIST)
            await cache_manager.delete(CacheKeys.LEAD_STATS)
        
        return created_leads, errors
    
    @staticmethod
    async def bulk_update_leads(
        db: AsyncSession,
        operation: BulkLeadOperation,
    ) -> tuple[int, List[str]]:
        """
        Update multiple leads in bulk.
        
        Args:
            db: Database session
            operation: Bulk operation data
            
        Returns:
            Tuple of (updated count, error messages)
        """
        updated_count = 0
        errors = []
        
        for lead_id in operation.lead_ids:
            try:
                lead = await LeadService.get_lead_by_id(db, lead_id)
                
                # Apply updates
                for field, value in operation.updates.items():
                    if hasattr(lead, field):
                        setattr(lead, field, value)
                
                lead.updated_at = datetime.utcnow()
                updated_count += 1
                
            except NotFoundError:
                errors.append(f"Lead {lead_id} not found")
            except Exception as e:
                errors.append(f"Error updating lead {lead_id}: {str(e)}")
        
        if updated_count > 0:
            await db.commit()
            
            # Invalidate caches
            await cache_manager.delete_pattern(CacheKeys.LEAD_LIST)
            await cache_manager.delete_pattern(CacheKeys.LEAD_DETAIL)
            await cache_manager.delete(CacheKeys.LEAD_STATS)
        
        return updated_count, errors
