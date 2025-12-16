"""
Email template model for reusable email templates.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class EmailTemplate(Base):
    """
    Email template for generating personalized outreach emails.
    Supports variable substitution using {{variable_name}} syntax.
    """
    __tablename__ = "email_templates"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Template Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Email Content
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Template Metadata
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Comma-separated
    
    # Usage Tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Owner
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_templates_name_active', 'name', 'is_active'),
        Index('ix_templates_category', 'category'),
        Index('ix_templates_usage', 'usage_count'),
    )
    
    def __repr__(self) -> str:
        return f"<EmailTemplate(id={self.id}, name='{self.name}')>"
