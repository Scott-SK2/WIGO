# API WIGO — guide rapide

Base : `/api/v1`. JSON UTF-8, pagination par curseur (`next`, `previous`, `results`), erreurs
`{"error": {"code", "message", "details"}}`. Schéma OpenAPI : `GET /api/schema/`, interface Swagger : `/api/docs/`.
Fichier versionné : `packages/shared/openapi.yaml`.

## Authentification

`Authorization: Bearer <access>`. Obtenir une paire avec `POST /auth/login {email, password}`, rafraîchir avec
`POST /auth/refresh {refresh}` (rotation : l'ancien refresh est révoqué), révoquer avec `POST /auth/logout {refresh}`.

| Méthode | Route | Rôle |
| --- | --- | --- |
| POST | /auth/register | inscription (`email`, `password`, `language`, `accept_terms`) |
| POST | /auth/verify-email | `{token}` reçu par e-mail |
| POST | /auth/password-reset, /auth/password-reset/confirm | réinitialisation |
| GET/PATCH/DELETE | /auth/me | profil, suppression (anonymisation) |
| GET | /auth/me/export | export JSON des données |
| GET/PATCH | /me/preferences | quartiers, envies, notifications |

## Public

| Méthode | Route | Paramètres |
| --- | --- | --- |
| GET | /events | `q, area, date (today|tomorrow|weekend|AAAA-MM-JJ), date_from, date_to, after, category, free, paid, max_price, lang, format, include_online, accessible, family, lat, lon, radius_km, sort (relevance|date|distance), cursor, page_size` |
| GET | /events/{slug} | fiche (publiée, annulée ou archivée) |
| GET | /events/{slug}/ics | iCalendar |
| GET | /events/{slug}/out | redirection billetterie comptée |
| GET | /events/counts | compteurs par catégorie |
| GET | /home | blocs de l'accueil |
| GET | /categories, /areas, /venues?q= | référentiels |
| GET | /organizations/{slug} | profil public |
| GET | /selection | sélection de la semaine |
| POST | /newsletter | `{email, area?, language, consent}` → double opt-in |
| GET | /newsletter/confirm?token=, /newsletter/unsubscribe?token= | |
| POST | /reports | `{event|organization, category, description?, reporter_email?}` |

## Organisateur (e-mail vérifié requis)

| Méthode | Route | Rôle |
| --- | --- | --- |
| POST | /events | brouillon (séances imbriquées `occurrences[]`, catégories par slug, `venue` par id, `organization` par slug) |
| GET | /events/mine?status= | mes événements |
| GET/PATCH/DELETE | /events/{id} | vue organisateur, édition, suppression d'un brouillon |
| POST | /events/{id}/submit · /cancel · /confirm · /back-to-draft | transitions |
| GET | /events/{id}/stats | vues, clics billetterie, favoris, ajouts calendrier |
| POST | /events/{id}/media · DELETE /events/{id}/media/{media_id} | visuels (multipart, `rights_confirmed=true`) |
| POST | /venues | nouveau lieu (`lat`, `lon` géocodés côté client) |
| POST/PATCH | /organizations, /organizations/{slug} | création, édition |
| POST/DELETE | /organizations/{slug}/members | `{email, role}` (propriétaire uniquement) |
| POST | /organizations/{slug}/claim | `{evidence}` |
| GET/POST/DELETE | /me/favorites, /me/favorites/{slug} | favoris synchronisés ; `POST {events: [slugs]}` fusionne les favoris locaux |

## Modération et administration

| Méthode | Route | Rôle |
| --- | --- | --- |
| GET/POST | /admin/moderation | file `?status=PENDING_REVIEW` ; décision `{event, action (APPROVE|REJECT|REQUEST_CHANGES|UNPUBLISH), reason_code, comment}` |
| GET | /admin/moderation/reasons | motifs codifiés |
| GET | /admin/reports · POST /admin/reports/{id}/decide `{founded, note}` | signalements |
| GET | /admin/claims · POST /admin/claims/{id}/decide `{approve, note}` | revendications |
| GET/POST | /admin/selection | sélection du week-end `{week_start?, title, intro, events: [{event, order, blurb}], send_status}` |
| GET/POST | /admin/imports | sources partenaires, déclenchement `{source}` |
| GET | /admin/audit?action=&target_id= | journal |
| GET | /admin/stats | KPI (administrateur) |

## Comptes de démonstration (`manage.py seed_demo`)

`admin@wigo.local / wigo-admin-2026` (admin), `modo@wigo.local / wigo-modo-2026` (modérateur),
`orga.confirme@wigo.local` et `orga.nouveau@wigo.local` / `wigo-demo-2026` (organisateurs Confirmé et Nouveau).
