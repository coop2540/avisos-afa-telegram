# menu-vision

## Why

El PDF mensual d'octubre publicat pel centre **no té capa de texte**
(`ilovepdf_merged-..._removed.pdf`, 0 caràcters): `extract_words()` retorna
buit, el servei no ha publicat cap menú des de l'1 d'octubre i la variant
`sense_porc` apunta a la pàgina equivocada (pàgina 1 = infografia, no el
calendari). A més, hi ha dos bugs deterministes que alteren el menú publicat
quan sí que hi ha texte: es retallen paraules a la columna de dilluns i la
primera setmana del mes es descarta si l'1 cau de dimecres a divendres.

## What Changes

- Extracció del menú per **visió local** (Ollama + model multimodal al propi
  servidor, sense núvol) quan el PDF no té capa de texte: es localitzen les
  cel·les per geometria i es llegeix cada cel·la amb transcripció literal.
- **Detecció de la pàgina de cada variant pel segell** del capçalera
  (`BASAL` / `NO PORC`), substituint l'índex de pàgina fix de la configuració
  (`page: 0/1`), que canvia cada mes.
- **Validació estricta** de tota extracció (dia imprès proper al dia real,
  nombre de línies i longituds raonables); si no valida → **no publicar** i
  registre d'error, mai inventar plats.
- Correcció dels dos bugs deterministes del parser de texte: límits de columna
  simètrics a `cell_words` (no retallar «LLUÇ») i resolució de la setmana
  parcial amb lunes ≤ 0.
- Distingir *dia sense cel·la* (resolt, sense missatge) de *fallada del motor*
  (pendent: no es marca com publicat, es reintenta al proper cicle).
- Nova configuració `menu.vision` (URL, model, temps límit) i actualització de
  `docs/transparencia.md` (IA local i privada, no «sense IA»).

## Capabilities

### New Capabilities
- `daily-menu`: extracció del menú del menjador des de PDFs **sense capa de
  texte** mitjançant visió local, amb detecció de variant pel segell i
  validació estricta abans de publicar.

## Impact

- **Codi**: `src/parse_menu.py` (bugs + detecció de pàgina), nou
  `src/menu_vision.py` (render, geometria, client Ollama, validació),
  `src/menu_service.py` (fallo de motor ≠ dia sense cel·la), `src/config.py`
  (secció `menu.vision`).
- **Dependències**: `pypdfium2` (ja present com a dependent de `pdfplumber`);
  servidor Ollama accessibles des del contenidor del servei (provar
  `http://192.168.0.18:11434`). Cap dependència nova a `requirements.txt`
  llevat de les proves (`respx` ja hi és).
- **Desplegament**: `compose/config` amb URL i model d'Ollama; el servei passa
  a dependre d'Ollama **només** per als PDFs sense texte.
- **Docs**: `docs/transparencia.md`, `README.md`,
  `docs/features-roadmap.md`, i els dissenys previs que declaraven «no OCR ni
  IA» (`openspec/changes/menu-dia/design.md`,
  `openspec/changes/afa-elisabadia-avisos/design.md`).
- **Comportament observable**: missatges de menú idèntics en contingut als
  d'ara (plats literals, sense inventar); si el motor cau, aquell dia no es
  publica el menú i queda constància al registre.
