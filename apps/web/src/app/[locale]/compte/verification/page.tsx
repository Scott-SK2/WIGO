import { getTranslations, setRequestLocale } from "next-intl/server";

import { EmptyState } from "@/components/EmptyState";
import { Link } from "@/i18n/navigation";

export const dynamic = "force-dynamic";
const API = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** AUTH-02 : consommation du lien de vérification e-mail. */
export default async function VerifyPage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ token?: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { token } = await searchParams;
  const t = await getTranslations("account");
  let ok = false;
  if (token) {
    try {
      ok = (await fetch(`${API}/api/v1/auth/verify-email`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }), cache: "no-store" })).ok;
    } catch {
      ok = false;
    }
  }
  return (
    <div className="container-wigo max-w-xl py-16">
      <EmptyState title={ok ? t("verified") : t("verifyError")}>
        <Link href="/compte/connexion" className="btn-primary">{t("login")}</Link>
      </EmptyState>
    </div>
  );
}
