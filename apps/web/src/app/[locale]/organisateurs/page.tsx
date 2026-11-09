import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Icon } from "@/components/Icon";
import { Link } from "@/i18n/navigation";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav");
  return { title: t("organizers") };
}

/** Page d'entrée organisateurs : proposition de valeur et accès à la publication. */
export default async function OrganizersPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [t, p] = await Promise.all([getTranslations("home"), getTranslations("publish")]);
  const steps = p.raw("steps") as string[];
  return (
    <div className="container-wigo py-10">
      <div className="panel bg-brique text-papier">
        <p className="label-caps text-sable">{t("publishCta")}</p>
        <h1 className="mt-2 text-4xl sm:text-5xl text-papier">{t("publishButton")}</h1>
        <p className="mt-4 max-w-2xl text-lg text-sable">{t("publishText")}</p>
        <Link href="/publier" className="btn mt-6 bg-papier text-encre hover:bg-creme">{t("publishButton")} <Icon name="arrow" size={16} /></Link>
      </div>
      <h2 className="section-title mt-12">{p("stepsTitle")}</h2>
      <ol className="mt-5 grid gap-3 sm:grid-cols-5">
        {steps.map((s, i) => (
          <li key={s} className="rounded-card border border-sable bg-white p-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-or font-bold">{i + 1}</span>
            <p className="mt-3 font-semibold">{s}</p>
          </li>
        ))}
      </ol>
      <p className="mt-8 max-w-3xl text-gris">{p("rules")}</p>
    </div>
  );
}
