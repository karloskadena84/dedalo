"""
Servidor MCP de Dédalo (esqueleto).

Para activarlo necesitas la dependencia opcional:
    pip install dedalo[mcp]

Luego puedes registrarlo en clientes compatibles con MCP
(Cursor, Claude Desktop, etc.).
"""

from __future__ import annotations

# Esqueleto listo para implementar con el SDK de MCP cuando se instale la extra.
# Las herramientas expuestas serán equivalentes a los comandos CLI:
#   - start_conversation
#   - configure_email_connector
#   - run_pipeline
#   - list_pipelines
#   - get_status

def create_mcp_server():
    """Crea y devuelve el servidor MCP de Dédalo."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        raise ImportError(
            "Para usar el servidor MCP instala la extra: pip install dedalo[mcp]"
        ) from e

    mcp = FastMCP("dedalo")

    @mcp.tool()
    def start_conversation() -> str:
        """Inicia la conversación guiada de Dédalo (requiere interacción)."""
        return (
            "Para una experiencia completa usa el CLI: `dedalo start`.\n"
            "Desde MCP puedes configurar conectores y ejecutar pipelines."
        )

    @mcp.tool()
    def list_pipelines() -> str:
        """Lista los pipelines y combinaciones disponibles."""
        from dedalo.core.pipeline.executor import PipelineExecutor
        from io import StringIO
        import sys

        # Captura simple; en producción se devolvería estructura
        executor = PipelineExecutor()
        pipelines = executor.storage.load_pipelines()
        if not pipelines:
            return "No hay pipelines guardados. Ejecuta primero `dedalo start`."
        lines = []
        for p in pipelines:
            kind = "completo" if p.is_full else "parcial"
            lines.append(f"- {p.name} ({kind}): {', '.join(p.agent_ids)}")
        return "\n".join(lines)

    @mcp.tool()
    def run_pipeline(name: str) -> str:
        """Ejecuta un pipeline o combinación por nombre."""
        from dedalo.core.pipeline.executor import PipelineExecutor

        executor = PipelineExecutor()
        # En MCP devolvemos mensaje; la ejecución real se hace en el CLI por ahora
        pipelines = executor.storage.load_pipelines()
        if not any(p.name == name for p in pipelines):
            return f"Pipeline '{name}' no encontrado."
        executor.run(name)
        return f"Pipeline '{name}' ejecutado."

    @mcp.tool()
    def get_status() -> str:
        """Devuelve el estado actual de Dédalo."""
        from dedalo.connectors.email.manager import EmailConnectorManager
        from dedalo.core.storage.local import LocalStorage

        manager = EmailConnectorManager()
        storage = LocalStorage()
        active = manager.get_active()
        pipelines = storage.load_pipelines()

        status = {
            "connector": active.provider if active else None,
            "pipelines_count": len(pipelines),
            "pipelines": [p.name for p in pipelines],
        }
        return str(status)

    return mcp


if __name__ == "__main__":
    server = create_mcp_server()
    server.run()
