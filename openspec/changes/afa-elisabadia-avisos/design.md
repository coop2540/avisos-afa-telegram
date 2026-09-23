# Design: afa-elisabadia-avisos

## Context

Veure `proposal.md` — Why. En resum: servei d'avisos per a famílies operat sota l'AFA de l'Escola Elisa Badia, traient només contingut **jà públic** de `agora.xtec.cat/escolaelisabadia` (RSS `/feed/`, enllaç de carta a la portada, pàgina de calendari) i publicant **avís + enllaç** a **un sol grup de Telegram amb topics**, en **català**, amb **quasi zero dades personals** (cap registre de famílies; el filtratge de curs és UX per silenciar topics).

Restriccions que marquen el disseny:

- Ha de cabre en un **VPS petit** i ser fàcil de moure (infra cedida inicialment, després transferible a AFA).
- Desplegament **escalonat**: operador sol → 1 beta → anuncis de features → AFA → famílies.
- La web del centre **no es toca** (només HTTP de lectura, interval amable).
- Transparencia com a part del producte (doc pública, veure `service-transparency`).
- El projecte **acabarà en un repositori públic** (GitHub); primer es revisa en **Forgejo privat** (instància pròpia a la xarxa local).

Fonts reals verificades durant l'exploració:

- Carta: botó/enllaç a PDF mensual (URL canvia cada mes; taula Dia|Curs|Activitat dins del PDF).
- Calendari: PDF per curs + pàgina HTML amb seccions de dates.
- RSS: categories de curs (I4, 3r…), Portada, General.

## Goals / Non-Goals

**Goals:**

- Fase A: pipeline cíclic fetch → dedup → `sendMessage` a topics, autorestart, config externa.
- Format de missatge estable, en català, avís+enllaç a URL original.
- Sondeo adaptatiu i tolerància a errors (font caiguda ≠ aturar el servei).
- Secrets fora del repo; estat de dedup persistent al volum.
- Document de transparencia com a artefacte del servei (pot viure al repo i publicar-se a Nextcloud).

**Non-Goals:**

- No sustitueix WhatsApp del centre ni missatges que no es publiquen a la web.
- No registre d'usuaris, classes ni telèfons.
- No resums ni preguntes amb IA (OpenRouter → fase futura, fora d'aquest canvi llevat que s'obri canvi a part).
- No espejo Nextcloud obligatori en fase A (emergent quan es baixi el PDF per processar).
- No modificacions a la web ni a plugins de XTEC.
- No multi-tenant genèric "qualsevol escola" (el disseny no ho impedeix, però no és objectiu).

## Decisions

### D1 — Python, procés únic, sense framework Telegram en fase A

- **Tria:** Python 3.12, `httpx` (o `requests`), `feedparser`, `beautifulsoup4`; HTTP directe a Bot API (`sendMessage` + `message_thread_id`); estat en JSON (sqlite si cal créixer).
- **Per què:** la complexitat real de fases futures és PDF→taula (pymupdf/pdfplumber) i allà Python és casa; la fase A no necessita `python-telegram-bot`/`aiogram` (no hi ha comandos ni webhook).
- **Descartat:** Node/grammY (viable però pitjor per al PDF de després); framework Telegram ara (acoblament prematur); webhook (no rebem missatges en A).

### D2 — Loop de sondeig amb intervals adaptatius (no cron rígid multi-job)

- **Tria:** un scheduler simple amb base ~60 min; finestra calenta (~15–30 min) després de novetat; cap a 4–24 h en calma llarga. Config amb límits.
- **Per què:** el centre publica de forma irregular (molt a setembre, poc a agomeny); un sol loop simplifica Docker i logs.
- **Descartat:** cron extern per fetcher (pitjor adaptació, més processos); webhooks des de XTEC (no n'hi ha).

### D3 — Un sol xat; topics = identitat de curs, no comptes d'usuari

- **Tria:** grup (preferentment fòrum amb topics) o canal+discussion segons com es muntés; config `origen → thread_id`; fase inicial un sol topic "general".
- **Per què:** mínim RGPD (no guardem qui és de quina classe), UX d'un sol link, multi-fills = silenciar topics, cost zero d'afegir curs.
- **Descartat:** N canales (dispersió, més invitis); registro clase→usuario (dades sensibles innecessàries en A/B); bot 1:1 com a única sortida (no és "assabentar").

### D4 — Enllaç = URL original de XTEC en fase A; espejo Nextcloud emergent

- **Tria:** publicar `https://agora.xtec.cat/...` com a enllaç; no baixar PDFs tret que un fetcher futur els processi; si es baixen, còpia a Nextcloud públic "de pas".
- **Per què:** zero infra de storage en A; quan hi hagi OCR/filtra carta, el byte ja és a mà i arxivar surt gratis; desacoblament de XTEC només quan aporta.
- **Descartat:** sempre baixar i servir des de Nextcloud (més peatge ara del que cal); hardcodejar URLs de PDF ( canvien cada mes).

### D5 — Català per defecte, textos externalitzats

- **Tria:** l'idioma per defecte és el **català** (alpha, beta i v1), però els textos **no** viuen al codi sinó en catàlegs per idioma (`src/i18n/*.json`); l'idioma es tria a la configuració.
- **Per què:** la font és en català i el públic inicial és de Catalunya; alhora, el projecte es vol reutilitzable per associacions d'altres comunitats sense reescriure res.
- **Descartat:** textos incrustats (impossibiliten traduir sense tocar codi); traducció automàtica en temps d'execució (innecessària, i amb IA a la fase C ja hi ha prou risc).

### D6 — Secrets i desplegament

- **Tria:** Docker Compose, imatge `python:3.12-slim`, volum per `state/`, `.env` per `TELEGRAM_BOT_TOKEN` i identitats de xat; restart `unless-stopped`; logs a stdout → `docker logs` o rotació.
- **Per què:** mínim VPS (1 vCPU / 1 GB sobra), migració = copiar compose + state; secrets no al git.
- **Alternativa:** systemd sense Docker — viable, menys portable; es pot escollir a l'aplicar segons gust, el disseny només exigeix "procés reiniciable + volum d'estat".

### D7 — Model de dades d'estat (dedup)

```json
{
  "rss_guids": ["...", "..."],
  "carta_url": "https://...",
  "cal_hash": "sha256:...",
  "ultima_novetat": "ISO8601",
  "intent_errors": {"rss": 0}
}
```

- Un sol document; atomicitat senzilla (write temp + rename). Prou per a milers d'items.

### D8 — Arquitectura de mòduls (orientativa, no contracte)

```
src/
  fetch_rss.py        # feed + filtres categories
  fetch_carta.py      # resol enllaç PDF portada
  fetch_calendari.py  # HTML → seccions dates
  state.py            # carrega/guarda dedup
  telegram_out.py     # sendMessage + thread_id
  scheduler.py        # loop adaptatiu
  config.py           # YAML + env
config.yaml
Dockerfile / compose.yml
docs/transparencia.md # publicable a Nextcloud
```

### D9 — Hosting del repositori: Forgejo privat → GitHub públic

- **Tria:** repositori git local; remot `origin` = Forgejo propi (`ssh://git@192.168.0.18:222/jordan/...`), privat; remot `github` afegit quan s'aprovi per publicar.
- **Per què:** Forgejo és instància pròpia ja en marxa (Docker a la xarxa local) i permet veure "com queda" sense exposar-ho; GitHub dona visibilitat i col·laboració externa quan el projecte estigui llest.
- **Descartat:** publicar directament a GitHub (sense fase de revisió); dependre només de GitHub (perd control sobre la revisió prèvia).

### D10 — Llicència oberta

- **Tria:** `LICENSE` **MIT** per defecte, amb titular "AFA Escola Elisa Badia".
- **Per què:** màxima simplicitat i reutilització per part d'altres AFAs; alineat amb l'esperit de servei públic.
- **Alternatives:** AGPL-3.0 (copyleft fort, si es vol garantir que les millores tornin a la comunitat). **Revisable** abans de fer públic a GitHub.

### D11 — Què és públic i què no

- **Tria (versionat al repo):** codi `src/`, tests, `Dockerfile`, `compose.yml`, plantilles `*.example`, `docs/`, artefactes OpenSpec.
- **Tria (mai versionat):** `.env`, `config.yaml` (conté `chat_id`), `state/`, qualsevol token o clau.
- **Per què:** el que es publica és el servei; el que és local o secret queda fora. El codi publicat és el que s'executa (auditabilitat).

### D12 — i18n per catàlegs

- **Tria:** textos en fitxers JSON a `src/i18n/` (`ca`, `es`, `en` de sortida); `translate(clau, idioma)` amb retrocés a català i, si no, a la clau; `language` a config (o `LANGUAGE` a l'entorn); variants regionals normalitzades (`es-ES` → `es`).
- **Per què:** afegir un idioma = afegir un fitxer, sense tocar codi; el codi descobreix idiomes pels catàlegs presents; encaixa amb el repo reutilitzable per altres AFA.
- **Alternatives:** gettext/`babel` (més maquinària i dependències per a unes poques cadenes); textos incrustats (descartat a D5).
- **Límit:** la documentació (`docs/`) es manté en català de moment; es podrà traduir més endavant si el projecte es reutilitza.

### D13 — Parser de la carta i agenda

- **Tria:** `pdfplumber` per extreure el **text** del PDF; parser per línies amb regex `^(\d{1,2})\s+(\S+)\s+(.+)$` després de la capçalera «Dia Curs Activitat»; mes/any de la capçalera «CARTA DEL MES DE <mes> <any>». Filtre per cursos configurats. Dues sortides: (1) **selecció** en detectar carta nova (reutilitza l'esdeveniment de carta existent), i (2) **agenda setmanal** programada (dia/hora) amb estat `last_weekly_post`.
- **Per què:** la taula és **text pla** al PDF → sense OCR ni IA; `extract_text` dona files netes; reutilitza el flux de detecció de carta; el filtre per curs compleix la visió original («el que toca al grup del teu fill»).
- **Descartat:** OCR (innecessari); `extract_tables()` (retorna les columnes com una sola cel·la amb salts; el text per línies és més fiable).
- **Límit:** si la setmana creua de mes, els actes del mes següent no apareixen fins que surt la carta nova; si la carta no té taula, es cau a avís+enllaç.


## Risks / Trade-offs

- **[XTEC canvia HTML/CSS de la portada o del calendari]** → fetchers amb selectors senzills + logs d'error; fallback a "no publicar" en lloc d'avisar malament; tests de fixtures HTML.
- **[RSS global massa sorollós (tot el centre)]** → filtre per categories a config; prioritzar categoria de curs + Portada/General segons decisió de l'operador; refinar en beta.
- **[URL de carta no es un `<a>` estable (JS/menú)]** → verificar HTML cru en l'aplicar; si cal, mirar altres punters (pàgina "carta", og:image, etc.); risc baix detectat en exploració.
- **[Taula de la carta és imatge → caldria OCR]** → fora de fase A (avís+enllaç); si B ho necessita, llavors pymupdf primer i OCR com a últim recurs.
- **[Telegram rate limit / error de xat]** → retry amb backoff senzill; no marcar dedup fins a enviament OK (o cua de fallits); alerta als logs.
- **[Spam en el grup quan s'obri a famílies]** → només admins publiquen + join-request + doc de normes; no dependre de moderació manual.
- **[Operador únic = bus factor 1]** → tot a git + doc de transparencia + secretos en Vaultwarden; migració AFA documentada com a pas de deploy.
- **[Agressió a XTEC] (ètica i tècnica)** → intervals amables, UA identificable, sense scraping de pàgines innecessàries; RSS quan existeix.
- **[Secret filtrat a l'historial git]** → `.gitignore` des del primer commit; auditoria de secretes abans de publicar; si s'hi filtrés, rotar el token (no n'hi ha prou d'esborrar el fitxer).

## Migration Plan

1. Desenvolupament local/dev (Geekom) amb xat de proves i 1–2 topics.
2. Contenedor a VPS (o Geekom always-on): posar `.env`, `config.yaml`, volum `state/`.
3. Canari: operador únic; revisar logs 1–2 setmanes i calibrar intervals.
4. Convidar 1 beta tester (invitació/seguretat del grup ja activa).
5. Activar més topics i publicar doc de transparencia a espai públic AFA/Nextcloud.
6. Demo a membre AFA; després obertura gradual amb join-request.
7. **Rollback:** aturar contenedor + retirar invitació/link; l'estat es pot conservar per reprendre; cap efecte a la web del centre.

## Open Questions

- Grup-fòrum amb topics vs. canal amb discussion group: decidir en el muntatge real de Telegram (no canvia specs, només la config de `thread_id` i qui és admin).
- Existeix RSS per categoria (`/categoria/infantil/i4/feed/`)? Verificar en aplicar; si sí, simplifica filtres.
- Freqüències exactes (base/calma/calenta): calibrar amb dades reals de publicació després del canari.
- Si més endavant hi ha "una nota que és només de I4B", com es etiqueta sense IA: probablement el Curs de la taula de la carta o categories — resoldre en fase B, no bloqueja A.
- Sortida addicional per **WhatsApp** (comunitat amb subgrups): es contempla com a feature de futur, no d'aquest canvi. Requeriria abstraure una capa de "publicadors" al costat del de Telegram i assumir les limitacions de la WhatsApp Business Platform (de pagament, plantilles aprovades). No afecta l'esquema actual.
