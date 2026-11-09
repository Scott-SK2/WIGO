# WIGO — Trouve ta prochaine sortie.

Plateforme web et mobile de découverte et de publication d'événements à Bruxelles, en FR · NL · EN.
Porteur : Genius Harmony. Référence : [Cahier des charges v1.2](docs/cahier-des-charges-v1.2.pdf).

> **Où est-ce que je vais aujourd'hui ?** Tout ce qui se passe à Bruxelles ce soir et ce week-end, y compris
> les petits événements qu'on ne trouve pas ailleurs, en trois langues, sans compte Facebook.

## Monorepo

```
apps/api        Django 5 + DRF + PostGIS + Celery        → /api/v1, OpenAPI, back-office Django admin
apps/web        Next.js 15 + TypeScript + Tailwind       → web responsive installable (PWA), FR/NL/EN, SSR/SEO
apps/mobile     (phase 2) React Native + Expo Router      → à créer au sprint 9
packages/shared Types TypeScript générés depuis l'OpenAPI → partagés web / mobile
docs/           Cahier des charges, architecture, backlog, plan de sprints, exploitation
infra/          Déploiement (à compléter : staging / prod)
```

## Démarrage rapide

### Avec Docker (recommandé)

```bash
cp .env.example .env
make up            # PostGIS, Redis, API (:8000), worker, beat, web (:3000)
docker compose exec api python manage.py seed_demo   # taxonomie, quartiers, événements de démo
```

- Web : http://localhost:3000 · API : http://localhost:8000/api/v1 · Docs API : http://localhost:8000/api/docs/
- Back-office : http://localhost:8000/admin/ (après `seed_demo` : `admin@wigo.local` / `wigo-admin-2026`)

### En local sans Docker

Prérequis : Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, PostgreSQL 16 avec PostGIS, Redis, GDAL/GEOS/PROJ.

```bash
# API
cd apps/api
cp ../../.env.example .env            # ajuster DATABASE_URL
uv venv && uv pip install -r pyproject.toml --extra dev
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

```bash
# Web
pnpm install
pnpm dev:web                           # http://localhost:3000 (API attendue sur :8000)
```

## Commandes utiles

| Commande | Rôle |
| --- | --- |
| `make api-test` | Tests de l'API (pytest, base PostGIS requise) |
| `make api-lint` | Lint et format (ruff) |
| `make schema` | Régénère `packages/shared/openapi.yaml` et les types TypeScript |
| `pnpm --filter @wigo/web typecheck` / `lint` / `build` | Qualité et build du web |
| `make api-seed` | Charge référentiel + jeu de démo |

## État d'avancement

Voir [docs/backlog.md](docs/backlog.md) (tickets P0 du cahier des charges avec leur statut) et
[docs/sprints.md](docs/sprints.md). Les décisions techniques sont consignées dans [docs/decisions.md](docs/decisions.md).

## Licence et marque

Code propriétaire Genius Harmony. La marque WIGO fait l'objet d'une vérification juridique (classes 9, 35, 38, 41) avant tout dépôt.
