import { getTranslations, setRequestLocale } from "next-intl/server";

import { ResetForm } from "./ResetForm";

export default async function ResetPage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ token?: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { token } = await searchParams;
  const t = await getTranslations("account");
  return (
    <div className="container-wigo max-w-md py-12">
      <h1 className="text-3xl">{t("resetTitle")}</h1>
      <div className="mt-6"><ResetForm token={token ?? ""} /></div>
    </div>
  );
}
