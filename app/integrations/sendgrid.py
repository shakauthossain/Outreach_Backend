"""SendGrid email API client."""

from typing import Optional, Dict, Any, List

import httpx

from app.config import settings
from app.core.exceptions import ExternalAPIError


class SendGridClient:
    """Client for SendGrid email API."""
    
    BASE_URL = "https://api.sendgrid.com/v3"
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        self.timeout = 30.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        to_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        custom_args: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via SendGrid.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            to_name: Recipient name
            reply_to: Reply-to email address
            cc: CC email addresses
            bcc: BCC email addresses
            attachments: List of attachments
            custom_args: Custom tracking arguments
            
        Returns:
            Send result
            
        Raises:
            ExternalAPIError: If API call fails
        """
        # Build personalizations
        personalizations = [{
            "to": [{"email": to_email}],
            "subject": subject,
        }]
        
        if to_name:
            personalizations[0]["to"][0]["name"] = to_name
        
        if cc:
            personalizations[0]["cc"] = [{"email": email} for email in cc]
        if bcc:
            personalizations[0]["bcc"] = [{"email": email} for email in bcc]
        if custom_args:
            personalizations[0]["custom_args"] = custom_args
        
        # Build content
        content = [
            {
                "type": "text/html",
                "value": html_content,
            }
        ]
        
        if text_content:
            content.insert(0, {
                "type": "text/plain",
                "value": text_content,
            })
        
        # Build payload
        payload = {
            "personalizations": personalizations,
            "from": {
                "email": self.from_email,
                "name": self.from_name,
            },
            "content": content,
        }
        
        if reply_to:
            payload["reply_to"] = {"email": reply_to}
        
        if attachments:
            payload["attachments"] = attachments
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/mail/send",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code not in [200, 201, 202]:
                    raise ExternalAPIError(
                        f"SendGrid API error: {response.status_code}",
                        detail={
                            "response": response.text[:500],
                            "to": to_email,
                        }
                    )
                
                return {
                    "status": "sent",
                    "to": to_email,
                    "subject": subject,
                    "message_id": response.headers.get("X-Message-Id"),
                }
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"SendGrid API request error: {str(e)}",
                detail={"to": to_email}
            )
    
    async def send_bulk_emails(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails in bulk.
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            List of send results
        """
        results = []
        
        for email_data in emails:
            try:
                result = await self.send_email(**email_data)
                results.append(result)
            except ExternalAPIError as e:
                results.append({
                    "status": "failed",
                    "to": email_data.get("to_email"),
                    "error": str(e),
                })
        
        return results
    
    async def get_stats(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        aggregated_by: str = "day",
    ) -> Dict[str, Any]:
        """
        Get email statistics.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            aggregated_by: Aggregation period (day, week, month)
            
        Returns:
            Email statistics
        """
        params = {
            "start_date": start_date,
            "aggregated_by": aggregated_by,
        }
        
        if end_date:
            params["end_date"] = end_date
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/stats",
                    headers=self._get_headers(),
                    params=params,
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"SendGrid API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"SendGrid API request error: {str(e)}"
            )
    
    async def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validate an email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Validation result
        """
        payload = {
            "email": email,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/validations/email",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"SendGrid API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"SendGrid API request error: {str(e)}"
            )


# Global client instance
sendgrid_client = SendGridClient()
