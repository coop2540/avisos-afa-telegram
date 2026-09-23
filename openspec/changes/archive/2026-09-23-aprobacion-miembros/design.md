# Design: aprobacion-miembros

## Context

Veure `proposal.md` — Why. El servei d'avisos actual (`src/``) només **emet**: sondeja la web del centre i publica al grup. Aquest canvi afegeix el camí **d'entrada**: rebre les solicituds d'unió al grup privat, avisar un administrador i aplicar la seva decisió.

Restriccions:

- No exposar res a Internet si es pot evitar (fase inicial, poques families).
- El bot no ha d'aprovar mai sol, per defecte.
- Ha de conviure amb l'emoji/servei existent sense trencar-lo.

## Goals / Non-Goals

**Goals:**

- Rebre `chat_join_request` i avisar l'administrador per xat privat amb botons.
- Aprovar/rebutjar amb un clic (`approveChatJoinRequest` / `declineChatJoinRequest`).
- Funcionar amb **long polling** per defecte (sense URL pública).
- No duplicar avisos ni dobles decisions.

**Non-Goals:**

- Verificar "parentalitat" real (Telegram no ho permet); la decisió final és humana.
- Aprovació totalment automàtica (descartada).
- Gestió d'enllaços d'invitació per part del bot (només recomanacions).
- Multi-grup / multi-admin (un destí d'avís; es podra ampliar).

## Decisions

### D1 — Long polling per defecte, webhook opcional

- **Tria:** `getUpdates` amb `offset` i `timeout` (long polling) com a mode per defecte; `setWebhook` com a alternativa configurable.
- **Per què:** polling no requereix URL pública ni TLS ni obrir ports; encaixa amb la infra minimista (VPS/Geekom). El webhook només te sentit si hi ha un domini exposat.
- **Descartat:** nomes webhook (complexitat d'infra per a poques families); ambdós alhora (Telegram no ho permet pel mateix bot).

### D2 — Dos bucles o un de sol?

- **Tria:** afegir un **segon fil** (thread) de polling al costat del bucle de sondeig de la web, dins el mateix procés; l'estat es comparteix amb un lock o es manté separat per clau.
- **Alternativa:** procés separat. Es descarta per simplicitat d'un sol servei/contenidor.
- **Nota:** a Telegram, polling i publicació son independents; el fil de polling queda bloquejat a `getUpdates` (timeout llarg) i no consumeix CPU.

### D3 — Missatge d'avís amb botons (inline keyboard)

- **Tria:** `sendMessage` al xat privat de l'admin amb `reply_markup.inline_keyboard`: `[✅ Aprovar] [❌ Rebutjar]`, amb `callback_data` que identifica la solicitud (`apr:<user_id>` / `rej:<user_id>`).
- **Per què:** un clic, sense comandes ni memoritzar res; `callback_data` cabut i sense dades sensibles.
- **Alternativa:** comandes (`/aprovar 123`). Descartat: pitjor UX i més error humà.

### D4 — Estat i idempotència

- **Tria:** clau d'estat `join_requests: { "<user_id>": {"status": "notified|approved|declined", "ts": "..."} }` dins del document d'estat existent.
- **Per què:** evita renotificar i dobles decisions; sobreviu a reinicis.
- **Límit:** Telegram pot tornar a enviar un update; la clau per usuari ho neutralitza.

### D5 — Filtres heurístics (opt-in, nomes rebuig)

- **Tria:** llista configurable de regles de **rebuig automàtic** (`nom buit o numeric`, `bio/username amb patrons de spam`, etc.). Cap regla aprova.
- **Per què:** el pitjor cas d'un fals positiu es "s'ha de revisar a ma"; mai deixa entrar algú per error.
- **Descartat:** puntuacio que aprova sola (risc inacceptable).

### D6 — Configuracio

```yaml
telegram:
  admin_chat_id: "<xat privat de l'admin>"
  approval:
    enabled: true
    receive: polling        # polling | webhook
    webhook:
      url: null
      secret_token: null    # es guarda a .env, no aqui
    auto_reject:            # opcional; si buit, nomes avis
      enabled: false
      block_empty_name: true
      block_spam_bio: true
```

### D7 — Privacitat

- Les dades del solicitant (nom, @usuari, id, bio) es **mostren** a l'admin pero **no s'emmagatzemen** mes enlla dels identificadors i la decisio.
- S'actualitza `docs/transparencia.md` per explicar-ho.

## Risks / Trade-offs

- **[Fals positiu d'un filtre]** → nomes pot rebutjar; l'admin rep l'avís i pot actuar manualment si cal.
- **[El bot necessita privacy mode / permisos]** → per rebre `chat_join_request` el bot ha de ser admin del grup amb "Afegir membres"? En realitat `chat_join_request` arriba si el bot es admin i el grup te join requests; documentar-ho i verificar en aplicar.
- **[Polling duplicat si ja hi ha webhook]** → en arrencar polling, cridar `deleteWebhook` per netejar.
- **[Rate limits de Telegram]** → backoff ja existent a `telegram_out`; reutilitzar-lo.
- **[Confusio amb el bucle existent]** → mantenir separacio de responsabilitats: `telegram_out` envia, un modul nou `approval` rep i decideix.
- **[Solicituds de desconeguts en massa]** → els filtres opt-in i la decisio manual ho contenen; documentar enllaços amb expiracio.

## Migration Plan

1. Obtenir el `admin_chat_id` (xat privat de l'admin) i afegir-lo a `config.yaml`.
2. Desplegar amb l'aprovacio desactivada per defecte i provar amb una solicitud de prova (el propi admin sol·licita entrar amb un segon compte).
3. Activar, comprovar avís + botons + decisio.
4. Documentar a `docs/transparencia.md` i a la guia.

## Open Questions

- Cal comprovar si el bot necessita permisos especials per rebre `chat_join_request` (verificar en aplicar; probablement n'hi ha prou amb ser admin i que el grup tingui join requests).
- Si mes endavant hi ha mes d'un admin, com es reparteixen els avisos (un xat per admin, o un grup intern d'admins). No bloqueja aquest canvi.
