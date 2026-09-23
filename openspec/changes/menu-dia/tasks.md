# Tasks: menu-dia

## 1. Configuració i estat

- [x] 1.1 `config.py`: `MenuConfig` (enabled, hora, link_markers, fallback_href_excludes, variants amb id/page/topic/enabled) i `MenuVariant`; càrrega des de la secció `menu` de YAML amb defaults; verificar amb test de càrrega de l'exemple i d'un YAML sense secció `menu` (deshabilitat)
- [x] 1.2 `config.yaml.example`: secció `menu` documentada (enabled, hora `19:00`, variants basal/sense_porc, marcadors d'href) + `telegram.topics.menu_basal` / `menu_sense_porc`; verificar que l'exemple segueix carregant amb `load_config`
- [x] 1.3 `state.py`: camps `menu_pdf_url: str | None`, `menu_posted: dict[str, str]` (variant → data ISO), `menu_pin_ids: dict[str, int]`; round-trip càrrega/guardat; verificar test de persistència i compatibilitat amb un state vell (sense claus noves → defaults)

## 2. Fetch del PDF del menjador

- [x] 2.1 `fetch_menjador.py`: `resolve_menu_url(html, base_url, markers, excludes)` — primer `<a href>` `.pdf` que contingui un marker i no contingui cap exclude (carta, calendari); fallback primer `.pdf` no exclòs; verificar amb fixture HTML (cop de la pàgina real) i amb HTML sense cap PDF → None
- [x] 2.2 `fetch_menu_url(page, ...)` amb `fetch_text`; test amb HTML local (sense xarxa); verificar que una URL relativa es resol contra `base_url`

## 3. Parser de cel·la (coordenades)

- [x] 3.1 Guardar fixture: PDF real del menjador de setembre 2026 a `tests/fixtures/menu_setembre_2026.pdf` (+ pàgina 2 si cal separada); verificar que el test carrega i té 3 pàgines
- [x] 3.2 `parse_menu.py`: `extract_words` → fronteres de columna per la capçalera `DILLUNS…DIVENDRES` i files de setmana agrupant dates per `top`; verificar test que les 5 columnes i les 4 files de setembre 2026 es reconstrueixen
- [x] 3.3 `cell_for_date(words_by_grid, target_date)` — resol data per dilluns de fila + índex de columna (ignorant número imprès); retorna línies de la cel·la; test amb errata real: demanar 2026-09-24 (dijous, imprès «25») → cel·la de dijous i NO la de divendres
- [x] 3.4 Variants per pàgina (page 1 basal, page 2 sense porc) i extracció de mes/any (títol + any de la ruta URL); test: 2026-09-23 basal → conté «CREMA DE CARBASSA»; sense porc → existeix cel·la o None net
- [x] 3.5 Fallback: cel·la buida / data fora de mes / PDF il·legible → None + log (mai excepció no controlada); test dels tres casos

## 4. Calendari de dies no lectius

- [x] 4.1 `menu_calendar.py` (o extensió de `fetch_calendari.py`): parsejar del text de la pàgina de calendari els rangs de vacances, festes de lliure disposició, festes locals i límits inici/fi de curs → `set[date]`; regla any creuat (`end < start` → any+1); verificar amb fixture del text real de calendari (rang nadal amb errata d'any)
- [x] 4.2 `is_school_day(d, festes, weekend=True)`: caps de setmana → False; jornada intensiva NO és festa; test: 2026-09-23 (dimecres) lectiu, 2026-09-26 (dissabte) no, 2026-11-02 (festiure) no, 2026-12-21 (intensiva) sí
- [x] 4.3 Integració: agafar el text de calendari amb el fetcher existent (cache al cicle o refetch); test d'integració que un cicle amb calendari festiu no publica

## 5. Slot diari i publicació

- [x] 5.1 `should_post_menu(now_local, cfg_menu, target_date, menu_posted, variant)`: True si `now >= target 19:00` i `menu_posted.get(variant) != target.isoformat()`; test amb rellotge simulat: abans de les 19:00 → False; a les 19:00 amb pendent → True; ja publicat → False
- [x] 5.2 Càlcul de data objectiu: demà local; si demà no és lectiu → None (no post); test divendres→dissabte = None, divendres→dilluns (si no hi ha festa) = dilluns quan demà dissabte no toca (el target és sempre demà, no \"proper dia lectiu\": divendres al vespre demà = dissabte → None). *Confirmar amb spec:* spec diu \"demà\" — divendres vespre no es publica per cap de setmana; dilluns es publica dimarts. Verificar amb tests dels tres dies
- [x] 5.3 `run_cycle` (o `maybe_publish_menu`): per variant activa → resoldre URL → parsejar cel·la demà → si OK i slot → `send_message` al topic de la variant → marcar `menu_posted[variant]` només si OK; fallida parcial no marca; test d'integració amb client Telegram mock (una OK, una KO → retry només la KO)

## 6. Pin del PDF vigent

- [x] 6.1 `telegram_out.py`: `pin_message(message_id)` (o `send_message` amb return del `message_id` + `pinChatMessage`); verificar amb dry_run/log i amb un enviament real a xat de proves
- [x] 6.2 Cicle: si `menu_pdf_url` resolt != `state.menu_pdf_url` → enviar missatge \"Menú del mes (PDF) + enllaç\" a cada topic de variant i pin; desar `menu_pdf_url` i `menu_pin_ids`; test: canvi d'URL → 2 missatges + 2 pins; URL igual → cap acció
- [x] 6.3 Missatge diari sense enllaç (només data + plats); test de format a `test_messages.py` (ca/es/en)

## 7. Missatges i18n

- [x] 7.1 Claus `menu.*` als catàlegs `ca`, `es`, `en` (títol \"Demà dinem …\", etiqueta variant, \"Menú del mes\", fallback sense cel·la si escau); test `translate` amb retrocés
- [x] 7.2 `menu_dema_message(plats, data, variant_label, lang)` i `menu_pin_message(url, lang)` a `messages.py`; tests de format HTML i escape

## 8. Orquestració i documentació

- [x] 8.1 Enganxar el pas de menú dins `run_cycle` després de l'agenda setmanal, tolerància a errors (fetch/parse fallit → log, resta del cicle continua); test: PDF caigut → cicle complet sense excepció
- [x] 8.2 README / `docs/guia-telegram.md` / `docs/features-roadmap.md`: documentar el topic de menú i la secció `menu`; verificar seccions presents
- [x] 8.3 Validació OpenSpec: `openspec validate menu-dia` en blau + `pytest` complet en blau

## 9. Desplegament (producció)

- [x] 9.1 Config local real: `menu.enabled: true`, `hora: "19:00"`, variants, `topics.menu_basal: 24`, `topics.menu_sense_porc: 27`; verificar càrrega sense error
- [x] 9.2 Reiniciar contenedor; verificar als logs que resol el PDF del menjador i que no publica fora de slot
- [x] 9.3 E2E: esperar un 19:00 (o forçar cicle amb data simulada en local) → verificar missatge \"Demà dinem\" al topic 24 (basal) i al 27 (sense porc) amb els plats reals del PDF, i pin amb l'enllaç vigent als dos topics
- [x] 9.4 Verificar salt: simular demà = dissabte (o esperar divendres) → cap missatge; reiniciar contenedor el mateix vespre → cap duplicat de `menu_posted`
