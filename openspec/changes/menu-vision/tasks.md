# Tasks — menu-vision

## 1. Correccions deterministes de la ruta de texte

- [x] 1.1 Fer simètrics els límits de columna a `cell_words` (dilluns → 0,
      divendres → ample de pàgina) i verificar-ho amb un test nou que reprodueix
      el cas «LLUÇ» (cel·la de dilluns amb paraula que comença abans del límit).
      *Verificació: `python -m pytest -q -k lluc` passa.*
- [x] 1.2 Corregir el càlcul de la setmana parcial (`_monday_day`/`_resolve_monday`
      amb dilluns ≤ 0) per resoldre-la amb el mes anterior, i verificar-ho amb un
      test de la primera fila d'octubre (dies 1 i 2 a dijous/divendres).
      *Verificació: `python -m pytest -q -k setmana` passa.*

## 2. Mòdul de visió (`src/menu_vision.py`)

- [x] 2.1 Implementar renderitzat i retall de pàgina/cel·la amb `pypdfium2`
      (píndola i caixes de cel·la per geometria: `cell_grid`, `variant_pill`).
      *Verificació: tests de geometria sobre els 2 fixtures (5 columnes, files
      i píndola a les pàgines de calendari; pàgines sense píndola descartades).*
- [x] 2.2 Implementar el client d'Ollama (httpx, timeout configurable,
      1 reintent, `temperature: 0`, `num_predict` 2400 (cel·la) / 1600 (segell)) que **llança error**
      quan `content` és buit o no és JSON interpretable.
      *Verificació: tests amb `httpx.MockTransport` per a èxit, resposta
      buida, JSON invàlid, error HTTP i timeout (5 tests).*
- [x] 2.3 Implementar la validació d'extracció (dia imprès ∈ {D−1, D, D+1}
      dins del mes, `coerce_blocks` + `validate_blocks`: 1..8 blocs, ≤8 línia
      ≤80 caràcters, alfabètic) sobre el prompt final `{dia, blocs}` (sense
      traducció `linies → blocs`).
      *Verificació: tests de validació amb dia correcte, errata ±1, dia fora
      de rang (±7) i estructures fora de rang.*
- [x] 2.4 Implementar l'extracció de cel·la amb anclatge per candidats de
      dilluns del calendari (fins a `MAX_CELL_CALLS` candidats i descarta els
      que no validin).
      *Verificació: tests amb motor fals (fila correcta en 1 crida, fila
      equivocada → 2a candidata, cap vàlida → `VisionError`, cel·la buida →
      `None`, fallada del motor → propaga).*
- [x] 2.5 Implementar la detecció de variant pel segell (marcadors
      configurables, fallback a l'índex `page:` només amb rejilla present) i el
      mapa `variant → pàgina` memoritzat per URL de PDF a l'estat.
      *Verificació: tests amb PDF d'octubre (pàgines 0 i 3 detectades, p1/p2
      descartades, p4 aturada aviat) i fallback a `page:` sense marcadors.*

## 3. Configuració

- [x] 3.1 Afegir `menu.vision` (`enabled`, `url`, `model`, `timeout_s`,
      `markers`) a `src/config.py`, `config.yaml.example` i `config.yaml`, amb
      valors per defecte i validació.
      *Verificació: tests de càrrega de configuració (secció absent = per
      defecte, secció buida = defaults, valors invàlidors = `ConfigError`).*

## 4. Integració

- [x] 4.1 Connectar la ruta de visió a `parse_menu_pdf` quan no hi ha capa de
      texte (o no es reconstrueix la rejilla), mantenint el contracte de
      sortida (`list[blocks] | None` o `VisionError`).
      *Verificació: tests que amb el PDF d'octubre i un motor fals es publiquen
      els plats del 8 d'octubre, que amb el de setembre no es fa cap crida i
      que sense visió el resultat és `None` resolt.*
- [x] 4.2 A `menu_service.py`, distingir *fallada de motor* (`except
      VisionError` → no marcar `menu_posted`, `log.error`, reintent al proper
      cicle) de *dia sense cel·la* (resolt sense missatge).
      *Verificació: tests del servei amb motor que falla → la data queda
      pendent i es publica al cicle següent; cel·la buida → resolta.*
- [x] 4.3 Memoritzar el mapa variant→pàgina a `state/state.json` clau per URL
      del PDF i invalidar-lo quan canvia l'URL.
      *Verificació: tests d'estat (round-trip) i de servei (la memòria és el
      dict de l'estat, compartit per variants, i es poda l'URL antiga).*

## 5. Proves completes

- [x] 5.1 Tests extrems: resposta buida del model, dia no interpretat, 0 o
      més de 8 blocs/línies, línia de 200 caràcters, caràcters de control.
      *Verificació: `python -m pytest -q` complet verd (242 tests).*

## 6. Documentació

- [x] 6.1 `docs/transparencia.md` ja descriu «IA local i privada»; actualitzar
      `README.md`, `docs/features-roadmap.md` i els dissenys previs que declaren
      «no OCR ni IA» (`menu-dia/design.md`, `afa-elisabadia-avisos/design.md`)
      perquè apuntin a aquest canvi.
      *Verificació: `grep -ri "sense IA\|Descartat: OCR" docs/ README.md
      openspec/changes/*/design.md` només retorna referències intencionades
      (fase A d'avisos, cartes de fase B i el mateix canvi menu-vision).*

## 7. Verificació amb el PDF real

- [x] 7.1 Dry-run contra el PDF d'octubre real (basal i sense porc, dies
      7–10) i comparar la sortida amb una lectura manual dels retalls.
      *Verificació: 8/8 casos resolts — dies 7, 8 i 9 coincideixen amb els
      retalls (`/tmp/opencode/menu_dryrun/cell_0*.png`), dissabte 10 → `None`
      resolt, pàgines detectades `{'basal': 0, 'sense_porc': 3}` (ignora
      l'índex configurat 1). Va destapar el trunca JSON per *thinking*
      (`num_predict` 900 → 2400/1600, D6).*
- [x] 7.2 Reconstruir la imatge Docker, reiniciar `avisos-afa-telegram`
      (confirmant-ho amb l'usuari) i observar el slot de les 19:00.
      *Verificació: `docker compose build && up -d` fet amb confirmació
      (07/10 17:35); dins el contenidor: `menu.vision` activat, `pypdfium2`
      instal·lat i Ollama accessible (200, `qwen3-vl:2b`). Arrancada neta,
      sense errors. Observació final: el slot de les 19:00 d'aquesta nit
      publica el menú del 8/10 als dos topics.*
