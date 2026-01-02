"""
Core module for Manus-aligned architecture.

This module provides the foundational components that align with the actual Manus
implementation, including:
- Event-driven architecture with 7 distinct event types
- Specialized system modules (Planner, Knowledge, Datasource)
- Context engineering optimizations
"""

from app.core.events import (
    Event,
    EventType,
    MessageEvent,
    ActionEvent,
    ObservationEvent,
    PlanEvent,
    KnowledgeEvent,
    DatasourceEvent,
    SystemEvent,
    EventStream,
)
from app.core.planner import Planner, PlanStep, Plan
from app.core.knowledge import KnowledgeModule, KnowledgeItem
from app.core.datasource import DatasourceModule, Datasource
from app.core.context import ContextEngine
from app.core.api_client import ApiClient, ApiClientFactory, ApiResponse

__all__ = [
    # Events
    "Event",
    "EventType",
    "MessageEvent",
    "ActionEvent",
    "ObservationEvent",
    "PlanEvent",
    "KnowledgeEvent",
    "DatasourceEvent",
    "SystemEvent",
    "EventStream",
    # Planner
    "Planner",
    "PlanStep",
    "Plan",
    # Knowledge
    "KnowledgeModule",
    "KnowledgeItem",
    # Datasource
    "DatasourceModule",
    "Datasource",
    # Context
    "ContextEngine",
    # API Client
    "ApiClient",
    "ApiClientFactory",
    "ApiResponse",
]
