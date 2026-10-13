import deData from "emojibase-data/de/compact.json";
import enData from "emojibase-data/en/compact.json";
import shortcodes from "emojibase-data/en/shortcodes/emojibase.json";

export type EmojiItem = {
  hexcode: string;
  emoji: string;
  label: string;
  keywords: string[];
  order: number;
};

type CompactRow = {
  hexcode: string;
  label: string;
  unicode: string;
  tags?: string[];
  order?: number;
};

function asList(value: string | string[] | undefined): string[] {
  if (!value) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
}

export function uniqueNormalized(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const next = value.trim().toLowerCase();
    if (!next || seen.has(next)) {
      continue;
    }
    seen.add(next);
    out.push(next);
  }
  return out;
}

const english = enData as CompactRow[];
const german = deData as CompactRow[];
const germanByHex = new Map(german.map((row) => [row.hexcode, row]));
const shortcodeByHex = shortcodes as Record<string, string | string[]>;

export const catalog: EmojiItem[] = english
  .filter((row) => row.order != null)
  .map((row) => {
    const de = germanByHex.get(row.hexcode);
    return {
      hexcode: row.hexcode,
      emoji: row.unicode,
      label: de?.label ?? row.label,
      keywords: uniqueNormalized([
        row.label,
        de?.label ?? "",
        ...(row.tags ?? []),
        ...(de?.tags ?? []),
        ...asList(shortcodeByHex[row.hexcode]),
      ]),
      order: row.order ?? Number.MAX_SAFE_INTEGER,
    };
  })
  .sort((a, b) => a.order - b.order);
