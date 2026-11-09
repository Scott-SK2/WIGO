import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AuthForm } from "./AuthForm";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("account");
  return { title: t("login"), robots: { index: false } };
}

/** SCR-05 : connexion / inscription (AUTH-01, AUTH-03). */
export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <div className="container-wigo max-w-md py-12">
      <AuthForm />
    </div>
  );
}
