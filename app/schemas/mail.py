"""
Mail generation and email schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator


class MailGenerateRequest(BaseModel):
    """Request schema for generating email content"""
    lead_id: int = Field(..., description="Lead ID to generate email for")
    template_id: Optional[int] = Field(None, description="Email template ID (optional)")
    custom_prompt: Optional[str] = Field(None, description="Custom instructions for email generation")
    tone: str = Field(default="professional", description="Email tone: professional, friendly, casual")
    include_performance_data: bool = Field(default=True, description="Include website performance metrics")
    include_recommendations: bool = Field(default=True, description="Include improvement recommendations")
    
    @field_validator('tone')
    @classmethod
    def validate_tone(cls, v: str) -> str:
        """Validate email tone"""
        allowed_tones = ['professional', 'friendly', 'casual', 'formal']
        if v not in allowed_tones:
            raise ValueError(f'Tone must be one of: {", ".join(allowed_tones)}')
        return v


class MailGenerateResponse(BaseModel):
    """Response schema for generated email"""
    lead_id: int
    subject: str
    body: str
    performance_summary: Optional[dict] = None
    recommendations_included: bool


class MailSaveRequest(BaseModel):
    """Request schema for saving generated email"""
    lead_id: int
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)


class MailSendRequest(BaseModel):
    """Request schema for sending email"""
    lead_id: int
    to_email: EmailStr = Field(..., description="Recipient email address")
    cc_emails: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc_emails: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    subject: Optional[str] = Field(None, description="Override saved subject")
    body: Optional[str] = Field(None, description="Override saved body")
    send_immediately: bool = Field(default=True, description="Send immediately or queue")


class MailSendResponse(BaseModel):
    """Response schema for email sending"""
    lead_id: int
    sent: bool
    message: str
    sendgrid_message_id: Optional[str] = None


class BulkMailSendRequest(BaseModel):
    """Request schema for bulk email sending"""
    lead_ids: List[int] = Field(..., min_length=1, description="List of lead IDs")
    template_id: Optional[int] = Field(None, description="Email template to use")
    send_immediately: bool = Field(default=False, description="Send immediately or queue")
    
    @field_validator('lead_ids')
    @classmethod
    def validate_lead_ids(cls, v: List[int]) -> List[int]:
        """Validate lead IDs"""
        if len(v) != len(set(v)):
            raise ValueError('Duplicate lead IDs found')
        
        if len(v) > 100:
            raise ValueError('Cannot send to more than 100 leads at once')
        
        return v


class EmailTemplateCreate(BaseModel):
    """Request schema for creating email template"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=255, description="Comma-separated tags")
    is_default: bool = Field(default=False)


class EmailTemplateUpdate(BaseModel):
    """Request schema for updating email template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    """Response schema for email template"""
    id: int
    name: str
    description: Optional[str] = None
    subject: str
    body: str
    category: Optional[str] = None
    tags: Optional[str] = None
    usage_count: int
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Aliases for backward compatibility
MailGenerationRequest = MailGenerateRequest
MailGenerationResponse = MailGenerateResponse

