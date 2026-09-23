## Purpose

Publicar avisos automàtics en català a un únic lloc d'entrada de Telegram (grup amb topics), amb format avís+enllaç i sense capacitat d'escriure per part de les famílies, perquè el servei sigui fiable i net per a qui el segueix.

## ADDED Requirements

### Requirement: Únic canal d'entrada amb topics
El sistema SHALL publicar tots els avisos en un sol destí de Telegram (grup o canal configurat). Els avisos SHALL poder anar dirigits a un topic (message_thread_id) segons la configuració d'origen→topic. El sistema MUST NO requerir que cada família es registri ni triï la seva classe en un servidor: el filtratge per curs es resol al client (silenciar topics).

#### Scenario: Avisos de fonts diferents al mateix grup
- **WHEN** es publica una carta, una notícia del curs objectiu i un canvi de calendari
- **THEN** cadascun arriba al topic configurat per a aquell origen dins del mateix grup

#### Scenario: Topic no configurat
- **WHEN** una font té un topic pendent (null a la configuració)
- **THEN** l'esdeveniment es publica al topic per defecte (general) o queda en cua segons la configuració, sense perdre's en silenci si es configura fallback

### Requirement: Missatges en català i format avís+enllaç
Els missatges publicats SHALL ser en català i en format breu d'avís amb un enllaç (URL original de la font). En la fase A el sistema MUST NO generar resums ni contingut amb IA.

#### Scenario: Carta del mes nova
- **WHEN** es detecta carta nova
- **THEN** es publica un missatge breu en català amb títol d'avís i enllaç a l'URL original de la carta

#### Scenario: Notícies
- **WHEN** es publica un element del RSS filtrat
- **THEN** el missatge conté títol, un resum curt si està disponible al feed i enllaç al post original (sense inventar contingut)

### Requirement: Els participants no publiquen
El destí de Telegram SHALL estar configurat de manera que només els admins (i el bot) puguin enviar missatges; les famílies només llegeixen. El sistema no exposa cap flux d'entrada de missatges de tercers en la fase A.

#### Scenario: Família intenta escriure al grup
- **WHEN** un membre que no és admin envia un missatge al grup
- **THEN** Telegram el bloqueja per permisos de grup; el servei no depèn de filtrar-lo programàticament

### Requirement: Entrada controlada
L'accés al grup SHALL ser privat (invitació o join-request aprovada). El bot SHALL ser admin del grup per poder publicar a qualsevol topic.

#### Scenario: Nou membre amb join-request
- **WHEN** una persona sol·licita unir-se al grup amb join-request activat
- **THEN** un admin del servei (AFA/operador) ha d'aprovar-la abans que pugui llegir

### Requirement: Identitat del servei
El sistema SHALL publicar en nom de l'AFA (perfil/nom del bot o grup coherent amb el servei documentat). Els secrets del bot (token) MUST NO apparèixer en logs, al repo ni en cap document públic.

#### Scenario: Token exposat per error
- **WHEN** un log o fitxer contindria el token
- **THEN** el sistema (o la pràctica de desplegament documentada) n'amaga la sortida i el token es rota si s'hagi filtrat
