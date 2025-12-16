"""Firecrawl web scraping API client."""

from typing import Optional, Dict, Any, List

import httpx

from app.config import settings
from app.core.exceptions import ExternalAPIError
from app.core.cache import cache_manager, CacheTTL, generate_cache_key


class FirecrawlClient:
    """Client for Firecrawl web scraping API."""
    
    BASE_URL = "https://api.firecrawl.dev/v0"
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.timeout = 60.0  # Scraping can take time
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        wait_for: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        Args:
            url: URL to scrape
            formats: Output formats (markdown, html, rawHtml, links, screenshot)
            include_tags: HTML tags to include
            exclude_tags: HTML tags to exclude
            wait_for: Milliseconds to wait before scraping
            
        Returns:
            Scraped content
            
        Raises:
            ExternalAPIError: If API call fails
        """
        # Check cache
        cache_key = generate_cache_key("firecrawl", url, prefix="scrape")
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        payload = {
            "url": url,
        }
        
        if formats:
            payload["formats"] = formats
        else:
            payload["formats"] = ["markdown", "html"]
        
        if include_tags:
            payload["includeTags"] = include_tags
        if exclude_tags:
            payload["excludeTags"] = exclude_tags
        if wait_for:
            payload["waitFor"] = wait_for
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/scrape",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"Firecrawl API error: {response.status_code}",
                        detail={"response": response.text[:500]}
                    )
                
                data = response.json()
                
                # Cache for 6 hours
                await cache_manager.set(cache_key, data, CacheTTL.SCREENSHOT)
                
                return data
                
        except httpx.TimeoutException:
            raise ExternalAPIError(
                f"Firecrawl API timeout after {self.timeout}s",
                detail={"url": url}
            )
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"Firecrawl API request error: {str(e)}",
                detail={"url": url}
            )
    
    async def crawl_website(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 100,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl an entire website.
        
        Args:
            url: Starting URL
            max_depth: Maximum crawl depth
            limit: Maximum number of pages
            include_paths: URL patterns to include
            exclude_paths: URL patterns to exclude
            
        Returns:
            Crawl job information
        """
        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": limit,
        }
        
        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/crawl",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code not in [200, 201]:
                    raise ExternalAPIError(
                        f"Firecrawl API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"Firecrawl API request error: {str(e)}"
            )
    
    async def get_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl job.
        
        Args:
            job_id: Crawl job ID
            
        Returns:
            Job status and results
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/crawl/status/{job_id}",
                    headers=self._get_headers(),
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"Firecrawl API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"Firecrawl API request error: {str(e)}"
            )
    
    async def extract_content(
        self,
        url: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured data from a URL using a schema.
        
        Args:
            url: URL to extract from
            schema: JSON schema for extraction
            
        Returns:
            Extracted structured data
        """
        payload = {
            "url": url,
        }
        
        if schema:
            payload["schema"] = schema
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/extract",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"Firecrawl API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"Firecrawl API request error: {str(e)}"
            )


# Global client instance
firecrawl_client = FirecrawlClient()
