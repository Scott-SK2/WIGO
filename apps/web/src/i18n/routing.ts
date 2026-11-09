import { defineRouting } from "next-intl/routing";

/** Routes localisées FR / NL / EN (§2.1 Langues, §10 SEO). */
export const routing = defineRouting({
  locales: ["fr", "nl", "en"],
  defaultLocale: "fr",
  localePrefix: "always",
  pathnames: {
    "/": "/",
    "/explorer": { fr: "/explorer", nl: "/verkennen", en: "/explore" },
    "/evenements/[slug]": { fr: "/evenements/[slug]", nl: "/evenementen/[slug]", en: "/events/[slug]" },
    "/organisateurs/[slug]": { fr: "/organisateurs/[slug]", nl: "/organisatoren/[slug]", en: "/organizers/[slug]" },
    "/organisateurs": { fr: "/organisateurs", nl: "/organisatoren", en: "/organizers" },
    "/quartiers": { fr: "/quartiers", nl: "/wijken", en: "/neighbourhoods" },
    "/agenda": "/agenda",
    "/publier": { fr: "/publier", nl: "/publiceren", en: "/publish" },
    "/newsletter": "/newsletter",
    "/newsletter/confirmation": "/newsletter/confirmation",
    "/newsletter/desinscription": { fr: "/newsletter/desinscription", nl: "/newsletter/uitschrijven", en: "/newsletter/unsubscribe" },
    "/compte/connexion": { fr: "/compte/connexion", nl: "/account/aanmelden", en: "/account/login" },
    "/compte/verification": { fr: "/compte/verification", nl: "/account/verificatie", en: "/account/verify" },
    "/compte/mot-de-passe": { fr: "/compte/mot-de-passe", nl: "/account/wachtwoord", en: "/account/password" },
    "/a-propos": { fr: "/a-propos", nl: "/over-ons", en: "/about" },
    "/legal/[page]": "/legal/[page]",
  },
});

export type AppPathname = keyof typeof routing.pathnames;
