# Tasks: afa-elisabadia-avisos

## 1. Esqueleto del proyecto i config

- [x] 1.1 Estructura `src/`, `config.yaml.example`, `requirements.txt` (httpx, feedparser, beautifulsoup4) i verificar que `python -m` / import del paquet no falla
- [x] 1.2 Mòdul de config (YAML + env): chat_id, topics origen→thread, intervals base/calma/calenta, filtres RSS, curs objectiu; verificar carregant l'exemple sense secrets reals
- [x] 1.3 Secrets: `.env.example` amb `TELEGRAM_BOT_TOKEN` / ids de xat, `.gitignorat` per `.env` i `state/`; verificar amb `git check-ignore .env` que no es versiona
- [x] 1.4 Logger a stdout sense token (màscara o no loguejar env); verificar amb una línia de log de prova que no surt el token

## 2. Estat i deduplicació

- [x] 2.1 `state.py`: càrrega/guardat JSON atòmic (write temp + rename) amb claus de rss_guids, carta_url, cal_hash, ultima_novetat; verificar round-trip en test/unitària o script
- [x] 2.2 Primera execució sense estat: no aboca l'històric massiu (inicialitza buit o avís únic segons config); verificar simulant estat absent

## 3. Fetchers web-ingest

- [x] 3.1 Fetch RSS (`/feed/`): parseig amb feedparser, filtre de categories per config, extracció títol/resum/link/guid; verificar amb fixture RSS local o captura
- [x] 3.2 Fetch carta: GET portada, resoldre href actual de "carta del mes" (sense hardcodejar URL PDF); verificar amb HTML de fixture i amb la portada real en un cop de prova
- [x] 3.3 Fetch calendari: GET pàgina calendari, extreure seccions de dates, resum/hash normalitzat; verificar hash estable amb el mateix HTML i canvi amb HTML alterat
- [x] 3.4 Tolerància a errors: cada fetch fallit es logueja i no atura la resta; verificar forçant timeout/404 en un fetcher i continuïtat del cicle
- [x] 3.5 Sondeig adaptatiu al scheduler: base, finestra calenta post-novetat, allargada en calma; verificar amb rellotge simulat o intervals molt petits en proves

## 4. Sortida Telegram

- [x] 4.1 `telegram_out.py`: `sendMessage` a chat_id + `message_thread_id` opcional, text en català avís+enllaç; verificar enviament a un xat de proves amb topic configurat
- [x] 4.2 Dedup només després d'enviament OK (o cua de fallits amb retry/backoff); verificar simulant error 429/400 i re-execució sense pèrdua ni duplicat
- [x] 4.3 Plantilles de missatge (carta, notícia, calendari) coherents amb `telegram-publish`; verificar llegint els missatges rebuts al xat de proves

## 5. Orquestració i desplegament

- [x] 5.1 Loop principal: cicle fetchers → diff → publicar → persistir estat → dormir segons interval adaptatiu; verificar un cicle complet en local amb xat de proves
- [x] 5.2 Dockerfile (python:3.12-slim) + compose amb volum `state/`, `.env`, restart unless-stopped; verificar `docker compose up` i supervivència de l'estat a `docker compose restart`
- [x] 5.3 Desplegar en destí (VPS o Geekom) amb xat canari i només topic general; verificar arribada d'un aviso real (carta o RSS) al grup
- [ ] 5.4 Robustesa 48h: logs nets, cap duplicat, intervals adaptatius plausibles; verificar revisant logs i missatges de dues dies

## 6. Grup Telegram i anti-bot (configuració, no codi)

- [ ] 6.1 Crear grup de proves (temes/topics ON), afegir el bot com a admin, "només admins publiquen"; verificar que un compte no-admin no pot enviar
- [ ] 6.2 Convidat/invitació controlada (join-request o link revocable) i, en obrir a beta, un segon membre amb lectura només; verificar unir-se i llegir sense poder publicar
- [ ] 6.3 Noms de topics i fallback general a `config.yaml`; verificar amb un esdeveniment per origen que cau al topic esperat
- [x] 6.4 Escriure guia pas a pas de creació del bot i el grup a Telegram (reutilitzable per altres AFA) a `docs/guia-telegram.md`; verificar que el document existeix i cobreix bot, grup/topics, chat_id/thread_id, configuració i seguretat

## 7. Transparència i rollout

- [x] 7.1 Esborrany `docs/transparencia.md` (què fa, fonts, dades, límits, AFA, contacte, fases); verificar seccions mínimes presents i sense secrets
- [ ] 7.2 Publicar la doc a l'espai públic (Nextcloud/web AFA) amb URL estable; verificar que l'enllaç obre sense login
- [ ] 7.3 Rollout pas 1–2: canari operador → convidar 1 beta tester; verificar que el beta llegeix i l'operador rep logs/errors
- [x] 7.4 Preparar llistat de "features" següents (topics extra, docs, fases B/C) per anunciar; verificar document o issue al repo amb el pla escalonat
- [x] 7.5 Documentar per què s'usa Telegram i no WhatsApp (a `docs/transparencia.md`, amb nota a la guia i al README); verificar secció present

## 8. Verificació integrada (fase A completa)

- [x] 8.1 Prova E2E: publicar/nova carta o element RSS a la web (o fixture si cal) → avís al topic correcte en català amb enllaç → estat actualitzat → restart sense duplicats; verificar cadascun dels passos observables
- [x] 8.2 Validació OpenSpec del canvi (`openspec validate`) en blau abans de donar la fase per tancada

## 9. Publicació del repositori (Forgejo → GitHub)

- [x] 9.1 Afegir `LICENSE` (MIT, titular "AFA Escola Elisa Badia") i verificar que el fitxer existeix i nomena el titular
- [x] 9.2 Escriure `README.md` públic (català): què és, requisits, arrencada (Docker i local), privacitat i enllaç a `docs/transparencia.md`; verificar seccions presents
- [x] 9.3 Auditoria de secrets: cercar tokens/claus al contingut versionat i comprovar `.gitignore`; verificar que `.env`, `config.yaml` i `state/` no es versionen
- [x] 9.4 Crear repositori privat a Forgejo i afegir remot `origin` (SSH); verificar amb `git remote -v`
- [x] 9.5 Primer commit i push a Forgejo; verificar que el repo privat conté el codi i cap secret
- [ ] 9.6 Revisar com es veu el repo (README, LICENSE, estructura) i ajustar abans de fer-lo públic
- [ ] 9.7 (Posterior, amb aprovació) Publicar a GitHub públic i afegir remot `github`; verificar accés públic
- [x] 9.8 Documentar el flux de publicació (Forgejo→GitHub, remots, preparar versió pública); verificar document present

## 10. Internacionalització (i18n)

- [x] 10.1 Catàlegs per idioma a `src/i18n/` (`ca`, `es`, `en`) amb càrrega i descobriment automàtic; verificar amb tests que els idiomes disponibles es detecten
- [x] 10.2 Selecció d'idioma a `config.yaml` (`language`) amb override per entorn (`LANGUAGE`) i normalització de variants regionals; verificar amb tests
- [x] 10.3 Missatges del servei construïts des del catàleg (per defecte català); verificar amb tests que els textos canvien per idioma i fan retrocés segur
- [x] 10.4 Documentar com triar i afegir idioma (README i `docs/guia-telegram.md`); verificar seccions presents

## 11. Agenda de la carta (carta-agenda)

- [x] 11.1 Parser de la carta: extreure mes/any i esdeveniments (dia, curs, activitat) del text del PDF; verificar amb fixture de text real i amb la carta real
- [x] 11.2 Filtratge per cursos configurats (+ compartits); verificar que només surten els del curs objectiu i els compartits
- [x] 11.3 Missatges d'i18n: selecció de la carta i agenda setmanal (ca/es/en); verificar tests de format
- [x] 11.4 Publicar la selecció en detectar carta nova (amb fallback a avís+enllaç si no hi ha taula); verificar amb test d'integració
- [x] 11.5 Agenda setmanal programada (dia/hora) amb estat `last_weekly_post` i sense duplicats; verificar amb rellotge simulat
- [x] 11.6 Config `agenda` (activar, cursos, carta_filtrada, setmanal dia/hora, topic); verificar càrrega de l'exemple
- [x] 11.7 Actualitzar docs (README/guia) amb l'agenda; verificar seccions presents
