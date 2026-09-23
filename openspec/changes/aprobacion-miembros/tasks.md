# Tasks: aprobacion-miembros

## 1. Configuració i estat

- [x] 1.1 Afegir a `config.yaml`/config.py: `telegram.admin_chat_id` i secció `telegram.approval` (enabled, receive polling|webhook, webhook.url, auto_reject); verificar càrrega de l'exemple
- [x] 1.2 Estendre l'estat amb `join_requests: {<user_id>: {status, ts}}`; verificar round-trip i retrocompatibilitat
- [x] 1.3 Verificar que si `admin_chat_id` no està configurat, el servei no intenta avisar ni decidir (i ho registra)

## 2. Recepció d'updates (polling per defecte)

- [x] 2.1 Mòdul `approval` amb bucle de `getUpdates` (offset + timeout llarg); verificar amb un update simulat
- [x] 2.2 Filtrar `chat_join_request` del grup configurat; ignorar la resta d'updates sense efectes
- [x] 2.3 En arrencar polling, cridar `deleteWebhook` per evitar conflictes; verificar idempotència
- [x] 2.4 Mode webhook opcional (`setWebhook` amb secret token des de `.env`); verificar que es tria un sol mode

## 3. Notificació a l'administrador

- [x] 3.1 Enviar avís al xat de l'admin amb dades del sol·licitant i botons ✅/❌ (`inline_keyboard`, `callback_data` `apr:`/`rej:`); verificar missatge rebut amb botons
- [x] 3.2 No renotificar la mateixa sol·licitud (estat `notified`); verificar amb un reinici simulat

## 4. Decisió per botó

- [x] 4.1 Gestionar `callback_query`: cridar `approveChatJoinRequest`/`declineChatJoinRequest`, respondre el botó (`answerCallbackQuery`) i editar el missatge amb el resultat; verificar cas aprovat
- [x] 4.2 Verificar cas rebutjat i cas de sol·licitud ja resolta/expirada (missatge clar, sense excepció)
- [x] 4.3 Evitar doble decisió (segona pulsació no torna a cridar l'API); verificar

## 5. Filtres heurístics (opt-in, només rebuig)

- [x] 5.1 Implementar regles de rebuig configurables (nom buit/numeric, patrons de bio/usuari) i verificar amb casos de fixture
- [x] 5.2 Quan un filtre actua: rebutjar, registrar motiu i avisar l'admin igualment; verificar

## 6. Integració i desplegament

- [x] 6.1 Integrar el bucle de polling al servei (fil paral·lel al sondeig web) sense bloquejar la publicació; verificar que tots dos funcionen alhora
- [x] 6.2 Prova E2E real: segon compte sol·licita entrar → avís a l'admin → aprovar → entra; verificar cada pas
- [x] 6.3 Actualitzar `docs/transparencia.md` (dades del sol·licitant, decisió) i la guia (admin_chat_id, enllaços amb expiració); verificar seccions
- [x] 6.4 `openspec validate` del canvi en blau; verificar
