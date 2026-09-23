## Purpose

Treure partit de la taula d'activitats de la carta mensual del centre (Dia | Curs | Activitat) per publicar, d'una banda, la selecció d'activitats que toquen al curs de cada família quan surt carta nova, i de l'altra, una agenda setmanal amb els actes de la setmana.

## ADDED Requirements

### Requirement: Extracció d'esdeveniments de la carta
El sistema SHALL obtenir el PDF de la carta vigent i extreure'n, com a mínim, el mes i l'any i la llista d'activitats amb dia, curs i descripció (a partir de la taula Dia | Curs | Activitat).

#### Scenario: Carta amb taula estàndard
- **WHEN** la carta conté la capçalera de taula «Dia Curs Activitat»
- **THEN** el sistema n'extreu el mes, l'any i una llista d'esdeveniments (data, curs, activitat)

#### Scenario: Carta sense taula o il·legible
- **WHEN** la carta no té taula reconeixible o el PDF no es pot llegir
- **THEN** el sistema no publica una selecció incorrecta; registra l'incident i, si escau, cau al comportament d'avís+enllaç

### Requirement: Filtratge per curs
El sistema SHALL filtrar els esdeveniments pels cursos configurats (p. ex. `I4`) i les etiquetes compartides (p. ex. `Tothom`, `Famílies`), de manera que cada família rebi només el que li toca.

#### Scenario: Activitats del curs i compartides
- **WHEN** hi ha activitats marcades amb el curs objectiu i activitats marcades com a compartides
- **THEN** totes dues apareixen a la selecció; les d'altres cursos no

### Requirement: Selecció en detectar carta nova
Quan es detecta una carta nova, el sistema SHALL publicar, si està configurat, una selecció de les activitats del curs (a més de l'enllaç al PDF complet), en lloc de només l'enllaç.

#### Scenario: Carta nova amb activitats del curs
- **WHEN** es detecta una carta nova i conté activitats del curs objectiu
- **THEN** es publica la llista d'activitats (data + descripció) amb un enllaç a la carta completa

#### Scenario: Carta nova sense activitats del curs
- **WHEN** la carta nova no té cap activitat del curs objectiu
- **THEN** es publica l'avís+enllaç habitual (sense llista buida)

### Requirement: Agenda setmanal programada
El sistema SHALL poder publicar, un dia i hora configurats de la setmana, una agenda amb els actes d'aquella setmana (dilluns a diumenge) del curs objectiu, amb enllaç a la carta.

#### Scenario: Dia i hora de l'agenda
- **WHEN** arriba el dia i l'hora configurats i encara no s'ha publicat l'agenda d'aquesta setmana
- **THEN** es publica l'agenda de la setmana (o s'omet si no hi ha cap acte), i es registra que ja s'ha publicat

#### Scenario: Sense duplicats
- **WHEN** el servei reinicia després d'haver publicat l'agenda d'aquesta setmana
- **THEN** no la torna a publicar

### Requirement: Configuració de l'agenda
El servei SHALL permetre configurar l'agenda: activar-la, els cursos a incloure, si es publica la selecció en detectar carta nova, i el dia/hora de l'agenda setmanal.

#### Scenario: Desactivar l'agenda
- **WHEN** l'agenda està desactivada a la configuració
- **THEN** el servei es comporta com abans (només avís+enllaç de carta)
