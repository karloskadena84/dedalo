"""Runners de agentes. Cada tipo sabe cómo ejecutarse."""

from __future__ import annotations

from typing import Any, Callable

from dedalo.core.agents.email_reader import EmailReaderAgent


def run_email_reader(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    agent = EmailReaderAgent(config)
    return agent.run(context)


def run_task_creator(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Crea tareas a partir de correos prioritarios.
    Por ahora genera un resumen estructurado listo para integrar con Notion/Todoist/Jira.
    """
    prioritized = []
    # Buscar resultado del lector en el contexto
    for value in context.values():
        if isinstance(value, dict) and "prioritized" in value:
            prioritized = value["prioritized"]
            break

    tool = config.get("tool", "notion")
    tasks = []
    for mail in prioritized[:10]:
        tasks.append({
            "title": f"[Email] {mail.get('subject', '(sin asunto)')}",
            "description": (
                f"De: {mail.get('from', '')}\n"
                f"Fecha: {mail.get('date', '')}\n"
                f"Prioridad: {mail.get('priority_score', 0)} — {mail.get('priority_reason', '')}\n\n"
                f"{mail.get('snippet', '') or mail.get('body', '')[:400]}"
            ),
            "source_email_id": mail.get("id"),
            "tool": tool,
        })

    return {
        "status": "ok",
        "agent": "TaskCreatorAgent",
        "tool": tool,
        "tasks_created": len(tasks),
        "tasks": tasks,
        "message": f"Preparadas {len(tasks)} tareas para {tool} (integración real pendiente de API keys)",
    }


def run_summarizer(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    prioritized = []
    for value in context.values():
        if isinstance(value, dict) and "prioritized" in value:
            prioritized = value["prioritized"]
            break

    lines = []
    for i, mail in enumerate(prioritized[:15], 1):
        lines.append(
            f"{i}. [{mail.get('priority_score', 0)}] {mail.get('subject', '')} — {mail.get('from', '')}"
        )

    summary = "Resumen de correos prioritarios:\n\n" + ("\n".join(lines) if lines else "No hay correos prioritarios.")
    return {
        "status": "ok",
        "agent": "SummarizerAgent",
        "summary": summary,
        "count": len(prioritized),
        "message": f"Resumen generado con {len(prioritized)} correos prioritarios",
    }


def run_data_extractor(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    prioritized = []
    for value in context.values():
        if isinstance(value, dict) and "prioritized" in value:
            prioritized = value["prioritized"]
            break

    extracted = []
    for mail in prioritized:
        extracted.append({
            "from": mail.get("from"),
            "subject": mail.get("subject"),
            "date": mail.get("date"),
            "priority_score": mail.get("priority_score"),
            "snippet": mail.get("snippet"),
        })

    return {
        "status": "ok",
        "agent": "DataExtractorAgent",
        "records": extracted,
        "count": len(extracted),
        "message": f"Extraídos {len(extracted)} registros estructurados",
    }


def run_draft_replier(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    prioritized = []
    for value in context.values():
        if isinstance(value, dict) and "prioritized" in value:
            prioritized = value["prioritized"]
            break

    drafts = []
    for mail in prioritized[:5]:
        drafts.append({
            "to": mail.get("from"),
            "subject": f"Re: {mail.get('subject', '')}",
            "body": (
                f"Hola,\n\n"
                f"Gracias por tu correo sobre \"{mail.get('subject', '')}\".\n"
                f"Lo estamos revisando y te responderemos a la brevedad.\n\n"
                f"Saludos."
            ),
            "in_reply_to": mail.get("id"),
        })

    return {
        "status": "ok",
        "agent": "DraftReplierAgent",
        "drafts": drafts,
        "count": len(drafts),
        "message": f"Preparados {len(drafts)} borradores de respuesta",
    }


def run_notifier(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    channel = config.get("channel", "slack")
    prioritized = []
    for value in context.values():
        if isinstance(value, dict) and "prioritized" in value:
            prioritized = value["prioritized"]
            break

    message = (
        f"📬 Dédalo — {len(prioritized)} correos prioritarios detectados.\n"
        + "\n".join(
            f"• {m.get('subject', '')} ({m.get('from', '')})"
            for m in prioritized[:8]
        )
    )

    return {
        "status": "ok",
        "agent": "NotifierAgent",
        "channel": channel,
        "notification": message,
        "message": f"Notificación preparada para {channel} (integración real pendiente de webhook/token)",
    }


# Registro de runners por tipo de agente
RUNNERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "email_reader": run_email_reader,
    "task_creator": run_task_creator,
    "summarizer": run_summarizer,
    "data_extractor": run_data_extractor,
    "draft_replier": run_draft_replier,
    "notifier": run_notifier,
}


def run_agent(agent_type: str, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    runner = RUNNERS.get(agent_type)
    if runner is None:
        return {
            "status": "error",
            "message": f"Tipo de agente desconocido: {agent_type}",
        }
    return runner(config, context)
