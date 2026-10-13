use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_global_shortcut::{Builder, GlobalShortcutExt, Shortcut, ShortcutState};

const DEFAULT_HOTKEY: &str = "CommandOrControl+Shift+E";

pub fn plugin() -> tauri::plugin::TauriPlugin<tauri::Wry> {
    Builder::new().build()
}

pub fn register(app: &AppHandle) -> Result<(), String> {
    let shortcut: Shortcut = DEFAULT_HOTKEY
        .parse()
        .map_err(|err| format!("invalid hotkey '{DEFAULT_HOTKEY}': {err}"))?;

    app.global_shortcut()
        .on_shortcut(shortcut, |app, _shortcut, event| {
            if event.state == ShortcutState::Pressed {
                let _ = toggle_picker(app);
            }
        })
        .map_err(|err| err.to_string())?;

    Ok(())
}

fn toggle_picker(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "main window missing".to_string())?;

    if window.is_visible().unwrap_or(false) {
        window.hide().map_err(|err| err.to_string())?;
        return Ok(());
    }

    let _ = window.center();
    window.show().map_err(|err| err.to_string())?;
    window.set_focus().map_err(|err| err.to_string())?;
    let _ = app.emit("picker-shown", ());
    Ok(())
}
