## Purpose

Definir la configuració externa i l'estat mínim de deduplicació que el servei necessita per operar de forma reproduïble, reiniciable i multi-fase (un topic o N) sense amagar secrets ni acoblar el codi a un únic xat.

## ADDED Requirements

### Requirement: Configuració externa
El servei SHALL llegir la seva configuració de fitxers externs (ex. config YAML + variables d'entorn) que incloguin com a mínim: chat_id de destí, mapa origen→topic (o topic per defecte), paràmetres de sondeig (interval base, calma, finestra calenta), filtres de categories RSS i curs objectiu. Els secrets (token del bot) SHALL anar NOMÉS en variables d'entorn o fitxer secret fora del repo.

#### Scenario: Canvi de xat de proves a xat AFA
- **WHEN** l'operador canvia el chat_id i els topics a la configuració
- **THEN** el mateix binari/contenedor publica al nou destí sense recompilar ni editar codi

#### Scenario: Secret al repo
- **WHEN** algú intenta commitejar el token
- **THEN** el .gitignore / pràctica documentada ho impedeix; el token no forma part del historial git del projecte

### Requirement: Estat persistent de deduplicació
El servei SHALL persistir l'estat de publicació (elements RSS vists, últim enllaç de carta, resum/hash de calendari, marca de temps d'última novetat) en un fitxer o base de dades local al volum del contenedor, supervivent a reinicis.

#### Scenario: Restart de Docker
- **WHEN** el contenedor es reinicia
- **THEN** l'estat de "ja publicat" es manté i no hi ha tornada a publicar avisos antics

### Requirement: Logging operatiu
El servei SHALL registrar a stdout (o fitxer de log) els cicles de sondeig, novetats publicades, errors de fetch i errors d'enviament a Telegram, amb nivell suficient per diagnosticar sense exposar secrets.

#### Scenario: Error d'enviament a Telegram
- **WHEN** l'API de Telegram rebutja un missatge
- **THEN** l'error queda als logs, l'esdeveniment es reintenta o es marca com a fallit segons política configurada, i el procés no cau
