use std::thread;
use std::time::Duration;

use enigo::{
    Direction::{Click, Press, Release},
    Enigo, Key, Keyboard, Settings,
};
use tauri::{AppHandle, Manager};
use tauri_plugin_clipboard_manager::ClipboardExt;

const HIDE_BEFORE_PASTE: Duration = Duration::from_millis(80);
const RESTORE_AFTER_PASTE: Duration = Duration::from_millis(120);

#[cfg(target_os = "macos")]
fn paste_shortcut() -> (Key, Key) {
    // kVK_ANSI_V — layout-independent, unlike Key::Unicode('v')
    (Key::Meta, Key::Other(9))
}

#[cfg(not(target_os = "macos"))]
fn paste_shortcut() -> (Key, Key) {
    (Key::Control, Key::Unicode('v'))
}

fn simulate_paste() -> Result<(), String> {
    let mut enigo = Enigo::new(&Settings::default()).map_err(|err| err.to_string())?;
    let (modifier, paste_key) = paste_shortcut();

    enigo
        .key(modifier, Press)
        .map_err(|err| err.to_string())?;
    let click = enigo.key(paste_key, Click);
    let release = enigo.key(modifier, Release);
    click.map_err(|err| err.to_string())?;
    release.map_err(|err| err.to_string())?;
    Ok(())
}

/// Hide the picker, paste into the previously focused app, then restore the clipboard.
#[tauri::command]
pub fn insert_emoji(app: AppHandle, text: String) -> Result<(), String> {
    prompt_accessibility();

    let clipboard = app.clipboard();
    let previous = clipboard.read_text().ok();

    if let Some(window) = app.get_webview_window("main") {
        window.hide().map_err(|err| err.to_string())?;
    }

    thread::sleep(HIDE_BEFORE_PASTE);

    clipboard
        .write_text(&text)
        .map_err(|err| err.to_string())?;

    match simulate_paste() {
        Ok(()) => {
            thread::sleep(RESTORE_AFTER_PASTE);
            if let Some(previous) = previous {
                let _ = clipboard.write_text(previous);
            }
            Ok(())
        }
        Err(err) => {
            // Leave the emoji on the clipboard so the user can paste manually.
            Err(format!(
                "{err}. Grant Accessibility to Quick Emoji in System Settings if paste did not work."
            ))
        }
    }
}

#[cfg(target_os = "macos")]
pub fn prompt_accessibility() {
    let _ = macos_accessibility_client::accessibility::application_is_trusted_with_prompt();
}

#[cfg(not(target_os = "macos"))]
pub fn prompt_accessibility() {}
