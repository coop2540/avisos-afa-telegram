# afa-elisabadia-avisos

Servei d'avisos de l'**AFA de l'Escola Elisa Badia** (Barberà del Vallès).

Recull el contingut que el centre ja publica a la seva web pública (carta
mensual, calendari del curs i notícies) i el reenvia com a **avisos + enllaç**
a un grup de Telegram amb topics, perquè les famílies no hagin de revisar la
web a mà.

> Transparència: vegeu [`docs/transparencia.md`](docs/transparencia.md) per
> saber què fa el servei, quines dades toca (cap de personal) i qui el sosté.

## Característiques

- Sondeig de la web pública del centre: RSS, enllaç de la carta del mes i
  pàgina de calendari.
- Publicació d'**avís + enllaç** en **català** (sense resums ni IA en la fase
  actual).
- **Sondeig adaptatiu**: més freqüent si hi ha novetat, més espaiat en calma.
- **Un sol grup de Telegram amb topics**; el filtre per curs es fa silenciant
  topics (sense registre de famílies).
- **Només els administradors publiquen**; accés per invitació.
- Estat de deduplicació persistent per no repetir avisos entre reinicis.

## Requisits

- Docker i Docker Compose (recomanat), o Python 3.12+.
- Un bot de Telegram (token de BotFather) i un grup amb topics.

## Posada en marxa (Docker)

```bash
cp config.yaml.example config.yaml   # ajusta chat_id i topics
cp .env.example .env                 # posa-hi TELEGRAM_BOT_TOKEN
docker compose up -d --build
docker compose logs -f
```

L'estat es desa a `./state/` (muntat com a volum). El contenedor s'executa amb
el teu UID/GID (`PUID`/`PGID`) perquè l'estat no quedi com a `root`.

## Posada en marxa (local)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
cp .env.example .env
python -m src.main            # bucle continu
python -m src.main --once     # un sol cicle (útil per a cron o proves)
```

Per provar sense enviar res a Telegram, posa `DRY_RUN=1` a `.env`: els
missatges només es registren als logs.

## Configuració

Tota la configuració és a `config.yaml` (vegeu `config.yaml.example`). Els
**secrets** (token del bot) van **només** a `.env`; mai al repositori.

## Idioma

Els missatges surten dels catàlegs de `src/i18n/` (`ca.json`, `es.json`,
`en.json`…). Per defecte el servei parla **català**; es canvia amb `language` a
`config.yaml` (o la variable `LANGUAGE`). **Afegir un idioma = afegir un fitxer
JSON**; el codi no canvia. Pensat perquè el projecte serveixi a associacions de
qualsevol comunitat.

## Privacitat

El servei **no registra** qui ets, ni quin fill o filla tens, ni el teu
telèfon. Només desa un estat tècnic de deduplicació. Detalls a
[`docs/transparencia.md`](docs/transparencia.md).

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Estructura

```
src/          codi del servei (fetchers, estat, sortida Telegram, scheduler)
tests/        proves automatitzades i fixtures
docs/         transparència, full de ruta i flux de publicació
openspec/     artefactes de planificació (proposta, disseny, specs, tasques)
```

## Llicència

[MIT](LICENSE) © AFA Escola Elisa Badia.
