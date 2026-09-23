# Proposal: aprobacion-miembros

## Why

El grupo de Telegram es privado y con solicitudes de unión, pero hoy **las aprueba un administrador a mano en la app**: no hay aviso, no hay criterio común y es fácil que se cuele quien no toca (p. ej. si un enlace de invitación o un QR se filtra). Necesitamos que el servicio **avise al administrador** con los datos del solicitante y le permita aprobar o rechazar con un clic, sin abrir la app ni revisar la cola.

## What Changes

- El servicio pasa de **solo emitir** a **también escuchar**: recibe las **solicitudes de unión** (`chat_join_request`) del grupo.
- Al recibir una solicitud, envía un **aviso al administrador** (chat privado) con los datos del solicitante (nombre, @usuario, id, bio si está) y **botones** Aprobar / Rechazar.
- Al pulsar un botón, el servicio llama a la API de Telegram (`approveChatJoinRequest` / `declineChatJoinRequest`) y confirma el resultado.
- Se añade un **modo de decisión**: por defecto, sólo avisar (decide el admin); opcionalmente, filtros heurísticos que *recomiendan* o rechazan automáticamente casos claramente sospechosos (nunca aprueban solos).
- **BREAKING (de despliegue):** el servicio necesita recibir updates de Telegram; se debe elegir entre **long polling** o **webhook**. Requiere que el bot no tenga webhook previo y que pueda recibir mensajes (revisar privacy mode si aplica).
- Guía/documentación: cómo crear **enlaces de invitación con expiración** y regenerarlos tras cada difusión (defensa principal contra filtraciones de link/QR).

## Capabilities

### New Capabilities

- `member-approval`: recepción de solicitudes de unión, aviso al administrador con datos del solicitante, aprobación/rechazo por botón, y registro mínimo de la decisión.

### Modified Capabilities

- `telegram-publish`: el sistema ya no es sólo de salida; se añade la recepción de `chat_join_request` y el envío de mensajes con botones. El resto del comportamiento de publicación no cambia.

## Impact

- Código nuevo: receptor de updates (polling o webhook), manejador de `chat_join_request`, manejador de `callback_query` de los botones, y envío de mensajes con `reply_markup`.
- Configuración nueva: identificador del **chat privado del administrador** (destino de los avisos), modo de decisión y filtros opcionales.
- Estado: registro de solicitudes procesadas (para no duplicar avisos y evitar dobles decisiones).
- API de Telegram: nuevos métodos (`getUpdates` o `setWebhook`, `sendMessage` con `reply_markup`, `answerCallbackQuery`, `approveChatJoinRequest`, `declineChatJoinRequest`).
- Infra: si se elige **webhook**, hace falta una URL pública y TLS (cambio de despliegue); con **long polling** no. En fase inicial se prefiere polling (sin exponer nada).
- Privacidad: el servicio verá datos del solicitante (nombre, @usuario, id, bio). **No se almacenan más allá del estado técnico de la decisión**; se documenta en transparencia.
- Sin cambios en la web del centre.
- Relación con el cambio existente `afa-elisabadia-avisos`: es una capability **independiente**; puede aplicarse por separado.
