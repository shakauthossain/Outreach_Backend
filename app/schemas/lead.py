"""
Lead schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator, field_validator
import re


class LeadBase(BaseModel):
    """Base lead schema with common fields"""
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    website_url: HttpUrl = Field(..., description="Company website URL")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact person name")
    location: Optional[str] = Field(None, max_length=255, description="Company location")
    industry: Optional[str] = Field(None, max_length=100, description="Industry/sector")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None:
            return v
        
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Check if it contains only digits and + (for international)
        if not re.match(r'^\+?[\d]{7,15}$', cleaned):
            raise ValueError('Invalid phone number format')
        
        return v


class LeadCreate(LeadBase):
    """Schema for creating a new lead"""
    conversation_id: Optional[str] = Field(None, max_length=255, description="GHL conversation ID")


class LeadUpdate(BaseModel):
    """Schema for updating a lead (all fields optional)"""
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[HttpUrl] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    contact_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    mail_sent: Optional[bool] = None
    conversation_id: Optional[str] = Field(None, max_length=255)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None:
            return v
        
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        if not re.match(r'^\+?[\d]{7,15}$', cleaned):
            raise ValueError('Invalid phone number format')
        
        return v


class LeadPerformanceUpdate(BaseModel):
    """Schema for updating performance metrics"""
    website_speed_web: Optional[float] = Field(None, ge=0, le=100)
    website_speed_mobile: Optional[float] = Field(None, ge=0, le=100)
    accessibility_score: Optional[float] = Field(None, ge=0, le=100)
    seo_score: Optional[float] = Field(None, ge=0, le=100)
    best_practices_score: Optional[float] = Field(None, ge=0, le=100)
    screenshot_url_web: Optional[str] = Field(None, max_length=512)
    screenshot_url_mobile: Optional[str] = Field(None, max_length=512)
    recommendations_screenshot_url: Optional[str] = Field(None, max_length=512)
    recommendations: Optional[str] = None


class LeadResponse(LeadBase):
    """Schema for lead response (full details, used for single lead fetch)"""
    id: int
    
    # Performance metrics
    website_speed_web: Optional[float] = None
    website_speed_mobile: Optional[float] = None
    accessibility_score: Optional[float] = None
    seo_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    
    # Screenshots
    screenshot_url_web: Optional[str] = None
    screenshot_url_mobile: Optional[str] = None
    recommendations_screenshot_url: Optional[str] = None
    
    # Recommendations
    recommendations: Optional[str] = None
    
    # PageSpeed Metrics (detailed performance diagnostics)
    pagespeed_metrics_mobile: Optional[str] = None
    pagespeed_metrics_desktop: Optional[str] = None
    
    # Email
    subject_line: Optional[str] = None
    generated_mail: Optional[str] = None
    mail_sent: bool = False
    
    # Punchlines
    punchlines: Optional[str] = None
    
    # GHL
    conversation_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LeadListItem(LeadBase):
    """Lightweight schema for lead list responses (excludes large JSON fields)"""
    id: int
    
    # Performance metrics
    website_speed_web: Optional[float] = None
    website_speed_mobile: Optional[float] = None
    accessibility_score: Optional[float] = None
    seo_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    
    # Screenshots
    screenshot_url_web: Optional[str] = None
    screenshot_url_mobile: Optional[str] = None
    recommendations_screenshot_url: Optional[str] = None
    
    # Recommendations - included as it's not as large
    recommendations: Optional[str] = None
    
    # Email
    subject_line: Optional[str] = None
    generated_mail: Optional[str] = None
    mail_sent: bool = False
    
    # Punchlines
    punchlines: Optional[str] = None
    
    # GHL
    conversation_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Note: pagespeed_metrics_mobile and pagespeed_metrics_desktop are excluded
    # for performance. Use the single lead fetch endpoint to get these.
    
    class Config:
        from_attributes = True


class LeadListQuery(BaseModel):
    """Query parameters for listing leads"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=100, ge=1, le=1000, description="Items per page")
    search: Optional[str] = Field(None, description="Search by company name")
    mail_sent: Optional[bool] = Field(None, description="Filter by mail sent status")
    has_speed_test: Optional[bool] = Field(None, description="Filter by speed test completion")
    min_web_speed: Optional[float] = Field(None, ge=0, le=100)
    max_web_speed: Optional[float] = Field(None, ge=0, le=100)
    min_mobile_speed: Optional[float] = Field(None, ge=0, le=100)
    max_mobile_speed: Optional[float] = Field(None, ge=0, le=100)
    industry: Optional[str] = Field(None, description="Filter by industry")
    conversation_id: Optional[str] = Field(None, description="Filter by GHL conversation")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")
    
    @property
    def skip(self) -> int:
        """Calculate skip offset from page and page_size"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Return page_size as limit"""
        return self.page_size
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order"""
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be either "asc" or "desc"')
        return v


class LeadStatistics(BaseModel):
    """Statistics about leads"""
    total_leads: int
    leads_with_speed_test: int
    leads_with_mail_sent: int
    average_web_speed: Optional[float] = None
    average_mobile_speed: Optional[float] = None
    performance_distribution: dict = Field(
        description="Breakdown by performance tier: excellent, good, needs_improvement, poor"
    )
    leads_by_industry: dict = Field(description="Count of leads per industry")
    recent_additions: int = Field(description="Leads added in last 7 days")


class BulkLeadOperation(BaseModel):
    """Schema for bulk operations on leads"""
    lead_ids: list[int] = Field(..., min_length=1, description="List of lead IDs")
    
    @field_validator('lead_ids')
    @classmethod
    def validate_lead_ids(cls, v: list[int]) -> list[int]:
        """Ensure lead IDs are unique and valid"""
        if len(v) != len(set(v)):
            raise ValueError('Duplicate lead IDs found')
        
        if any(id <= 0 for id in v):
            raise ValueError('Invalid lead ID (must be positive)')
        
        return v


class CSVColumnMapping(BaseModel):
    """Schema for CSV column mapping during import"""
    company: str
    website_url: str
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None


class LeadListResponse(BaseModel):
    """Response schema for paginated lead list"""
    leads: list[LeadListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkLeadResponse(BaseModel):
    """Response schema for bulk operations"""
    successful_count: int
    failed_count: int
    errors: list[str] = []
    created_ids: list[int] = []

