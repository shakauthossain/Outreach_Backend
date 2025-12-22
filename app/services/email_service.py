"""Email generation and sending service."""

import os
import re
import httpx
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.models.lead import Lead
from app.services.llm_provider import get_llm_client
from app.config import settings


MAIL_SENDER = os.getenv("MAIL_SENDER", "contact@notionhive.com")
GHL_API_KEY = os.getenv("GOHIGHLEVEL_KEY", "")
GHL_LOCATION_ID = os.getenv("GOHIGHLEVEL_LOCATION_ID", "")
ENV = os.getenv("ENV", "prod")
TEST_EMAIL = os.getenv("TEST_EMAIL", None)


EMAIL_TEMPLATE = '''
Write an awesome cold outbound sales email for the following lead:

- First Name: {first_name}
- Job Title: {title}
- Company: {company}
- Website URL: {website_url}
- Desktop PageSpeed Score: {desktop_score}
- Mobile PageSpeed Score: {mobile_score}
- Screenshot Link: {screenshot_url_web}

This email should:
- Address the lead by name and reference their job role
- Highlight their website's low PageSpeed score (mention both desktop and mobile)
- Reference real-world impact of slow websites (e.g., "a 1s delay can drop conversions by X%")
- Mention that a performance audit screenshot is available (use {screenshot_url_web})
- Offer a quick, no-pressure consultation to improve performance
- Keep the tone confident, friendly, and brief
- Include a clear call-to-action to book a short call
- Do not add regards or ending of the mail
- Make it personalized, relevant, and focused on solving their problem.

Make it personalized, relevant, and focused on solving their problem.
'''


class EmailService:
    """Service for generating and sending emails to leads."""
    
    @staticmethod
    async def generate_email(
        db: AsyncSession,
        lead_id: int
    ) -> Tuple[str, str]:
        """
        Generate a personalized email for a lead.
        
        Args:
            db: Database session
            lead_id: Lead ID
            
        Returns:
            Tuple of (subject, body)
            
        Raises:
            ValueError: If lead not found or missing required data
        """
        # Fetch lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Extract first name from contact_name
        first_name = lead.contact_name.split()[0] if lead.contact_name else "there"
        
        # Build prompt
        prompt = PromptTemplate(
            input_variables=[
                "first_name", "title", "company", "website_url",
                "desktop_score", "mobile_score", "screenshot_url_web"
            ],
            template=EMAIL_TEMPLATE,
        )
        
        # Get LLM client
        llm = get_llm_client()
        
        # Create chain
        chain = prompt | llm | StrOutputParser()
        
        # Prepare variables
        variables = {
            "first_name": first_name,
            "title": lead.title or "Team Member",
            "company": lead.company,
            "website_url": lead.website_url,
            "desktop_score": lead.website_speed_web or 0,
            "mobile_score": lead.website_speed_mobile or 0,
            "screenshot_url_web": lead.screenshot_url_web or "N/A"
        }
        
        # Generate email
        result_text = chain.invoke(variables).strip()
        
        # Extract subject line
        match = re.search(r"Subject:\s*(.*)", result_text, re.IGNORECASE)
        subject_line = match.group(1).strip() if match else f"Website performance improvements for {lead.company}"
        
        # Extract body (remove subject line if present)
        body = re.sub(r"Subject:.*\n?", "", result_text, flags=re.IGNORECASE).strip()
        
        # Add sign-off
        body = body.strip() + "\n\nBest regards,\nNotionhive Tech Team"
        
        # Update lead with generated email
        lead.generated_email = body
        lead.final_email = body
        lead.email_subject = subject_line
        
        await db.commit()
        
        return subject_line, body
    
    @staticmethod
    async def send_email(
        db: AsyncSession,
        lead_id: int,
        email_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email to a lead via GoHighLevel.
        
        Args:
            db: Database session
            lead_id: Lead ID
            email_body: Optional custom email body (uses lead.final_email if None)
            
        Returns:
            Dict with send status and details
            
        Raises:
            ValueError: If lead not found, missing email, or missing GHL contact ID
            RuntimeError: If email send fails
        """
        # Fetch lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        if not lead.email:
            raise ValueError("Lead has no email address")
        
        if not lead.ghl_contact_id:
            raise ValueError("Lead has no GoHighLevel contact ID")
        
        # Use provided body or lead's final_email
        body = email_body or lead.final_email
        
        if not body:
            raise ValueError("No email body provided and lead has no final_email")
        
        # Determine recipient (use test email in dev mode)
        recipient_email = TEST_EMAIL if ENV == "dev" and TEST_EMAIL else lead.email
        
        # Get subject
        subject = lead.email_subject or f"Website performance improvements for {lead.company}"
        
        # Update lead
        lead.final_email = body
        
        # Prepare GHL API request
        send_url = "https://services.leadconnectorhq.com/conversations/messages"
        
        payload = {
            "type": "Email",
            "contactId": lead.ghl_contact_id,
            "emailFrom": MAIL_SENDER,
            "emailTo": recipient_email,
            "subject": subject,
            "html": f"<p>{body.replace(chr(10), '<br>')}</p>",
            "message": body,
            "emailReplyMode": "reply"
        }
        
        headers = {
            "Authorization": f"Bearer {GHL_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": "2021-04-15"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(send_url, headers=headers, json=payload)
                response.raise_for_status()
            
            # Try to get conversation ID
            conversation_id = None
            search_url = "https://services.leadconnectorhq.com/conversations/search"
            search_params = {
                "locationId": GHL_LOCATION_ID,
                "contactId": lead.ghl_contact_id
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for attempt in range(5):
                    search_resp = await client.get(search_url, headers=headers, params=search_params)
                    
                    if search_resp.status_code == 200:
                        data = search_resp.json()
                        for convo in data.get("conversations", []):
                            if convo.get("lastMessageType") == "TYPE_EMAIL":
                                conversation_id = convo.get("id")
                                break
                    
                    if conversation_id:
                        lead.conversation_id = conversation_id
                        break
                    
                    await asyncio.sleep(1.5)
            
            # Mark as sent
            lead.mail_sent = True
            await db.commit()
            
            return {
                "success": True,
                "lead_id": lead_id,
                "recipient": recipient_email,
                "subject": subject,
                "conversation_id": conversation_id
            }
            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"GHL email send failed: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Failed to send email: {str(e)}")
    
    @staticmethod
    async def save_draft(
        db: AsyncSession,
        lead_id: int,
        email_body: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save email draft for a lead.
        
        Args:
            db: Database session
            lead_id: Lead ID
            email_body: Email body text
            subject: Optional subject line
            
        Returns:
            Dict with save confirmation
            
        Raises:
            ValueError: If lead not found
        """
        # Fetch lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Update lead
        lead.final_email = email_body
        
        if subject:
            lead.email_subject = subject
        elif not lead.email_subject:
            lead.email_subject = f"Website performance improvements for {lead.company}"
        
        await db.commit()
        
        return {
            "success": True,
            "lead_id": lead_id,
            "message": "Draft saved successfully"
        }


# Import asyncio for sleep
import asyncio
