import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/EmptyState";
import { Link } from "@/i18n/navigation";

export default function NotFound() {
  const t = useTranslations("common");
  return (
    <div className="container-wigo py-16">
      <EmptyState title={t("notFound")} text={t("notFoundText")}>
        <Link href="/" className="btn-primary">{t("home")}</Link>
      </EmptyState>
    </div>
  );
}
