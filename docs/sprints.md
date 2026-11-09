# Plan de sprints (12 × 2 semaines)

D'après le cahier des charges §11.2. Cadence : 12 sprints de 2 semaines. Équipe de référence à confirmer.
Avec ~375 points P0 sur 8 sprints (~45 pts/sprint), il faut 3 à 4 développeurs, ou allonger la phase 1 à 10–12 sprints avec 2 développeurs.

## Phase 1 — Web

| Sprint | Livrable (cahier des charges) | Ce qui est déjà en place | Reste à faire |
| --- | --- | --- | --- |
| 1 | Socle technique, environnements, maquettes validées, dépôt de marque, domaines, comptes Apple/Google | Monorepo, Docker, PostGIS, CI, PWA, design tokens | Maquettes définitives (DES-01), vérification juridique du nom, réservation des domaines, comptes développeur |
| 2 | Comptes, organisations, niveaux de confiance | API complète (AUTH-01→06, ORG-01→04, MOD-01, CAT-03), écran connexion/inscription web | Écran « Espace organisateur » (SCR-09), gestion des membres dans l'UI |
| 3 | Modèles et API événements, outil de saisie interne, début du catalogue | Modèles, API, machine à états, recherche, ICS | Formulaire de saisie catalogue (SCR-12), contacts partenaires (publiq, visit.brussels), acquisition terrain |
| 4 | Formulaire de publication web, médias | API médias (upload, EXIF, WebP) | Formulaire 5 étapes avec brouillon auto et prévisualisation (EVT-03, EVT-05) |
| 5 | Recherche, filtres, géolocalisation, import partenaire | Recherche et filtres complets, Explorer web | Connecteur UiTdatabank (CAT-02), géocodage UrbIS pour les nouveaux lieux |
| 6 | Web public (accueil, explorer, fiche, SEO) → pilote fermé | Accueil, Explorer, Fiche, quartiers, SEO, sitemap | Design final, contenus, 10 organisateurs pilotes, ≥ 30 événements/jour |
| 7 | Carte, modération, signalements, sélection, newsletter, calendrier | API modération / signalements / sélection / newsletter, ICS | Carte web MapLibre (SRC-09a), back-office dédié (SCR-10), gabarits e-mail HTML |
| 8 | Langues, accessibilité, sécurité, recette → lancement public | FR/NL/EN, bases d'accessibilité, tests API | Audit WCAG, tests E2E, charge, sécurité, sauvegardes/restauration, documentation d'exploitation |

## Phase 2 — Application mobile (sprints 9–12)

Expo Router dans `apps/mobile`, types partagés via `packages/shared`. Onglets Accueil, Carte, Agenda, Explorer, Alertes.
Prérequis : comptes Apple (D-U-N-S) et Google ouverts au sprint 1, Sign in with Apple si connexion sociale.

## Definition of Done

Code relu, tests automatisés pertinents, permissions contrôlées, UX responsive conforme au design system,
chaînes traduites FR/NL/EN, documentation API et technique à jour, validation sur staging.
