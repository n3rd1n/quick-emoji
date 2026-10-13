import Fuse from "fuse.js";
import { catalog, type EmojiItem } from "./emojiCatalog";
import type { CustomKeywords } from "./customKeywords";

export type SearchItem = EmojiItem & { customKeywords: string[] };

function withCustomKeywords(custom: CustomKeywords): SearchItem[] {
  return catalog.map((item) => ({
    ...item,
    customKeywords: custom[item.hexcode] ?? [],
  }));
}

export function searchEmoji(
  query: string,
  custom: CustomKeywords,
  recents: string[],
): SearchItem[] {
  const items = withCustomKeywords(custom);
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) {
    const recentItems = recents
      .map((hexcode) => items.find((item) => item.hexcode === hexcode))
      .filter((item): item is SearchItem => Boolean(item));
    const recentHex = new Set(recents);
    return [...recentItems, ...items.filter((item) => !recentHex.has(item.hexcode))];
  }

  const fuse = new Fuse(items, {
    keys: [
      { name: "customKeywords", weight: 2 },
      { name: "keywords", weight: 1 },
      { name: "emoji", weight: 0.4 },
    ],
    threshold: 0.32,
    ignoreLocation: true,
    minMatchCharLength: 1,
  });
  return fuse.search(trimmed).map((result) => result.item);
}
