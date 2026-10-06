import type { Metadata } from "next";

// Public product name. Internal code, packages and env vars keep the Civic Intel name.
export const SITE_NAME = "모두의국감";
const DEFAULT_TITLE = `${SITE_NAME} — 국감 참여 인물 이력 검색`;
const DEFAULT_DESCRIPTION =
  "국정감사 참여 인물의 공개 이력과 근거를 검색합니다. 공개 기준을 통과한 기록만 출처와 함께 보여줍니다.";

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
      template: `%s — ${SITE_NAME}`,
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
      siteName: SITE_NAME,
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
      siteName: SITE_NAME,
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
