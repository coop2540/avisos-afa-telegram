# Proposal: menu-dia

## Why

Les famílies preparen el dia següent a la nit (sopar, motxilla, xerrada amb la criatura) i el menú del menjador només és visible com un PDF mensual penjat a la pàgina del menjador de l'escola: no es pot consultar ràpidament ni arriba a les famílies. Publicar el menú de demà a les 19:00, amb els plats del dia, a dos topics de preferència (basal / sense porc), tanca aquest buit amb el mateix pipeline d'avisos ja existent.

## What Changes

- Nou fetcher que resol dinàmicament l'URL del PDF del menjador des de la pàgina `/serveis/menjador-escolar/` (canvia cada mes; sense hardcodejar).
- Parser del PDF mensual per coordenades (`extract_words`): reconstrueix la rejilla Dilluns–Divendres, ancla les files pel dilluns de cada setmana (tolerància a errata de data imprès) i extreu la cel·la del dia següent per a cada variant.
- Publicació programada el dia anterior a les 19:00 (missatge «Demà dinem …») als dos topics configurats: **basal** i **sense porc**; cada topic rep només la seva variant.
- El missatge diari conté **només els plats** de la cel·la (sense enllaç). L'enllaç al PDF vigent viu en un **missatge anunciat** a cada topic, refrescat automàticament quan canvia l'URL del PDF.
- Salt de publicació si l'endemà no és dia lectiu (cap de setmana o festa extreta de la pàgina de calendari) o si la cel·la no existeix al PDF.
- Dues claus d'estat (`menu_posted` per variant) per evitar duplicats entre reinicis.
- Nova capability `daily-menu` (delta spec); ampliació de `telegram.topics` amb `menu_basal` i `menu_sense_porc`.
- Sortida per a sopars (pàgina 3 del PDF) i post matinal (7:45) **fora d'abast** d'aquest change.

## Capabilities

### New Capabilities

- `daily-menu`: resolució dinàmica del PDF del menjador, extracció de la cel·la diària per variant, publicació programada el dia anterior amb dedup per data de menú, salt de dies no lectius, missatge anunciat amb l'enllaç vigent i configuració de variants/topics.

### Modified Capabilities

(ninguna — les capacitats existents no canvien de requisits a nivell de spec; `telegram-publish` ja cobreix topics i idioma; `web-ingest` ja cobreix sondeig i dedup genèrics.)

## Impact

- **Codi nou**: `src/fetch_menjador.py`, `src/parse_menu.py`, parser de dies no lectius (al costat de `fetch_calendari` o `menu_festes.py`), `pin_message` a `telegram_out.py`, entrades de menú a `messages.py` + catàlegs `src/i18n/*.json`, secció `menu` a `config.py` / `config.yaml.example`, camps nous a `state.py`, trucada a `run_cycle`.
- **Config local**: `telegram.topics.menu_basal: 24`, `telegram.topics.menu_sense_porc: 27`, secció `menu` activada.
- **Fonts externes (read-only)**: pàgina del menjador, PDF mensual del menjador, pàgina de calendari (rangos de festes).
- **Sortida**: Bot API de Telegram — dos missatges diaris (una variant per topic) + refresh de pin, sense canvis en la resta d'orígens.
- **Dependències**: no n'hi ha de noves (`pdfplumber` ja hi és; `pinChatMessage` és un endpoint més de la Bot API).
- **Sense impacte**: web del centre, capacitat `member-approval`, canvi `afa-elisabadia-avisos` (segueix amb els seus propis pendents).
