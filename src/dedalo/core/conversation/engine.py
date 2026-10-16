"""Motor conversacional de Dédalo."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from dedalo.connectors.email.manager import EmailConnectorManager
from dedalo.core.conversation.state import (
    AgentSpec,
    ConversationPhase,
    ConversationState,
    PipelineSpec,
)
from dedalo.core.storage.local import LocalStorage

console = Console()


class ConversationEngine:
    """Orquesta el diálogo con el usuario y construye la secuencia de agentes."""

    def __init__(self):
        self.storage = LocalStorage()
        self.email_manager = EmailConnectorManager()
        self.state = self.storage.load_conversation() or ConversationState()

    def start(self) -> None:
        console.print(
            Panel.fit(
                "[bold cyan]Dédalo[/bold cyan]\n"
                "Vamos a construir juntos un pipeline de agentes\n"
                "para automatizar tus procesos repetitivos.",
                border_style="cyan",
            )
        )

        # Paso obligatorio: conector de correo
        if not self.email_manager.has_active_connector():
            self._configure_connector()
        else:
            connector = self.email_manager.get_active()
            console.print(
                f"[green]✓[/green] Conector activo: [bold]{connector.provider}[/bold]"
            )
            if not Confirm.ask("¿Quieres seguir con este conector?", default=True):
                self._configure_connector()

        self.state.phase = ConversationPhase.CLARIFY_PRIORITIES
        self._clarify_priorities()
        self._ask_next_actions()
        self._naming_phase()
        self._finish()

    def _configure_connector(self) -> None:
        console.print("\n[bold]Antes de empezar necesito que configures tu correo.[/bold]\n")
        console.print("Proveedores disponibles:")
        console.print("  1. Gmail (OAuth recomendado)")
        console.print("  2. IMAP genérico (Proton, Fastmail, Zoho, etc.)")

        choice = Prompt.ask("Elige una opción", choices=["1", "2"], default="1")

        if choice == "1":
            connector = self.email_manager.get_connector("gmail")
            console.print(
                "\n[yellow]Necesitas un client_secrets.json de Google Cloud Console.[/yellow]"
            )
            console.print(
                "Guárdalo en: ~/.dedalo/connectors/gmail_client_secrets.json\n"
            )
            try:
                connector.configure()
                if connector.test_connection():
                    self.email_manager.set_active("gmail")
                    console.print("[green]✓ Gmail configurado correctamente[/green]")
                else:
                    console.print("[red]No se pudo verificar la conexión[/red]")
                    raise SystemExit(1)
            except Exception as e:
                console.print(f"[red]Error configurando Gmail: {e}[/red]")
                raise SystemExit(1)
        else:
            host = Prompt.ask("Servidor IMAP (ej: imap.gmail.com)")
            port = int(Prompt.ask("Puerto", default="993"))
            email = Prompt.ask("Email")
            password = Prompt.ask("Contraseña / App Password", password=True)

            connector = self.email_manager.get_connector("imap")
            connector.configure(host=host, port=port, email=email, password=password)
            if connector.test_connection():
                self.email_manager.set_active("imap")
                console.print("[green]✓ IMAP configurado correctamente[/green]")
            else:
                console.print("[red]No se pudo conectar con esos datos[/red]")
                raise SystemExit(1)

        self.state.phase = ConversationPhase.CLARIFY_PRIORITIES
        self.storage.save_conversation(self.state)

    def _clarify_priorities(self) -> None:
        console.print("\n[bold cyan]Paso 1 — Prioridades de correo[/bold cyan]\n")

        console.print(
            "¿Qué tipo de correos son los más importantes para ti?\n"
            "(ej: clientes, facturas, oportunidades, soporte, internos...)"
        )
        priorities_raw = Prompt.ask("Prioridades (separadas por coma)")
        self.state.priorities = [p.strip() for p in priorities_raw.split(",") if p.strip()]

        console.print(
            "\n¿Hay remitentes o asuntos que siempre deben tener prioridad alta?"
        )
        high = Prompt.ask("Remitentes/asuntos prioritarios (opcional)", default="")
        if high:
            self.state.metadata["high_priority_rules"] = [
                r.strip() for r in high.split(",") if r.strip()
            ]

        console.print("\n¿Qué correos quieres ignorar completamente?")
        ignore_raw = Prompt.ask("Ignorar (newsletters, LinkedIn, etc.)", default="")
        self.state.ignore_rules = [i.strip() for i in ignore_raw.split(",") if i.strip()]

        # Crear el primer agente: Gmail Reader + Prioritizer
        reader = AgentSpec(
            id="gmail_reader",
            name="GmailReaderAgent",
            type="email_reader",
            description="Lee correos y aplica reglas de prioridad e ignorados",
            config={
                "priorities": self.state.priorities,
                "high_priority_rules": self.state.metadata.get("high_priority_rules", []),
                "ignore_rules": self.state.ignore_rules,
            },
        )
        self.state.add_agent(reader)
        console.print("\n[green]✓ Agente creado:[/green] GmailReaderAgent")

        self.state.phase = ConversationPhase.ASK_NEXT_ACTION
        self.storage.save_conversation(self.state)

    def _ask_next_actions(self) -> None:
        console.print("\n[bold cyan]Paso 2 — ¿Qué debe pasar después?[/bold cyan]\n")

        while True:
            console.print(
                "Cuando se detecte un correo prioritario, ¿qué quieres que haga Dédalo?\n"
                "  1. Crear una tarea (Notion / Todoist / Jira)\n"
                "  2. Generar un resumen\n"
                "  3. Extraer datos y guardarlos\n"
                "  4. Preparar un borrador de respuesta\n"
                "  5. Notificar por Slack / Discord\n"
                "  6. Ya está, no quiero más agentes\n"
            )
            choice = Prompt.ask("Elige una opción", choices=["1", "2", "3", "4", "5", "6"])

            if choice == "6":
                break

            agent = self._create_agent_from_choice(choice)
            if agent:
                self.state.add_agent(agent)
                console.print(f"[green]✓ Agente creado:[/green] {agent.name}")

            if not Confirm.ask("\n¿Quieres añadir otro paso después de este?", default=False):
                break

        self.state.phase = ConversationPhase.NAMING
        self.storage.save_conversation(self.state)

    def _create_agent_from_choice(self, choice: str) -> Optional[AgentSpec]:
        mapping = {
            "1": ("task_creator", "TaskCreatorAgent", "Crea tareas a partir de correos prioritarios"),
            "2": ("summarizer", "SummarizerAgent", "Genera resúmenes de correos prioritarios"),
            "3": ("data_extractor", "DataExtractorAgent", "Extrae datos estructurados de correos"),
            "4": ("draft_replier", "DraftReplierAgent", "Prepara borradores de respuesta"),
            "5": ("notifier", "NotifierAgent", "Envía notificaciones (Slack/Discord)"),
        }
        if choice not in mapping:
            return None

        type_, name, desc = mapping[choice]
        extra_config = {}

        if choice == "1":
            tool = Prompt.ask(
                "¿En qué herramienta crear las tareas?",
                choices=["notion", "todoist", "jira", "otro"],
                default="notion",
            )
            extra_config["tool"] = tool
        elif choice == "5":
            channel = Prompt.ask("Canal de notificación", choices=["slack", "discord"], default="slack")
            extra_config["channel"] = channel

        return AgentSpec(
            id=f"{type_}_{len(self.state.agents)}",
            name=name,
            type=type_,
            description=desc,
            config=extra_config,
        )

    def _naming_phase(self) -> None:
        console.print("\n[bold cyan]Paso 3 — Nombres de pipelines y combinaciones[/bold cyan]\n")

        console.print("Secuencia actual de agentes:")
        for i, agent in enumerate(self.state.agents, 1):
            console.print(f"  {i}. {agent.name} — {agent.description}")

        full_name = Prompt.ask(
            "\n¿Cómo quieres llamar al pipeline completo?",
            default="flujo-principal",
        )
        full_pipeline = PipelineSpec(
            name=full_name,
            description="Pipeline completo",
            agent_ids=[a.id for a in self.state.agents],
            is_full=True,
        )
        self.state.add_pipeline(full_pipeline)
        console.print(f"[green]✓ Pipeline completo:[/green] {full_name}")

        if Confirm.ask(
            "\n¿Quieres crear combinaciones parciales para ahorrar tokens?",
            default=True,
        ):
            while True:
                name = Prompt.ask("Nombre de la combinación (ej: solo-prioridad)")
                console.print("Indica los números de los agentes que incluye (ej: 1,2)")
                ids_raw = Prompt.ask("Agentes")
                try:
                    indices = [int(x.strip()) - 1 for x in ids_raw.split(",")]
                    selected_ids = [
                        self.state.agents[i].id
                        for i in indices
                        if 0 <= i < len(self.state.agents)
                    ]
                    if selected_ids:
                        partial = PipelineSpec(
                            name=name,
                            description=f"Combinación parcial: {name}",
                            agent_ids=selected_ids,
                            is_full=False,
                        )
                        self.state.add_pipeline(partial)
                        console.print(f"[green]✓ Combinación:[/green] {name}")
                except Exception:
                    console.print("[red]Entrada inválida, se omite[/red]")

                if not Confirm.ask("¿Crear otra combinación?", default=False):
                    break

        self.state.phase = ConversationPhase.READY
        self.storage.save_conversation(self.state)

    def _finish(self) -> None:
        self.storage.save_pipelines(self.state.pipelines)
        self.storage.save_agents(self.state.agents)

        console.print(
            Panel.fit(
                "[bold green]¡Listo![/bold green]\n\n"
                "Puedes ejecutar tus pipelines con:\n"
                f"  [cyan]dedalo run {self.state.pipelines[0].name}[/cyan]\n\n"
                "Ver todas las combinaciones:\n"
                "  [cyan]dedalo list[/cyan]",
                border_style="green",
            )
        )
