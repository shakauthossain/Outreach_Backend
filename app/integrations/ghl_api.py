"""GoHighLevel CRM API client."""

from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from app.config import settings
from app.core.exceptions import ExternalAPIError, AuthenticationError
from app.core.cache import cache_manager, CacheTTL, generate_cache_key


class GoHighLevelClient:
    """Client for GoHighLevel CRM API."""
    
    BASE_URL = "https://rest.gohighlevel.com/v1"
    
    def __init__(self):
        self.api_key = settings.GHL_API_KEY
        self.location_id = settings.GHL_LOCATION_ID
        self.timeout = 30.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    async def get_contacts(
        self,
        limit: int = 100,
        skip: int = 0,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get contacts from GoHighLevel.
        
        Args:
            limit: Number of contacts to retrieve
            skip: Number of contacts to skip (pagination)
            query: Search query
            
        Returns:
            Contacts data
            
        Raises:
            ExternalAPIError: If API call fails
        """
        params = {
            "locationId": self.location_id,
            "limit": limit,
            "skip": skip,
        }
        
        if query:
            params["query"] = query
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/contacts",
                    headers=self._get_headers(),
                    params=params,
                )
                
                if response.status_code == 401:
                    raise AuthenticationError("GoHighLevel API authentication failed")
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}",
                        detail={"response": response.text[:500]}
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )
    
    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Get a single contact by ID.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Contact data
        """
        # Check cache
        cache_key = generate_cache_key("ghl_contact", contact_id, prefix="ghl:contact")
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/contacts/{contact_id}",
                    headers=self._get_headers(),
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}"
                    )
                
                data = response.json()
                
                # Cache for 5 minutes
                await cache_manager.set(cache_key, data, CacheTTL.LIST)
                
                return data
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )
    
    async def create_contact(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        company_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new contact in GoHighLevel.
        
        Args:
            email: Contact email
            first_name: First name
            last_name: Last name
            phone: Phone number
            website: Website URL
            company_name: Company name
            tags: List of tags
            custom_fields: Custom field values
            
        Returns:
            Created contact data
        """
        payload = {
            "locationId": self.location_id,
            "email": email,
        }
        
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if phone:
            payload["phone"] = phone
        if website:
            payload["website"] = website
        if company_name:
            payload["companyName"] = company_name
        if tags:
            payload["tags"] = tags
        if custom_fields:
            payload["customFields"] = custom_fields
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/contacts",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code not in [200, 201]:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}",
                        detail={"response": response.text[:500]}
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )
    
    async def update_contact(
        self,
        contact_id: str,
        **fields,
    ) -> Dict[str, Any]:
        """
        Update a contact in GoHighLevel.
        
        Args:
            contact_id: Contact ID
            **fields: Fields to update
            
        Returns:
            Updated contact data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.BASE_URL}/contacts/{contact_id}",
                    headers=self._get_headers(),
                    json=fields,
                )
                
                if response.status_code != 200:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}"
                    )
                
                # Invalidate cache
                cache_key = generate_cache_key("ghl_contact", contact_id, prefix="ghl:contact")
                await cache_manager.delete(cache_key)
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )
    
    async def add_note(
        self,
        contact_id: str,
        body: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a note to a contact.
        
        Args:
            contact_id: Contact ID
            body: Note content
            user_id: User ID creating the note
            
        Returns:
            Created note data
        """
        payload = {
            "contactId": contact_id,
            "body": body,
        }
        
        if user_id:
            payload["userId"] = user_id
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/contacts/{contact_id}/notes",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code not in [200, 201]:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )
    
    async def send_message(
        self,
        contact_id: str,
        message: str,
        message_type: str = "Email",
    ) -> Dict[str, Any]:
        """
        Send a message to a contact.
        
        Args:
            contact_id: Contact ID
            message: Message content
            message_type: Type of message (Email, SMS)
            
        Returns:
            Message send result
        """
        payload = {
            "contactId": contact_id,
            "type": message_type,
            "message": message,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/conversations/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code not in [200, 201]:
                    raise ExternalAPIError(
                        f"GoHighLevel API error: {response.status_code}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalAPIError(
                f"GoHighLevel API request error: {str(e)}"
            )


# Global client instance
ghl_client = GoHighLevelClient()
