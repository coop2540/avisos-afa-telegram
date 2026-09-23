## Purpose

Publicar de forma permanent i accessible una explicació del servei —com funciona, quines dades toca, on les guarda, qui hi darrere— perquè les famílies i l'AFA puguin entendre i verificar el sistema sense dependre de l'operador.

## ADDED Requirements

### Requirement: Document de transparencia publicat
El sistema (el projecte) SHALL produir i mantenir un document públic de transparencia en català amb, com a mínim: què fa el servei, de quines fonts públiques treballa, quin ús fa de Telegram, quines dades personals toca (i quines no), on s'emmagatzema qualsevol còpia o estat, qui el opera (AFA + infraestructura cedida), límits (no substitueix els canals oficials del centre) i com contactar/corregir.

#### Scenario: Família pregunta "com funciona això"
- **WHEN** una família o membre de l'AFA vol entendre el servei
- **THEN** troba el document en l'espai públic del servei (Nextcloud/web AFA) sense haver de preguntar a l'operador

#### Scenario: Revisió de dades
- **WHEN** algú vol saber què es guarda
- **THEN** el document llista explícitament: fonts públiques consultades, estat de deduplicació (sense dades de famílies en fase A), i que no hi ha base de dades d'alumnes ni de telèfons gestionada pel servei

### Requirement: Publicació en espai públic compartit
El document de transparencia SHALL viure al mateix espai públic on es poguin oferir els recursos del servei (directori Nextcloud públic o web equivalent de l'AFA), amb URL estable citable des del canal de Telegram o des de l'AFA.

#### Scenario: Enllaç des del material del servei
- **WHEN** cal referir-se a "com funciona" des d'un lloc visible
- **THEN** existeix una URL pública única cap al document de transparencia

### Requirement: Documentació de fases i límits
El document SHALL deixar clar l'estat de maduresa (fase A/B/C), què encara no fa (p. ex. resums IA, substitució del WhatsApp del centre, registre de famílies) i que les dades de compte de Telegram les gestiona Telegram (telèfon), no el servei.

#### Scenario: Expectativa de WhatsApp
- **WHEN** una família espera que tots els avisos del centre passin per aquí
- **THEN** el document explícita que el servei només recull el que ja es publica a la web del centre i no substitueix missatges exclusius d'altres canals
