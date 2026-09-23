# Flux de publicació del repositori

El projecte es publica en dues etapes: primer **privat** a Forgejo (instància
pròpia) per revisar com queda, i després **públic** a GitHub.

## Remots

| Remot | Destinació | Visibilitat | Ús |
|-------|-----------|-------------|-----|
| `origin` | Forgejo propi (`ssh://git@192.168.0.18:222/jordan/afa-elisabadia-avisos.git`) | Privat | Enviament habitual |
| `github` | GitHub (`git@github.com:<org>/afa-elisabadia-avisos.git`) | Públic | Publicació (posterior) |

Afegir els remots:

```bash
git remote add origin ssh://git@192.168.0.18:222/jordan/afa-elisabadia-avisos.git
# Quan toqui publicar:
git remote add github git@github.com:<org>/afa-elisabadia-avisos.git
```

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
   git ls-files   # després del primer commit
   ```
   No hi ha d'haver `.env`, `config.yaml` ni `state/`.
3. **Comprovar README i LICENSE** presents i correctes.
4. Fer el push a GitHub i verificar que el repo és públic i que no exposa
   secrets.

> Si mai es filtrés un secret, **rotar-lo** (no n'hi ha prou d'esborrar el
> fitxer: queda a l'historial).

## Primer enviament a Forgejo

```bash
git add -A
git commit -m "Primera versió del servei d'avisos (fase A)"
git push -u origin main
```

El repositori de Forgejo s'ha de crear **privat** (via API o interfície web)
abans del push.
