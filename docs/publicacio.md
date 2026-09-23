# Flux de publicació del repositori

Guia genèrica per publicar el projecte. Cada qui adapta el seu remot a la seva
plataforma (GitHub, GitLab, Forgejo…).

## Remots

Els remots són **concrets de cada desplegament** i no es versionen. Defineix-los
al teu entorn:

```bash
git remote add origin <URL-del-teu-repositori>
```

Si vols mantenir un **mirall privat** (p. ex. una instància pròpia) mentre
treballes, afegeix-lo com a remot addicional:

```bash
git remote add mirror <URL-del-mirall>
```

> Els detalls del teu entorn concret (URLs, hosts, usuaris) no han de viure en
> aquest fitxer del repositori públic.

## Documentació pública

La documentació del servei (transparència, guia, full de ruta) viu **dins el
repositori**, així que la plataforma la publica com a pàgina web navegable i amb
historial. Les URLs de referència es poden citar des del canal de Telegram o des
de l'associació.

## Preparar una versió pública

Abans de fer públic el repositori:

1. **Auditoria de secrets** — cap token ni clau al contingut versionat:
   ```bash
   git grep -nIE 'bot[0-9]{6,}:[A-Za-z0-9_-]{20,}|BEGIN .*PRIVATE KEY|api[_-]?key' || echo "cap coincidència"
   git check-ignore -v .env config.yaml state/   # han d'aparèixer ignorats
   ```
2. **Revisar el que es versiona**:
   ```bash
   git status --porcelain
   git ls-files
   ```
   No hi ha d'haver `.env`, `config.yaml`, `state/` ni `local/`.
3. **Comprovar README i LICENSE** presents i correctes.
4. Fer el push i verificar que el repositori és públic i que no exposa secrets.

> Si mai es filtrés un secret, **rotar-lo** (no n'hi ha prou d'esborrar el
> fitxer: queda a l'historial).

## Primera publicació

```bash
git add -A
git commit -m "Primera versió del servei d'avisos"
git push -u origin main
```

Crea el repositori **buit** (sense README ni .gitignore) abans del push.
