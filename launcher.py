import os
import zipfile
import io
import urllib.request
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

ZERO_PY_CONTENT = '''import os
import json
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-key", methods=["GET"])
def get_key():
    config = load_config()
    api_key = config.get("GEMINI_API_KEY", "")
    return jsonify({"success": True, "api_key": api_key})

@app.route("/api/save-key", methods=["POST"])
def save_key():
    data = request.json
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "API Key không được để trống"})
    
    config = load_config()
    config["GEMINI_API_KEY"] = api_key
    save_config(config)
    return jsonify({"success": True, "message": "Lưu API Key thành công!"})

@app.route("/api/command", methods=["POST"])
def command():
    data = request.json
    cmd = data.get("command", "").strip()
    return jsonify({"success": True, "reply": f"Zero đã nhận lệnh: {cmd}"})

def open_browser():
    url = "http://127.0.0.1:5000"
    print(f"🌐 Đang mở giao diện trên trình duyệt: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    print("🤖 Zero Assistant Server đang khởi động...")
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
'''

INSTALL_LIBS_PY_CONTENT = '''import subprocess
import sys
import time

libs = [
    "flask",
    "python-dotenv",
    "sounddevice",
    "numpy",
    "SpeechRecognition",
    "edge-tts",
    "pygame-ce",
    "google-generativeai"
]

print("📦 Đang tiến hành cài đặt các thư viện cần thiết cho Zero Assistant...")
for lib in libs:
    print(f"-> Đang cài đặt: {lib}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)
    except Exception as e:
        print(f"❌ Lỗi khi cài đặt {lib}: {e}")

print("\\n✅ Cài đặt tất cả thư viện hoàn tất!")
time.sleep(3)
'''

RUN_BAT_CONTENT = '''@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 🤖 Đang khởi động Zero Assistant...
python zero.py
pause
'''

def select_installation_directory():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    messagebox.showinfo("Cài đặt Zero Assistant", "Vui lòng chọn thư mục để cài đặt ứng dụng.")
    chosen_dir = filedialog.askdirectory(title="Chọn thư mục cài đặt Zero Assistant")
    
    if not chosen_dir:
        sys.exit(0)
        
    target_dir = os.path.join(chosen_dir, "ZeroAssistant")
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def fix_html_autocomplete(target_dir):
    html_path = os.path.join(target_dir, "templates", "index.html")
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "<input" in content and "autocomplete=\"off\"" not in content:
                content = content.replace("<input ", "<input autocomplete=\"off\" ")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            pass

def setup_environment(target_dir):
    with open(os.path.join(target_dir, "zero.py"), "w", encoding="utf-8") as f:
        f.write(ZERO_PY_CONTENT)

    with open(os.path.join(target_dir, "install_libs.py"), "w", encoding="utf-8") as f:
        f.write(INSTALL_LIBS_PY_CONTENT)

    with open(os.path.join(target_dir, "run.bat"), "w", encoding="utf-8") as f:
        f.write(RUN_BAT_CONTENT)

    zip_urls = [
        "https://github.com/trangthanhdai287-blip/zero/archive/refs/heads/main.zip",
        "https://github.com/trangthanhdai287-blip/zero/archive/refs/heads/master.zip"
    ]
    
    success = False
    for zip_url in zip_urls:
        try:
            with urllib.request.urlopen(zip_url, timeout=10) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    for member in z.namelist():
                        parts = member.split('/')[1:]
                        if not parts or parts == ['']:
                            continue
                        dest_path = os.path.join(target_dir, *parts)
                        if member.endswith('/'):
                            os.makedirs(dest_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            with z.open(member) as source, open(dest_path, "wb") as target:
                                target.write(source.read())
                    success = True
                    break
        except Exception:
            continue

    if success:
        fix_html_autocomplete(target_dir)

def create_desktop_shortcut(target_dir):
    try:
        user_profile = os.path.expanduser("~")
        desktop = os.path.join(user_profile, "Desktop")
        onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
        if os.path.exists(onedrive_desktop):
            desktop = onedrive_desktop
            
        shortcut_path = os.path.join(desktop, "Zero Assistant.lnk")
        working_dir = target_dir
        run_bat_abs = os.path.abspath(os.path.join(target_dir, "run.bat"))
        icon_path = os.path.abspath(os.path.join(target_dir, "icon.ico"))

        ps_script = f'''
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{run_bat_abs}"
        $Shortcut.WorkingDirectory = "{working_dir}"
        $Shortcut.Description = "Zero Assistant - Trợ lý ảo"
        if (Test-Path "{icon_path}") {{
            $Shortcut.IconLocation = "{icon_path},0"
        }}
        $Shortcut.Save()
        '''
        
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    except Exception as e:
        pass

def self_delete_installer():
    if getattr(sys, 'frozen', False):
        try:
            exe_path = sys.executable
            bat_path = os.path.join(os.environ['TEMP'], 'clean_installer.bat')
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak > nul
del /f /q "{exe_path}"
del /f /q "%~f0"
''')
            subprocess.Popen(['cmd.exe', '/c', bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

if __name__ == "__main__":
    install_target_dir = select_installation_directory()
    setup_environment(install_target_dir)
    create_desktop_shortcut(install_target_dir)
    
    install_py_path = os.path.join(install_target_dir, "install_libs.py")
    if os.path.exists(install_py_path):
        subprocess.Popen(f'cmd.exe /c "python install_libs.py"', cwd=install_target_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)

    self_delete_installer()