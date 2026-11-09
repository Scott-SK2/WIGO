import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AgendaClient } from "./AgendaClient";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("agenda");
  return { title: t("title"), robots: { index: false } };
}

/** SCR-06 : Agenda — favoris locaux (RET-01), export calendrier. */
export default async function AgendaPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("agenda");
  return (
    <div className="container-wigo py-8">
      <h1 className="section-title">{t("title")}</h1>
      <p className="mt-2 max-w-xl text-gris">{t("intro")}</p>
      <AgendaClient />
    </div>
  );
}
