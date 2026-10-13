# Quick Emoji

A small Tauri picker: search emoji by keyword (including German) and copy or insert them at the caret.

## Development

Requires Node 24+, npm 11.10+, and a Rust toolchain.

```bash
npm install
npm run prepare
npm run tauri dev
```

Custom keywords are stored in the app webview (`localStorage`) and are not committed.
