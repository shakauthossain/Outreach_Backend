"""Mail generation service using LLM providers."""

from typing import Optional, Dict, Any
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.schemas.mail import MailGenerationRequest, MailGenerationResponse
from app.core.exceptions import ValidationError, ExternalAPIError
from app.config import settings


class MailService:
    """Service for email generation and templating."""
    
    @staticmethod
    def validate_lead_data(lead: Lead) -> None:
        """
        Validate that lead has required data for mail generation.
        
        Args:
            lead: Lead instance
            
        Raises:
            ValidationError: If required data is missing
        """
        missing_fields = []
        
        if not lead.company:
            missing_fields.append("company")
        if not lead.website_url:
            missing_fields.append("website_url")
        if not lead.website_speed_web and not lead.website_speed_mobile:
            missing_fields.append("performance scores")
        
        if missing_fields:
            raise ValidationError(
                f"Lead is missing required fields for mail generation: {', '.join(missing_fields)}"
            )
    
    @staticmethod
    def build_mail_context(lead: Lead) -> Dict[str, Any]:
        """
        Build context data for mail generation.
        
        Args:
            lead: Lead instance
            
        Returns:
            Context dictionary with lead data
        """
        # Calculate average performance
        avg_performance = lead.average_performance_score or 0
        
        # Determine performance category
        if avg_performance >= 90:
            performance_category = "excellent"
        elif avg_performance >= 75:
            performance_category = "good"
        elif avg_performance >= 50:
            performance_category = "moderate"
        else:
            performance_category = "poor"
        
        # Build context
        context = {
            "company": lead.company,
            "website_url": lead.website_url,
            "web_speed": lead.website_speed_web,
            "mobile_speed": lead.website_speed_mobile,
            "average_performance": round(avg_performance, 1),
            "performance_category": performance_category,
            "seo_score": lead.seo_score,
            "accessibility_score": lead.accessibility_score,
            "best_practices_score": lead.best_practices_score,
            "has_recommendations": bool(lead.recommendations),
            "recommendations_count": len(lead.recommendations.split("\n")) if lead.recommendations else 0,
        }
        
        return context
    
    @staticmethod
    def build_prompt(
        context: Dict[str, Any],
        tone: str = "professional",
        include_punchline: bool = False,
        punchline: Optional[str] = None,
    ) -> str:
        """
        Build LLM prompt for mail generation.
        
        Args:
            context: Lead context data
            tone: Email tone (professional, casual, friendly)
            include_punchline: Whether to include punchline
            punchline: Optional punchline text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Generate a professional email for a web performance audit outreach.

Company: {context['company']}
Website: {context['website_url']}

Performance Analysis:
- Desktop Performance: {context['web_speed']}/100
- Mobile Performance: {context['mobile_speed']}/100
- Average Performance: {context['average_performance']}/100 ({context['performance_category']})
- SEO Score: {context['seo_score']}/100
- Accessibility: {context['accessibility_score']}/100
- Best Practices: {context['best_practices_score']}/100

Email Requirements:
1. Tone: {tone}
2. Keep it concise (150-200 words)
3. Focus on the business impact of poor performance
4. Mention specific scores that need improvement
5. Include a clear call-to-action
6. Don't be overly salesy
7. Be helpful and consultative
"""
        
        if include_punchline and punchline:
            prompt += f"\n8. Include this punchline naturally: '{punchline}'\n"
        
        prompt += """
Generate the email body only (no subject line). Use proper formatting with paragraphs.
Make it personalized and relevant to their specific performance issues.
"""
        
        return prompt
    
    @staticmethod
    async def generate_mail_content(
        lead: Lead,
        request: MailGenerationRequest,
        llm_provider: str = "groq",
    ) -> MailGenerationResponse:
        """
        Generate email content using LLM.
        
        Args:
            lead: Lead instance
            request: Mail generation parameters
            llm_provider: LLM provider to use (groq, gemini, openai)
            
        Returns:
            Generated email content
            
        Raises:
            ValidationError: If lead data is invalid
            ExternalAPIError: If LLM API fails
        """
        # Validate lead data
        MailService.validate_lead_data(lead)
        
        # Build context
        context = MailService.build_mail_context(lead)
        
        # Build prompt
        prompt = MailService.build_prompt(
            context=context,
            tone=request.tone,
            include_punchline=request.include_punchline,
            punchline=request.punchline,
        )
        
        # Generate content using LLM
        # This will be implemented with actual LLM integration
        # For now, return a template-based response
        
        generated_body = MailService._generate_template_mail(context, request)
        
        # Generate subject line
        subject = MailService._generate_subject_line(context)
        
        return MailGenerationResponse(
            subject=subject,
            body=generated_body,
            lead_id=lead.id,
            company=lead.company,
            website_url=lead.website_url,
        )
    
    @staticmethod
    def _generate_template_mail(
        context: Dict[str, Any],
        request: MailGenerationRequest,
    ) -> str:
        """
        Generate email using template (fallback when LLM unavailable).
        
        Args:
            context: Lead context data
            request: Mail generation parameters
            
        Returns:
            Email body text
        """
        # Identify main issues
        issues = []
        if context['web_speed'] < 75:
            issues.append("desktop performance")
        if context['mobile_speed'] < 75:
            issues.append("mobile performance")
        if context['seo_score'] < 75:
            issues.append("SEO")
        if context['accessibility_score'] < 75:
            issues.append("accessibility")
        
        issues_text = ", ".join(issues) if issues else "web performance"
        
        # Build email
        body = f"""Hi there,

I was analyzing {context['company']}'s website and noticed some opportunities to improve your {issues_text}.

Your current performance scores are:
• Desktop: {context['web_speed']}/100
• Mobile: {context['mobile_speed']}/100
• SEO: {context['seo_score']}/100

These scores can directly impact your conversion rates and search rankings. Even a 1-second delay in page load time can result in a 7% reduction in conversions.

"""
        
        if request.include_punchline and request.punchline:
            body += f"{request.punchline}\n\n"
        
        body += """I'd be happy to share a detailed analysis and actionable recommendations to help improve these metrics.

Would you be interested in a quick call to discuss?

Best regards"""
        
        return body
    
    @staticmethod
    def _generate_subject_line(context: Dict[str, Any]) -> str:
        """
        Generate email subject line.
        
        Args:
            context: Lead context data
            
        Returns:
            Subject line text
        """
        avg_score = context['average_performance']
        
        if avg_score < 50:
            return f"Quick question about {context['company']}'s website performance"
        elif avg_score < 75:
            return f"Opportunity to improve {context['company']}'s web performance"
        else:
            return f"Thoughts on {context['company']}'s website optimization"
    
    @staticmethod
    def clean_html_content(html_content: str) -> str:
        """
        Clean and sanitize HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned HTML content
        """
        # Remove script tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        
        # Remove style tags
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # Remove on* event handlers
        html_content = re.sub(r'\son\w+="[^"]*"', '', html_content)
        
        return html_content
    
    @staticmethod
    async def mark_mail_sent(
        db: AsyncSession,
        lead_id: int,
    ) -> Lead:
        """
        Mark lead as mail sent.
        
        Args:
            db: Database session
            lead_id: Lead ID
            
        Returns:
            Updated lead instance
        """
        from app.services.lead_service import LeadService
        from app.schemas.lead import LeadUpdate
        
        lead = await LeadService.get_lead_by_id(db, lead_id)
        
        update_data = LeadUpdate(mail_sent=True)
        return await LeadService.update_lead(db, lead_id, update_data)
