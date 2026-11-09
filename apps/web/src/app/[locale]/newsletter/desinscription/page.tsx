import { getTranslations, setRequestLocale } from "next-intl/server";

import { EmptyState } from "@/components/EmptyState";
import { Link } from "@/i18n/navigation";

export const dynamic = "force-dynamic";
const API = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function UnsubscribePage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ token?: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { token } = await searchParams;
  const t = await getTranslations("newsletter");
  let ok = false;
  if (token) {
    try {
      ok = (await fetch(`${API}/api/v1/newsletter/unsubscribe?token=${encodeURIComponent(token)}`, { cache: "no-store" })).ok;
    } catch {
      ok = false;
    }
  }
  return (
    <div className="container-wigo max-w-xl py-16">
      <EmptyState title={ok ? t("unsubscribed") : t("unsubscribeError")}>
        <Link href="/" className="btn-primary">WIGO</Link>
      </EmptyState>
    </div>
  );
}
