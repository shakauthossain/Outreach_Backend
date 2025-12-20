"""Email generation and sending endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.email_service import EmailService
from app.core.rate_limit import limiter


router = APIRouter()


class EmailBody(BaseModel):
    """Request body for saving/sending emails."""
    email_body: str
    subject: Optional[str] = None


class EmailResponse(BaseModel):
    """Response model for email generation."""
    subject: str
    body: str
    lead_id: int


@router.post("/generate/{lead_id}", response_model=EmailResponse)
@limiter.limit("20/minute")
async def generate_email_for_lead(
    request: Request,
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> EmailResponse:
    """
    Generate a personalized email for a lead using LLM.
    
    Args:
        lead_id: ID of the lead
        
    Returns:
        Generated email with subject and body
        
    Raises:
        404: Lead not found
        400: Lead missing required data
    """
    try:
        subject, body = await EmailService.generate_email(db, lead_id)
        return EmailResponse(
            subject=subject,
            body=body,
            lead_id=lead_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate email: {str(e)}"
        )


@router.post("/save/{lead_id}", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def save_email_draft(
    request: Request,
    lead_id: int,
    email_data: EmailBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Save an email draft for a lead.
    
    Args:
        lead_id: ID of the lead
        email_data: Email body and optional subject
        
    Returns:
        Confirmation of save
        
    Raises:
        404: Lead not found
    """
    try:
        result = await EmailService.save_draft(
            db,
            lead_id,
            email_data.email_body,
            email_data.subject
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save draft: {str(e)}"
        )


@router.post("/send/{lead_id}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def send_email_to_lead(
    request: Request,
    lead_id: int,
    email_data: Optional[EmailBody] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Send email to a lead via GoHighLevel.
    
    Args:
        lead_id: ID of the lead
        email_data: Optional email body (uses saved draft if not provided)
        
    Returns:
        Send confirmation with details
        
    Raises:
        404: Lead not found
        400: Missing email or GHL contact ID
    """
    try:
        email_body = email_data.email_body if email_data else None
        result = await EmailService.send_email(db, lead_id, email_body)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )


@router.get("/{lead_id}", response_model=Dict[str, Any])
async def get_lead_email(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get saved email for a lead.
    
    Args:
        lead_id: ID of the lead
        
    Returns:
        Lead's email data
        
    Raises:
        404: Lead not found
    """
    from sqlalchemy import select
    from app.models.lead import Lead
    
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "lead_id": lead_id,
        "subject": lead.email_subject,
        "generated_email": lead.generated_email,
        "final_email": lead.final_email,
        "mail_sent": lead.mail_sent
    }
