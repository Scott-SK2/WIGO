import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Link } from "@/i18n/navigation";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("publish");
  return { title: t("title") };
}

/** SCR-08 : point d'entrée de la publication. Le formulaire en 5 étapes (EVT-03) est planifié au sprint 4. */
export default async function PublishPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("publish");
  const steps = t.raw("steps") as string[];
  return (
    <div className="container-wigo max-w-3xl py-10">
      <h1 className="text-4xl sm:text-5xl">{t("title")}</h1>
      <p className="mt-4 text-lg text-gris">{t("intro")}</p>
      <ol className="mt-8 flex flex-wrap gap-2">
        {steps.map((s, i) => (
          <li key={s} className="chip"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-or text-xs font-bold">{i + 1}</span>{s}</li>
        ))}
      </ol>
      <div className="panel mt-8">
        <p className="font-semibold">{t("loginFirst")}</p>
        <Link href="/compte/connexion" className="btn-primary mt-4">{t("loginFirst").split(" ")[0]}</Link>
        <p className="mt-6 text-sm text-gris">{t("comingSoon")}</p>
      </div>
      <p className="mt-8 text-sm text-gris">{t("rules")}</p>
    </div>
  );
}
