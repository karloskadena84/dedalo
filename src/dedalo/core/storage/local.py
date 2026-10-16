"""Almacenamiento local de Dédalo (JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from dedalo.core.conversation.state import AgentSpec, ConversationState, PipelineSpec
from dedalo.utils.config import settings


class LocalStorage:
    def __init__(self):
        settings.ensure_data_dir()
        self.base = settings.data_dir
        self.conversation_file = self.base / "conversations" / "current.json"
        self.agents_file = self.base / "pipelines" / "agents.json"
        self.pipelines_file = self.base / "pipelines" / "pipelines.json"

    def _read(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def save_conversation(self, state: ConversationState) -> None:
        self._write(self.conversation_file, state.model_dump())

    def load_conversation(self) -> Optional[ConversationState]:
        data = self._read(self.conversation_file)
        if data is None:
            return None
        return ConversationState.model_validate(data)

    def save_agents(self, agents: list[AgentSpec]) -> None:
        self._write(
            self.agents_file,
            {"agents": [a.model_dump() for a in agents]},
        )

    def load_agents(self) -> list[AgentSpec]:
        data = self._read(self.agents_file)
        if data is None:
            return []
        return [AgentSpec.model_validate(a) for a in data.get("agents", [])]

    def save_pipelines(self, pipelines: list[PipelineSpec]) -> None:
        self._write(
            self.pipelines_file,
            {"pipelines": [p.model_dump() for p in pipelines]},
        )

    def load_pipelines(self) -> list[PipelineSpec]:
        data = self._read(self.pipelines_file)
        if data is None:
            return []
        return [PipelineSpec.model_validate(p) for p in data.get("pipelines", [])]
