import type { Metadata, Viewport } from "next";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ServiceWorker } from "@/components/ServiceWorker";
import { routing } from "@/i18n/routing";

import "../globals.css";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "brand" });
  return {
    metadataBase: new URL(SITE),
    title: { default: `WIGO — ${t("tagline")}`, template: "%s · WIGO" },
    description: "Événements et sorties à Bruxelles, en FR, NL et EN.",
    applicationName: "WIGO",
    manifest: "/manifest.webmanifest",
    icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }, { url: "/icons/icon-192.png", sizes: "192x192" }], apple: "/apple-touch-icon.png" },
    appleWebApp: { capable: true, title: "WIGO", statusBarStyle: "default" },
    alternates: { languages: { fr: `${SITE}/fr`, nl: `${SITE}/nl`, en: `${SITE}/en`, "x-default": `${SITE}/fr` } },
    openGraph: { type: "website", siteName: "WIGO", locale },
  };
}

export const viewport: Viewport = { themeColor: "#A2694F", width: "device-width", initialScale: 1 };

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return (
    <html lang={locale}>
      <body className="flex min-h-screen flex-col">
        <NextIntlClientProvider>
          <Header />
          <main id="contenu" className="flex-1">{children}</main>
          <Footer />
          <ServiceWorker />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
