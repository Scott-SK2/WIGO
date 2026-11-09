import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { ReportForm } from "./ReportForm";

/** SCR-11 / LEG-01 : pages légales (squelettes à valider juridiquement) et formulaire de signalement. */
const PAGES: Record<string, { key: "privacy" | "terms" | "moderation" | "report" | "contact"; body: string[] }> = {
  confidentialite: {
    key: "privacy",
    body: [
      "Responsable du traitement : Genius Harmony [À COMPLÉTER : adresse, numéro BCE, e-mail DPO].",
      "Données traitées : compte (e-mail, mot de passe haché, langue), préférences (quartiers, envies), favoris synchronisés, événements publiés, signalements, abonnement newsletter (e-mail, consentement horodaté). Les favoris sans compte restent sur votre appareil.",
      "Finalités et bases légales : fourniture du service (contrat), newsletter (consentement, double opt-in), modération et sécurité (intérêt légitime et obligations légales), statistiques sans cookie tiers.",
      "Conservation : comptes inactifs relancés après 24 mois et supprimés après 36 mois ; journaux d'audit et décisions de modération 3 ans ; newsletter jusqu'à la désinscription.",
      "Vos droits : accès, rectification, effacement, portabilité (export JSON depuis votre compte), opposition. Contact : [À COMPLÉTER]. Réclamation possible auprès de l'Autorité de protection des données.",
      "Géolocalisation : uniquement après votre autorisation explicite, jamais stockée côté serveur.",
    ],
  },
  cgu: {
    key: "terms",
    body: [
      "WIGO est un service gratuit de découverte et de publication d'événements publics à Bruxelles, édité par Genius Harmony.",
      "La consultation est libre. La publication requiert un compte avec e-mail vérifié. L'organisateur garantit l'exactitude des informations et déclare détenir les droits sur les visuels, qu'il concède à WIGO sous licence d'affichage non exclusive, révocable sur notification.",
      "WIGO ne vend aucun billet : les liens de billetterie renvoient vers des sites tiers, sous leur responsabilité.",
      "Les contenus payés (« Partenaire », « Sélection WIGO ») sont toujours signalés.",
      "WIGO peut refuser, corriger ou retirer un contenu conformément à sa politique de modération, avec exposé des motifs et possibilité de recours.",
    ],
  },
  moderation: {
    key: "moderation",
    body: [
      "Critères d'approbation : événement public ou ouvert sur inscription, date et lieu réels, titre et description compréhensibles, pas de promotion d'activités illégales, discriminatoires ou haineuses, pas de publicité commerciale déguisée.",
      "Niveaux de confiance : Nouveau (chaque événement relu avant publication), Confirmé (publication immédiate, contrôle a posteriori), Vérifié (organisation contrôlée, badge visible). Un signalement fondé ramène au niveau Nouveau.",
      "Délai cible de traitement : 24 h ouvrées pendant le pilote, 12 h au lancement.",
      "Suspension : 7 jours après 2 signalements fondés en 30 jours ; définitive en cas de fraude ou de contenu illégal, avec exposé des motifs et recours interne.",
      "Point de contact unique (DSA) : [À COMPLÉTER].",
    ],
  },
  signalement: { key: "report", body: [] },
  contact: { key: "contact", body: ["Genius Harmony — [À COMPLÉTER : adresse postale, e-mail de contact, e-mail presse].", "Point de contact DSA : [À COMPLÉTER]."] },
};

export function generateStaticParams() {
  return Object.keys(PAGES).map((page) => ({ page }));
}

export async function generateMetadata({ params }: { params: Promise<{ page: string }> }): Promise<Metadata> {
  const { page } = await params;
  const def = PAGES[page];
  if (!def) return {};
  const t = await getTranslations("legal");
  return { title: t(def.key) };
}

export default async function LegalPage({ params, searchParams }: { params: Promise<{ locale: string; page: string }>; searchParams: Promise<{ event?: string }> }) {
  const { locale, page } = await params;
  setRequestLocale(locale);
  const def = PAGES[page];
  if (!def) notFound();
  const t = await getTranslations("legal");
  const { event } = await searchParams;
  return (
    <div className="container-wigo max-w-3xl py-12">
      <p className="label-caps text-brique">{t("draft")}</p>
      <h1 className="mt-3 text-4xl">{t(def.key)}</h1>
      {def.key === "report" ? (
        <div className="mt-8"><ReportForm event={event} /></div>
      ) : (
        <div className="mt-6 space-y-4 text-[17px] leading-relaxed">
          {def.body.map((p) => <p key={p}>{p}</p>)}
        </div>
      )}
    </div>
  );
}
