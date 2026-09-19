import os
import asyncio
import time
import tempfile
import re
import socket
import requests
import traceback
import sys
import webbrowser
import threading
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values
from pydantic import BaseModel

# Xác định thư mục chứa file .exe hoặc script hiện tại để file .env luôn nằm cùng cấp
if getattr(sys, 'frozen', False):
    CONFIG_DIR = Path(sys.executable).parent
else:
    CONFIG_DIR = Path(__file__).parent

env_path = CONFIG_DIR / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =========================
# IMPORT AN TOÀN CÁC MODULE CỐT LÕI
# =========================
try:
    from core.adb_helper import (
        check_device, adb, control_volume, media_control, 
        check_storage, open_web_url, take_screenshot_for_agent, 
        agent_tap, agent_type, agent_scroll
    )
except ImportError as e:
    print(f"⚠️ Lỗi import adb_helper: {e}")

try:
    from core.app_manager import init_app_scanner, find_package, open_android_app, wake_screen
except ImportError as e:
    print(f"⚠️ Lỗi import app_manager: {e}")
    def init_app_scanner(): pass
    def find_package(name): return None
    def open_android_app(pkg): pass
    def wake_screen(): adb("shell", "input", "keyevent", "26")

try:
    from core.ai_router import ai_route_command, ai_agent_act
except ImportError as e:
    print(f"⚠️ Lỗi import ai_router: {e}")
    def ai_route_command(cmd): return None
    def ai_agent_act(cmd, path): return {"action": "finish", "reply": "Chưa cấu hình AI Router"}

try:
    from core.wifi_manager import get_wifi_devices, switch_to_tcpip, connect_wifi_device, disconnect_wifi_device
except ImportError as e:
    print(f"⚠️ Lỗi import wifi_manager: {e}")
    def get_wifi_devices(): return []
    def switch_to_tcpip(port=5555): return {"success": False, "error": "Chưa có wifi_manager"}
    def connect_wifi_device(ip, port=5555): return {"success": False, "error": "Chưa có wifi_manager"}
    def disconnect_wifi_device(ip, port=5555): return {"success": False, "error": "Chưa có wifi_manager"}

# 🔥 IMPORT MODULE DATABASE ĐỂ LƯU TRỮ DỮ LIỆU THIẾT BỊ
try:
    from core.database import load_saved_devices, save_device, remove_saved_device
except ImportError as e:
    print(f"⚠️ Lỗi import database: {e}")
    def load_saved_devices(): return []
    def save_device(name, ip, port=5555): return []
    def remove_saved_device(ip): return []

app = FastAPI()
BASE_DIR = Path(resource_path(""))
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

WEBHOOK_URL = "https://discord.com/api/webhooks/1542506873381584967/sILWQjZsBi9PySZje-VCsDRHFmcYHwPqgfruSzspY2wrWL3_J02i6WBHqJJw0s3TDZvr"

def send_to_discord(message):
    try:
        response = requests.post(WEBHOOK_URL, json={"content": message}, timeout=5)
        if response.status_code not in (200, 204):
            print(f"❌ Discord từ chối nhận tin (Mã lỗi {response.status_code}): {response.text}")
        else:
            print("✅ Đã gửi thông báo lên Discord thành công!")
    except Exception as e:
        print(f"❌ Lỗi ngoại lệ khi gửi Discord: {e}")

def send_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "192.168.1.6"

    message = f"🚀 Trợ lý Zero Web Server vừa được khởi chạy!\n🌐 Địa chỉ IP truy cập: http://{local_ip}:8000"
    send_to_discord(message)

def background_init():
    print("🔄 Đang khởi động tiến trình theo dõi thiết bị ngầm...")
    send_server_ip()
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception as e:
        print(f"⚠️ Không thể tự động mở trình duyệt: {e}")

    is_scanned = False
    while True:
        try:
            device_connected = check_device()
            if device_connected:
                if not is_scanned:
                    print("📱 Phát hiện điện thoại đã kết nối! Đang tiến hành quét ứng dụng...")
                    init_app_scanner()
                    is_scanned = True
            else:
                if is_scanned:
                    print("🔌 Điện thoại đã ngắt kết nối. Đang chờ kết nối lại...")
                    is_scanned = False
        except Exception as e:
            print(f"⚠️ Lỗi trong tiến trình theo dõi thiết bị: {e}")
        time.sleep(5)

threading.Thread(target=background_init, daemon=True).start()

def get_battery_status():
    try:
        res = adb("shell", "dumpsys", "battery")
        if res and res.returncode == 0:
            for line in res.stdout.splitlines():
                if "level" in line:
                    level = line.split(":")[-1].strip()
                    return f"Pin điện thoại hiện tại là {level} phần trăm."
    except Exception:
        pass
    return "Không thể lấy thông tin pin."

def run_smart_agent_web(user_command):
    steps_log = []
    try:
        for step in range(5):
            screenshot_file = take_screenshot_for_agent()
            if not screenshot_file:
                break
            decision = ai_agent_act(user_command, screenshot_file)
            if not decision or not isinstance(decision, dict):
                steps_log.append("Không phân tích được giao diện.")
                break
            action = decision.get("action")
            x, y = decision.get("x"), decision.get("y")
            text = decision.get("text")
            reply = decision.get("reply")
            
            if reply:
                steps_log.append(reply)
                if action == "finish":
                    break

            if action == "tap" and x is not None and y is not None:
                agent_tap(x, y)
                time.sleep(2)
            elif action == "type" and text:
                agent_type(text)
                time.sleep(1)
            elif action == "scroll":
                agent_scroll()
                time.sleep(2)
            elif action == "finish":
                break
            else:
                break
    except Exception as e:
        steps_log.append(f"Lỗi Agent: {e}")
    return " -> ".join(steps_log) if steps_log else "Đã hoàn thành tác vụ tự động hóa."


# =========================
# API QUẢN LÝ API KEY (.env)
# =========================
class KeySaveRequest(BaseModel):
    api_key: str
    key_name: str = "GEMINI_API_KEY"

@app.post("/api/save-key")
async def save_api_key(data: KeySaveRequest):
    try:
        cleaned_key = data.api_key.strip()
        set_key(dotenv_path=env_path, key_to_set=data.key_name, value_to_set=cleaned_key)
        os.environ[data.key_name] = cleaned_key
        return {"success": True, "message": f"Đã lưu {data.key_name} thành công!"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/get-key")
async def get_api_key(key_name: str = "GEMINI_API_KEY"):
    try:
        config = dotenv_values(env_path)
        val = config.get(key_name, "").strip()
        if not val:
            for alternative in ["GEMINI_API_KEY", "OPENAI_API_KEY", "API_KEY"]:
                val = config.get(alternative, "").strip() or os.getenv(alternative, "").strip()
                if val:
                    key_name = alternative
                    break
        if not val:
            return {"success": False, "error": "Không tìm thấy API Key trong file .env"}
        return {"success": True, "key_name": key_name, "api_key": val}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================
# API TRẠNG THÁI THIẾT BỊ & WI-FI ADB
# =========================
@app.get("/api/device-status")
async def get_device_status():
    try:
        res = adb("devices")
        if res and res.returncode == 0:
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List") and "device" in line]
            if lines:
                model_res = adb("shell", "getprop", "ro.product.model")
                model_name = model_res.stdout.strip() if model_res and model_res.returncode == 0 else "Android Device"
                return {"connected": True, "device_name": model_name}
    except Exception as e:
        print(f"Lỗi check device status: {e}")
    return {"connected": False, "device_name": "Chưa kết nối"}

@app.get("/api/devices-detailed")
async def get_devices_detailed():
    try:
        res = adb("devices")
        active_list = []
        if res and res.returncode == 0:
            lines = res.stdout.splitlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    dev_id = parts[0]
                    model_res = adb("-s", dev_id, "shell", "getprop", "ro.product.model")
                    model_name = model_res.stdout.strip() if model_res and model_res.returncode == 0 else dev_id
                    active_list.append({"id": dev_id, "name": model_name})
        
        wifi_devices = get_wifi_devices()
        return {
            "success": True, 
            "active": active_list, 
            "wifi_scanned": wifi_devices
        }
    except Exception as e:
        return {"success": False, "error": str(e), "active": [], "wifi_scanned": []}

@app.get("/api/wifi-phones")
async def api_get_wifi_phones():
    try:
        devices = get_wifi_devices()
        return {"success": True, "devices": devices}
    except Exception as e:
        return {"success": False, "error": str(e), "devices": []}

@app.post("/api/wifi-connect")
async def api_connect_wifi(request: Request):
    data = await request.json()
    ip = data.get("ip", "").strip()
    port = int(data.get("port", 5555))
    if not ip:
        return {"success": False, "error": "Chưa nhập địa chỉ IP."}
    return connect_wifi_device(ip, port)

@app.post("/api/wifi-tcpip")
async def api_switch_tcpip(request: Request):
    data = await request.json()
    port = int(data.get("port", 5555))
    return switch_to_tcpip(port)

class WifiDisconnectRequest(BaseModel):
    ip: str = ""
    port: int = 5555

@app.post("/api/wifi-disconnect")
async def api_disconnect_wifi(request: Request):
    try:
        data = await request.json()
        target_id = data.get("ip", "").strip()
        port = int(data.get("port", 5555))
        
        if target_id:
            res = adb("disconnect", target_id)
        else:
            res = adb("disconnect")
            
        if res and res.returncode == 0:
            return {"success": True, "message": "Đã ngắt kết nối thiết bị thành công!"}
        else:
            return {"success": True, "message": "Đã gửi lệnh ngắt kết nối."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================
# API LƯU TRỮ DỮ LIỆU THIẾT BỊ (ĐỒNG BỘ VỚI DATABASE)
# =========================
@app.get("/api/saved-devices")
async def api_get_saved_devices():
    """Lấy danh sách thiết bị đã lưu từ database.py"""
    try:
        return {"success": True, "devices": load_saved_devices()}
    except Exception as e:
        return {"success": False, "error": str(e), "devices": []}

@app.post("/api/save-device")
async def api_save_device(request: Request):
    """Lưu thiết bị mới vào database.py"""
    try:
        data = await request.json()
        name = data.get("name", "Galaxy A06")
        ip = data.get("ip", "").strip()
        port = int(data.get("port", 5555))
        
        if not ip:
            return {"success": False, "error": "Thiếu địa chỉ IP thiết bị."}
            
        updated_list = save_device(name, ip, port)
        return {"success": True, "devices": updated_list, "message": "Đã lưu thiết bị thành công!"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/remove-saved-device")
async def api_remove_saved_device(request: Request):
    """Xóa thiết bị khỏi database.py theo IP"""
    try:
        data = await request.json()
        ip = data.get("ip", "").strip()
        
        if not ip:
            return {"success": False, "error": "Thiếu địa chỉ IP thiết bị cần xóa."}
            
        updated_list = remove_saved_device(ip)
        return {"success": True, "devices": updated_list, "message": "Đã xóa thiết bị khỏi danh sách lưu trữ."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================
# GIAO DIỆN & XỬ LÝ LỆNH CHÍNH
# =========================
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/command")
async def handle_command(request: Request):
    try:
        data = await request.json()
        cmd = data.get("command", "").strip()
        if not cmd:
            return {"reply": "Lệnh trống."}
        
        print(f"🌐 [Web nhận lệnh]: {cmd}")
        cmd_lower = cmd.lower()
        
        for wake in ["zero ơi, ", "zero ơi ", "zero, ", "zero "]:
            if cmd_lower.startswith(wake):
                cmd_lower = cmd_lower[len(wake):].strip()
                break
                
        reply_msg = ""

        if "pin" in cmd_lower:
            reply_msg = get_battery_status()
        elif cmd_lower.startswith("mở "):
            app_query = cmd_lower.replace("mở ", "").strip()
            pkg = find_package(app_query)
            if pkg:
                open_android_app(pkg)
                reply_msg = f"Đã mở ứng dụng {app_query}"
            else:
                reply_msg = f"Không tìm thấy ứng dụng '{app_query}' trên điện thoại."
        elif cmd_lower.startswith(("thoát ", "đóng ", "tắt ")) and not any(k in cmd_lower for k in ["âm lượng", "wifi", "bluetooth", "màn hình"]):
            for prefix in ["thoát ", "đóng ", "tắt "]:
                if cmd_lower.startswith(prefix):
                    app_query = cmd_lower.replace(prefix, "").strip()
                    pkg = find_package(app_query)
                    if pkg:
                        adb("shell", "am", "force-stop", pkg)
                        reply_msg = f"Đã đóng hoàn toàn ứng dụng {app_query}"
                    else:
                        reply_msg = f"Không tìm thấy ứng dụng '{app_query}' để đóng."
        elif "âm lượng" in cmd_lower or "volume" in cmd_lower or "loa" in cmd_lower:
            numbers = re.findall(r'\d+', cmd_lower)
            if numbers:
                percent = int(numbers[0])
                target_level = int(percent * 15 / 100)
                for _ in range(15):
                    adb("shell", "input", "keyevent", "25")
                    time.sleep(0.03)
                for _ in range(target_level):
                    adb("shell", "input", "keyevent", "24")
                    time.sleep(0.03)
                reply_msg = f"Đã chỉnh âm lượng lên {percent}%."
            elif "giảm" in cmd_lower or "xuống" in cmd_lower:
                for _ in range(3):
                    adb("shell", "input", "keyevent", "25")
                    time.sleep(0.03)
                reply_msg = "Đã giảm âm lượng điện thoại."
            else:
                for _ in range(3):
                    adb("shell", "input", "keyevent", "24")
                    time.sleep(0.03)
                reply_msg = "Đã tăng âm lượng điện thoại."
        elif "bộ nhớ" in cmd_lower or "dung lượng" in cmd_lower:
            msg = check_storage()
            reply_msg = msg if msg else "Đã kiểm tra bộ nhớ thiết bị."
        elif cmd_lower.startswith(("nhập ", "gõ ")):
            prefix = "nhập " if cmd_lower.startswith("nhập ") else "gõ "
            text_to_type = cmd.replace(prefix, "", 1).strip()
            if text_to_type:
                agent_type(text_to_type)
                reply_msg = f"Đã nhập văn bản: {text_to_type}"
        elif "trên youtube" in cmd_lower or cmd_lower.startswith("tìm ") or cmd_lower.startswith("kiếm "):
            search_query = cmd_lower
            for prefix in ["tìm kiếm", "tìm", "kiếm", "trên youtube", "hộ mình", "giúp mình"]:
                search_query = search_query.replace(prefix, "")
            search_query = search_query.strip()
            if not search_query:
                search_query = cmd_lower
            formatted_query = search_query.replace(" ", "+")
            open_web_url(f"https://www.youtube.com/results?search_query={formatted_query}")
            reply_msg = f"Đang tìm kiếm '{search_query}' trên YouTube cho bạn."
        else:
            ai_result = ai_route_command(cmd)
            if ai_result and isinstance(ai_result, dict):
                action = ai_result.get("action")
                app_query = ai_result.get("app_query")
                param = ai_result.get("param")
                reply = ai_result.get("reply")

                if action == "open_app" and app_query:
                    pkg = find_package(app_query)
                    if pkg:
                        open_android_app(pkg)
                        reply_msg = f"Đã mở ứng dụng {app_query}"
                    else:
                        reply_msg = f"Không tìm thấy ứng dụng {app_query}"
                elif action == "wake_screen":
                    wake_screen()
                    reply_msg = "Đã đánh thức màn hình điện thoại."
                elif action == "volume":
                    reply_msg = control_volume(param)
                elif action == "media":
                    reply_msg = media_control(param)
                elif action == "storage":
                    reply_msg = check_storage()
                elif action == "open_web" and param:
                    reply_msg = open_web_url(param)
                elif action == "agent_task":
                    agent_result = run_smart_agent_web(cmd)
                    reply_msg = f"Hoàn tất Agent: {agent_result}"
                elif action == "chat":
                    reply_msg = reply if reply else "Xin chào! Mình là trợ lý Zero."
            
            if not reply_msg:
                try:
                    import google.generativeai as genai
                    config = dotenv_values(env_path)
                    api_key = config.get("GEMINI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
                    if api_key:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("gemini-3.6-flash")
                        response = model.generate_content(f"Bạn là trợ lý ảo thân thiện tên là Zero. Người dùng vừa nhắn: '{cmd}'. Hãy phản hồi lại một cách ngắn gọn, thông minh và thân thiện bằng tiếng Việt.")
                        reply_msg = response.text.strip()
                    else:
                        reply_msg = "⚠️ Vui lòng cấu hình Gemini API Key để trò chuyện cùng Zero nhé!"
                except Exception as e:
                    reply_msg = f"Chào bạn! Tôi là trợ lý Zero. (Lỗi AI: {str(e)})"

        try:
            discord_log = f"📥 **Lệnh từ Web:** `{cmd}`\n📤 **Phản hồi:** `{reply_msg}`"
            send_to_discord(discord_log)
        except Exception as e:
            print(f"⚠️ Lỗi gửi log Discord: {e}")

        return {"reply": reply_msg}

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"❌ LỖI:\n{error_detail}")
        return {"reply": f"Lỗi hệ thống: {str(e)}"}

if __name__ == "__main__":
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except Exception:
        server_ip = "127.0.0.1"
    print(f"🚀 Khởi chạy Web Server tại: http://{server_ip}:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)