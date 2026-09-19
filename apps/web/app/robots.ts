import type { MetadataRoute } from "next";

import { indexingEnabled, publicSiteBaseUrl } from "./site-metadata";

export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  const base = publicSiteBaseUrl();
  if (!indexingEnabled() || !base) {
    return {
      rules: {
        userAgent: "*",
        disallow: "/",
      },
    };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin/"],
    },
    sitemap: new URL("/sitemap.xml", base).toString(),
    host: base.origin,
  };
}
