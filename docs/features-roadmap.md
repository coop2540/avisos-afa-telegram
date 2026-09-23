# Visió i evolució del projecte

Full de ruta complet: què està fet, què està capturat (OpenSpec), què s'ha
explorat i què queda per decidir. Serveix per anunciar funcionalitats de mica
en mica i perquè altres associacions vegin cap a on va.

> Estat a setembre de 2026. Llegenda: ✅ fet · 🟡 parcial · 📋 capturat (change
> OpenSpec) · 💡 idea (sense capturar) · ⛔ descartat/decisió

---

## Fase A — Avisos automàtics ✅

- ✅ Sondeig de la web pública del centre (RSS, carta del mes, calendari).
- ✅ Publicació d'**avís + enllaç** (sense IA en aquesta fase).
- ✅ **Sondeig adaptatiu** (ràpid si hi ha novetat, lent en calma).
- ✅ Estat de deduplicació persistent (sense duplicats entre reinicis).
- ✅ Contenidor Docker desplegat (24/7) + robustesa.
- ✅ Interfície de configuració externa (`config.yaml` + `.env`).

## Fase B — Organització del grup i filtratge ✅/🟡

- ✅ Un sol grup amb **topics**; conversió de l'admin; només admins publiquen.
- ✅ **Agenda de la carta** (taula Dia|Curs|Activitat): carta filtrada per curs
  en sortir + agenda setmanal programada.
- ✅ **Aprovació de membres** semi-automàtica (avís a l'admin amb botons,
  filtres opt-in només de rebuig).
- ✅ Missatge de **benvinguda + normes** (fins i tot fixat).
- 📋 **Menú del menjador diari**: el menú de demà a les 19:00 als topics de cada
  variant (basal / sense porc), amb salt de dies no lectius i missatge fixat amb
  l'enllaç al PDF vigent.
- 🟡 **Topics per curs actius**: decisio pendent (tants topics com cursos
  omple el grup; alternatives: per tipus o per cicle).
- 💡 Enllaços d'invitació amb **caducitat** i rotació (ja s'usen; formalitzar).

## Fase C — Consulta (bot sota demanda) 💡

- 💡 Comandes al bot: `/carta`, `/calendari`, `/properes`.
- 💡 **Botó de "aquesta setmana"** (sense memoritzar comandes).
- 💡 Filtratge per curs a la consulta (silenciar topics o preferència).
- 💡 **Bot 1:1**: cada família tria la seva classe i rep només el que li toca
  (sense que el servidor guardi dades personals més enllà del mínim).
- 💡 Subscripcions per tipus ("només excursiones", etc.).

## Fase D — Assistència amb IA 💡

- 💡 **Resums** de la carta adaptats a cada curs (models gratuïts d'OpenRouter).
- 💡 Resposta a **preguntes freqüents** sobre el contingut ja publicat.
- 💡 **Butlletí setmanal** automàtic.
- 💡 Redacció/ajuda per als missatges de l'AFA.
- ⛔ **Criteri ferm:** cap funcionalitat d'IA calcula dates ni inventa dades.
  Les dades dures sempre vénen del contingut publicat pel centre.
- 💡 Documentar a transparència "com s'usa la IA" quan arribi el moment.

## Publicació i governança ✅

- ✅ Repositori **públic a GitHub** + mirall privat a Forgejo.
- ✅ Licència **MIT**; README genèric reutilitzable per altres AFA.
- ✅ Documentació de **transparència** pública (dades, límits, per què Telegram).
- ✅ Guia pas a pas per muntar bot i grup (reutilitzable).
- ✅ **Idioma configurable** (i18n: ca per defecte; es, en inclosos).
- ✅ Flux **OpenSpec** perquè altres proposin canvis.
- 💡 **Multicentre**: cada AFA desplega la seva instància amb el seu `config.yaml`.

## Reutilització per altres associacions 💡

- 💡 Plantilla de desplegament (Docker + config d'exemple) documentada.
- 💡 Guia de "com adaptar-ho a un altre centre/idioma".
- 💡 Possible **botó de desplegament** (un clic) o imatge publicada.

## Futur — altres canals ⛔/💡

- 💡 **Sortida addicional per WhatsApp** (comunitat amb subgrups):
  - Requereix la **WhatsApp Business Platform**: de pagament, empresa
    verificada i plantilles aprovades.
  - Un pont no oficial (WhatsApp Web) **no es recomana** (vulnera ToS, fràgil).
  - Comportaria una capa de **publicadors intercanviables**.
- 💡 Sortida per **correu** o **web de l'AFA** si el projecte creix.

---

## Ordre suggerit d'evolució

```
Fase A ✅ ─► Fase B ✅/🟡 ─► Fase C (consulta) ─► Fase D (IA)
                              │
                              ├─ Decidir model de topics per curs
                              ├─ Bot 1:1 amb preferència de curs
                              └─ Subscripcions per tipus

transversal: multicentre, WhatsApp (si cal), plantilla reutilitzable
```

## Idees sense madurar (parking)

- Predicció/recordatoris ("demà cal portar X").
- Resum "el més important del mes per al teu curs".
- Integració amb el calendari del mòbil (iCal).
- Traducció de la documentació del projecte (ara només en català).
- Mètriques d'ús agregades i anònimes (quants avisos, sense perfilar ningú).
- **Menú del menjador — xarxa de seguretat**: si el parser del PDF falla (canvi
  de plantilla del centre), avisar l'admin per Telegram per revisar-lo a mà.
  Es descarta fer servir IA per extreure els plats (risc d'inventar dades;
  criteri ferm de la Fase D).
