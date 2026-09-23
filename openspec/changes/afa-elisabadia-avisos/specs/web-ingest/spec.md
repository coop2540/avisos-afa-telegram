## Purpose

Capturar de forma fiable las novedades publicadas en la web pública del centre (Àgora/XTEC) —carta mensual, calendari i notícies— perquè el servei d'avisos pugui reenviar-les sense duplicats ni sondeig agressiu.

## ADDED Requirements

### Requirement: Sondeig de fonts públiques
El sistema SHALL consultar periòdicament les fonts públiques del centre: el RSS del blog, l'enllaç vigent de la carta del mes a la portada, i la pàgina de calendari del curs. El sondeig SHALL ser adaptatiu: interval base configurat, interval més curt després de detectar novetat recent, i interval més llarg quan hi ha molts dies sense cap canvi.

#### Scenario: Novetat en RSS es detecta
- **WHEN** apareix un element nou al RSS que compleix els filtres de categories configurats (per defecte: curs objectiu i/o genèriques del centre)
- **THEN** el sistema el marca com a pendent de publicar i el publica (o encola) al canal de Telegram d'acord amb `telegram-publish`

#### Scenario: Sense canvis redueix la freqüència
- **WHEN** no hi ha hagut cap novetat durant el període de calma configurat
- **THEN** el sistema incrementa l'interval entre sondejos fins al límit màxim configurat, sense deixar de consultar del tot

#### Scenario: Després de novetat augmenta la freqüència
- **WHEN** el sistema detecta almenys una novetat
- **THEN** redueix l'interval de sondeig durant la finestra "calenta" configurada abans de tornar a l'interval base

### Requirement: Resolució dinàmica de l'enllaç de la carta
El sistema SHALL resoldre cada cicle l'URL actual de la carta del mes a partir del HTML de la portada (text o àncora "carta del mes" / equivalent). MUST NOT hardcodar l'URL del PDF, puix que canvia cada mes.

#### Scenario: Carta nova publicada pel centre
- **WHEN** l'enllaç de la carta del mes a la portada canvia de destinació o contingut respecte a l'últim enllaç registrat
- **THEN** el sistema considera que hi ha carta nova i genera un esdeveniment de publicació amb l'URL original com a enllaç

#### Scenario: Portada no accessible
- **WHEN** la portada del centre no es pot obtenir (error HTTP, timeout, HTML buit)
- **THEN** el sistema registra l'error, manté l'últim enllaç conegut i reintenta al proper cicle sense publicar avisos falsos

### Requirement: Canvis del calendari del curs
El sistema SHALL extreure de la pàgina de calendari les seccions de dates (vacances, festes de lliure disposició, festes locals, jornada intensiva, fi de curs i inici de curs) i detectar-ne el canvi de contingut normalitzat.

#### Scenario: El centre actualitza el calendari
- **WHEN** el text normalitzat de les seccions de calendari canvia respecte a l'estat desat
- **THEN** el sistema genera un esdeveniment de "calendari actualitzat" amb enllaç a la pàgina o PDF de calendari

#### Scenario: Calendari estable
- **WHEN** el contingut del calendari no canvia entre cicles
- **THEN** el sistema no publica cap avís de calendari

### Requirement: Deduplicació d'esdeveniments
El sistema SHALL mantenir estat persistent de què ja s'ha publicat (identificador d'element RSS, últim enllaç de carta, hash o resum del calendari) perquè un reinici del procés no proviqui avisos duplicats.

#### Scenario: Reinici del contenedor
- **WHEN** el procés s'atura i torna a arrencar amb l'estat persistit intacte
- **THEN** no es tornen a publicar elements ja emesos anteriorment

#### Scenario: Primer arranc
- **WHEN** el sistema arrenca sense estat previ
- **THEN** no fa un esclat massiu d'avisos històrics: només es considera "primera vegada" i s'inicialitza l'estat sense publicar tot l'històric (o publica un únic avís de benvinguda si així es configura)

### Requirement: Tolerància a errors de la font
El sistema SHALL seguir en funcionament (loop viu) quan alguna font falli, sense aturar la resta de fetchers ni bolcar excepcions no controlades.

#### Scenario: Una font cau, les altres segueixen
- **WHEN** el fetch del RSS falla però la carta i el calendari responen
- **THEN** carta i calendari es processen amb normalitat i l'error del RSS queda registrat als logs
