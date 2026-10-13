<script lang="ts">
  import { onMount } from "svelte";
  import { copyText, hidePicker } from "$lib/clipboard";
  import {
    loadCustomKeywords,
    loadRecents,
    pushRecent,
    saveCustomKeywords,
    type CustomKeywords,
  } from "$lib/customKeywords";
  import { uniqueNormalized } from "$lib/emojiCatalog";
  import { searchEmoji, type SearchItem } from "$lib/search";

  const COLUMNS = 8;

  let query = $state("");
  let customKeywords = $state<CustomKeywords>(loadCustomKeywords());
  let recents = $state<string[]>(loadRecents());
  let selectedIndex = $state(0);
  let keywordDraft = $state("");
  let status = $state("Type to search, Enter to copy");
  let searchEl = $state<HTMLInputElement | undefined>();

  const results = $derived(searchEmoji(query, customKeywords, recents));
  const selected = $derived(results[selectedIndex] ?? results[0] ?? null);

  $effect(() => {
    query;
    selectedIndex = 0;
  });

  onMount(() => {
    searchEl?.focus();
  });

  function addKeyword(item: SearchItem, raw: string) {
    const [keyword] = uniqueNormalized([raw]);
    if (!keyword) {
      return;
    }
    if (item.keywords.includes(keyword) || item.customKeywords.includes(keyword)) {
      status = `“${keyword}” is already a keyword for ${item.emoji}`;
      return;
    }
    const next = {
      ...customKeywords,
      [item.hexcode]: [...item.customKeywords, keyword],
    };
    customKeywords = next;
    saveCustomKeywords(next);
    keywordDraft = "";
    status = `Added “${keyword}” to ${item.emoji}`;
  }

  function removeKeyword(item: SearchItem, keyword: string) {
    const remaining = item.customKeywords.filter((entry) => entry !== keyword);
    const next = { ...customKeywords };
    if (remaining.length === 0) {
      delete next[item.hexcode];
    } else {
      next[item.hexcode] = remaining;
    }
    customKeywords = next;
    saveCustomKeywords(next);
  }

  async function choose(item: SearchItem) {
    await copyText(item.emoji);
    recents = pushRecent(item.hexcode);
    status = `Copied ${item.emoji}`;
  }

  async function onSearchKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      await hidePicker();
      return;
    }
    if (!results.length) {
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      selectedIndex = Math.min(results.length - 1, selectedIndex + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      selectedIndex = Math.max(0, selectedIndex - 1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      selectedIndex = Math.min(results.length - 1, selectedIndex + COLUMNS);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      selectedIndex = Math.max(0, selectedIndex - COLUMNS);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (selected) {
        await choose(selected);
      }
    }
  }
</script>

<div class="shell">
  <header data-tauri-drag-region>
    <input
      bind:this={searchEl}
      bind:value={query}
      onkeydown={onSearchKeydown}
      placeholder="Search emoji…"
      spellcheck="false"
      autocomplete="off"
    />
  </header>

  <div class="grid" role="listbox" aria-label="Emoji results">
    {#each results.slice(0, 80) as item, index (item.hexcode)}
      <button
        type="button"
        class:active={index === selectedIndex}
        role="option"
        aria-selected={index === selectedIndex}
        title={item.label}
        onmouseenter={() => (selectedIndex = index)}
        onclick={() => choose(item)}
      >
        {item.emoji}
      </button>
    {/each}
    {#if results.length === 0}
      <p class="empty">No matches</p>
    {/if}
  </div>

  {#if selected}
    <footer>
      <div class="meta">
        <span class="preview">{selected.emoji}</span>
        <div>
          <strong>{selected.label}</strong>
          <p>{status}</p>
        </div>
      </div>
      <div class="chips">
        {#each selected.customKeywords as keyword (keyword)}
          <button type="button" class="chip custom" onclick={() => removeKeyword(selected, keyword)}>
            {keyword} ×
          </button>
        {/each}
        {#each selected.keywords.slice(0, 8) as keyword (keyword)}
          <span class="chip">{keyword}</span>
        {/each}
      </div>
      <form
        onsubmit={(event) => {
          event.preventDefault();
          addKeyword(selected, keywordDraft);
        }}
      >
        <input
          bind:value={keywordDraft}
          placeholder="Add your own keyword"
          spellcheck="false"
        />
        <button type="submit">Add</button>
      </form>
    </footer>
  {/if}
</div>

<style>
  .shell {
    height: 100vh;
    display: grid;
    grid-template-rows: auto 1fr auto;
  }

  header {
    padding: 10px;
    border-bottom: 1px solid #27272a;
  }

  header input,
  footer input {
    width: 100%;
    border: 1px solid #3f3f46;
    background: #09090b;
    border-radius: 8px;
    padding: 8px 10px;
    outline: none;
  }

  header input:focus,
  footer input:focus {
    border-color: #60a5fa;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    align-content: start;
    gap: 4px;
    padding: 8px;
    overflow: auto;
  }

  .grid button {
    height: 40px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    font-size: 22px;
    cursor: pointer;
  }

  .grid button.active,
  .grid button:hover {
    background: #27272a;
    border-color: #3b82f6;
  }

  .empty {
    grid-column: 1 / -1;
    text-align: center;
    color: #a1a1aa;
  }

  footer {
    padding: 10px;
    border-top: 1px solid #27272a;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .meta {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .preview {
    font-size: 28px;
  }

  .meta p,
  .meta strong {
    margin: 0;
  }

  .meta p {
    color: #a1a1aa;
    font-size: 12px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    max-height: 52px;
    overflow: auto;
  }

  .chip {
    border-radius: 999px;
    padding: 2px 8px;
    background: #27272a;
    color: #d4d4d8;
    font-size: 11px;
  }

  .chip.custom {
    border: 0;
    background: #1d4ed8;
    color: white;
    cursor: pointer;
  }

  form {
    display: flex;
    gap: 6px;
  }

  form button {
    border: 0;
    border-radius: 8px;
    background: #2563eb;
    padding: 0 12px;
    cursor: pointer;
  }
</style>
