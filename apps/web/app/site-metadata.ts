import type { Metadata } from "next";

const DEFAULT_TITLE = "Civic Intel — Evidence Directory";
const DEFAULT_DESCRIPTION = "공개 기록과 근거를 따라가는 Civic Intel Evidence Directory";

export function publicSiteBaseUrl(): URL | null {
  const raw = process.env.CIVIC_PUBLIC_BASE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
      return null;
    }
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

export function indexingEnabled(): boolean {
  return process.env.CIVIC_INDEXING_ENABLED === "true" && publicSiteBaseUrl() !== null;
}

function canonicalUrl(path: string): string | null {
  const base = publicSiteBaseUrl();
  if (!base || !indexingEnabled()) return null;
  return new URL(path, base).toString();
}

export function buildRootMetadata(): Metadata {
  const base = publicSiteBaseUrl();
  const index = indexingEnabled();
  const canonical = canonicalUrl("/");
  return {
    title: {
      default: DEFAULT_TITLE,
      template: "%s — Civic Intel",
    },
    description: DEFAULT_DESCRIPTION,
    icons: {
      icon: "/icon.svg",
    },
    ...(base ? { metadataBase: base } : {}),
    robots: {
      index,
      follow: index,
      googleBot: {
        index,
        follow: index,
        "max-image-preview": "large",
        "max-snippet": -1,
        "max-video-preview": -1,
      },
    },
    openGraph: {
      type: "website",
      locale: "ko_KR",
      siteName: "Civic Intel",
      title: DEFAULT_TITLE,
      description: DEFAULT_DESCRIPTION,
      ...(canonical ? { url: canonical } : {}),
    },
    twitter: {
      card: "summary",
      title: DEFAULT_TITLE,
      description: DEFAULT_DESCRIPTION,
    },
    ...(canonical ? { alternates: { canonical } } : {}),
  };
}

export function buildPageMetadata({
  title,
  description,
  path,
}: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  const canonical = canonicalUrl(path);
  return {
    title,
    description,
    openGraph: {
      type: "website",
      locale: "ko_KR",
      siteName: "Civic Intel",
      title,
      description,
      ...(canonical ? { url: canonical } : {}),
    },
    twitter: {
      card: "summary",
      title,
      description,
    },
    ...(canonical ? { alternates: { canonical } } : {}),
  };
}
