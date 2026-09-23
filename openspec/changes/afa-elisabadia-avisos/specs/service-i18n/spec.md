## Purpose

Separar els textos del servei del codi, en catàlegs per idioma, perquè el mateix programari pugui servir associacions de diferents comunitats canviant només la configuració i afegint un fitxer de traducció.

## ADDED Requirements

### Requirement: Textos separats del codi
Els textos publicats pel servei SHALL residir en catàlegs per idioma (fitxers de dades dins del projecte), no incrustats a la lògica. El codi SHALL carregar-los en temps d'execució.

#### Scenario: Traduir sense tocar el codi
- **WHEN** es vol canviar o afegir un text
- **THEN** es fa editant o afegint un fitxer de catàleg, sense modificar la lògica del programa

### Requirement: Idioma per defecte
El servei SHALL tenir un idioma per defecte (**català**) que s'aplica quan no se n'especifica cap altre. Aquest SHALL ser l'idioma de la versió alpha, beta i v1.

#### Scenario: Sense configuració d'idioma
- **WHEN** no es configura cap idioma
- **THEN** els missatges es publiquen en català

### Requirement: Selecció d'idioma per configuració
El servei SHALL permetre triar l'idioma mitjançant la configuració (fitxer o variable d'entorn), acceptant variants regionals (p. ex. `es-ES` → `es`).

#### Scenario: Configurar castellà
- **WHEN** es configura l'idioma a `es`
- **THEN** els missatges del servei es publiquen en castellà

#### Scenario: Variant regional
- **WHEN** es configura un idioma com `en-GB`
- **THEN** el servei el resol al codi base disponible (`en`)

### Requirement: Retrocessos (fallback) segurs
Si l'idioma configurat no té catàleg, o una clau no hi és, el servei SHALL retrocedir a l'idioma per defecte i, si encara no hi és, no SHALL fallar: ha de publicar alguna cosa raonable (com a mínim, la clau) sense aturar-se.

#### Scenario: Idioma no suportat
- **WHEN** es configura un idioma sense catàleg (p. ex. `fr`)
- **THEN** el servei publica en l'idioma per defecte (català) i ho registra, sense error

#### Scenario: Clau absent en un catàleg
- **WHEN** un catàleg no conté una clau que sí que té el català
- **THEN** el servei usa el valor del català per a aquesta clau

### Requirement: Afegir un idioma sense tocar codi
Afegir un idioma nou SHALL consistir a afegir un fitxer de catàleg amb el codi corresponent; el codi SHALL descobrir els idiomes disponibles a partir dels catàlegs presents.

#### Scenario: Nova comunitat
- **WHEN** una associació d'una altra comunitat vol el servei en el seu idioma
- **THEN** copia el catàleg base, el tradueix, en fixa el codi a la configuració i el servei l'usa sense canvis de codi

### Requirement: Documentació de l'idioma
El projecte SHALL documentar com es tria l'idioma i com se n'afegeix un de nou, tant per a l'operador com per a qui vulgui reutilitzar el servei.

#### Scenario: Persona d'una altra associació
- **WHEN** algú vol desplegar el servei en un altre idioma
- **THEN** troba a la documentació els passos (configurar `language`, afegir el catàleg) sense haver de llegir el codi
