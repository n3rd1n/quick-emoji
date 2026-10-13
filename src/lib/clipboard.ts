export async function copyText(text: string): Promise<void> {
  try {
    const { writeText } = await import("@tauri-apps/plugin-clipboard-manager");
    await writeText(text);
    return;
  } catch {
    // Fall through to the browser clipboard when not running inside Tauri.
  }
  await navigator.clipboard.writeText(text);
}

export async function hidePicker(): Promise<void> {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().hide();
  } catch {
    // Ignore when the Vite preview is open in a browser.
  }
}
