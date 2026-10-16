"""Ejecutor de pipelines de Dédalo con lógica real de agentes."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dedalo.core.agents.runners import run_agent
from dedalo.core.conversation.state import AgentSpec
from dedalo.core.storage.local import LocalStorage
from dedalo.connectors.email.manager import EmailConnectorManager
from dedalo.utils.config import settings

console = Console()


class PipelineExecutor:
    """Ejecuta un pipeline o combinación por nombre."""

    def __init__(self):
        self.storage = LocalStorage()
        self.email_manager = EmailConnectorManager()

    def run(self, name: str) -> None:
        pipelines = self.storage.load_pipelines()
        agents = self.storage.load_agents()

        pipeline = next((p for p in pipelines if p.name == name), None)
        if pipeline is None:
            console.print(f"[red]No existe ningún pipeline llamado '{name}'[/red]")
            console.print("Usa [cyan]dedalo list[/cyan] para ver los disponibles.")
            return

        selected_agents = [a for a in agents if a.id in pipeline.agent_ids]
        selected_agents.sort(key=lambda a: a.order)

        if not selected_agents:
            console.print("[yellow]El pipeline no tiene agentes asociados.[/yellow]")
            return

        console.print(
            Panel.fit(
                f"[bold]Ejecutando:[/bold] {pipeline.name}\n"
                f"Agentes: {', '.join(a.name for a in selected_agents)}",
                border_style="cyan",
            )
        )

        context: dict = {}
        for agent in selected_agents:
            console.print(f"\n→ Ejecutando [bold]{agent.name}[/bold]...")
            try:
                result = run_agent(agent.type, agent.config, context)
                context[agent.id] = result
                status = result.get("status", "ok")
                msg = result.get("message", "")
                if status == "ok":
                    console.print(f"  [green]✓[/green] {msg}")
                    self._print_agent_details(agent.type, result)
                else:
                    console.print(f"  [red]✗[/red] {msg}")
            except Exception as e:
                console.print(f"  [red]✗ Error: {e}[/red]")
                context[agent.id] = {"status": "error", "message": str(e)}

        # Guardar resultado de la ejecución
        self._save_run_result(name, context)
        console.print("\n[bold green]Pipeline finalizado[/bold green]")

    def _print_agent_details(self, agent_type: str, result: dict) -> None:
        if agent_type == "email_reader":
            prioritized = result.get("prioritized", [])
            if prioritized:
                table = Table(title="Correos prioritarios", show_lines=False)
                table.add_column("Score", style="cyan", width=6)
                table.add_column("Asunto", max_width=40)
                table.add_column("De", max_width=30)
                table.add_column("Razón", max_width=30)
                for m in prioritized[:10]:
                    table.add_row(
                        str(m.get("priority_score", 0)),
                        (m.get("subject") or "")[:40],
                        (m.get("from") or "")[:30],
                        (m.get("priority_reason") or "")[:30],
                    )
                console.print(table)
            else:
                console.print("  (ningún correo prioritario en esta ejecución)")

        elif agent_type == "summarizer":
            summary = result.get("summary", "")
            if summary:
                console.print(Panel(summary, title="Resumen", border_style="dim"))

        elif agent_type == "task_creator":
            tasks = result.get("tasks", [])
            for t in tasks[:5]:
                console.print(f"  • {t.get('title', '')}")

        elif agent_type == "notifier":
            notif = result.get("notification", "")
            if notif:
                console.print(Panel(notif, title=f"Notificación ({result.get('channel')})", border_style="dim"))

        elif agent_type == "draft_replier":
            drafts = result.get("drafts", [])
            console.print(f"  Borradores: {len(drafts)}")

        elif agent_type == "data_extractor":
            console.print(f"  Registros: {result.get('count', 0)}")

    def _save_run_result(self, pipeline_name: str, context: dict) -> None:
        settings.ensure_data_dir()
        out = settings.data_dir / "cache" / f"last_run_{pipeline_name}.json"
        # Serializar de forma segura (solo datos básicos)
        serializable = {}
        for k, v in context.items():
            if isinstance(v, dict):
                # Quitar bodies largos para no inflar el archivo
                clean = {**v}
                if "prioritized" in clean:
                    clean["prioritized"] = [
                        {kk: vv for kk, vv in m.items() if kk != "body"}
                        for m in clean["prioritized"]
                    ]
                if "normal" in clean:
                    clean["normal"] = [
                        {kk: vv for kk, vv in m.items() if kk != "body"}
                        for m in clean.get("normal", [])
                    ]
                serializable[k] = clean
            else:
                serializable[k] = str(v)
        out.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_pipelines(self) -> None:
        pipelines = self.storage.load_pipelines()
        agents = {a.id: a for a in self.storage.load_agents()}

        if not pipelines:
            console.print(
                "[yellow]No hay pipelines guardados. "
                "Ejecuta [cyan]dedalo start[/cyan] primero.[/yellow]"
            )
            return

        console.print("\n[bold]Pipelines y combinaciones disponibles:[/bold]\n")
        for p in pipelines:
            agent_names = [agents[aid].name for aid in p.agent_ids if aid in agents]
            kind = "completo" if p.is_full else "parcial"
            console.print(f"  • [cyan]{p.name}[/cyan]  ({kind})")
            console.print(f"    → {' + '.join(agent_names)}\n")
