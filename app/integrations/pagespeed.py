"""Google PageSpeed Insights API client."""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

import httpx

from app.config import settings
from app.core.exceptions import ExternalAPIError, TokenExhaustedError
from app.core.cache import cache_manager, CacheTTL, generate_cache_key


class PageSpeedClient:
    """Client for Google PageSpeed Insights API."""
    
    BASE_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    def __init__(self):
        self.api_key = settings.PAGESPEED_API_KEY
        self.timeout = 60.0  # PageSpeed can be slow
    
    async def analyze_url(
        self,
        url: str,
        strategy: str = "mobile",
        categories: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a URL using PageSpeed Insights API.
        
        Args:
            url: URL to analyze
            strategy: 'mobile' or 'desktop'
            categories: List of categories to analyze (performance, accessibility, seo, best-practices)
            
        Returns:
            PageSpeed analysis results
            
        Raises:
            ExternalAPIError: If API call fails
            TokenExhaustedError: If API quota exceeded
        """
        # Check cache first
        cache_key = generate_cache_key("pagespeed", url, strategy, prefix="speedtest")
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Default categories
        if categories is None:
            categories = ["performance", "accessibility", "seo", "best-practices"]
        
        # Build query parameters - need to pass category multiple times
        params = {
            "url": url,
            "key": self.api_key,
            "strategy": strategy,
        }
        
        # Build params list with multiple category values
        # httpx doesn't support duplicate keys in dict, so build manually
        param_list = [
            ("url", url),
            ("key", self.api_key),
            ("strategy", strategy),
        ]
        
        # Add each category as separate parameter
        for category in categories:
            param_list.append(("category", category))
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=param_list)
                
                # Check for quota exceeded
                if response.status_code == 429:
                    raise TokenExhaustedError(
                        "PageSpeed API quota exceeded",
                        detail={"url": url, "strategy": strategy}
                    )
                
                # Check for other errors
                if response.status_code != 200:
                    error_detail = response.text[:500]
                    print(f"PageSpeed API Error for {url}: {response.status_code}")
                    print(f"Response: {error_detail}")
                    raise ExternalAPIError(
                        f"PageSpeed API error: {response.status_code}",
                        detail={
                            "status_code": response.status_code,
                            "response": error_detail,
                            "url": url
                        }
                    )
                
                data = response.json()
                
                # Extract relevant data
                result = self._extract_results(data, strategy)
                
                # Cache for 24 hours
                await cache_manager.set(cache_key, result, CacheTTL.SPEEDTEST)
                
                return result
                
        except httpx.TimeoutException:
            raise ExternalAPIError(
                f"PageSpeed API timeout after {self.timeout}s",
                detail={"url": url}
            )
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"PageSpeed API request error: {str(e)}",
                detail={"url": url}
            )
    
    def _extract_results(self, data: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """
        Extract relevant data from PageSpeed response.
        
        Args:
            data: Raw PageSpeed API response
            strategy: 'mobile' or 'desktop'
            
        Returns:
            Extracted and formatted results
        """
        lighthouse_result = data.get("lighthouseResult", {})
        categories = lighthouse_result.get("categories", {})
        audits = lighthouse_result.get("audits", {})
        
        # Extract scores (0-1 scale, convert to 0-100)
        performance_score = categories.get("performance", {}).get("score", 0) * 100
        seo_score = categories.get("seo", {}).get("score", 0) * 100
        accessibility_score = categories.get("accessibility", {}).get("score", 0) * 100
        best_practices_score = categories.get("best-practices", {}).get("score", 0) * 100
        
        # Extract key metrics
        metrics = audits.get("metrics", {}).get("details", {}).get("items", [{}])[0]
        
        return {
            "url": data.get("id"),
            "strategy": strategy,
            "timestamp": datetime.utcnow().isoformat(),
            "scores": {
                "performance": round(performance_score, 1),
                "seo": round(seo_score, 1),
                "accessibility": round(accessibility_score, 1),
                "best_practices": round(best_practices_score, 1),
            },
            "metrics": {
                "first_contentful_paint": metrics.get("firstContentfulPaint", 0),
                "largest_contentful_paint": metrics.get("largestContentfulPaint", 0),
                "total_blocking_time": metrics.get("totalBlockingTime", 0),
                "cumulative_layout_shift": metrics.get("cumulativeLayoutShift", 0),
                "speed_index": metrics.get("speedIndex", 0),
            },
            "raw_data": data,  # Store full response for detailed analysis
        }
    
    async def analyze_both_strategies(self, url: str) -> Dict[str, Any]:
        """
        Analyze URL for both mobile and desktop.
        
        Args:
            url: URL to analyze
            
        Returns:
            Combined results for both strategies
        """
        # Run both analyses in parallel
        mobile_task = self.analyze_url(url, strategy="mobile")
        desktop_task = self.analyze_url(url, strategy="desktop")
        
        mobile_result, desktop_result = await asyncio.gather(
            mobile_task,
            desktop_task,
            return_exceptions=True
        )
        
        # Handle errors
        if isinstance(mobile_result, Exception):
            mobile_result = {"error": str(mobile_result)}
        if isinstance(desktop_result, Exception):
            desktop_result = {"error": str(desktop_result)}
        
        return {
            "mobile": mobile_result,
            "desktop": desktop_result,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    async def get_opportunities(self, url: str, strategy: str = "mobile") -> list[Dict[str, Any]]:
        """
        Get optimization opportunities from PageSpeed analysis.
        
        Args:
            url: URL to analyze
            strategy: 'mobile' or 'desktop'
            
        Returns:
            List of optimization opportunities
        """
        result = await self.analyze_url(url, strategy)
        raw_data = result.get("raw_data", {})
        lighthouse_result = raw_data.get("lighthouseResult", {})
        audits = lighthouse_result.get("audits", {})
        
        opportunities = []
        
        # Extract failed audits with recommendations
        for audit_id, audit_data in audits.items():
            if audit_data.get("score", 1) < 0.9:  # Failed or needs improvement
                opportunities.append({
                    "id": audit_id,
                    "title": audit_data.get("title", ""),
                    "description": audit_data.get("description", ""),
                    "score": audit_data.get("score", 0),
                    "display_value": audit_data.get("displayValue", ""),
                    "details": audit_data.get("details", {}),
                })
        
        # Sort by impact (lower score = higher priority)
        opportunities.sort(key=lambda x: x["score"])
        
        return opportunities


# Global client instance
pagespeed_client = PageSpeedClient()
