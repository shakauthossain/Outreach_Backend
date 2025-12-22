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
        self.timeout = float(settings.PAGESPEED_TIMEOUT)  # PageSpeed can be slow, 120s recommended
    
    async def analyze_url(
        self,
        url: str,
        strategy: str = "mobile",
        categories: Optional[list[str]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Analyze a URL using PageSpeed Insights API with retry logic.
        
        Args:
            url: URL to analyze
            strategy: 'mobile' or 'desktop'
            categories: List of categories to analyze (performance, accessibility, seo, best-practices)
            max_retries: Maximum number of retries for 500 errors (default: 3)
            
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
        
        # Retry logic for 500 errors (Lighthouse internal errors)
        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** attempt
                print(f"Retrying PageSpeed API for {url} ({strategy}) after {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(wait_time)
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.BASE_URL, params=param_list)
                    
                    # Check for quota exceeded - don't retry
                    if response.status_code == 429:
                        raise TokenExhaustedError(
                            "PageSpeed API quota exceeded",
                            detail={"url": url, "strategy": strategy}
                        )
                    
                    # Check for 500 errors - retry these
                    if response.status_code == 500:
                        error_detail = response.text[:500]
                        print(f"PageSpeed API Error for {url} ({strategy}): {response.status_code}")
                        print(f"Response: {error_detail}")
                        last_error = ExternalAPIError(
                            f"PageSpeed API error: {response.status_code}",
                            detail={
                                "status_code": response.status_code,
                                "response": error_detail,
                                "url": url,
                                "strategy": strategy,
                            }
                        )
                        # Continue to retry
                        if attempt < max_retries:
                            continue
                        else:
                            raise last_error
                    
                    # Check for other errors - don't retry
                    if response.status_code != 200:
                        error_detail = response.text[:500]
                        print(f"PageSpeed API Error for {url} ({strategy}): {response.status_code}")
                        print(f"Response: {error_detail}")
                        
                        # Parse error message for better user feedback
                        error_message = f"PageSpeed API error: {response.status_code}"
                        try:
                            error_json = response.json()
                            if "error" in error_json and "message" in error_json["error"]:
                                lighthouse_msg = error_json["error"]["message"]
                                # Provide friendly messages for common errors
                                if "FAILED_DOCUMENT_REQUEST" in lighthouse_msg:
                                    error_message = "Website is unreachable or too slow to respond"
                                elif "ERR_TIMED_OUT" in lighthouse_msg:
                                    error_message = "Website took too long to respond (timeout)"
                                elif "ERR_NAME_NOT_RESOLVED" in lighthouse_msg:
                                    error_message = "Website domain not found (DNS error)"
                                elif "ERR_CONNECTION_REFUSED" in lighthouse_msg:
                                    error_message = "Website refused connection"
                                elif "SSL" in lighthouse_msg or "certificate" in lighthouse_msg.lower():
                                    error_message = "SSL certificate error"
                                else:
                                    error_message = lighthouse_msg[:100]  # Use first 100 chars of error
                        except:
                            pass  # Use default error message if parsing fails
                        
                        raise ExternalAPIError(
                            error_message,
                            detail={
                                "status_code": response.status_code,
                                "response": error_detail,
                                "url": url,
                                "strategy": strategy,
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
            except TokenExhaustedError:
                # Don't retry quota errors
                raise
            except ExternalAPIError as e:
                # Only retry if it's a 500 error
                if e.detail and e.detail.get("status_code") != 500:
                    raise
                last_error = e
                if attempt >= max_retries:
                    raise
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise ExternalAPIError("Unexpected error in PageSpeed API call")
    
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
