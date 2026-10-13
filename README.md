# Quick Emoji

A small Tauri picker: search emoji by keyword (including German) and copy or insert them at the caret.

## Development

Requires Node 24+, npm 11.10+, and a Rust toolchain.

```bash
npm install
npm run prepare
npm run tauri:dev
```

The picker starts hidden. Toggle it with **⌘⇧E** (Windows/Linux: **Ctrl+Shift+E**).

Enter inserts the emoji at the caret in the previously focused app. Shift+Enter copies it and keeps the picker open.

On macOS, grant **Accessibility** to Quick Emoji the first time you insert (System Settings → Privacy & Security → Accessibility).

Custom keywords are stored in the app webview (`localStorage`) and are not committed.
