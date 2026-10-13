import { invoke } from "@tauri-apps/api/core";

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

/** Hide the picker and paste into the app that was focused before. */
export async function insertEmoji(text: string): Promise<void> {
  try {
    await invoke("insert_emoji", { text });
  } catch (error) {
    await copyText(text);
    await hidePicker();
    throw error;
  }
}
