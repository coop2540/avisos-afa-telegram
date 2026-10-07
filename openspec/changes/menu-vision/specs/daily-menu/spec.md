## Purpose

Assegura que el menú del menjador es pot extreure i publicar també quan el PDF
mensual del centre ve **sense capa de texte**, fent servir visió local i
privada amb validació estricta, i que el text extret no es retalla ni es
descarta per errors de càlcul de dates.

## ADDED Requirements

### Requirement: Extracció d'un PDF sense capa de texte per visió local
El sistema SHALL extreure el menú d'un PDF del menjador que no conté capa de
texte mitjançant un model de visió que funcioni **al propi servidor del
servei** (sense núvol, sense enviar-ne cap part a tercers), transcrivint
literalment el que hi ha imprès a la cel·la. La publicació MUST NO inventar,
resumir ni completar cap contingut que el model no hagi transcrit.

#### Scenario: PDF amb capa de texte
- **WHEN** el PDF permet extreure'n paraules i localitzar-ne les capçaleres de
  la rejilla de manera determinista
- **THEN** el sistema usa l'extracció determinista i NO fa cap crida al model
  de visió

#### Scenario: PDF sense capa de texte
- **WHEN** el PDF no conté cap text extraïble i té una rejilla de cel·les
  localitzable per geometria
- **THEN** el sistema localitza la cel·la del dia demanat, en llegeix el
  contingut amb el model de visió i publica només el text transcrit

#### Scenario: Resposta del model il·legible o buida
- **WHEN** el model de visió no respon, torna una resposta que no es pot
  interpretar o el servidor no és accessible
- **THEN** el sistema registra l'error i **no publica** cap menú per a aquella
  data; el missatge anunciat amb l'enllaç al PDF continua sent la via de
  consulta

### Requirement: Detecció de la variant de cada pàgina pel segell
El sistema SHALL identificar quina pàgina del PDF correspon a cada variant de
menú llegint el **segell del capçalera** de cada pàgina (p. ex. «BASAL»,
«NO PORC»), i no a partir d'un índex de pàgina fix, perquè l'ordre de les
pàgines canvia cada mes.

#### Scenario: Ordre de pàgines diferent del de la configuració
- **WHEN** el PDF vigent té el calendari basal a la pàgina 0 i el calendari
  sense porc a la pàgina 3, mentre la configuració indica les pàgines 0 i 1
- **THEN** el sistema publica cada variant des de la seva pàgina real,
  detectada pel segell

#### Scenario: Segell llegible en una pàgina que no és calendari
- **WHEN** una pàgina del PDF no té rejilla de cel·les (infografia, proposta
  de sopars)
- **THEN** el sistema la descarta sense intentar extreure'n cap menú

#### Scenario: Cap pàgina correspon a la variant
- **WHEN** el segell de cap pàgina coincideix amb els marcadors de la variant
  i l'índex configurat tampoc apunta a una pàgina amb rejilla
- **THEN** el sistema registra l'error i no publica aquella variant

### Requirement: Validació de l'extracció abans de publicar
El sistema SHALL validar tota extracció abans de publicar: el número de dia
imprès a la cel·la ha de correspondre al dia real (admetent una desviació
d'un dia per errata de l'origen) i l'estructura ha de tenir entre 1 i 8 línies
de fins a 80 caràcters. MUST NO publicar cap contingut que no superi aquesta
validació.

#### Scenario: Cel·la correcta
- **WHEN** el dia imprès és el dia esperat (o un dia al costat, per errata) i
  l'estructura és raonable
- **THEN** el sistema publica els plats transcrits tal com estan

#### Scenario: Fila equivocada de la rejilla
- **WHEN** la cel·la llegida correspon a una altra setmana (el dia imprès
  difereix més d'un dia del real)
- **THEN** el sistema descarta aquella lectura i prova les setmanes veïnes;
  si cap valida, **no publica** i registra l'error

#### Scenario: Cel·la buida o de festiu
- **WHEN** la cel·la del dia no té contingut al PDF
- **THEN** el sistema no genera cap missatge de menú per a aquesta data

### Requirement: Fallada del motor no equiv a dia sense menú
El sistema SHALL tractar per separat el *dia sense cel·la* (resolt: no hi ha
missatge) de la *fallada del motor d'extracció* (pendent): davant d'una
fallada NO SHALL marcar la data com publicada, de manera que es reintentarà al
proper cicle.

#### Scenario: Motor caigut o timeout a l'hora de publicar
- **WHEN** el model de visió no respon dins del temps límit configurat
- **THEN** la data queda pendent de publicació, es registra l'error i el
  següen cicle torna a intentar-ho

#### Scenario: Data sense cel·la
- **WHEN** el menú d'aquella data s'ha resolt correctament i la cel·la és
  buida (cap de setmana o festa)
- **THEN** la data queda resolta sense missatge i no es reintenta

### Requirement: Integritat del text extret del parser de texte
El sistema SHALL extreure el text de les cel·les sense retallar paraules que
comencin a l'esquerra del límit de columna, i SHALL resoldre la primera fila
de la rejilla encara que el dilluns calculat caigui en un mes anterior.

#### Scenario: Paraule que toca el límit de la columna de dilluns
- **WHEN** una paraula de la cel·la de dilluns comença abans del límit
  derivat de la capçalera (p. ex. «LLUÇ»)
- **THEN** el menú publicat conté la paraula sencera

#### Scenario: Primera setmana amb dies del mes anterior
- **WHEN** la primera fila de la rejilla correspon a una setmana anterior a
  l'1 del mes (dies 1 i 2 en dijous i divendres)
- **THEN** la fila es resol amb el dilluns del mes anterior i el menú d'aquests
  dies s'extreu correctament
