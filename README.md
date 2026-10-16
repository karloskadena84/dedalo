# Dédalo

<p align="center">
  <img src="assets/cover.jpg" alt="Dédalo — Automatiza lo que haces todos los días" width="100%" />
</p>

**Dédalo** te ayuda a automatizar lo que haces todos los días (empezando por el correo) creando agentes que trabajan en cadena.

Tú le dices qué es importante. Él construye el flujo. Tú le pones un nombre y lo ejecutas cuando quieras.

---

## Cómo usarlo (modo fácil — MCP)

Si usas **Cursor, Claude Desktop, Windsurf** u otra herramienta con MCP, casi no necesitas la terminal.

### 1. Instalar (solo una vez)

Pide a tu IA (o a alguien técnico) que ejecute esto:

```bash
pip install git+https://github.com/karloskadena84/dedalo.git
```

Luego configura Dédalo como servidor MCP en tu herramienta (Cursor / Claude Desktop / etc.).

### 2. Configurar tu correo (solo una vez)

Dile a la IA:

> Configura mi correo en Dédalo con Gmail

o

> Configura mi correo en Dédalo con IMAP

Sigue las indicaciones que te dé (autorizar Gmail en el navegador o poner datos de IMAP).

### 3. Crear tu automatización

Dile a la IA:

> Empieza Dédalo

La IA te irá preguntando:
- Qué correos son prioritarios
- Qué quieres que haga después (crear tareas, resumen, avisar, etc.)
- Cómo quieres llamar al flujo completo
- Si quieres combinaciones más pequeñas (para gastar menos tokens)

### 4. Ejecutar cuando quieras

Dile a la IA:

> Ejecuta en Dédalo el flujo **flujo-clientes**

o

> Ejecuta en Dédalo **solo-prioridad**

---

## Resumen de frases útiles para la IA

| Qué quieres hacer              | Qué le dices a la IA                          |
|--------------------------------|-----------------------------------------------|
| Configurar Gmail               | Configura mi correo en Dédalo con Gmail       |
| Configurar otro correo (IMAP)  | Configura mi correo en Dédalo con IMAP        |
| Empezar a crear automatización | Empieza Dédalo                                |
| Ver mis flujos                 | Lista los flujos de Dédalo                    |
| Ejecutar un flujo              | Ejecuta en Dédalo el flujo [nombre]           |
| Ver el estado                  | ¿Cuál es el estado de Dédalo?                 |

---

## ¿Qué hace Dédalo por dentro?

1. Lee tus correos (Gmail o IMAP).
2. Separa los importantes según las reglas que le dijiste.
3. Pasa esos correos a los siguientes agentes (tareas, resumen, notificaciones…).
4. Tú puedes ejecutar el flujo completo o solo una parte (ahorras tokens).

---

## Para quien sí usa terminal

```bash
# Instalar
pip install git+https://github.com/karloskadena84/dedalo.git

# Configurar correo
dedalo connectors add gmail    # o: dedalo connectors add imap

# Crear automatización
dedalo start

# Ejecutar
dedalo run flujo-clientes
dedalo list
dedalo status
```

---

## Licencia

MIT
