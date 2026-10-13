const KEYWORDS_KEY = "quick-emoji.custom-keywords.v1";
const RECENTS_KEY = "quick-emoji.recents.v1";
const MAX_RECENTS = 16;

export type CustomKeywords = Record<string, string[]>;

function readJson<T>(key: string, fallback: T): T {
  if (typeof localStorage === "undefined") {
    return fallback;
  }
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadCustomKeywords(): CustomKeywords {
  const stored = readJson<CustomKeywords>(KEYWORDS_KEY, {});
  const cleaned: CustomKeywords = {};
  for (const [hexcode, keywords] of Object.entries(stored)) {
    if (!Array.isArray(keywords)) {
      continue;
    }
    const next = keywords
      .map((keyword) => keyword.trim().toLowerCase())
      .filter(Boolean);
    if (next.length > 0) {
      cleaned[hexcode] = Array.from(new Set(next));
    }
  }
  return cleaned;
}

export function saveCustomKeywords(keywords: CustomKeywords): void {
  localStorage.setItem(KEYWORDS_KEY, JSON.stringify(keywords));
}

export function loadRecents(): string[] {
  const stored = readJson<string[]>(RECENTS_KEY, []);
  return Array.isArray(stored) ? stored.filter((item) => typeof item === "string") : [];
}

export function pushRecent(hexcode: string): string[] {
  const recents = [hexcode, ...loadRecents().filter((item) => item !== hexcode)].slice(
    0,
    MAX_RECENTS,
  );
  localStorage.setItem(RECENTS_KEY, JSON.stringify(recents));
  return recents;
}
