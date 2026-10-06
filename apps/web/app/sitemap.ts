import type { MetadataRoute } from "next";

import { getOrganizations, getPeople } from "./data";
import { indexingEnabled, publicSiteBaseUrl } from "./site-metadata";

export const dynamic = "force-dynamic";

// The Sites snapshot is exported with trailing slashes; keep sitemap URLs equal to canonical URLs.
const trailing = process.env.CIVIC_SITES_EXPORT === "1" ? "/" : "";
const page = (path: string, base: URL) => new URL(path === "/" ? path : `${path}${trailing}`, base).toString();

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = publicSiteBaseUrl();
  if (!indexingEnabled() || !base) return [];

  const [peopleResult, organizationsResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
  ]);

  const core: MetadataRoute.Sitemap = [
    { url: page("/", base), changeFrequency: "weekly" },
    { url: page("/people", base), changeFrequency: "daily" },
    { url: page("/organizations", base), changeFrequency: "daily" },
    { url: page("/gukgam/2026", base), changeFrequency: "daily" },
  ];

  const people: MetadataRoute.Sitemap =
    peopleResult.state === "success"
      ? peopleResult.data.map((person) => ({
          url: page(`/people/${person.id}`, base),
          changeFrequency: "weekly" as const,
        }))
      : [];

  const organizations: MetadataRoute.Sitemap =
    organizationsResult.state === "success"
      ? organizationsResult.data.map((organization) => ({
          url: page(`/organizations/${organization.id}`, base),
          changeFrequency: "weekly" as const,
        }))
      : [];

  return [...core, ...people, ...organizations];
}
