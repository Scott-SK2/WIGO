import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Logo } from "@/components/Logo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("about");
  return { title: t("title"), description: t("text") };
}

export default async function AboutPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("about");
  return (
    <div className="container-wigo max-w-3xl py-12">
      <Logo size={72} />
      <h1 className="mt-6 text-4xl sm:text-5xl">{t("title")}</h1>
      <p className="mt-5 text-lg leading-relaxed text-gris">{t("text")}</p>
    </div>
  );
}
