# Transparència del servei d'avisos

> Document públic. Explica què fa aquest servei, d'on treu la informació,
> quines dades toca i qui el sosté. Si trobes res incorrecte, avisa'ns.

## Què és

Un servei de la **AFA de l'Escola Elisa Badia** (Barberà del Vallès) que
recull el contingut que el centre ja publica a la seva web pública i el
reenvia com a **avisos** a un grup de Telegram, perquè les famílies no
hagin de revisar la web a mà.

Els avisos tenen la forma **avís + enllaç**: un text breu en català i un
enllaç al document o notícia original. No resumim ni modifiquem el
contingut del centre.

## Per què Telegram i no WhatsApp?

La decisió no és de gust: ve del fet que el servei ha de **publicar avisos de
manera automàtica**.

- **WhatsApp no es pot automatitzar de forma oberta.** La seva API oficial
  (WhatsApp Business Platform) és de pagament, exigeix una empresa verificada i
  plantilles aprovades, i es cobra per conversa. No hi ha manera gratuïta i
  senzilla que un programa publiqui avisos; els canals de WhatsApp tampoc no
  ofereixen API per publicar-hi automàticament.
- **Telegram sí que ho permet:** té una API de bots **gratuïta i oberta**. El
  bot publica sol, que és exactament el que necessitem.
- **Privacitat:** en un grup de WhatsApp tothom veu el número de telèfon de
  tothom. A Telegram, el bot **no veu el telèfon** dels membres (només un
  identificador opac), i les famílies no cal que comparteixin el seu número
  entre elles.
- **Ordenació:** Telegram té **topics** (fils), així que hi ha un sol lloc
  d'entrada però cada família silencia el que no li interessa. WhatsApp no té
  res equivalent.
- **Control del soroll:** el grup es pot configurar perquè **només els
  administradors publiquin**; ningú no pot omplir-lo de missatges.
- **Cost:** gratuït, sense quotes de missatges ni servidors addicionals.

**Contrapartida honesta:** no tothom té Telegram instal·lat. Per això aquest
servei **complementa** els canals oficials del centre i el WhatsApp de la
classe; no els substitueix. Qui vulgui els avisos automàtics s'instal·la
Telegram; qui no, continua com fins ara.

## D'on surt la informació

Només de fonts **públiques** del centre:

- La **carta del mes** (PDF enllaçat a la portada).
- El **calendari del curs** (pàgina pública del centre).
- Les **notícies** del blog (RSS públic), filtrades per curs i temes generals.

No accedim a cap àrea privada, ni a Google Classroom, ni a dades
d'alumnes.

## Quines dades personals toca

**Cap.** El servei no registra qui ets, ni quin fill o filla tens, ni el
teu telèfon. No hi ha base de dades de famílies.

- El **compte de Telegram** (i el telèfon associat) el gestiona
  **Telegram**, no nosaltres. Nosaltres no el veiem ni l'emmagatzemem.
- El **filtre per curs** es fa al teu mòbil: simplement **silencies** els
  temes (topics) que no t'interessen. Aquesta preferència no surt del teu
  dispositiu.

## Què guardem

Només un petit **estat tècnic** per no repetir avisos: la llista
d'identificadors de notícies ja publicades, l'enllaç de la carta vigent i
una empremta del calendari. No conté cap dada personal.

No hi ha servidors de tercers recollint estadístiques d'aquest servei.

## Qui ho opera

L'**AFA** posa el servei a disposició de les famílies. La infraestructura
inicial va **cedida per un col·laborador tècnic**; el dia que convingui,
l'AFA la pot assumir directament. El programari és obert i auditable.

## Què NO fa (límits)

- **No substitueix** els canals oficials del centre ni el WhatsApp de la
  classe. Si una cosa no es publica a la web del centre, aquest servei no
  la pot saber.
- No tradueix: publiquem en **català**, com el centre.
- No respon preguntes ni genera resums amb intel·ligència artificial en la
  fase actual.
- No envia missatges privats a famílies: només publica al grup.

## Estat del servei (fases)

- **Fase A (actual):** avisos automàtics de carta, calendari i notícies.
- **Fase B (prevista):** consulta sota demanda i filtrat més fi per curs.
- **Fase C (exploració):** resums i preguntes amb IA (models gratuïts).

## Com contactar o corregir

Per demanar una correcció, donar-te de baixa o plantejar un dubte,
adreça't a l'**AFA de l'Escola Elisa Badia** pels seus canals habituals.
