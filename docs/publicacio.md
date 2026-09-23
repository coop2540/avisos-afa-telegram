# Flux de publicació del repositori

El projecte es publica a **GitHub** (públic). Opcionalment, es pot mantenir un
**mirall privat** a Forgejo (instància pròpia) mentre es treballa.

## Remots

| Remot | Destinació | Visibilitat | Ús |
|-------|-----------|-------------|-----|
| `origin` | GitHub (`git@github.com:coop2540/avisos-afa-telegram.git`) | Públic | Enviament habitual |
| `forgejo` | Forgejo propi (`ssh://git@192.168.0.18:222/jordan/avisos-afa-telegram.git`) | Privat | Mirall privat (opcional) |

Afegir els remots:

```bash
git remote add origin git@github.com:coop2540/avisos-afa-telegram.git
# Mirall privat (opcional):
git remote add forgejo ssh://git@192.168.0.18:222/jordan/avisos-afa-telegram.git
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

## Primer enviament

```bash
git add -A
git commit -m "Primera versió del servei d'avisos (fase A)"
git push -u origin main
```

El repositori de GitHub s'ha de crear **buit** (sense README ni .gitignore) i
públic abans del push.
