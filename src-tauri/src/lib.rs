use tauri::Emitter;

/// Check if the Python backend is healthy
#[tauri::command]
async fn check_backend_health() -> Result<String, String> {
    match reqwest::get("http://127.0.0.1:8420/health").await {
        Ok(resp) => {
            if resp.status().is_success() {
                resp.text().await.map_err(|e| e.to_string())
            } else {
                Err(format!("Backend returned status: {}", resp.status()))
            }
        }
        Err(e) => Err(format!("Backend not reachable: {}", e)),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![check_backend_health])
        .setup(|app| {
            let handle = app.handle().clone();

            // Spawn a background task to poll for the Python backend
            tauri::async_runtime::spawn(async move {
                let mut attempts = 0;
                let max_attempts = 60; // 30 seconds max wait

                loop {
                    match reqwest::get("http://127.0.0.1:8420/health").await {
                        Ok(resp) if resp.status().is_success() => {
                            let _ = handle.emit("backend-ready", true);
                            println!("[SplatMaker] Python backend is ready!");
                            break;
                        }
                        _ => {
                            attempts += 1;
                            if attempts >= max_attempts {
                                let _ = handle.emit("backend-error", "Backend failed to start after 30s");
                                eprintln!("[SplatMaker] Backend failed to start!");
                                break;
                            }
                            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                        }
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
