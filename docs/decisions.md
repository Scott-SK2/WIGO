# Registre des décisions techniques (ADR)

Format court : contexte → décision → conséquences. Toute modification de périmètre est inscrite ici,
estimée et validée avant implémentation (cahier des charges, annexe B).

## ADR-001 — Monorepo pnpm + uv

Un seul dépôt pour l'API (Python, géré par `uv`), le web et le futur mobile (pnpm workspaces), avec un paquet
`@wigo/shared` de types générés depuis l'OpenAPI. Permet un client typé commun web/mobile et une CI unique.

## ADR-002 — Deux vues sur la même ressource `/api/v1/events`

Le cahier des charges adresse les fiches publiques par `{slug}` et les mutations par `{id}`. Deux viewsets DRF
partagent le préfixe : l'UUID (gestion, authentifié) est résolu avant le slug (public). `GET /events` et
`POST /events` sont servis par une vue combinée. Hors périmètre, l'espace organisateur répond 404 (pas de fuite).

## ADR-003 — Recherche PostgreSQL FTS plutôt qu'un moteur dédié

Conforme à §8.1. Configuration `wigo_simple` (simple + unaccent), vecteur pondéré recalculé à la sauvegarde,
recherche par préfixe. Un moteur dédié ne sera envisagé que si la p95 < 500 ms n'est plus tenue. La
tolérance aux fautes (SRC-11, P1) pourra s'appuyer sur `pg_trgm`, déjà activé pour les doublons.

## ADR-004 — Dates en UTC, fuseau IANA par séance, logique « jour » en Europe/Brussels

Les presets Ce soir / Demain / Ce week-end sont calculés en Europe/Brussels côté API, pour que web et mobile
partagent exactement la même définition (week-end = vendredi 17h → dimanche 23h59).

## ADR-005 — Niveau de confiance porté par l'organisation si elle existe

Un compte Nouveau qui publie au nom d'une organisation Confirmée publie immédiatement : c'est l'organisation
qui est responsable. La rétrogradation sur signalement fondé frappe l'entité porteuse.

## ADR-006 — Un événement 18+ passe en modération sauf organisation Vérifiée

Interprétation de RG-26 (« visuel soumis à modération renforcée »). À confirmer avec le responsable de modération.

## ADR-007 — Favoris locaux en `localStorage`, fusion à la connexion

RET-01 P0 sans compte. À la connexion, les slugs locaux sont envoyés à `POST /me/favorites {events: [...]}`.

## ADR-008 — Next.js 15 (pas 16) et Tailwind 3 pour la phase 1

Versions majeures éprouvées au démarrage du projet ; montée de version planifiée en fin de phase 1.

## ADR-009 — Clic billetterie compté via une redirection API

`GET /api/v1/events/{slug}/out` incrémente `ticket_clicks` puis redirige (RG-17 : un clic n'est pas une vente).

## Décisions ouvertes (à trancher par le porteur)

- Hébergeur (API + Postgres managé), fournisseur e-mail UE, tuiles cartographiques, géocodeur hors Bruxelles.
- Responsable de modération et SLA.
- Accord publiq (UiTdatabank) et visit.brussels pour l'import.
- Slogans NL/EN à valider avec des locuteurs natifs.
