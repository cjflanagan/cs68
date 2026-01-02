"""
Datasource Module for Manus-aligned agent.

This module provides documentation for authoritative data APIs, which are
prioritized over general web search. Unlike OpenManus which relies on generic
web search and browser automation, this module provides:
- Pre-configured API endpoints with documentation
- Authentication methods and API clients
- Example usage patterns
- Priority-based selection of data sources

The agent calls these APIs via generated Python code using a pre-configured
ApiClient, enabling direct programmatic access to authoritative data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
import json


class AuthMethod(str, Enum):
    """API authentication methods."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class HttpMethod(str, Enum):
    """HTTP methods for API calls."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ApiEndpoint(BaseModel):
    """Represents a single API endpoint."""

    path: str
    method: HttpMethod = HttpMethod.GET
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    request_body_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    example_request: str = ""
    example_response: str = ""
    rate_limit: Optional[str] = None

    def to_documentation(self) -> str:
        """Generate documentation string for this endpoint."""
        lines = [
            f"  {self.method.value} {self.path}",
            f"    Description: {self.description}",
        ]
        if self.parameters:
            lines.append("    Parameters:")
            for name, spec in self.parameters.items():
                required = spec.get("required", False)
                param_type = spec.get("type", "string")
                desc = spec.get("description", "")
                req_marker = " (required)" if required else ""
                lines.append(f"      - {name}: {param_type}{req_marker} - {desc}")
        if self.example_request:
            lines.append(f"    Example: {self.example_request}")
        if self.rate_limit:
            lines.append(f"    Rate Limit: {self.rate_limit}")
        return "\n".join(lines)


class Datasource(BaseModel):
    """Represents an authoritative data source (API).

    Datasources are prioritized over general web search and provide
    structured access to authoritative data through documented APIs.
    """

    id: str
    name: str
    description: str
    base_url: str
    auth_method: AuthMethod = AuthMethod.NONE
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    endpoints: List[ApiEndpoint] = Field(default_factory=list)
    documentation_url: Optional[str] = None
    priority: int = 5  # 1-10, higher is more authoritative
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    usage_count: int = 0
    last_used: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

    def generate_python_code(self, endpoint_path: str, params: Dict[str, Any] = None) -> str:
        """Generate Python code to call this API endpoint.

        The code uses a pre-configured ApiClient that handles authentication.
        """
        endpoint = self._find_endpoint(endpoint_path)
        if not endpoint:
            return f"# Error: Endpoint '{endpoint_path}' not found"

        method = endpoint.method.value.lower()
        url = f"{self.base_url}{endpoint.path}"

        # Build the code
        lines = [
            "from app.core.api_client import ApiClient",
            "",
            f"# Call {self.name} API: {endpoint.description}",
            f"client = ApiClient('{self.id}')",
        ]

        # Format parameters
        if params:
            params_str = json.dumps(params, indent=4)
            lines.append(f"params = {params_str}")
            if method == "get":
                lines.append(f"response = await client.{method}('{endpoint.path}', params=params)")
            else:
                lines.append(f"response = await client.{method}('{endpoint.path}', json=params)")
        else:
            lines.append(f"response = await client.{method}('{endpoint.path}')")

        lines.extend([
            "",
            "# Process response",
            "if response.ok:",
            "    data = response.json()",
            "else:",
            "    print(f'Error: {response.status_code}')",
        ])

        return "\n".join(lines)

    def _find_endpoint(self, path: str) -> Optional[ApiEndpoint]:
        """Find an endpoint by path."""
        for endpoint in self.endpoints:
            if endpoint.path == path:
                return endpoint
        return None

    def to_documentation(self) -> str:
        """Generate full documentation for this datasource."""
        lines = [
            f"[DATASOURCE] {self.name}",
            f"Base URL: {self.base_url}",
            f"Description: {self.description}",
            f"Authentication: {self.auth_method.value}",
            "",
            "Endpoints:",
        ]
        for endpoint in self.endpoints:
            lines.append(endpoint.to_documentation())
            lines.append("")

        if self.documentation_url:
            lines.append(f"Full documentation: {self.documentation_url}")

        return "\n".join(lines)

    def matches_query(self, query: str) -> bool:
        """Check if this datasource is relevant for a query."""
        query_lower = query.lower()
        # Check name, description, and tags
        if self.name.lower() in query_lower or query_lower in self.name.lower():
            return True
        if any(tag.lower() in query_lower for tag in self.tags):
            return True
        # Check endpoint descriptions
        for endpoint in self.endpoints:
            if query_lower in endpoint.description.lower():
                return True
        return False

    def mark_used(self) -> None:
        """Mark this datasource as used."""
        self.usage_count += 1
        self.last_used = datetime.utcnow()


class DatasourceModule(BaseModel):
    """Datasource module that provides access to authoritative APIs.

    This module maintains a registry of data sources that are prioritized
    over general web search. When the agent needs data, it should first
    check available datasources before falling back to web search.

    Key features:
    - Priority-based source selection
    - Automatic API code generation
    - Pre-configured authentication
    - Relevance matching for queries
    """

    sources: Dict[str, Datasource] = Field(default_factory=dict)
    default_timeout: int = 30
    max_retries: int = 3

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        if not self.sources:
            self._load_default_sources()

    def _load_default_sources(self) -> None:
        """Load default datasource configurations."""
        defaults = [
            # Weather API
            Datasource(
                id="openweathermap",
                name="OpenWeatherMap",
                description="Current weather and forecasts for any location",
                base_url="https://api.openweathermap.org/data/2.5",
                auth_method=AuthMethod.API_KEY,
                auth_config={"header": "appid", "env_var": "OPENWEATHER_API_KEY"},
                priority=8,
                tags=["weather", "forecast", "temperature", "climate"],
                endpoints=[
                    ApiEndpoint(
                        path="/weather",
                        method=HttpMethod.GET,
                        description="Get current weather for a city",
                        parameters={
                            "q": {"type": "string", "required": True, "description": "City name"},
                            "units": {"type": "string", "description": "Units: metric, imperial, kelvin"},
                        },
                        example_request="/weather?q=London&units=metric",
                    ),
                    ApiEndpoint(
                        path="/forecast",
                        method=HttpMethod.GET,
                        description="Get 5-day weather forecast",
                        parameters={
                            "q": {"type": "string", "required": True, "description": "City name"},
                            "units": {"type": "string", "description": "Units: metric, imperial, kelvin"},
                        },
                    ),
                ],
            ),

            # GitHub API
            Datasource(
                id="github",
                name="GitHub API",
                description="Access GitHub repositories, issues, and user data",
                base_url="https://api.github.com",
                auth_method=AuthMethod.BEARER_TOKEN,
                auth_config={"env_var": "GITHUB_TOKEN"},
                priority=9,
                tags=["github", "repository", "code", "issues", "pull requests"],
                endpoints=[
                    ApiEndpoint(
                        path="/repos/{owner}/{repo}",
                        method=HttpMethod.GET,
                        description="Get repository information",
                        parameters={
                            "owner": {"type": "string", "required": True, "description": "Repository owner"},
                            "repo": {"type": "string", "required": True, "description": "Repository name"},
                        },
                    ),
                    ApiEndpoint(
                        path="/repos/{owner}/{repo}/issues",
                        method=HttpMethod.GET,
                        description="List repository issues",
                        parameters={
                            "state": {"type": "string", "description": "Filter by state: open, closed, all"},
                        },
                    ),
                    ApiEndpoint(
                        path="/search/repositories",
                        method=HttpMethod.GET,
                        description="Search repositories",
                        parameters={
                            "q": {"type": "string", "required": True, "description": "Search query"},
                        },
                    ),
                ],
            ),

            # Wikipedia API
            Datasource(
                id="wikipedia",
                name="Wikipedia API",
                description="Access Wikipedia articles and search",
                base_url="https://en.wikipedia.org/api/rest_v1",
                auth_method=AuthMethod.NONE,
                priority=7,
                tags=["wikipedia", "encyclopedia", "knowledge", "articles"],
                endpoints=[
                    ApiEndpoint(
                        path="/page/summary/{title}",
                        method=HttpMethod.GET,
                        description="Get article summary",
                        parameters={
                            "title": {"type": "string", "required": True, "description": "Article title"},
                        },
                    ),
                    ApiEndpoint(
                        path="/page/related/{title}",
                        method=HttpMethod.GET,
                        description="Get related articles",
                    ),
                ],
            ),

            # REST Countries API
            Datasource(
                id="restcountries",
                name="REST Countries",
                description="Information about countries",
                base_url="https://restcountries.com/v3.1",
                auth_method=AuthMethod.NONE,
                priority=7,
                tags=["countries", "geography", "population", "capital"],
                endpoints=[
                    ApiEndpoint(
                        path="/name/{name}",
                        method=HttpMethod.GET,
                        description="Search countries by name",
                    ),
                    ApiEndpoint(
                        path="/all",
                        method=HttpMethod.GET,
                        description="Get all countries",
                    ),
                ],
            ),

            # JSONPlaceholder (for testing)
            Datasource(
                id="jsonplaceholder",
                name="JSONPlaceholder",
                description="Free fake API for testing and prototyping",
                base_url="https://jsonplaceholder.typicode.com",
                auth_method=AuthMethod.NONE,
                priority=3,
                tags=["test", "fake", "placeholder", "demo"],
                endpoints=[
                    ApiEndpoint(
                        path="/posts",
                        method=HttpMethod.GET,
                        description="Get all posts",
                    ),
                    ApiEndpoint(
                        path="/posts/{id}",
                        method=HttpMethod.GET,
                        description="Get a specific post",
                    ),
                    ApiEndpoint(
                        path="/users",
                        method=HttpMethod.GET,
                        description="Get all users",
                    ),
                ],
            ),
        ]

        for source in defaults:
            self.sources[source.id] = source

    def register(self, source: Datasource) -> None:
        """Register a new datasource."""
        self.sources[source.id] = source

    def unregister(self, source_id: str) -> bool:
        """Unregister a datasource."""
        if source_id in self.sources:
            del self.sources[source_id]
            return True
        return False

    def get(self, source_id: str) -> Optional[Datasource]:
        """Get a datasource by ID."""
        return self.sources.get(source_id)

    def find_relevant(self, query: str, limit: int = 3) -> List[Datasource]:
        """Find datasources relevant to a query.

        Returns sources sorted by priority that match the query.
        These should be preferred over web search.
        """
        relevant = []
        for source in self.sources.values():
            if source.enabled and source.matches_query(query):
                relevant.append(source)

        relevant.sort(key=lambda s: s.priority, reverse=True)
        return relevant[:limit]

    def get_datasource_events(self, context: str) -> List[Dict[str, Any]]:
        """Get datasource events to inject into the event stream.

        Called to provide the agent with available authoritative sources
        for the current context.
        """
        relevant = self.find_relevant(context)
        events = []

        for source in relevant:
            source.mark_used()
            events.append({
                "type": "datasource",
                "source_id": source.id,
                "name": source.name,
                "description": source.description,
                "endpoint": source.base_url,
                "auth_method": source.auth_method.value,
                "documentation": source.to_documentation(),
                "priority": source.priority,
            })

        return events

    def get_context_string(self, query: str) -> str:
        """Get datasources as a formatted context string.

        Injects relevant API documentation into the agent's context,
        providing direct access to authoritative data sources.
        """
        relevant = self.find_relevant(query)

        if not relevant:
            return ""

        parts = [
            "[AUTHORITATIVE DATA SOURCES - Prefer these over web search:]",
            "",
        ]

        for source in relevant:
            source.mark_used()
            parts.append(source.to_documentation())
            parts.append("-" * 40)
            parts.append("")

        return "\n".join(parts)

    def suggest_api_call(self, query: str) -> Optional[str]:
        """Suggest Python code to call a relevant API.

        Returns generated Python code if a matching datasource/endpoint is found.
        """
        relevant = self.find_relevant(query, limit=1)
        if not relevant:
            return None

        source = relevant[0]
        # Find most relevant endpoint
        if source.endpoints:
            # For now, suggest the first endpoint
            endpoint = source.endpoints[0]
            return source.generate_python_code(endpoint.path)

        return None


class ApiClient(BaseModel):
    """Pre-configured API client for datasource access.

    Handles authentication and common patterns for API access.
    The agent uses this client via generated Python code.
    """

    datasource_id: str
    timeout: int = 30
    max_retries: int = 3

    class Config:
        arbitrary_types_allowed = True

    async def get(self, path: str, params: Dict[str, Any] = None) -> Any:
        """Make a GET request to the API."""
        # Implementation would use httpx or aiohttp
        # This is a placeholder for the interface
        pass

    async def post(self, path: str, json: Dict[str, Any] = None) -> Any:
        """Make a POST request to the API."""
        pass

    async def put(self, path: str, json: Dict[str, Any] = None) -> Any:
        """Make a PUT request to the API."""
        pass

    async def delete(self, path: str) -> Any:
        """Make a DELETE request to the API."""
        pass
