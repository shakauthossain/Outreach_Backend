"""Mail sending background tasks."""

import asyncio
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.integrations.sendgrid import sendgrid_client
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.services.mail_service import MailService
from app.schemas.mail import MailGenerationRequest
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name="mail.send_single",
    max_retries=3,
)
def send_single_email(
    self,
    lead_id: int,
    subject: str,
    html_content: str,
    text_content: str = None,
):
    """
    Send email to a single lead.
    
    Args:
        lead_id: Lead ID
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body
        
    Returns:
        Send result
    """
    self.update_state(
        state="PROGRESS",
        meta={"status": "Sending email..."}
    )
    
    try:
        return asyncio.run(_send_email(lead_id, subject, html_content, text_content))
    except Exception as e:
        raise self.retry(exc=e)


async def _send_email(
    lead_id: int,
    subject: str,
    html_content: str,
    text_content: str = None,
) -> Dict[str, Any]:
    """
    Internal async function to send email.
    
    Args:
        lead_id: Lead ID
        subject: Email subject
        html_content: HTML content
        text_content: Text content
        
    Returns:
        Send result
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        if not lead.email:
            raise ValueError(f"Lead {lead_id} has no email address")
        
        # Send email via SendGrid
        send_result = await sendgrid_client.send_email(
            to_email=lead.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=lead.company,
            custom_args={
                "lead_id": str(lead_id),
                "campaign": "speed_outreach",
            }
        )
        
        # Mark as sent
        await MailService.mark_mail_sent(db, lead_id)
        
        return {
            "lead_id": lead_id,
            "email": lead.email,
            "send_result": send_result,
            "status": "sent",
        }


@celery_app.task(
    bind=True,
    name="mail.generate_and_send",
    max_retries=2,
)
def generate_and_send_email(
    self,
    lead_id: int,
    tone: str = "professional",
    include_punchline: bool = False,
):
    """
    Generate and send email for a lead.
    
    Args:
        lead_id: Lead ID
        tone: Email tone
        include_punchline: Whether to include punchline
        
    Returns:
        Generation and send result
    """
    self.update_state(
        state="PROGRESS",
        meta={"status": "Generating email content..."}
    )
    
    try:
        return asyncio.run(_generate_and_send(lead_id, tone, include_punchline))
    except Exception as e:
        raise self.retry(exc=e)


async def _generate_and_send(
    lead_id: int,
    tone: str,
    include_punchline: bool,
) -> Dict[str, Any]:
    """
    Internal async function to generate and send email.
    
    Args:
        lead_id: Lead ID
        tone: Email tone
        include_punchline: Include punchline flag
        
    Returns:
        Result data
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Generate email content
        request = MailGenerationRequest(
            tone=tone,
            include_punchline=include_punchline,
            punchline=lead.punchline if include_punchline else None,
        )
        
        mail_response = await MailService.generate_mail_content(lead, request)
        
        # Send email
        send_result = await sendgrid_client.send_email(
            to_email=lead.email,
            subject=mail_response.subject,
            html_content=mail_response.body,
            to_name=lead.company,
            custom_args={
                "lead_id": str(lead_id),
                "campaign": "speed_outreach",
            }
        )
        
        # Mark as sent
        await MailService.mark_mail_sent(db, lead_id)
        
        return {
            "lead_id": lead_id,
            "email": lead.email,
            "subject": mail_response.subject,
            "send_result": send_result,
            "status": "completed",
        }


@celery_app.task(
    bind=True,
    name="mail.send_bulk",
)
def send_bulk_emails(self, lead_ids: list[int], tone: str = "professional"):
    """
    Send emails to multiple leads.
    
    Args:
        lead_ids: List of lead IDs
        tone: Email tone
        
    Returns:
        Batch results
    """
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(lead_ids),
            "status": "Starting bulk send...",
        }
    )
    
    results = {
        "successful": [],
        "failed": [],
        "total": len(lead_ids),
    }
    
    for i, lead_id in enumerate(lead_ids):
        try:
            task_result = generate_and_send_email.apply_async(
                args=[lead_id, tone],
                countdown=i * 5,  # Stagger by 5 seconds to respect rate limits
            )
            
            results["successful"].append({
                "lead_id": lead_id,
                "task_id": task_result.id,
            })
            
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(lead_ids),
                    "status": f"Queued {i + 1}/{len(lead_ids)}...",
                }
            )
            
        except Exception as e:
            results["failed"].append({
                "lead_id": lead_id,
                "error": str(e),
            })
    
    return results
