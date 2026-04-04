#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::{
    env,
    fs::{self, OpenOptions},
    io::Write,
    net::TcpStream,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    thread,
    time::{Duration, Instant},
};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

const APP_NAME: &str = "Chia Market Maker";
const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: u16 = 5000;
const BACKEND_URL: &str = "http://127.0.0.1:5000/";
const BACKEND_WAIT_SECS: u64 = 25;
const SPLASH_LABEL: &str = "splash";
const MAIN_LABEL: &str = "main";
const INSTANCE_LOCKFILE: &str = ".tauri-instance.lock";

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<Child>>,
    shutting_down: AtomicBool,
    allow_splash_close: AtomicBool,
    allow_main_close: AtomicBool,
}

#[tauri::command]
fn allow_main_window_close(app: tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<BackendState>();
    state.allow_main_close.store(true, Ordering::SeqCst);
    Ok(())
}

struct AppInstanceLock {
    path: PathBuf,
}

impl Drop for AppInstanceLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

fn project_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("src-tauri should have a workspace parent")
        .to_path_buf()
}

fn instance_lock_path(root: &Path) -> PathBuf {
    root.join(INSTANCE_LOCKFILE)
}

fn read_instance_lock_pid(path: &Path) -> Option<u32> {
    let contents = fs::read_to_string(path).ok()?;
    let first_line = contents.lines().next()?.trim();
    first_line.parse::<u32>().ok()
}

#[cfg(target_os = "windows")]
fn is_pid_running(pid: u32) -> bool {
    let filter = format!("PID eq {pid}");
    match Command::new("tasklist")
        .args(["/FI", &filter, "/FO", "CSV", "/NH"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .output()
    {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            stdout.contains(&format!("\"{pid}\""))
        }
        Err(_) => false,
    }
}

#[cfg(not(target_os = "windows"))]
fn is_pid_running(pid: u32) -> bool {
    let proc_path = PathBuf::from(format!("/proc/{pid}"));
    proc_path.exists()
}

fn try_acquire_instance_lock(root: &Path) -> Result<AppInstanceLock, String> {
    let path = instance_lock_path(root);

    for _ in 0..2 {
        match OpenOptions::new().create_new(true).write(true).open(&path) {
            Ok(mut file) => {
                let _ = writeln!(file, "{}", std::process::id());
                let _ = writeln!(file, "{}", APP_NAME);
                return Ok(AppInstanceLock { path });
            }
            Err(err) if err.kind() == std::io::ErrorKind::AlreadyExists => {
                if let Some(existing_pid) = read_instance_lock_pid(&path) {
                    if is_pid_running(existing_pid) {
                        return Err(format!(
                            "{APP_NAME} is already running. Return to the existing window instead of opening a second copy."
                        ));
                    }
                }
                let _ = fs::remove_file(&path);
            }
            Err(err) => {
                return Err(format!("Could not create app instance lock: {err}"));
            }
        }
    }

    Err(format!(
        "{APP_NAME} is already running, or its startup lock could not be refreshed."
    ))
}

fn is_backend_reachable() -> bool {
    TcpStream::connect((BACKEND_HOST, BACKEND_PORT)).is_ok()
}

fn request_backend_shutdown(cancel_offers: bool) -> bool {
    let body = if cancel_offers {
        r#"{"cancel_offers":true}"#
    } else {
        r#"{"cancel_offers":false}"#
    };

    let request = format!(
        "POST /api/shutdown HTTP/1.1\r\nHost: {host}:{port}\r\nContent-Type: application/json\r\nContent-Length: {len}\r\nConnection: close\r\n\r\n{body}",
        host = BACKEND_HOST,
        port = BACKEND_PORT,
        len = body.len(),
        body = body
    );

    match TcpStream::connect((BACKEND_HOST, BACKEND_PORT)) {
        Ok(mut stream) => stream.write_all(request.as_bytes()).is_ok(),
        Err(_) => false,
    }
}

fn wait_for_backend(state: &BackendState, timeout: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < timeout {
        if state.shutting_down.load(Ordering::SeqCst) {
            return false;
        }
        if is_backend_reachable() {
            return true;
        }
        thread::sleep(Duration::from_millis(250));
    }
    false
}

fn python_candidates() -> Vec<String> {
    #[cfg(target_os = "windows")]
    {
        vec![
            "pythonw.exe".into(),
            "python.exe".into(),
            "py.exe".into(),
        ]
    }
    #[cfg(not(target_os = "windows"))]
    {
        vec!["python3".into(), "python".into()]
    }
}

fn try_spawn_backend(root: &Path) -> Result<Child, String> {
    let backend_script = root.join("api_server.py");
    if !backend_script.exists() {
        return Err(format!("Backend script not found: {}", backend_script.display()));
    }

    let env_pairs = env::vars().collect::<Vec<_>>();
    let stdio_to_file = true;
    let log_path = root.join("tauri_backend_stdout.log");

    for candidate in python_candidates() {
        let mut cmd = Command::new(&candidate);
        if candidate.eq_ignore_ascii_case("py.exe") {
            #[cfg(target_os = "windows")]
            {
                cmd.arg("-3");
            }
        }

        cmd.arg(&backend_script)
            .current_dir(root)
            .stdin(Stdio::null());

        if stdio_to_file {
            match std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_path)
            {
                Ok(file) => {
                    let stderr = match file.try_clone() {
                        Ok(clone) => clone,
                        Err(err) => return Err(format!("Could not clone backend log handle: {err}")),
                    };
                    cmd.stdout(Stdio::from(file));
                    cmd.stderr(Stdio::from(stderr));
                }
                Err(err) => return Err(format!("Could not open backend log file: {err}")),
            }
        }

        for (k, v) in &env_pairs {
            cmd.env(k, v);
        }
        cmd.env("PYTHONIOENCODING", "utf-8");
        cmd.env("PYTHONUTF8", "1");

        #[cfg(target_os = "windows")]
        {
            cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }

        match cmd.spawn() {
            Ok(child) => return Ok(child),
            Err(_) => continue,
        }
    }

    Err("Could not launch Python backend. Make sure python/pythonw is installed and on PATH.".into())
}

fn ensure_backend(state: &BackendState) -> Result<(), String> {
    if state.shutting_down.load(Ordering::SeqCst) {
        return Err("Startup cancelled".into());
    }

    if is_backend_reachable() {
        return Ok(());
    }

    let mut guard = state.child.lock().map_err(|_| "Backend mutex poisoned".to_string())?;
    if guard.is_none() {
        let mut child = try_spawn_backend(&project_root())?;
        if state.shutting_down.load(Ordering::SeqCst) {
            let _ = child.kill();
            let _ = child.wait();
            return Err("Startup cancelled".into());
        }
        *guard = Some(child);
    }
    drop(guard);

    if wait_for_backend(state, Duration::from_secs(BACKEND_WAIT_SECS)) {
        Ok(())
    } else if state.shutting_down.load(Ordering::SeqCst) {
        Err("Startup cancelled".into())
    } else {
        Err(format!(
            "Backend did not start on {} within {} seconds",
            BACKEND_URL, BACKEND_WAIT_SECS
        ))
    }
}

fn stop_backend(state: &BackendState) {
    state.shutting_down.store(true, Ordering::SeqCst);
    if let Ok(mut guard) = state.child.lock() {
        if let Some(mut child) = guard.take() {
            #[cfg(target_os = "windows")]
            {
                let _ = Command::new("taskkill")
                    .args(["/PID", &child.id().to_string(), "/T", "/F"])
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .creation_flags(CREATE_NO_WINDOW)
                    .status();
                let _ = child.wait();
            }

            #[cfg(not(target_os = "windows"))]
            {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

fn graceful_stop_backend(state: &BackendState) {
    state.shutting_down.store(true, Ordering::SeqCst);

    if is_backend_reachable() {
        let _ = request_backend_shutdown(false);
        let start = Instant::now();
        while start.elapsed() < Duration::from_secs(6) {
            if !is_backend_reachable() {
                break;
            }
            thread::sleep(Duration::from_millis(200));
        }
    }

    stop_backend(state);
}

fn build_splash_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<(), String> {
    if app.get_webview_window(SPLASH_LABEL).is_some() {
        return Ok(());
    }

    WebviewWindowBuilder::new(app, SPLASH_LABEL, WebviewUrl::App("index.html".into()))
        .title(APP_NAME)
        .inner_size(560.0, 480.0)
        .min_inner_size(560.0, 480.0)
        .resizable(false)
        .maximizable(false)
        .minimizable(false)
        .closable(true)
        .center()
        .build()
        .map(|_| ())
        .map_err(|err| format!("Could not create splash window: {err}"))
}

fn build_main_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<(), String> {
    if app.get_webview_window(MAIN_LABEL).is_some() {
        return Ok(());
    }

    let url = BACKEND_URL
        .parse()
        .map_err(|err| format!("Bad backend URL: {err}"))?;

    WebviewWindowBuilder::new(app, MAIN_LABEL, WebviewUrl::External(url))
        .title(APP_NAME)
        .inner_size(1600.0, 1000.0)
        .min_inner_size(1000.0, 700.0)
        .resizable(true)
        .maximized(false)
        .center()
        .build()
        .map_err(|err| format!("Could not create main window: {err}"))?;

    if let Some(splash) = app.get_webview_window(SPLASH_LABEL) {
        let state = app.state::<BackendState>();
        state.allow_splash_close.store(true, Ordering::SeqCst);
        let _ = splash.close();
    }

    Ok(())
}

#[cfg(target_os = "windows")]
fn ps_single_quote(value: &str) -> String {
    value.replace('\'', "''")
}

#[cfg(target_os = "windows")]
fn show_launch_block_message(message: &str) {
    let title = ps_single_quote(APP_NAME);
    let body = ps_single_quote(message);
    let script = format!(
        "Add-Type -AssemblyName PresentationFramework; \
         [System.Windows.MessageBox]::Show('{body}', '{title}', 'OK', 'Warning') | Out-Null"
    );

    let mut cmd = Command::new("powershell.exe");
    cmd.arg("-NoProfile")
        .arg("-NonInteractive")
        .arg("-ExecutionPolicy")
        .arg("Bypass")
        .arg("-Command")
        .arg(script)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW);
    let _ = cmd.status();
}

#[cfg(not(target_os = "windows"))]
fn show_launch_block_message(message: &str) {
    eprintln!("{message}");
}

#[cfg(target_os = "windows")]
fn ensure_desktop_shortcut() {
    let exe = match env::current_exe() {
        Ok(path) => path,
        Err(_) => return,
    };
    let workdir = exe
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(project_root);

    let exe_str = ps_single_quote(&exe.to_string_lossy());
    let workdir_str = ps_single_quote(&workdir.to_string_lossy());
    let app_name = ps_single_quote(APP_NAME);

    let script = format!(
        "$desktop=[Environment]::GetFolderPath('Desktop'); \
         if ([string]::IsNullOrWhiteSpace($desktop)) {{ exit 0 }}; \
         $shortcutPath=Join-Path $desktop '{app}.lnk'; \
         $shell=New-Object -ComObject WScript.Shell; \
         $shortcut=$shell.CreateShortcut($shortcutPath); \
         $shortcut.TargetPath='{exe}'; \
         $shortcut.WorkingDirectory='{workdir}'; \
         $shortcut.IconLocation='{exe},0'; \
         $shortcut.Save()",
        app = app_name,
        exe = exe_str,
        workdir = workdir_str,
    );

    let mut cmd = Command::new("powershell.exe");
    cmd.arg("-NoProfile")
        .arg("-NonInteractive")
        .arg("-ExecutionPolicy")
        .arg("Bypass")
        .arg("-Command")
        .arg(script)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW);

    let _ = cmd.status();
}

#[cfg(not(target_os = "windows"))]
fn ensure_desktop_shortcut() {}

fn show_splash_error<R: tauri::Runtime>(app: &tauri::AppHandle<R>, message: &str) {
    if let Some(splash) = app.get_webview_window(SPLASH_LABEL) {
        let escaped = message
            .replace('\\', "\\\\")
            .replace('\'', "\\'")
            .replace('\r', "")
            .replace('\n', "\\n");
        let _ = splash.eval(&format!(
            "window.setSplashError && window.setSplashError('{}');",
            escaped
        ));
    }
}

fn main() {
    let _instance_lock = match try_acquire_instance_lock(&project_root()) {
        Ok(lock) => lock,
        Err(err) => {
            show_launch_block_message(&err);
            return;
        }
    };

    let backend_state = BackendState::default();

    let builder = tauri::Builder::default()
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let state = window.state::<BackendState>();

                if window.label() == SPLASH_LABEL {
                    if state.allow_splash_close.load(Ordering::SeqCst) {
                        return;
                    }
                    api.prevent_close();
                    if state.shutting_down.swap(true, Ordering::SeqCst) {
                        return;
                    }
                    let app_handle = window.app_handle().clone();
                    if let Some(splash) = app_handle.get_webview_window(SPLASH_LABEL) {
                        let _ = splash.eval(
                            "window.setSplashShutdownState && window.setSplashShutdownState('Closing down local services...', 'Closing local services and backend processes cleanly before exit.');",
                        );
                    }
                    thread::spawn(move || {
                        let state = app_handle.state::<BackendState>();
                        graceful_stop_backend(&state);
                        app_handle.exit(0);
                    });
                    return;
                }

                if window.label() == MAIN_LABEL {
                    // Allow close if explicitly permitted OR if backend is
                    // already shutting down (e.g. the Flask-side shutdown
                    // was triggered from the in-page modal).  The IPC
                    // command `allow_main_window_close` is unreachable from
                    // Flask-served content (external URL), so we also
                    // honour the `shutting_down` flag which the backend
                    // monitor sets when the Python process exits. Also allow
                    // the close to go through once the local backend is no
                    // longer reachable, which covers in-page shutdown flows
                    // that stop Flask before the monitor thread observes the
                    // child exit.
                    if state.allow_main_close.load(Ordering::SeqCst)
                        || state.shutting_down.load(Ordering::SeqCst)
                        || !is_backend_reachable()
                    {
                        return;
                    }
                    api.prevent_close();
                    if let Some(main) = window.app_handle().get_webview_window(MAIN_LABEL) {
                        let _ = main.eval(
                            "window.showShutdownModal && window.showShutdownModal();",
                        );
                    }
                    return;
                }
            }
        })
        .invoke_handler(tauri::generate_handler![allow_main_window_close])
        .manage(backend_state)
        .setup(|app| {
            let app_handle = app.handle().clone();
            ensure_desktop_shortcut();
            build_splash_window(&app_handle)
                .map_err(|err| -> Box<dyn std::error::Error> { err.into() })?;

            let worker_handle = app.handle().clone();
            thread::spawn(move || {
                let state = worker_handle.state::<BackendState>();
                if let Err(err) = ensure_backend(&state) {
                    if err == "Startup cancelled" {
                        return;
                    }
                    let error_handle = worker_handle.clone();
                    let err_copy = err.clone();
                    let _ = worker_handle.run_on_main_thread(move || {
                        show_splash_error(&error_handle, &err_copy);
                    });
                    return;
                }

                if worker_handle
                    .state::<BackendState>()
                    .shutting_down
                    .load(Ordering::SeqCst)
                {
                    return;
                }

                let main_handle = worker_handle.clone();
                let _ = worker_handle.run_on_main_thread(move || {
                    if let Err(err) = build_main_window(&main_handle) {
                        show_splash_error(&main_handle, &err);
                    }
                });
            });

            let monitor_handle = app.handle().clone();
            thread::spawn(move || loop {
                thread::sleep(Duration::from_millis(500));
                let state = monitor_handle.state::<BackendState>();
                let should_exit = if let Ok(mut guard) = state.child.lock() {
                    if let Some(child) = guard.as_mut() {
                        match child.try_wait() {
                            Ok(Some(_status)) => {
                                guard.take();
                                true
                            }
                            Ok(None) => false,
                            Err(_) => false,
                        }
                    } else {
                        false
                    }
                } else {
                    false
                };

                if should_exit {
                    monitor_handle.exit(0);
                    break;
                }
            });

            Ok(())
        });

    builder
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| match event {
            RunEvent::Exit | RunEvent::ExitRequested { .. } => {
                let state = app.state::<BackendState>();
                stop_backend(&state);
            }
            _ => {}
        });
}
