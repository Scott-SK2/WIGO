import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const API = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** SEO-01 : sitemap avec pages statiques, catégories, quartiers et événements publiés. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const statics = ["", "/explorer", "/quartiers", "/organisateurs", "/newsletter", "/a-propos"].flatMap((p) =>
    (["fr", "nl", "en"] as const).map((l) => ({ url: `${SITE}/${l}${p}`, changeFrequency: "daily" as const, priority: p === "" ? 1 : 0.7 })),
  );
  try {
    const [cats, areas, events] = await Promise.all([
      fetch(`${API}/api/v1/categories`, { next: { revalidate: 3600 } }).then((r) => r.json()),
      fetch(`${API}/api/v1/areas`, { next: { revalidate: 3600 } }).then((r) => r.json()),
      fetch(`${API}/api/v1/events?page_size=50`, { next: { revalidate: 600 } }).then((r) => r.json()),
    ]);
    return [
      ...statics,
      ...cats.map((c: { slug: string }) => ({ url: `${SITE}/fr/explorer?category=${c.slug}`, changeFrequency: "daily" as const, priority: 0.6 })),
      ...areas.map((a: { slug: string }) => ({ url: `${SITE}/fr/explorer?area=${a.slug}`, changeFrequency: "daily" as const, priority: 0.6 })),
      ...events.results.map((e: { slug: string }) => ({ url: `${SITE}/fr/evenements/${e.slug}`, changeFrequency: "weekly" as const, priority: 0.8 })),
    ];
  } catch {
    return statics;
  }
}
