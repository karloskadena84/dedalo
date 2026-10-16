"""CLI de Dédalo."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from dedalo import __version__
from dedalo.connectors.email.manager import EmailConnectorManager
from dedalo.core.conversation.engine import ConversationEngine
from dedalo.core.pipeline.executor import PipelineExecutor
from dedalo.utils.config import settings

app = typer.Typer(
    name="dedalo",
    help="Dédalo — Construye pipelines de agentes secuenciales de forma conversacional.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

connectors_app = typer.Typer(help="Gestiona conectores de correo")
app.add_typer(connectors_app, name="connectors")


@app.callback()
def main():
    """Dédalo — Automatiza procesos repetitivos con agentes secuenciales."""
    settings.ensure_data_dir()


@app.command()
def version():
    """Muestra la versión de Dédalo."""
    console.print(f"Dédalo v{__version__}")


@app.command()
def start():
    """Inicia la conversación guiada para construir tu pipeline de agentes."""
    engine = ConversationEngine()
    engine.start()


@app.command()
def run(
    name: str = typer.Argument(..., help="Nombre del pipeline o combinación a ejecutar"),
):
    """Ejecuta un pipeline o combinación por su nombre."""
    executor = PipelineExecutor()
    executor.run(name)


@app.command("list")
def list_pipelines():
    """Lista todos los pipelines y combinaciones guardadas."""
    executor = PipelineExecutor()
    executor.list_pipelines()


@app.command()
def status():
    """Muestra el estado actual de Dédalo."""
    email_manager = EmailConnectorManager()
    executor = PipelineExecutor()

    console.print(Panel.fit("[bold cyan]Estado de Dédalo[/bold cyan]", border_style="cyan"))

    # Conector
    active = email_manager.get_active()
    if active:
        console.print(f"Conector de correo: [green]✓ {active.provider}[/green]")
    else:
        console.print("Conector de correo: [red]✗ No configurado[/red]")

    # Pipelines
    pipelines = executor.storage.load_pipelines()
    console.print(f"Pipelines guardados: [bold]{len(pipelines)}[/bold]")
    if pipelines:
        for p in pipelines:
            console.print(f"  • {p.name}")


# ─── Subcomandos de connectors ───────────────────────────────────────────────

@connectors_app.command("list")
def connectors_list():
    """Lista los conectores disponibles y el activo."""
    manager = EmailConnectorManager()
    console.print("\n[bold]Proveedores disponibles:[/bold]")
    for p in manager.list_available():
        console.print(f"  • {p}")

    active = manager.get_active()
    if active:
        console.print(f"\n[green]Activo:[/green] {active.provider}")
    else:
        console.print("\n[yellow]Ningún conector activo[/yellow]")


@connectors_app.command("add")
def connectors_add(
    provider: str = typer.Argument(..., help="gmail | imap"),
):
    """Añade y configura un conector de correo."""
    from rich.prompt import Prompt

    manager = EmailConnectorManager()
    provider = provider.lower()

    if provider not in manager.list_available():
        console.print(f"[red]Proveedor no soportado: {provider}[/red]")
        raise typer.Exit(1)

    connector = manager.get_connector(provider)

    if provider == "gmail":
        console.print(
            "[yellow]Asegúrate de tener el archivo client_secrets.json[/yellow]\n"
            f"Ubicación recomendada: {settings.data_dir / 'connectors' / 'gmail_client_secrets.json'}"
        )
        try:
            connector.configure()
            if connector.test_connection():
                manager.set_active("gmail")
                console.print("[green]✓ Gmail configurado y activado[/green]")
            else:
                console.print("[red]Conexión fallida[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    elif provider == "imap":
        host = Prompt.ask("Servidor IMAP")
        port = int(Prompt.ask("Puerto", default="993"))
        email = Prompt.ask("Email")
        password = Prompt.ask("Contraseña / App Password", password=True)
        connector.configure(host=host, port=port, email=email, password=password)
        if connector.test_connection():
            manager.set_active("imap")
            console.print("[green]✓ IMAP configurado y activado[/green]")
        else:
            console.print("[red]No se pudo conectar[/red]")
            raise typer.Exit(1)


@connectors_app.command("use")
def connectors_use(
    provider: str = typer.Argument(..., help="gmail | imap"),
):
    """Cambia el conector de correo activo."""
    manager = EmailConnectorManager()
    provider = provider.lower()
    connector = manager.get_connector(provider)
    if not connector.is_configured():
        console.print(f"[red]{provider} no está configurado. Usa: dedalo connectors add {provider}[/red]")
        raise typer.Exit(1)
    manager.set_active(provider)
    console.print(f"[green]✓ Conector activo: {provider}[/green]")


if __name__ == "__main__":
    app()
