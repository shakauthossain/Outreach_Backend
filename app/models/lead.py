"""
Lead model with optimized indexes for performance.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Lead(Base):
    """
    Lead model representing a business prospect with website performance data.
    
    Indexes are strategically placed on frequently queried columns to optimize:
    - Search operations (company name)
    - Filtering (mail_sent status, speed scores)
    - GHL integration lookups (conversation_id)
    - Duplicate prevention (website_url)
    """
    __tablename__ = "leads"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Core Business Information
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Website Performance Metrics
    website_speed_web: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    website_speed_mobile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accessibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seo_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_practices_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Screenshot URLs
    screenshot_url_web: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    screenshot_url_mobile: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    recommendations_screenshot_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Recommendations Data (stored as JSON string)
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Email Generation
    subject_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    generated_mail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mail_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Punchlines
    punchlines: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # GoHighLevel Integration
    conversation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Additional Metadata
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Composite Indexes for Common Query Patterns
    __table_args__ = (
        # Index for filtering by mail status and performance (used in dashboard filters)
        Index('ix_leads_mail_sent_web_speed', 'mail_sent', 'website_speed_web'),
        
        # Index for duplicate detection and lookup
        Index('ix_leads_company_website', 'company', 'website_url'),
        
        # Index for date-based queries with status
        Index('ix_leads_created_mail_sent', 'created_at', 'mail_sent'),
        
        # Index for GHL conversation lookups
        Index('ix_leads_conversation_id', 'conversation_id'),
        
        # Partial index for active (non-deleted) records
        Index('ix_leads_active', 'deleted_at', postgresql_where='deleted_at IS NULL'),
        
        # Check constraints for data integrity
        CheckConstraint('website_speed_web >= 0 AND website_speed_web <= 100', name='ck_web_speed_range'),
        CheckConstraint('website_speed_mobile >= 0 AND website_speed_mobile <= 100', name='ck_mobile_speed_range'),
        CheckConstraint('accessibility_score >= 0 AND accessibility_score <= 100', name='ck_a11y_range'),
        CheckConstraint('seo_score >= 0 AND seo_score <= 100', name='ck_seo_range'),
        CheckConstraint('best_practices_score >= 0 AND best_practices_score <= 100', name='ck_bp_range'),
    )
    
    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, company='{self.company}', website_url='{self.website_url}')>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if lead is soft-deleted"""
        return self.deleted_at is not None
    
    @property
    def average_performance_score(self) -> Optional[float]:
        """Calculate average performance score across all metrics"""
        scores = [
            self.website_speed_web,
            self.website_speed_mobile,
            self.accessibility_score,
            self.seo_score,
            self.best_practices_score
        ]
        valid_scores = [s for s in scores if s is not None]
        
        if not valid_scores:
            return None
        
        return sum(valid_scores) / len(valid_scores)
