# daily-menu

## Purpose

Publicar el menú del menjador de l'endemà a les 19:00 als topics configurats (basal i sense porc), traient-lo del PDF mensual de la pàgina del menjador, i mantenir un missatge anunciat amb l'enllaç al PDF vigent.

## ADDED Requirements

### Requirement: Resolució dinàmica de l'enllaç del PDF del menjador
El sistema SHALL resoldre cicle rere cicle l'URL actual del PDF del menú del menjador a partir del HTML de la pàgina del menjador del centre (text o àncora «menjador» / fragments d'href configurats). MUST NO hardcodar l'URL del PDF, puix que canvia cada mes.

#### Scenario: Menú mensual nou publicat pel centre
- **WHEN** l'enllaç del menú a la pàgina del menjador canvia de destinació respecte a l'últim enllaç registrat
- **THEN** el sistema el considera el PDF vigent i el fa servir per extreure'n el menú

#### Scenario: Pàgina del menjador no accessible
- **WHEN** la pàgina del menjador no es pot obtenir (error HTTP, timeout, HTML buit)
- **THEN** el sistema registra l'error, manté l'últim enllaç conegut i reintenta al proper cicle sense publicar avisos falsos

### Requirement: Extracció del menú d'un dia concret
El sistema SHALL extreure del PDF del menjador els plats corresponents a una data concreta i a una variant concreta (p. ex. basal / sense porc), identificant la cel·la del dia dins la rejilla de la setmana i la columna del dia de la setmana.

#### Scenario: Data amb menú publicat
- **WHEN** la data demanada té una cel·la amb contingut al PDF de la variant
- **THEN** el sistema retorna la llista de plats d'aquella cel·la (sense inventar-hi res)

#### Scenario: Data sense cel·la (cap de setmana o festa al menú)
- **WHEN** la data demanada no té cel·la o la cel·la és buida al PDF
- **THEN** el sistema no genera cap missatge de menú per a aquesta data

#### Scenario: Errata de data impresa al PDF
- **WHEN** el número de dia imprès a la cel·la no correspon al dia real de la columna (errata de l'origen)
- **THEN** el sistema resol la data real per posició (dilluns de la fila + índex de columna), no pel número imprès

#### Scenario: PDF il·legible o amb estructura desconeguda
- **WHEN** el PDF no es pot llegir o la rejilla no es pot reconstruir (canvi de format)
- **THEN** el sistema registra l'error i no publica plats inventats; el missatge anunciat amb l'enllaç al PDF continua sent la via de consulta

### Requirement: Publicació del menú de l'endemà a l'hora programada
El sistema SHALL publicar, el dia anterior a l'hora configurada (per defecte 19:00), un missatge «Demà dinem …» (o equivalent en l'idioma configurat) amb la data de l'endemà i els plats d'aquesta, al topic configurat de cada variant activa. El missatge diari MUST NO incloure l'enllaç al PDF.

#### Scenario: Publicació normal
- **WHEN** arriba l'hora programada del dia D i demà (D+1) és dia lectiu amb menú publicat
- **THEN** es publica el missatge de menú de D+1 al topic de cada variant activa

#### Scenario: Sense duplicats entre reinicis
- **WHEN** el servei reinicia després d'haver publicat el menú de D+1
- **THEN** no el torna a publicar per a la mateixa data i variant

#### Scenario: Fallida parcial d'una variant
- **WHEN** la variant basal es publica correctament però la sense porc falla (error de xarxa o Telegram)
- **THEN** la basal no es torna a publicar i la sense porc es reintenta al proper cicle

#### Scenario: Demà no té menú o no és dia lectiu
- **WHEN** l'endemà no té cel·la al PDF o cau en cap de setmana/festa segons el calendari del centre
- **THEN** no es publica cap missatge de menú

### Requirement: Salt de publicació en dies no lectius
El sistema SHALL determinar si l'endemà és dia lectiu creuant el calendari del centre (vacances, festes de lliure disposició, festes locals, abans d'inici/després de fi de curs) amb el dia de la setmana. Els caps de setmana no són dies lectius. La jornada intensiva SÍ és dia lectiu.

#### Scenario: Demà és festa del calendari
- **WHEN** l'endemà cau dins un rang de vacances o una festa de lliure disposició/festa local del calendari
- **THEN** no es publica cap missatge de menú

#### Scenario: Demà és jornada intensiva
- **WHEN** l'endemà és jornada intensiva segons el calendari
- **THEN** es publica el menú amb normalitat (hi ha escola)

#### Scenario: Cap de setmana
- **WHEN** l'endemà és dissabte o diumenge
- **THEN** no es publica cap missatge de menú

### Requirement: Missatge anunciat amb l'enllaç al PDF vigent
El sistema SHALL mantenir, a cada topic de menú, un missatge anunciat (pin) amb l'enllaç al PDF del menjador del mes vigent. Quan canviï l'URL del PDF, el sistema SHALL actualitzar el pin (o publicar-ne un de nou i fixar-lo) perquè la referència no quedi caducada.

#### Scenario: Canvi de mes (nou PDF)
- **WHEN** canvia l'URL del PDF del menjador respecte a l'estat desat
- **THEN** es publica (o actualitza) el missatge anunciat amb l'enllaç nou a cada topic de menú i es fixa

#### Scenario: Pin ja present i URL estable
- **WHEN** l'URL del PDF no canvia entre cicles
- **THEN** el sistema no torna a publicar ni a fixar cap missatge nou

### Requirement: Configuració de variants i topics del menú
El servei SHALL permetre configurar el menú: activació, hora de publicació, marcadors d'enllaç del PDF, i les variants (id, pàgina del PDF, topic) amb un topic per variant. Cada variant activa es publica només al seu topic.

#### Scenario: Variant desactivada
- **WHEN** una variant està desactivada a la configuració
- **THEN** no es publica cap missatge per a aquella variant ni es genera cap pin associat

#### Scenario: Topic de variant no configurat
- **WHEN** una variant activa no té topic (thread_id) assignat
- **THEN** el missatge cau al topic per defecte (general), tal com fa la resta d'origen

#### Scenario: Menú completament desactivat
- **WHEN** menú està desactivat a la configuració
- **THEN** el servei no resol ni parseja el PDF del menjador ni publica res de menú
