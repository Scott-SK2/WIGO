# Architecture technique

Référence : cahier des charges v1.2, §8 et §9.

## Vue d'ensemble

```
┌────────────┐   HTTPS /api/v1 (JSON, JWT)   ┌─────────────────────┐
│  Web Next  │ ───────────────────────────▶  │  API Django + DRF    │ ──▶ PostgreSQL 16 + PostGIS
│  (SSR/PWA) │                               │  /api/v1, OpenAPI    │ ──▶ Redis (Celery broker)
└────────────┘                               └─────────┬───────────┘
┌────────────┐                                         │ tâches
│ Mobile Expo│  (phase 2, mêmes types TS)              ▼
└────────────┘                               Celery worker + beat : e-mails, médias, relances,
                                             archivage, newsletter, imports
```

- **Web** (`apps/web`) : Next.js App Router, rendu serveur pour le SEO (métadonnées, `schema.org/Event`,
  sitemap, routes localisées `/fr/evenements/…`, `/nl/evenementen/…`, `/en/events/…`), PWA (manifest,
  service worker, icônes maskable). Les appels API serveur passent par `API_URL`, les appels navigateur par
  `NEXT_PUBLIC_API_URL`.
- **API** (`apps/api`) : apps Django par domaine métier.

| App | Responsabilité | Entités (§9.1) |
| --- | --- | --- |
| `core` | enums, pagination curseur, erreurs structurées, audit, sécurité des URL, permissions | — |
| `accounts` | inscription, vérification e-mail, JWT (rotation + liste noire), réinitialisation, préférences, export / suppression | User, AccountToken |
| `organizations` | organisations, membres (propriétaire / éditeur), revendication de page | Organization, OrganizationMember, OwnershipClaim |
| `catalog` | taxonomie traduite, communes et quartiers (géométries), lieux, liste blanche billetteries | Category, Tag, Area, Venue, TicketingDomain |
| `events` | événements, séances, médias, favoris, statistiques, machine à états, recherche, ICS | Event, EventOccurrence, EventMedia, Favorite, EventDailyStat |
| `moderation` | signalements, décisions motivées (DSA), journal d'audit, doublons, suspension | Report, ModerationDecision, AuditLog |
| `engagement` | newsletter double opt-in, sélection du week-end, sources d'import | NewsletterSubscription, WeekendSelection, ImportSource, ImportRun |

## Règles métier implémentées (§6)

| Règle | Où |
| --- | --- |
| RG-02 e-mail vérifié avant publication | `core.permissions.HasVerifiedEmail` |
| RG-04 modération selon le niveau de confiance | `events.workflow.requires_moderation` |
| RG-05 / RG-07 non approuvé ou terminé = invisible | `Event.objects.public()` |
| RG-06 fin > début | contrainte SQL `occurrence_ends_after_start` + sérialiseur |
| RG-10 permissions côté serveur | `Event.can_edit`, vues `EventManageViewSet` (404 hors périmètre) |
| RG-11 modification importante (annexe A.2) | `events.workflow.is_major_change` / `after_edit` |
| RG-12 annulation visible | fiche publique servie pour `CANCELLED` |
| RG-13 séances indépendantes | `EventOccurrence` |
| RG-19 fuseau | UTC en base, `timezone` IANA par séance, filtres calculés en Europe/Brussels |
| RG-20 doublons | `moderation.services.find_duplicates` (pg_trgm) |
| RG-21 billetterie HTTPS + liste blanche | `core.urlsafety`, `catalog.TicketingDomain`, `workflow.evaluate_ticketing_link` |
| RG-23 événements longs | annotation `is_long`, tri `long_group` |
| RG-24 en ligne hors carte / rayon | `events.search.apply_filters` |
| RG-25 catégories | validation sérialiseur + `validate_ready_for_submission` |
| RG-26 18+ | `requires_moderation` |
| RG-27 revendication | `organizations.services.decide_claim` |
| Annexe A.3 suspension | `moderation.services.check_suspension` |
| Annexe A.4 conservation | `accounts.services.anonymize_user`, tâches planifiées à compléter (purge comptes inactifs) |

Statuts : `DRAFT → PENDING_REVIEW | PUBLISHED → CHANGES_REQUESTED / REJECTED / CANCELLED → ARCHIVED`.
Toutes les transitions passent par `events/workflow.py` et sont journalisées dans `AuditLog`.

## Recherche (§5.1)

PostgreSQL Full Text Search avec une configuration `wigo_simple` (dictionnaire `simple` + `unaccent`) créée en
migration. Le vecteur est pondéré : titre (A), catégorie / organisateur / lieu / tags (B), description (C).
Chaque terme est recherché par préfixe (`jaz` → `jazz`). Filtres combinables, pagination par curseur stable,
tri par date (ponctuels avant les événements longs), pertinence ou distance (PostGIS `dwithin`).

## Sécurité (§8.2)

Argon2, JWT access 15 min / refresh 14 j avec rotation et liste noire, CORS restrictif, limitation de débit
par portée (auth, newsletter, signalement, soumission), validation HTTPS + anti-SSRF des URL externes,
uploads limités (8 Mo, JPEG/PNG/WebP) et retraités (EXIF supprimé, WebP), en-têtes de sécurité, réponses
d'erreur homogènes `{"error": {code, message, details}}`.

## Environnements (§8.3)

`wigo.settings.dev` / `test` / `prod`. Secrets via variables d'environnement (`.env.example`). Médias en
local (dev) ou Cloudflare R2 (`MEDIA_BACKEND=r2`). CI GitHub Actions : lint, migrations, tests sur PostGIS,
OpenAPI, typecheck/lint/build du web, build des images Docker.
