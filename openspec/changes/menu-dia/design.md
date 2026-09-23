# Design: menu-dia

## Context

Veure `proposal.md` — Why. En resum: el menú del menjador ja existeix com a PDF mensual a la pàgina del menjador de l'escola, però no arriba a les famílies en un format consultable ni al moment útil (la nit abans de preparar el dia). El servei d'avisos ja té fetchers, dedup, topics, agenda setmanal programada i sortida Telegram; aquest change afegeix una font nova (PDF del menjador) i un nou slot de publicació (dia abans, 19:00) reutilitzant el mateix patró.

Fonts reals verificades durant l'exploració:

- Pàgina del menjador: `agora.xtec.cat/.../serveis/menjador-escolar/` amb 5 PDFs (menú basal, sense porc via pàgines 1/2 del mateix `Basal-escolar_merged.pdf`, funcionament, preus, què cal portar). El PDF del menú canvia d'URL cada mes (ex. `/2026/09/Basal-escolar_merged.pdf`).
- PDF del menú: 3 pàgines (1 BASAL, 2 SENSE PORC, 3 sopars — sopars fora d'abast). Text extraïble amb `pdfplumber` (sense OCR), però **0 taules**: és una rejilla de calendari Dilluns–Divendres amb dates a files. `extract_text()` barreja columnes; `extract_words()` amb coordenades sí permet reconstruir les columnes (provat amb el menú real de setembre 2026).
- Errata real detectada: el dijous 24 de setembre està imprès com a «25» (dues dates «25» a la mateixa fila). Per tant, la data objectiu NO es pot derivar del número imprès sol.
- Pàgina de calendari: text estructurat amb rangs (vacances «del 21 de desembre al 7 de gener», festes de lliure disposició, festes locals, jornada intensiva). `fetch_calendari.py` actualment només n'extreu títols de secció i un hash — no pas dates normalitzades per a \"és dia lectiu?\".

Restriccions del servei existent (vegeu `afa-elisabadia-avisos/design.md`): procés únic Python, sondeig adaptatiu base ~60 min, estat JSON atòmic, secrets fora del repo, català per defecte amb i18n per catàlegs, filtre per topics (sense registre de famílies), web del centre només en lectura amb UA identificable.

## Goals / Non-Goals

**Goals:**

- Publicar cada dia laborable, a les 19:00 del dia anterior, el menú de demà als dos topics (basal i sense porc), cadascú amb la seva variant.
- Resoldre dinàmicament l'URL del PDF del menjador (sense hardcodejar, canvia cada mes).
- Extreure la cel·la del dia correcte tolerànt a errata de data impresa i a variació de layout entre mesos.
- Saltar caps de setmana i dies no lectius segons el calendari del centre (excepte jornada intensiva, que sí és lectiu).
- Missatge anunciat (pin) a cada topic amb l'enllaç al PDF vigent, refrescat quan canvia l'URL.
- Dedup per data de menú i variant (reinici no duplica; fallida parcial reintenta només la variant pendent).
- Configuració flexible: variants, hora, marcadors d'enllaç, topics per variant.

**Non-Goals:**

- Sopars (pàgina 3 del PDF) — fora d'\"avui/demà dinem\".
- Post de 7:45 \"Avui dinem\" (es descarta a favor de \"Demà dinem\" a les 19:00; vegeu D3).
- OCR ni inferència amb IA sobre el PDF (només `pdfplumber` + coordenades).
- Edició dels missatges diaris ja publicats (només es refresca el pin quan cal).
- Creació/edició de topics via API (es creen a mà; el servei només hi escriu).
- Creuar el menú amb preferències al·lèrgies o dietes per família (filtre = topic, no registre).

## Decisions

### D1 — Resolució de l'URL del PDF: pàgina del menjador + marcador d'href

- **Tria:** fetcher nou tipus `fetch_carta`: GET de la pàgina `/serveis/menjador-escolar/`, primer `<a href>` que contingui els fragments configurats (`basal`, `menu`) i acabi en `.pdf`, excloent la carta i el calendari. Si no, fallback: primer `.pdf` de la pàgina que no sigui carta/calendari.
- **Per què:** els àncores del menú no tenen text (són imatges de previsualització); per tant cal cercar per href, no per text d'enllaç. Els marcadors van a config perquè una altra escola pugui ajustar-los. La carta del menjador i el calendari també són `.pdf` a la mateixa pàgina → cal l'exclusió.
- **Descartat:** hardcodejar `Basal-escolar_merged.pdf` (canvia cada mes); parsejar per `alt` de la imatge (buit a la font real).

### D2 — Parser del PDF: `extract_words` + reconstrucció de rejilla per coordenades

- **Tria:** per cada pàgina de variant (1=basal, 2=sense porc): `extract_words()`; fronteres de columna a partir de la capçalera `DILLUNS DIMARTS DIMECRES DIJOUS DIVENDRES` (mig entre `x1` d'un i `x0` del següent); files de setmana agrupant les dates per `top` amb tolerància (~25px). Cel·la del dia = paraules dins (columna, franja de fila) ordenades per `(top, x0)` i agrupades en línies. Mes/any del títol (`SETEMBRE`) + any de l'URL (`/2026/09/`). Data objectiu resolta pel **dilluns de la fila + índex de columna** (0–4), NO pel número imprès.
- **Per què:** `extract_text()` barreja columnes (provat: la pàgina 2 surt encabalgada); `extract_tables()` retorna 0 taules (la rejilla no té línies de taula que pdfplumber detecti). Les coordenades sí funcionen — verificat amb el PDF real. L'ancla pel dilluns tolera l'errata 24→25 detectada. Sense categories inventades (no sabem si la línia 2 és \"segon\" o \"guarnició\"): es llisen tal qual.
- **Descartat:** OCR (hi ha text de veritat); regex sobre `extract_text()` (fràgil davant el desordre de columnes); confiar en el número de dia imprès (errata real al PDF); PyMuPDF (dependència nova quan `pdfplumber` ja serveix).

### D3 — Slot diari: 19:00 \"Demà dinem\" (no 7:45 \"Avui dinem\")

- **Tria:** publicar el dia anterior a les 19:00 amb el títol \"Demà dinem …\". Lògica paral·lela a `should_post_weekly`: calcular la data objectiu (demà, o el proper dia lectiu si demà no ho és — vegeu D5), i publicar si `ara >= slot` i `menu_posted[variant] != data_objectiu`. El slot de 19:00 amb el sondeig base de 60 min pot arribar entre 19:00 i ~20:00 — acceptable (finestra de preparació de la nit). NO es toca el scheduler per arribar quirúrgicament a les 19:00 en aquest change.
- **Per què:** la finestra de 19:00–20:00 és útil per preparar sopar/motxilla/xerrada del dia següent i és tolerant a la deriva del sondeig. A les 7:45 la deriva (fins a ~8:45) trencaria l'ús de drop-off a les 8:00 i requeriria \"slot-aware sleep\" al scheduler. El topic ja es va renombrar a \"Demà dinem …\", coherent amb aquesta decisió.
- **Descartat:** 7:45 \"Avui dinem\" (deriva del sondeig vs drop-off a les 8:00; només confirma el que ja passa avui, no permet preparar-se); els dos slots junts (duplicaria notificacions); cron extern (el projecte ja va decidir loop únic a `afa-elisabadia-avisos` D2).
- **Variante futura (no en aquest change):** si es vol puntualitat quirúrgica, afegir \"slot-aware sleep\" al `next_interval_minutes` (cap al proper slot diari/setmanal) — tocaria `scheduler.py` però no canvia aquest contracte.

### D4 — Estat: dedup per (data de menú, variant), no per timestamp

- **Tria:** `state.menu_posted = {"basal": "2026-09-24", "sense_porc": "2026-09-24"}` (data ISO de la **cel·la**, no del moment d'enviament). Un missatge es marca com a publicat **només després de `send_message` OK** per a aquella variant. Fallida parcial → l'altra variant ja marcada no es torna a enviar.
- **Per què:** idempotent entre reinicis; permet retry net per variant sense duplicar la que ja ha sortit; la data de la cel·la és la clau natural (si el servei cau i torna el mateix vespre, no reenvia).
- **Descartat:** un sol booleà `menu_posted_today` (no distingeix variants ni tolera fallida parcial); `last_menu_post` amb timestamp de publicació (com l'agenda setmanal) — amb dues variants i retry seria ambigu quina data és la rellevant.

### D5 — Dies lectius: doble candado (calendari + cel·la al PDF)

- **Tria:** (1) Parser nous sobre el text de la pàgina de calendari → set `dies_no_lectius` (rangos de vacances, festes de lliure disposició, festes locals, dies fora d'inici/fi de curs, caps de setmana). **Jornada intensiva NO entra** al set. Regla d'any creuat: si `end < start` en un rang, l'any de `end` és `start+1` (tolla l'errata de la font \"al 7 de gener de 2026\" després de \"21 de desembre de 2026\"). (2) Publicar **només si** demà és lectiu **i** el PDF té cel·la per a demà. Si el calendari diu lectiu però no hi ha cel·la (ex. festa que el càtering sí surt, o PDF desactualitzat) → no es publica (candado 2); si el calendari falla, es pot caure a \"cel·la existeix\" com a mínim (log warning) — decisió d'implementació a tasks, el contracte de spec exigeix no publicar en festa/cap de setmana clars.
- **Per què:** el càtering i el centre no sempre coincideixen (el PDF pot tenir cel·la en un dia festiu o saltar-se'n un). Doble candado = el menú publicat és actionable (hi ha escola) i el pin/diari no s'omple de dies buits. Reutilitza la font de calendari que el servei ja consulta.
- **Descartat:** només \"cel·la existeix al PDF\" (publicaria en festes si el càtering no les treu del PDF); només calendari (podria demanar una cel·la buida i treure un missatge buit); codificar la llista de festes a `config.yaml` (es desincronitza cada curs).

### D6 — Pin: `pinChatMessage` + refresc quan canvia l'URL

- **Tria:** missatge nou \"Menú del mes (PDF) + enllaç\" enviat al topic i passat per `pinChatMessage` (bot admin). Estat `menu_pin_message_id` per variant topic (opcional: per poder-hi fer `unpin` si cal; com a mínim es guarda `menu_pdf_url` per detectar canvi). Quan l'URL resolta canvia → nou missatge + pin als dos topics. Els missatges diaris **no** porten enllaç.
- **Per què:** l'URL del PDF canvia cada mes; un pin estàtic caduca. Pin a cada topic = cada comunitat (basal / sense porc) veu la referència seva. Missatge nou (no `editMessageText`) = més senzill i el pin anterior queda desplaçat (acceptable; unpin explícit opcional).
- **Descartat:** enllaç a cada missatge diari (soroll; l'usuari ho va decidir així); `editMessageText` sobre el pin (caldria gestionar message_id i edicions fallides); pin global al topic general (fora del context de cada variant).

### D7 — Variants com a llista de config, no com a codi dur

- **Tria:** `menu.variants: [{id: basal, page: 1, topic: menu_basal, enabled: true}, {id: sense_porc, page: 2, topic: menu_sense_porc, enabled: true}]`. El cicle itera variants actives; `page` és l'índex de pàgina del PDF (1-based o 0-based — decidir a implementació i documentar a config; la font actual és 1=basal, 2=sense porc). `topic` és la clau de `telegram.topics` (fallback a `default` si és `null`, tal com ja fa `thread_id_for`).
- **Per què:** una altra escola amb una variant més (p. ex. \"sense lactosa\") només toca config si el PDF té la pàgina. Els dos topics ja existeixen (thread 24 i 27). Inclusiu sense bifurcar el codi.
- **Descartat:** dos blocs de config fixos `basal:`/`sense_porc:` (no escala, dupliquen la lògica); un sol topic amb les dues variants en un missatge (contradiu \"cada família silencia el que no li toca\" i faria soroll a la majoria basal).

### D8 — Arquitectura de mòduls (orientativa)

```
src/
  fetch_menjador.py   # pàgina HTML → URL PDF menú (marcadors href)
  parse_menu.py       # bytes PDF + data + variant → list[str] plats | None
  menu_calendar.py    # text calendari → set[date] dies no lectius (+ helpers data objectiu)
  (o ampliació de fetch_calendari.py per extreure dates, si encaixa millor)
  messages.py         # + menu_dema_message(...), menu_pin_message(...)
  telegram_out.py     # + pin_message(message_id)
  state.py            # + menu_posted, menu_pdf_url, (menu_pin_ids)
  config.py           # + MenuConfig, MenuVariantConfig
  main.py             # pas dins run_cycle: resoldre PDF → cel·la demà → publicar/pin
config.yaml           # secció menu + topics menu_basal/menu_sense_porc
```

## Risks / Trade-offs

- **[Canvi de layout del PDF entre mesos (setembre vs octubre)]** → fixtures de com a mínim 2 mesos reals; si el parse falla, fallback a "no publicar el diari" + pin (que sí té l'enllaç); alerta per log. El contracte de spec només exigeix no inventar plats. **RISC OBERT EN DESPLEGAR:** a data de 23/09/2026 el centre només ha publicat el PDF de setembre; no s'ha pogut verificar un segon mes. Cal revisar el primer PDF d'octubre que publiqui el centre (la dedup i el fallback fan que un parse fallit no publiqui plats inventats).
- **[Errata de data impresa (ja detectada: 24→25)]** → D2 ancla pel dilluns de la fila + índex de columna; test explícit amb l'errata real de setembre.
- **[Pàgina 2 (sense porc) amb text més solapat en `extract_text`]** → D2 ja no usa `extract_text` per a cel·les; validar amb fixture de la pàgina 2 real. Si surt buida, no es publica (pin cobreix).
- **[Calendari amb errata d'any en rang (font actual: \"gener de 2026\" després de desembre 2026)]** → regla `end < start → end.year += 1`; test amb el rang de Nadal real.
- **[Doble candado massa estricte: festa que el càtering sí surt al PDF]** → es prefereix no publicar en dia festiu (candado 2); si el centre publica menú en un dia no lectiu real, es pot afegir \"override per cel·la\" després sense tocar specs (seria un requisit afegit).
- **[Deriva 19:00→20:00 pel sondeig base de 60 min]** → acceptable per a l'ús de \"preparació de la nit\"; documentat a D3. Si demanen puntualitat, futur \"slot-aware sleep\" al scheduler.
- **[Fallida de Telegram en una de les dues variants]** → D4 marca per variant després d'OK; retry neta. Risc baix: 2 `sendMessage` + pin en el mateix cicle, dins el backoff existent.
- **[El bot no té permís de pin al topic]** → task de verificació al desplegar; si falla, log i el missatge diari sense enllaç continua sent correcte (l'enllaç es pot citar al pin manualment com a pla B).
- **[El pin s'acumula un de nou cada mes sense treure l'antic]** → Telegram manté N pins per topic (els més recents a dalt); acceptat; si cal, futur `unpinChatMessage` del message_id desat.

## Migration Plan

1. Implementar amb fixtures locals (PDF real de setembre 2026 ja descarregat durant l'exploració) i tests de rellotge simulat — sense tocar el desplegament.
2. `openspec validate menu-dia` en blau + `pytest` sencer.
3. Activar a `config.yaml` local: secció `menu.enabled: true`, `hora: \"19:00\"`, variants amb `topic: menu_basal` / `menu_sense_porc`, `telegram.topics.menu_basal: 24`, `menu_sense_porc: 27`.
4. Prova manual: un cicle `--once` forçat (o esperar el slot) → verificar missatge al topic 24 i 27 correctes, pin present, URL del pin = PDF actual.
5. Verificar salt: simular \"demà = dissabte\" (o esperar divendres) → cap missatge.
6. Reiniciar el contenedor → verificar que `menu_posted` sobreviu i no hi ha duplicat.
7. **Rollback:** `menu.enabled: false` + restart (el servei torna al comportament anterior; els pins es poden treure a mà si cal). Cap efecte a la web del centre.

## Open Questions

- Cap que canviï specs, abast ni desglossat de tasks. Detalls resolts o diferibles a implementació: (a) 0-based vs 1-based per `page` a config (documentar a `config.yaml.example`); (b) si el calendari falla, es cau a \"només cel·la\" amb warning o es bloqueja tot (recomanat: cel·la + warning per no perdre dies bons per una caiguda puntual de la pàgina de calendari, sempre que demà no sigui cap de setmana segons rellotge); (c) unpin explícit del pin vell o deixar-lo desplaçat (recomanat: deixar-lo, menys crides).
