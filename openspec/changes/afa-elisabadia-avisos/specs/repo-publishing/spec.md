## Purpose

Preparar i publicar el repositori del projecte de manera que sigui auditable i segur: primer en una instància Forgejo privada per revisar-ne l'aspecte, i després en un repositori públic de GitHub, sense secrets versionats i amb llicència i documentació pública.

## ADDED Requirements

### Requirement: Repositori sense secrets
El repositori SHALL no contenir cap secret (token de Telegram, credencials, claus) en cap commit. Els fitxers amb secrets o estat local (`.env`, `config.yaml`, `state/`) SHALL estar exclosos via `.gitignore`, i hi SHALL haver un `.env.example` i un `config.yaml.example` com a plantilles.

#### Scenario: Auditoria abans de publicar
- **WHEN** es prepara el repositori per fer-lo públic
- **THEN** una cerca al contingut versionat no troba tokens ni claus, i `.env`/`config.yaml`/`state/` apareixen com a ignorats per git

#### Scenario: Clonació per tercers
- **WHEN** una persona clona el repositori
- **THEN** obté les plantilles d'exemple però cap valor real, i el servei no arrenca en mode real sense que l'usuari hi posi el seu propi token

### Requirement: Llicència i README públics
El repositori SHALL incloure un fitxer `LICENSE` amb una llicència oberta i un `README` que expliqui què és el servei, com executar-lo, quines dades toca i on és la documentació de transparència.

#### Scenario: Persona externa avalua el projecte
- **WHEN** algú arriba al repositori per primer cop
- **THEN** troba al README l'objectiu, els requisits, com arrencar-lo i un enllaç a la documentació de transparència, i el `LICENSE` indica clarament els termes d'ús

### Requirement: Publicació privada primer, pública després
El repositori SHALL alojar-se primer en una instància **Forgejo** en mode **privat**, i només després d'una revisió/aprovació SHALL publicar-se en un repositori **públic** de GitHub. El remot de Forgejo SHALL quedar configurat per permetre l'enviament.

#### Scenario: Revisió en privat
- **WHEN** el projecte s'envia per primer cop
- **THEN** ho fa a un repositori privat de Forgejo, visible només per a qui hi té accés, per poder valorar-ne l'aspecte abans de fer-lo públic

#### Scenario: Publicació a GitHub
- **WHEN** el repositori privat ha estat aprovat
- **THEN** es publica una versió a GitHub com a repositori públic, amb el mateix contingut auditat

### Requirement: El codi publicat és el que s'executa
El codi font del servei SHALL ser el mateix que s'executa en producció; les diferències (configuració, secrets, estat) SHALL viure fora del repositori.

#### Scenario: Auditabilitat
- **WHEN** algú vol comprovar què fa el servei
- **THEN** pot llegir el codi del repositori i correspondre'l amb el comportament documentat, sense peces propietàries ocultes

### Requirement: Flux de publicació documentat
El projecte SHALL documentar com es publica (Forgejo → GitHub), quins remots existeixen i com es prepara una versió pública, de manera que qualsevol col·laborador pugui reproduir-ho.

#### Scenario: Nova persona col·laboradora
- **WHEN** una persona s'incorpora al projecte
- **THEN** troba documentat el flux de publicació i els remots, i pot enviar canvis sense endevinar la configuració
