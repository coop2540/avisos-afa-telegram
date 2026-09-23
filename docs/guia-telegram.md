# Guia: crear el bot i el grup de Telegram

Guia **reutilitzable per a qualsevol AFA**. Explica com crear el bot, muntar el
grup amb topics, obtenir els identificadors que necessita el servei i deixar-ho
configurat. No calen coneixements de programació; sí accés a un lloc on
executar el servei (pot ser el teu ordinador per provar).

Temps aproximat: 15 minuts.

---

## Abans de començar

- Un compte de **Telegram** (mòbil o escriptori).
- El repositori descarregat i Python o Docker disponibles.
- Decidir **quins topics** voleu (per exemple: `General`, `Cartes del mes`,
  `Calendari`, `I4`, `3r`, `6è`…).

> **Model triat:** un **grup amb topics** (fòrum). Un sol enllaç d'entrada, i
> cada família silencia els topics que no li interessen. Alternativa: un
> **canal** de només difusió (més limitat: no té topics i no permet fils).
>
> **Per què Telegram i no WhatsApp?** Ho expliquem a
> [`docs/transparencia.md`](transparencia.md#per-què-telegram-i-no-whatsapp)
> (bàsicament: WhatsApp no permet automatitzar la publicació; Telegram sí).

---

## 1. Crear el bot (BotFather)

1. Obre Telegram i cerca **@BotFather** (el verificat, amb la marca blava).
2. Envia-li `/newbot`.
3. Tria un **nom visible** (p. ex. `Avisos AFA Escola X`).
4. Tria un **nom d'usuari** que acabi en `bot`
   (p. ex. `afa_escolax_avisos_bot`). Ha de ser únic.
5. BotFather respon amb un **token** (una cadena llarga: uns dígits, dos punts
   i una part alfanumèrica). Aquest és el `TELEGRAM_BOT_TOKEN`.

   **No el posis mai al repositori ni el comparteixis**; anirà a `.env`.

6. Opcional: amb `/setdescription` i `/setuserpic` li pots donar la identitat
   de l'AFA.

---

## 2. Crear el grup amb topics

1. Telegram → **Nou grup**. Per crear-lo cal afegir com a mínim un altre
   membre (pot ser un compte secundari o un contacte de confiança; després el
   pots treure).
2. Posa-li un nom, p. ex. `AFA Escola X — Avisos`.
3. Obre **Ajustos del grup** → activa **Temes** (*Topics*). Això converteix el
   grup en supergrup i habilita els fils.
4. **Afegeix el bot** al grup (cerca el seu `@usuari` i afegeix-lo).
5. Fes el bot **administrador** amb aquests permisos:
   - **Enviar missatges** (per publicar).
   - **Gestionar temes** (per poder crear topics i publicar-hi).
6. Restringeix qui pot escriure, perquè les famílies **només llegeixin**:
   - **Mòbil:** toca el nom del grup → **Edita** (llapis) → **Permisos** →
     **desactiva** l'interruptor **Enviar missatges**.
   - **Escriptori:** clica el nom del grup → **Edita** → **Permisos** →
     **desactiva** **Enviar missatges**.
   - Alguns clients mostren una opció **Enviar missatges** amb els valors
     *Tots els membres* / *Només administradors*: tria **Només administradors**.
   - És un permís **a nivell de grup** (val per tots els topics del fòrum).
   - Els **administradors** (i el bot) sempre poden escriure; els membres només
     llegeixen (anti-soroll).

   **Conjunt recomanat** a la pantalla «Permisos» (deixa-ho tot en vermell
   excepte el que vulguis): desactiva **Enviar missatges**, **Crear temes**,
   **Fixar missatges**, **Afegir membres** i **Canviar la informació del grup**.
   Així les famílies només llegeixen i només els administradors organitzen el
   grup.
7. Privacitat: **Ajustos → Grups i canals → Grup privat**. Activa **Aprovar
   membres nous** (sol·licituds d'unió) si vols controlar qui entra.
8. Crea els **topics** que vulguis (General, Cartes, Calendari, I4, 3r…).

---

## 3. Obtenir el `chat_id` i els `thread_id`

### 3.1 `chat_id` del grup

1. Envia un missatge qualsevol al grup (en un topic).
2. Consulta:

   ```bash
   curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates"
   ```

3. Busca `"chat":{"id":-100...}`. Aquest número negatiu és el **`chat_id`**.

> Si `getUpdates` surt buit: assegura't que has enviat el missatge **després**
> d'afegir el bot, i que no hi ha cap webhook configurat (aquest servei no
> n'usa).

### 3.2 `thread_id` de cada topic

**Opció A (recomanada): deixa que el bot creï els topics.** Amb el bot com a
administrador amb «Gestionar temes»:

```bash
curl -s -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/createForumTopic" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":-100XXXXXXXXXX,"name":"Cartes del mes"}'
```

La resposta inclou `"message_thread_id": <número>`. Repeteix per cada topic
(General no cal: deixa'l com a `null`).

**Opció B:** crea els topics a mà, envia un missatge dins de cadascun i llegeix
`message_thread_id` a la sortida de `getUpdates`.

---

## 4. Configurar el servei

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

A **`.env`**:

```dotenv
TELEGRAM_BOT_TOKEN=<el-token-que-t'ha-donat-BotFather>
```

A **`config.yaml`**, posa el `chat_id` i els thread ids:

```yaml
telegram:
  chat_id: "-1001234567890"
  topics:
    default: null     # topic general
    rss: 12           # notícies
    carta: 13         # carta del mes
    calendari: 14     # calendari
```

Qualsevol origen sense topic propi cau a `default` (topic general).

### Idioma dels missatges

Per defecte el servei parla **català**. Es canvia a `config.yaml`:

```yaml
language: ca   # opcions: ca, es, en (catàlegs a src/i18n/)
```

Per afegir un idioma nou, copia `src/i18n/ca.json` a `<codi>.json` i tradueix
els valors. No cal tocar el codi.

### Agenda de la carta

El servei extreu la taula d'activitats de la carta i en publica la selecció del
curs (en sortir carta nova) i una agenda setmanal. Es configura a `config.yaml`:

```yaml
agenda:
  enabled: true
  cursos: ["I4", "Tothom", "Famílies"]   # "I4" inclou "I4B"
  carta_filtrada: true
  setmanal:
    enabled: true
    dia: 1        # 1=dilluns … 7=diumenge
    hora: "08:00"
```

---

## 5. Provar

Primer **sense enviar res** (només registra als logs):

```bash
DRY_RUN=1 python -m src.main --once
```

Si tot és correcte, arrenca de veritat:

```bash
# local
python -m src.main

# o amb Docker
docker compose up -d --build
docker compose logs -f
```

La **primera execució** només desa la línia base (no publica l'històric). A
partir d'aquí, publicarà les novetats que detecti.

---

## 6. Checklist de seguretat

- [ ] El bot és **administrador** del grup.
- [ ] **Només els administradors** poden enviar missatges.
- [ ] El grup és **privat** (invitació / sol·licitud d'unió).
- [ ] El **token** només és a `.env` (mai al repositori).
- [ ] `.env`, `config.yaml` i `state/` estan al `.gitignore`.
- [ ] (Opcional) «Aprovar membres nous» activat.

---

## Adaptar-ho a una altra escola

El codi no té res específic d'un centre. Per apuntar-lo a una altra escola,
canvia només `config.yaml`:

```yaml
site:
  base_url: "https://agora.xtec.cat/ALTRACENTRE"
  homepage: "https://agora.xtec.cat/ALTRACENTRE/"
  feed: "https://agora.xtec.cat/ALTRACENTRE/feed/"
  calendari_page: "https://agora.xtec.cat/ALTRACENTRE/lescola/calendari-del-curs/"
rss:
  include_categories: ["I4", "Portada", "General"]   # els cursos i etiquetes del centre
carta:
  link_text_markers: ["carta del mes"]
  fallback_href_contains: ["carta-mes"]
```

Els textos dels missatges es poden adaptar a `src/messages.py` i, sobretot,
traduir-se als catàlegs `src/i18n/*.json` (vegeu «Idioma dels missatges»).

---

## Problemes comuns

| Símptoma | Causa probable / solució |
|----------|--------------------------|
| `getUpdates` buit | No has enviat missatge després d'afegir el bot, o hi ha un webhook configurat |
| `403` en publicar | El bot no és admin o no té permís «Enviar missatges» |
| `message thread not found` | `message_thread_id` incorrecte per a aquell topic |
| No trobo «Només administradors» | En grups sol ser un **interruptor** «Enviar missatges» que has de **desactivar** (no un desplegable) |
| El bot no pot crear topics | Fes-lo admin amb el permís **Gestionar temes** |
| No publica res | Primera execució (només línia base) o `DRY_RUN=1` actiu |
| Avisos duplicats | `state/` no persisteix entre reinicis (revisa el volum) |
