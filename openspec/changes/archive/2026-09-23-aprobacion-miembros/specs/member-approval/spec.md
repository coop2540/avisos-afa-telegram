## Purpose

Permetre que el servei rebi les sol·licituds d'unió al grup privat i que un administrador les aprovi o rebutgi amb un clic, amb avís previ i sense que ningú hi entri sense control.

## ADDED Requirements

### Requirement: Recepció de sol·licituds d'unió
El servei SHALL rebre les sol·licituds d'unió (`chat_join_request`) del grup configurat i processar-les encara que siguin de tercers. El servei MUST NOT aprovar automàticament cap sol·licitud sense una decisió explícita de l'administrador (llevat del mode de filtratge opt-in, que només pot *rebutjar* automàticament, mai aprovar).

#### Scenario: Arriba una sol·licitud
- **WHEN** una persona sol·licita unir-se al grup
- **THEN** el servei la rep i genera una notificació per a l'administrador

#### Scenario: Sol·licitud sense dades mínimes
- **WHEN** la sol·licitud no porta usuari ni bio
- **THEN** el servei igualment avisa l'administrador amb els identificadors disponibles

### Requirement: Avis a l'administrador amb dades del sol·licitant
El servei SHALL enviar al **chat privat de l'administrador** configurat un avís amb les dades del sol·licitant (nom complet, `@usuari` si en té, id i bio si està disponible) i **botons** per decidir.

#### Scenario: Avis amb botons
- **WHEN** es rep una sol·licitud
- **THEN** l'administrador rep un missatge amb les dades i els botons «Aprovar» i «Rebutjar»

#### Scenario: Administrador no configurat
- **WHEN** no hi ha chat d'administrador configurat
- **THEN** el servei no intenta avisar ningú, ho registra com a error de configuració i no aprova ni rebutja res

### Requirement: Aprovació i rebuig per botó
El servei SHALL, en rebre la pulsació d'un botó, cridar l'API de Telegram per aprovar o rebutjar la sol·licitud corresponent, i respondre al botó perquè la interfície no quedi penjada.

#### Scenario: Aprovar
- **WHEN** l'administrador prem «Aprovar»
- **THEN** el servei crida `approveChatJoinRequest` per a aquell usuari i xat, i confirma la decisió a l'administrador

#### Scenario: Rebutjar
- **WHEN** l'administrador prem «Rebutjar»
- **THEN** el servei crida `declineChatJoinRequest` per a aquell usuari i xat, i confirma la decisió a l'administrador

#### Scenario: Sol·licitud ja resolta o expirada
- **WHEN** la decisió s'intenta aplicar sobre una sol·licitud que ja no és vàlida
- **THEN** el servei informa l'administrador que ja no es pot aplicar i no trenca

### Requirement: Ideempotència de decisions
El servei SHALL no duplicar avisos per a la mateixa sol·licitud ni permetre dobles decisions conflictives; ha de recordar que una sol·licitud ja s'ha notificat i el resultat de la decisió.

#### Scenario: Reinici amb sol·licitud pendent
- **WHEN** el servei es reinicia després d'haver notificat una sol·licitud no decidida
- **THEN** no torna a notificar-la fins que canviï el seu estat rellevant (o segons la política configurada)

#### Scenario: Doble pulsació del botó
- **WHEN** l'administrador prem dues vegades el mateix botó
- **THEN** el servei no aplica dues vegades la decisió ni mostra un error greu

### Requirement: Filtres heurístics opcionals (només rebuig)
El servei SHALL poder aplicar, si es configura, filtres heurístics que **rebutgen automàticament** sol·licituds clarament sospitoses (p. ex. sense nom vàlid, patrons de bot, comptes sense bio ni usuari), i enviar l'avís igualment perquè l'administrador en tingui constància. Els filtres MUST NOT aprovar automàticament mai.

#### Scenario: Filtre actiu
- **WHEN** una sol·licitud compleix un criteri de rebuig configurat
- **THEN** el servei la rebutja, ho registra i informa l'administrador de què ha passat i per què

#### Scenario: Filtre inactiu (per defecte)
- **WHEN** els filtres no estan configurats
- **THEN** el servei només notifica i espera la decisió manual

### Requirement: Mode de recepció configurable
El servei SHALL poder rebre updates mitjançant **long polling** o **webhook**, segons configuració, i MUST triar un de sol (no ambdós alhora pel mateix bot).

#### Scenario: Mode polling (per defecte)
- **WHEN** es configura polling
- **THEN** el servei obté les sol·licituds cridant `getUpdates` periòdicament, sense necessitat d'exposar cap URL pública

#### Scenario: Mode webhook
- **WHEN** es configura webhook
- **THEN** el servei enregistra la URL amb `setWebhook` i processa els updates entrants; neteja qualsevol webhook anterior si es canvia a polling

### Requirement: Traçabilitat mínima i privacitat
El servei SHALL registrar l'estat tècnic de cada sol·licitud (id, decisió, moment) sense conservar més dades personals de les necessàries, i la documentació de transparència SHALL explicar que el servei veu les dades del sol·licitant per poder avisar l'administrador.

#### Scenario: Consulta de transparència
- **WHEN** algú vol saber quines dades es guarden arran d'una sol·licitud
- **THEN** la documentació indica que es guarden identificadors i la decisió, i que no es fa cap perfilat ni es comparteixen
