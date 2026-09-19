import type { MetadataRoute } from "next";

import { getOrganizations, getPeople } from "./data";
import { indexingEnabled, publicSiteBaseUrl } from "./site-metadata";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = publicSiteBaseUrl();
  if (!indexingEnabled() || !base) return [];

  const [peopleResult, organizationsResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
  ]);

  const core: MetadataRoute.Sitemap = [
    { url: new URL("/", base).toString(), changeFrequency: "weekly" },
    { url: new URL("/people", base).toString(), changeFrequency: "daily" },
    { url: new URL("/organizations", base).toString(), changeFrequency: "daily" },
    { url: new URL("/gukgam/2026", base).toString(), changeFrequency: "daily" },
  ];

  const people: MetadataRoute.Sitemap =
    peopleResult.state === "success"
      ? peopleResult.data.map((person) => ({
          url: new URL(`/people/${person.id}`, base).toString(),
          changeFrequency: "weekly" as const,
        }))
      : [];

  const organizations: MetadataRoute.Sitemap =
    organizationsResult.state === "success"
      ? organizationsResult.data.map((organization) => ({
          url: new URL(`/organizations/${organization.id}`, base).toString(),
          changeFrequency: "weekly" as const,
        }))
      : [];

  return [...core, ...people, ...organizations];
}
