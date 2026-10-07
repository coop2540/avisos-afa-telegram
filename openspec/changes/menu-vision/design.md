# Design — menu-vision

## Context

Veure `proposal.md` (Why). Punts de context tècnic que condicionen el disseny:

- El PDF d'octubre és **imatge pura** (0 caràcters; `pdftotext` buit), però
  **manté la geometria**: caixes de cel·la ~98×108 pt i segells de data de
  18×18 pt dibuixats com a *curves*, amb posicions idèntiques a les del PDF de
  setembre (que sí té texte). Això permet localitzar cel·les **sense OCR**.
- El PDF d'octubre té 5 pàgines: 0 = calendari + segell `BASAL`, 1 =
  infografia, 2 = propostes de sopars, 3 = calendari + `NO PORC`, 4 =
  calendari + `AL·LÈRGIA A L'OU` (no configurable). La config actual
  (`page: 0/1`) apuntava la variant `sense_porc` a la infografia.
- **Spike validat** (Ollama `qwen3-vl:2b`, servidor local, des del propi
  contenidor del servei via `http://192.168.0.18:11434`):
  - Recorte de cel·la → `{dia, blocs}`: **estable**, dia imprès correcte
    (reprodueix l'errata coneguda «24 imprès com a 25»); cel·la buida →
    `{dia: null, blocs: []}`. El prompt final demana `blocs` (agrupació de
    línies visuals ja feta pel model, 6/6 estable en els spikes) en lloc del
    `linies` pla del primer esborrany.
  - Banda de fila sencera i pàgina completa → el model **no acaba mai**
    (`done_reason=length`, `content=''`); passa amb `qwen3-vl:2b`,
    `qwen3.5:9b` i `minicpm-v`, amb i sense `think:false`/`format:json`.
    Descartat com a estratègia.
  - Segell de variante (retall geòmetric `x0≈291, top≈58`) → `BASAL`,
    `NO PORC`, `AL·LÈRGIA A L'OU`; cal `num_predict ≥ 1600`.
- Els dissenys previs (`menu-dia`, `afa-elisabadia-avisos`) declaraven
  «Descartat: OCR/IA». Aquest canvi **reverteix** aquesta decisió sota les
  condicions de D2.

## Goals / Non-Goals

**Goals:**
- Publicar el menú correcte cada dia, també amb PDFs sense capa de texte.
- Mai publicar contingut inventat, truncat o de la variant equivocada.
- Mantinguda la ruta determinista (texte) com a preferida quan existeix.
- Dependència d'Ollama **només** per als PDFs sense texte, amb degradació
  controlada (no publicar + registre).

**Non-Goals:**
- Resumir, traduir ni reescriure el menú (la transcripció és literal).
- Llegir la pàgina de «Propostes de sopars» ni la variant d'al·lèrgies
  (configurables endavant, fora d'aquest canvi).
- Garantir disponibilitat d'Ollama (sistema extern); es gestiona per error.
- OCR alternatiu (Tesseract): es podria afegir després rere la mateixa
  interfície, però no forma part d'aquest canvi.

## Decisions

**D1 — La visió només quan la ruta de texte falla.**
`parse_menu_pdf` intenta primer l'extracció determinista actual; si no hi ha
capes de texte ni capçaleres de columna, passa al mòdul de visió. Alternativa
descartada: visió sempre (més lent, menys determinista, perjudicaria el cas
bo).

**D2 — Reversió controlada de «sense IA».**
Es permet IA **exclusivament local i privada** (Ollama al mateix servidor, cap
crida a la xarxa pública) i **exclusivament com a transcripció**: la IA no
calcula dates, no completa frases, no inventa. Tot el que no superi la
validació es descarta. `docs/transparencia.md` es documenta com «IA local i
privada» (mai «sense IA»).

**D3 — Localització de cel·les per geometria, no per OCR.**
Clustering de les *curves* de mida ~98×110 → columnes (x) i files (y).
Alternatives: Tesseract (dependent nova, precisió desconeguda en aquesta
tipografia) i detectar capçaleres de texte (impossible sense capa de texte).

**D4 — Anclatge de setmanes pel calendari + validació del dia imprès.**
Sense poder llegir les dates en massa (D4a), es generen els candidats de
*dilluns de fila 0* a partir del mes/demana objectiu (com a màxim 2–3), es
prova la cel·la i es **valida el dia imprès** (`dia ∈ {D−1, D, D+1}`: tolera
l'errata de l'origen, detecta una fila equivocada). Si cap candidat valida →
no publicar.
- *D4a (descartat)*: banda de fila → array de dates. Provat: el model no
  convergeix (bucle de raonament fins a `num_predict` i contingut buit) en
  qualsevol model o prompt provats.
- *D4b*: l'ordre de proves és de més probable a menys (fila 0 = setmana de
  l'1 del mes primer), de manera normalment en 1–2 crides es resol.

**D5 — Variant pel segell del capçalera.**
Cerca de la píndola farcida a la part superior (geometria: `top < 150`,
`w ∈ [30,130]`, `h ∈ [8,25]`, `x0 ≈ centre`) → retall → crida de visió amb
`num_predict ≥ 1600` → text contra els marcadors de la variant
(`basal: ["BASAL"]`, `sense_porc: ["NO PORC", "SENSE PORC"]`, configurables).
El `page:` de la config queda com a *pista* de fallback només si el segell no
es pot llegir **i** aquella pàgina té rejilla. El mapa `variant → pàgina` es
desa a `state.json` clau per URL del PDF (canvia cada mes → es recalcula).

**D6 — Model i paràmetres.**
`qwen3-vl:2b` (provat, ~4–12 s/crida), `temperature: 0`,
`num_predict`: 2400 (cel·la) / 1600 (segell). El model **raona abans de
respondre** i `think:false` no el desactiva (provat: el *thinking* s'emporta
tots els tokens i el JSON surt truncat amb `done_reason=length`), per això el
sostre és alt: només és un límit, si el model acaba abans no costaria més.
Model i URL configurable → es podrà canviar a `qwen3.5:9b` sense tocar codi.
`think:false` i `format:json` es van provar i **no** eviten el col·lapse dels
prompts amplis → els prompts són estrets i el `content` truncat o buit es
tracta com a error, no com a resposta vàlida.

**D7 — Mapa de sortida.**
El prompt demana directament `{dia, blocs}`, amb `blocs` = llistes de línies
visuals (un bloc per plat/parell), equivalent als *blocs* de la ruta de texte:
no cal cap traducció intermèdia. Validació d'estructura: 1..8 blocs, 1..8
línies en total, ≤80 caràcters per línia, sense caràcters de control i amb
contingut alfabètic.

**D8 — Semàntica d'error.**
El contracte és `blocks | None` o excepció `VisionError`. `menu_service`
distingueix: dia *resolt buit* (`None`, no es reintenta) de *fallada de
motor* (`VisionError`: no es marca `menu_posted` → reintent al proper cicle,
amb `log.error`). Timeout 60 s per crida, 1 reintento.

**D9 — Injecció per proves.**
El client d'Ollama és una funció substituïble (paràmetre/opció), de manera que
els tests unitaris fan servir un motor fals i els d'integració `respx`; cap
test depèn d'un Ollama real.

## Risks / Trade-offs

- [El model no convergeix (`content=''`)] → es tracta com a error: 1
  reintents i, si persisteix, no publicar. Els prompts són deliberadament
  estrets (tarea única) per minimitzar-ho (evidència del spike).
- [Al·lucinació del model] → validació del dia imprès + estructura; la
  transcripció literal es publica tal com ve, sense processar-la.
- [Ollama apagat a les 19:00] → dia sense menú + registre (decisió de
  l'usuari). Es documenta la dependència a `docs/transparencia.md`.
- [Canvi de layout del PDF] → la detecció és geomètrica (clustering de
  mides), no de coordenades fixes; si no hi ha ni texte ni caixes → error i no
  publicar.
- [Cost/latència] → 1–3 crides per variant/ dia (~5–30 s) a l'hora de
  publicació; el mapa variant→pàgina es memoreja per URL.
- [Duplicat de la capacitat `daily-menu` amb el canvi `menu-dia`] → tots dos
  deltas són ADDED amb requisits de títol diferent; l'arxiu els concatenarà.
  Es revisa l'ordre d'arxiu quan es tanqui cap dels dos.

## Migration Plan

1. Implementar amb tests (motor fals + `respx`) sense tocar el desplegament.
2. Afegir `menu.vision` a `config.yaml` (i `.example`) i publicar.
3. Reconstruir la imatge Docker i reiniciar `avisos-afa-telegram` (confirmant
   amb l'usuari; contenidor local, no servidor de producció extern).
4. Dry-run contra el PDF real d'octubre (basal i sense porc) i comparar amb
   lectura manual; observar el slot de les 19:00.
5. *Rollback*: `menu.vision.enabled: false` → torna a la ruta de sola
   extracció de texte (com avui: els PDFs sense texte no es publiquen) sense
   desfer el codi.

## Open Questions

Cap: queda recollit a la proposta que, si el motor falla, **no es publica** i
només es registra l'error (decisió explícita de l'usuari).
