"""Estado de la conversación de Dédalo."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationPhase(str, Enum):
    NEED_CONNECTOR = "need_connector"
    CLARIFY_PRIORITIES = "clarify_priorities"
    ASK_NEXT_ACTION = "ask_next_action"
    BUILDING_AGENTS = "building_agents"
    NAMING = "naming"
    READY = "ready"


class AgentSpec(BaseModel):
    """Especificación de un agente creado dinámicamente."""

    id: str
    name: str
    type: str
    description: str
    config: dict[str, Any] = Field(default_factory=dict)
    order: int = 0


class PipelineSpec(BaseModel):
    """Pipeline o combinación con nombre."""

    name: str
    description: str = ""
    agent_ids: list[str] = Field(default_factory=list)
    is_full: bool = False


class ConversationState(BaseModel):
    phase: ConversationPhase = ConversationPhase.NEED_CONNECTOR
    priorities: list[str] = Field(default_factory=list)
    ignore_rules: list[str] = Field(default_factory=list)
    agents: list[AgentSpec] = Field(default_factory=list)
    pipelines: list[PipelineSpec] = Field(default_factory=list)
    current_question: Optional[str] = None
    history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_agent(self, agent: AgentSpec) -> None:
        agent.order = len(self.agents)
        self.agents.append(agent)

    def add_pipeline(self, pipeline: PipelineSpec) -> None:
        # Evitar duplicados por nombre
        self.pipelines = [p for p in self.pipelines if p.name != pipeline.name]
        self.pipelines.append(pipeline)
