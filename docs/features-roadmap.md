# Full de ruta de funcionalitats (per anunciar)

El servei s'obre de forma **escalonada**. Aquest és el pla de funcionalitats
previst, pensat per anunciar-se a mesura que cada fase estigui llesta.

## Fase A — Avisos automàtics (en curs)

- [x] Sondeig de la web pública del centre (carta, calendari, notícies).
- [x] Publicació d'avisos (avís + enllaç) en català.
- [x] Sondeig adaptatiu (més ràpid si hi ha novetat, més lent en calma).
- [x] Un sol grup de Telegram, amb topics per curs i per tipus.
- [x] Només els administradors publiquen; entrada per invitació.
- [ ] Desplegament canari (operador) i calibratge d'intervals.
- [ ] Document de transparència publicat en espai públic.

## Fase B — Consulta i filtratge fi (previst)

- [ ] Bot amb comandes: `/carta`, `/calendari`, `/properes`.
- [ ] Extracció de la taula de la carta per publicar només el que toca a
      cada curs.
- [ ] Topics per curs actius a mesura que la comunitat creix.
- [ ] Espejo de documents a Nextcloud (quan el pipeline els processi).

## Fase C — Assistència amb IA (exploració)

- [ ] Resums de la carta adaptats a cada curs (models gratuïts d'OpenRouter).
- [ ] Resposta a preguntes freqüents sobre el contingut ja publicat.
- [ ] Butlletí setmanal automàtic.
- [ ] Multiclase / multicentre si el model funciona.

> Criteri: cap funcionalitat de la fase C no calcula dates ni inventa dades.
> Les dades dures sempre vénen del contingut publicat pel centre.
