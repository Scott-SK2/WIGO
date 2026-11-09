# Backlog P0 — état d'avancement

Tickets du cahier des charges v1.2 (§11.1). Légende : ✅ livré · 🟡 partiel · ⬜ à faire.
Les points sont ceux du cahier des charges.

## EP-01 Fondations

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| INF-01 | Monorepo web / mobile / API | 5 | ✅ | `apps/api`, `apps/web`, `packages/shared`, pnpm workspaces ; `apps/mobile` au sprint 9 |
| INF-02 | Docker et configurations | 5 | ✅ | Dockerfiles API + web, `docker-compose.yml`, `.env.example`, settings dev/test/prod |
| INF-03 | PostgreSQL / PostGIS et migrations | 3 | ✅ | Extensions postgis, unaccent, pg_trgm, config FTS ; migrations initiales |
| INF-04 | CI, lint et tests | 5 | ✅ | GitHub Actions (ruff, makemigrations --check, pytest sur PostGIS, OpenAPI, eslint, tsc, next build, images Docker) |
| INF-05 | Stockage médias et secrets | 3 | 🟡 | Backend R2 configuré (`MEDIA_BACKEND=r2`), secrets par env ; compte R2 à créer |
| INF-06 | Staging, logs et monitoring | 5 | 🟡 | Logs JSON structurés ; hébergeur, Sentry/alertes et staging à provisionner |
| WEB-01 | PWA installable | 3 | ✅ | manifest, service worker, icônes maskable, page hors ligne |

## EP-02 Comptes

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| AUTH-01 | Inscription e-mail | 5 | ✅ | `POST /auth/register`, validation CGU, e-mail de vérification |
| AUTH-02 | Vérification e-mail | 3 | ✅ | Jetons hachés, usage unique, TTL 48 h |
| AUTH-03 | Sessions et authentification API | 5 | ✅ | JWT 15 min / 14 j, rotation, liste noire, logout |
| AUTH-04 | Réinitialisation mot de passe | 3 | ✅ | Réponse neutre, TTL 2 h |
| AUTH-05 | Profil, langue, préférences | 3 | ✅ | `/auth/me`, `/me/preferences` (quartiers, envies, notifications) |
| AUTH-06 | Export et suppression des données | 5 | ✅ | Export JSON, anonymisation ; purge comptes inactifs (A.4) à planifier |
| AUTH-07 | Connexion sociale + Sign in with Apple | 5 | ⬜ P1 | |

## EP-03 Organisateurs

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| ORG-01 | Profil individuel | 3 | ✅ | nom affiché, langue, niveau de confiance |
| ORG-02 | Créer une organisation | 5 | ✅ | créateur = propriétaire |
| ORG-03 | Permissions propriétaire / éditeur | 5 | ✅ | gestion des membres réservée au propriétaire, tests d'isolation |
| ORG-04 | Profil public organisateur | 3 | ✅ | API + page web `/organisateurs/[slug]` |
| MOD-01 | Niveaux de confiance | 3 | ✅ | Nouveau → Confirmé après 3 approbations, rétrogradation sur signalement fondé |
| CAT-03 | Revendication de page | 5 | ✅ | API organisateur + décision modérateur ; écran back-office à faire (ADM-03) |
| ORG-05 | Vérification d'organisation et badge | 5 | 🟡 P1 | champ et badge présents, processus de vérification BCE manuel via admin |
| ORG-06 | Invitations de collaborateurs | 5 | ⬜ P1 | |

## EP-04 Publication

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| EVT-01 | Modèles événement / séance / lieu | 8 | ✅ | |
| EVT-02 | CRUD API et permissions | 8 | ✅ | brouillon, édition, soumission, annulation, confirmation, stats, médias |
| EVT-03 | Formulaire web en 5 étapes | 8 | ⬜ | sprint 4 ; page `/publier` d'accueil livrée |
| EVT-04 | Formulaire mobile | 8 | ⬜ P0-M | |
| EVT-05 | Brouillon automatique et prévisualisation | 5 | 🟡 | API (`draft_step`, erreurs de complétude) ; UI au sprint 4 |
| EVT-06 | Upload et optimisation des médias | 5 | ✅ | limites taille/type, EXIF supprimé, WebP, droits confirmés |
| EVT-07 | Dates, fuseaux, séances multiples | 8 | ✅ | |
| EVT-08 | Tarification informative | 3 | ✅ | gratuit / payant / participation libre, fourchette, EUR |
| EVT-09 | Lien billetterie externe | 3 | ✅ | HTTPS, anti-SSRF, liste blanche, redirection comptée `/events/{slug}/out` |
| EVT-10 | Modification, annulation, archivage | 5 | ✅ | RG-11, RG-12, archivage horaire |
| EVT-11 / EVT-12 | Duplication, récurrence avancée | — | ⬜ P1 | |

## EP-05 Recherche et carte

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| SRC-01 | API de recherche paginée | 8 | ✅ | curseur stable, URL partageables |
| SRC-02 | Recherche texte | 5 | ✅ | FTS pondéré, sans accents, préfixes |
| SRC-03 | Filtres dates et heures | 5 | ✅ | today / tomorrow / weekend / date / plage / heure |
| SRC-04 | Filtres catégorie, prix, langue, accessibilité | 5 | ✅ | + en famille, format, en ligne |
| SRC-05 | Commune, quartier, géolocalisation, rayon | 8 | ✅ | hiérarchie de territoires, `dwithin` |
| SRC-06 | Tri et classement (événements longs) | 5 | ✅ | |
| SRC-07 | Explorer web | 8 | ✅ | filtres combinables, états vides, pagination |
| SRC-08 / SRC-09b | Explorer et carte mobile | — | ⬜ P0-M | |
| SRC-09a | Carte web | 8 | ⬜ | sprint 7 (MapLibre, tuiles à contractualiser) |
| SRC-10 | États vides et suggestions | 3 | ✅ | |

## EP-06 Fiches et rétention

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| UI-01 | Fiche web et SEO | 8 | ✅ | métadonnées, hreflang, `schema.org/Event`, sitemap |
| UI-02 | Fiche mobile | 5 | ⬜ P0-M | |
| UI-03 | Cartes événement réutilisables | 5 | ✅ | 4:5, dégradé, badges, cœur |
| UI-04 | Partage et liens profonds | 5 | 🟡 | Web Share / copie ; liens profonds mobiles en phase 2 |
| UI-06 | Export calendrier ICS / Google / Apple | 3 | ✅ | |
| UI-07 | Écran Agenda (favoris) | 3 | ✅ | |
| RET-01 | Favoris locaux sans compte | 3 | ✅ | localStorage, fusion à la connexion |
| RET-02 | Newsletter hebdomadaire | 5 | ✅ | double opt-in, désinscription 1 clic, génération depuis la sélection, envoi jeudi 10h (beat) ; template HTML et fournisseur UE à choisir |
| UI-05 | Favoris synchronisés | 5 | ✅ P1 | API `/me/favorites` livrée |
| GRO-02 | Alertes et rappels push | 8 | ⬜ P1 | |

## EP-07 Back-office, modération et catalogue

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| ADM-01 | File de modération | 8 | ✅ API | `GET/POST /admin/moderation` avec niveau de confiance, alerte lien, doublons |
| ADM-02 | Décisions et motifs (DSA) | 5 | ✅ | motifs codifiés, commentaire, historique |
| ADM-03 | Interface d'administration | 8 | 🟡 | Django admin complet ; back-office dédié (SCR-10) au sprint 7 |
| ADM-04 | Signalements | 5 | ✅ | anonymes ou connectés, traitement, suspension A.3 |
| ADM-05 | Audit des actions | 5 | ✅ | `AuditLog` + `GET /admin/audit` |
| ADM-06 | Gestion des catégories | 3 | ✅ | Django admin, référentiel `seed_reference` |
| ADM-07 | Anti-spam et quotas | 5 | ✅ | quota quotidien compte Nouveau, limitation de débit |
| ADM-08 | Détection des doublons | 5 | ✅ | pg_trgm, même lieu, même jour |
| ADM-09 | Sélection du week-end | 3 | ✅ API | |
| CAT-01 | Outil de saisie interne | 5 | 🟡 | rôle éditeur catalogue + `source=INTERNAL` ; formulaire condensé (SCR-12) à faire |
| CAT-02 | Import partenaire | 8 | 🟡 | modèles ImportSource/ImportRun, registre de connecteurs ; UiTdatabank après accord publiq |
| TRU-01 | Liste blanche billetteries | 3 | ✅ | |
| TRU-02 | Relance fraîcheur et archivage | 3 | ✅ | tâches Celery beat |
| ADM-10 | Générateur de visuels | 5 | ⬜ P1 | |

## EP-08 Langues et accessibilité

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| I18N-01 | FR / NL / EN web | 5 | ✅ | next-intl, routes localisées, hreflang |
| I18N-02 | FR / NL / EN mobile | 5 | ⬜ P0-M | |
| I18N-03 | Traductions système et catégories | 5 | ✅ | taxonomie et territoires trilingues, e-mails FR/NL/EN |
| I18N-05 | Audit d'accessibilité | 8 | 🟡 | cibles ≥ 44 px, focus visible, libellés, contraste ; audit WCAG 2.2 AA formel à planifier (sprint 8) |

## EP-09 Design, contenu, légal et mesure

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| DES-01 | Maquettes et design system | 8 | 🟡 | jetons, typographies, composants de base ; maquettes définitives à produire |
| BRD-01 | Logo, icône d'app, kit réseaux | 3 | 🟡 | logo rond et icônes PWA provisoires |
| LEG-01 | Pages légales et politique de modération | 3 | 🟡 | squelettes publiés, [À COMPLÉTER] juridiques |
| MAIL-01 | E-mails transactionnels FR/NL/EN | 3 | 🟡 | texte brut ; gabarits HTML à faire |
| SEO-01 | Sitemap, données structurées, pages catégorie et quartier | 5 | ✅ | |
| ANA-01 | Analytics et tableau KPI | 3 | 🟡 | `GET /admin/stats` ; Plausible/Matomo à brancher |

## EP-10 Recette et livraison

| Ticket | Travail | Pts | État | Notes |
| --- | --- | --- | --- | --- |
| QA-01 | Tests des règles métier | 8 | ✅ | `tests/test_workflow.py` |
| QA-02 | Tests API et permissions | 8 | ✅ | `tests/test_permissions_api.py`, `test_search_api.py`, `test_auth.py`, `test_engagement_moderation.py` (60 tests) |
| QA-03 | Tests E2E | 8 | ⬜ | Playwright à ajouter au web |
| QA-04 / QA-05 / QA-06 / QA-08a / QA-09 | Performance, sécurité, sauvegarde, déploiement, documentation d'exploitation | — | ⬜ | voir `docs/exploitation.md` (plan) |
