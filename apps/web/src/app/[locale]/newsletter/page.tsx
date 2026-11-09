import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { NewsletterForm } from "@/components/NewsletterForm";
import { api } from "@/lib/api";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("newsletter");
  return { title: t("title"), description: t("text") };
}

export default async function NewsletterPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [t, areas] = await Promise.all([getTranslations("newsletter"), api.areas()]);
  return (
    <div className="container-wigo max-w-2xl py-10">
      <p className="label-caps text-brique">Newsletter</p>
      <h1 className="mt-2 text-4xl sm:text-5xl">{t("title")}</h1>
      <p className="mt-4 text-lg text-gris">{t("text")}</p>
      <div className="panel mt-8"><NewsletterForm areas={areas} /></div>
    </div>
  );
}
