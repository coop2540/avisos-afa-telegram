# Proposal: afa-elisabadia-avisos

## Why

Las familias del centre pierden avisos porque la información del cole vive repartida en la web d'Àgora (carta mensual PDF, calendari, notícies amb categories de curs) mentre el dia a dia se diluye en WhatsApps de classe. L'AFA pot oferir un servei d'avisos automàtics —sense reunir dades personals— que faci arribar el que interessa (curs de la criatura + general del centre) a un únic canal de Telegram, amb el mateix contingut ja públic.

## What Changes

- Nou servei operat en nom de l'AFA (infraestructura cedida inicialment per tècnic col·laborador) que:
  - sondeja la web pública del centre (RSS, enllaç de la carta del mes, pàgina de calendari);
  - detecta novetats i les publica a un sol grup/canal de Telegram amb topics;
  - publica **avís + enllaç** (sense resum IA en la fase inicial); idiomade sortida: **català**.
- Modelo de un solo lugar de entrada (grupo con topics por curso/tipo); el filtro de clase es UX (silenciar topic), **sin registro ni base de datos de familias**.
- Sondeo adaptativo (frecuencia base + subida si hay novedad + bajada en calma) para respetar la fuente.
- Documentación pública de transparencia (qué hace, qué datos, dónde se guarda, límites legales) publicada en el mismo espacio público (Nextcloud/web AFA).
- Despliegue gradual: solo el operador → 1 beta tester → anuncio de features (topics) → miembro AFA → familias.
- Espejo en Nextcloud de PDFs solo emerge en fase B cuando el pipeline ya descarga el PDF para procesarlo (no es requisito de la fase A).
- **Repositorio del proyecto**: el código se aloja primero en **Forgejo** (instancia propia, **privado**) para revisar cómo quedaría, y tras aprobación se publica en **GitHub** (**público**). Incluye licencia abierta, README público y auditoría de que no haya secretos versionados. El código publicado es el mismo que ejecuta el servicio (auditabilidad).

## Capabilities

### New Capabilities

- `web-ingest`: captura y detección de novedades desde la web pública del centre (RSS por categorías, enllaç carta del mes, pàgina de calendari) con sondeo adaptativo y deduplicación.
- `telegram-publish`: publicación de avisos en un único grupo/canal de Telegram con topics, solo-admins publican, entrada por invitación/join-request, mensajes en català, formato avís+enllaç.
- `service-transparency`: documentación pública del servicio (funcionamiento, datos tocados, dónde se almacena, rol AFA/infra, límites y contacto) publicada en espacio público.
- `service-config-estado`: configuración (chat, topics por origen, umbrales de sondeo) y estado mínimo de "ya publicado" para reinicios sin duplicar avisos.
- `repo-publishing`: preparación y publicación del repositorio del proyecto — privado en Forgejo primero, público en GitHub después — con licencia, README, ausencia de secretos y documentación pública del propio flujo.

### Modified Capabilities

(ninguna — no hay specs de capacidades existentes en este repo)

## Impact

- Código nuevo en este repo: pipeline Python de fase A (fetchers, estado, sender Telegram, scheduler), Dockerfile/compose, config y `.env` (secretos fuera del VPS/repo).
- Sistemas externos de solo lectura: `agora.xtec.cat/escolaelisabadia` (web, RSS `/feed/`, PDFs de carta y calendario).
- Salida: Bot API de Telegram (grupo foro privado; después canal/discusión según evolución).
- Infra: un VPS pequeño (1 vCPU / ~1 GB) o el Geekom en fase inicial; secretos en Vaultwarden/.env; sin Postgres/Redis.
- Nextcloud (host3) solo en fases B/C para espejo opcional y alojo de la doc de transparencia.
- Repositorios: **Forgejo** propio (instancia local, privado) como primer destino; **GitHub** público tras aprobación. Llicència oberta (per defecte MIT, revisable).
- OpenRouter (modelos free) solo fase C — fuera del alcance de este cambio salvo como extensión explícita posterior.
- Sin impacto en la web del centre (no se publica ni se modifica nada allí).
