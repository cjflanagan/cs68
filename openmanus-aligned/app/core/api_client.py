"""
API Client for Manus-aligned agent.

This module provides a pre-configured API client for accessing authoritative
data sources. The agent generates Python code that uses this client to call
APIs documented in the Datasource module.

Key features:
- Automatic authentication based on datasource configuration
- Retry logic with exponential backoff
- Response caching
- Rate limit handling
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import json


class ApiResponse(BaseModel):
    """Represents an API response."""

    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    data: Any = None
    error: Optional[str] = None
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def ok(self) -> bool:
        """Check if the response was successful."""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """Return the response data as JSON."""
        return self.data


class CacheEntry(BaseModel):
    """Represents a cached API response."""

    response: ApiResponse
    expires_at: datetime
    key: str


class ApiClient(BaseModel):
    """Pre-configured API client for datasource access.

    Handles authentication, retries, and caching for API calls.
    The agent uses this client via generated Python code.
    """

    datasource_id: str
    base_url: str = ""
    auth_method: str = "none"
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds

    # Cache configuration
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes default
    _cache: Dict[str, CacheEntry] = {}

    class Config:
        arbitrary_types_allowed = True

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on configuration."""
        headers = {}

        if self.auth_method == "none":
            return headers

        if self.auth_method == "api_key":
            env_var = self.auth_config.get("env_var", f"{self.datasource_id.upper()}_API_KEY")
            header_name = self.auth_config.get("header", "X-API-Key")
            api_key = os.environ.get(env_var, "")
            if api_key:
                headers[header_name] = api_key

        elif self.auth_method == "bearer_token":
            env_var = self.auth_config.get("env_var", f"{self.datasource_id.upper()}_TOKEN")
            token = os.environ.get(env_var, "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_method == "basic_auth":
            username_var = self.auth_config.get("username_env", f"{self.datasource_id.upper()}_USERNAME")
            password_var = self.auth_config.get("password_env", f"{self.datasource_id.upper()}_PASSWORD")
            username = os.environ.get(username_var, "")
            password = os.environ.get(password_var, "")
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        return headers

    def _get_cache_key(self, method: str, path: str, params: Dict[str, Any] = None) -> str:
        """Generate a cache key for a request."""
        key_parts = [self.datasource_id, method, path]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        return ":".join(key_parts)

    def _get_from_cache(self, key: str) -> Optional[ApiResponse]:
        """Get a response from cache if valid."""
        if not self.cache_enabled:
            return None

        entry = self._cache.get(key)
        if entry and entry.expires_at > datetime.utcnow():
            response = entry.response
            response.cached = True
            return response

        # Remove expired entry
        if entry:
            del self._cache[key]

        return None

    def _add_to_cache(self, key: str, response: ApiResponse) -> None:
        """Add a response to cache."""
        if not self.cache_enabled or not response.ok:
            return

        expires_at = datetime.utcnow() + timedelta(seconds=self.cache_ttl)
        self._cache[key] = CacheEntry(
            response=response,
            expires_at=expires_at,
            key=key,
        )

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make an HTTP request with retry logic.

        Note: This is a placeholder implementation. In production,
        this would use httpx or aiohttp for actual HTTP requests.
        """
        url = f"{self.base_url}{path}"
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)

        # Check cache for GET requests
        if method.upper() == "GET":
            cache_key = self._get_cache_key(method, path, params)
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        # Placeholder for actual HTTP implementation
        # In production, this would use httpx:
        #
        # async with httpx.AsyncClient() as client:
        #     response = await client.request(
        #         method=method,
        #         url=url,
        #         params=params,
        #         json=json_data,
        #         headers=request_headers,
        #         timeout=self.timeout,
        #     )

        # For now, return a mock response
        response = ApiResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data={"message": f"Mock response for {method} {path}"},
        )

        # Cache successful GET responses
        if method.upper() == "GET" and response.ok:
            cache_key = self._get_cache_key(method, path, params)
            self._add_to_cache(cache_key, response)

        return response

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a request with exponential backoff retry."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    method=method,
                    path=path,
                    params=params,
                    json_data=json_data,
                    headers=headers,
                )

                # Don't retry on client errors (4xx)
                if response.status_code < 500:
                    return response

                # Retry on server errors (5xx)
                last_error = f"Server error: {response.status_code}"

            except Exception as e:
                last_error = str(e)

            # Exponential backoff
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        return ApiResponse(
            status_code=500,
            error=f"Request failed after {self.max_retries} retries: {last_error}",
        )

    async def get(
        self,
        path: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a GET request."""
        return await self._request_with_retry(
            method="GET",
            path=path,
            params=params,
            headers=headers,
        )

    async def post(
        self,
        path: str,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a POST request."""
        return await self._request_with_retry(
            method="POST",
            path=path,
            json_data=json,
            headers=headers,
        )

    async def put(
        self,
        path: str,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a PUT request."""
        return await self._request_with_retry(
            method="PUT",
            path=path,
            json_data=json,
            headers=headers,
        )

    async def delete(
        self,
        path: str,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a DELETE request."""
        return await self._request_with_retry(
            method="DELETE",
            path=path,
            headers=headers,
        )

    async def patch(
        self,
        path: str,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> ApiResponse:
        """Make a PATCH request."""
        return await self._request_with_retry(
            method="PATCH",
            path=path,
            json_data=json,
            headers=headers,
        )

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()


class ApiClientFactory:
    """Factory for creating pre-configured API clients."""

    _instances: Dict[str, ApiClient] = {}

    @classmethod
    def get_client(
        cls,
        datasource_id: str,
        base_url: str = "",
        auth_method: str = "none",
        auth_config: Dict[str, Any] = None,
    ) -> ApiClient:
        """Get or create an API client for a datasource."""
        if datasource_id not in cls._instances:
            cls._instances[datasource_id] = ApiClient(
                datasource_id=datasource_id,
                base_url=base_url,
                auth_method=auth_method,
                auth_config=auth_config or {},
            )
        return cls._instances[datasource_id]

    @classmethod
    def clear_all(cls) -> None:
        """Clear all client instances."""
        cls._instances.clear()
