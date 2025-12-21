"""Recommendation capture background tasks."""

import asyncio
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.integrations.firecrawl import firecrawl_client
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name="recommendations.capture_single",
    max_retries=2,
)
def capture_single_recommendations(self, lead_id: int):
    """
    Capture recommendations for a single lead.
    
    Args:
        lead_id: Lead ID
        
    Returns:
        Captured recommendations
    """
    self.update_state(
        state="PROGRESS",
        meta={"status": "Capturing recommendations..."}
    )
    
    try:
        return asyncio.run(_capture_recommendations(lead_id))
    except Exception as e:
        raise self.retry(exc=e)


async def _capture_recommendations(lead_id: int) -> Dict[str, Any]:
    """
    Internal async function to capture recommendations.
    
    Args:
        lead_id: Lead ID
        
    Returns:
        Recommendations data
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Scrape website content
        scraped = await firecrawl_client.scrape_url(
            lead.website_url,
            formats=["markdown"],
        )
        
        content = scraped.get("data", {}).get("markdown", "")
        
        # Generate recommendations using AI analysis
        recommendations = await _generate_ai_recommendations(lead, content)
        
        # Update lead
        lead.recommendations = "\n".join(recommendations)
        await db.commit()
        
        return {
            "lead_id": lead_id,
            "website_url": lead.website_url,
            "recommendations": recommendations,
            "count": len(recommendations),
            "status": "completed",
        }


def _generate_recommendations(lead: Lead, content: str) -> list[str]:
    """
    Generate recommendations based on lead data and website content.
    
    Args:
        lead: Lead model
        content: Website content
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Performance recommendations
    if lead.website_speed_web and lead.website_speed_web < 50:
        recommendations.append(
            "🚀 Critical: Desktop performance is very poor (score < 50). "
            "Consider optimizing images, minimizing JavaScript, and enabling caching."
        )
    elif lead.website_speed_web and lead.website_speed_web < 75:
        recommendations.append(
            "⚡ Important: Desktop performance needs improvement. "
            "Optimize large images and reduce render-blocking resources."
        )
    
    if lead.website_speed_mobile and lead.website_speed_mobile < 50:
        recommendations.append(
            "📱 Critical: Mobile performance is very poor (score < 50). "
            "Mobile users are likely experiencing slow load times."
        )
    elif lead.website_speed_mobile and lead.website_speed_mobile < 75:
        recommendations.append(
            "📱 Important: Mobile performance could be better. "
            "Ensure images are properly sized for mobile devices."
        )
    
    # SEO recommendations
    if lead.seo_score and lead.seo_score < 75:
        recommendations.append(
            "🔍 SEO: Improve meta descriptions, title tags, and ensure proper heading hierarchy."
        )
    
    # Accessibility recommendations
    if lead.accessibility_score and lead.accessibility_score < 75:
        recommendations.append(
            "♿ Accessibility: Add alt text to images, improve color contrast, and ensure keyboard navigation."
        )
    
    # Content-based recommendations
    if content:
        content_lower = content.lower()
        
        if "image" in content_lower and len(content) > 10000:
            recommendations.append(
                "🖼️ Images: Consider lazy loading images and using modern formats like WebP."
            )
        
        if "video" in content_lower:
            recommendations.append(
                "🎥 Video: Ensure videos are properly optimized and consider using a CDN."
            )
    
    # Default recommendation if none generated
    if not recommendations:
        recommendations.append(
            "✅ Your website is performing well! Consider implementing monitoring to maintain these scores."
        )
    
    return recommendations


async def _generate_ai_recommendations(lead: Lead, content: str) -> list[str]:
    """
    Generate AI-powered recommendations based on lead data and website content.
    
    Args:
        lead: Lead model
        content: Website content
        
    Returns:
        List of AI-generated recommendations
    """
    from app.services.llm_provider import get_llm_client
    
    # Build context for AI
    context = f"""Website Performance Analysis:
- Company: {lead.company}
- URL: {lead.website_url}
- Desktop Performance: {lead.website_speed_web or 'Not tested'}/100
- Mobile Performance: {lead.website_speed_mobile or 'Not tested'}/100
- SEO Score: {lead.seo_score or 'Not tested'}/100
- Accessibility Score: {lead.accessibility_score or 'Not tested'}/100
- Best Practices Score: {lead.best_practices_score or 'Not tested'}/100

Website Content Preview:
{content[:1000] if content else 'No content available'}
"""
    
    prompt = f"""{context}

Based on this website analysis, generate 3-5 specific, actionable recommendations to improve their web performance and user experience.

Format each recommendation as:
[Icon] [Priority]: [Specific action with technical details]

Use these icons:
🚀 for critical performance issues
⚡ for important optimizations
🔍 for SEO improvements
♿ for accessibility fixes
🖼️ for image/media optimizations
🎯 for best practice recommendations

Make recommendations specific, technical, and actionable. Focus on the biggest impact areas based on the scores.

Recommendations:"""
    
    try:
        llm = get_llm_client(temperature=0.5)
        response = llm.invoke(prompt)
        
        # Extract content
        if hasattr(response, 'content'):
            recommendations_text = response.content.strip()
        else:
            recommendations_text = str(response).strip()
        
        # Split into individual recommendations
        recommendations = [line.strip() for line in recommendations_text.split('\n') if line.strip() and not line.strip().startswith('Recommendations:')]
        
        # If AI didn't generate good recommendations, fall back to rule-based
        if len(recommendations) < 3:
            return _generate_recommendations(lead, content)
        
        return recommendations[:5]  # Limit to 5 recommendations
        
    except Exception as e:
        print(f"AI recommendation generation failed: {e}, using rule-based")
        return _generate_recommendations(lead, content)


@celery_app.task(
    bind=True,
    name="recommendations.capture_bulk",
)
def capture_bulk_recommendations(self, lead_ids: list[int]):
    """
    Capture recommendations for multiple leads.
    
    Args:
        lead_ids: List of lead IDs
        
    Returns:
        Batch results
    """
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(lead_ids),
            "status": "Starting bulk capture...",
        }
    )
    
    results = {
        "successful": [],
        "failed": [],
        "total": len(lead_ids),
    }
    
    for i, lead_id in enumerate(lead_ids):
        try:
            task_result = capture_single_recommendations.apply_async(
                args=[lead_id],
                countdown=i * 3,  # Stagger by 3 seconds
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
