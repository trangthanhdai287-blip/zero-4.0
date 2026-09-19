import os
import json
from pathlib import Path

# Xác định đường dẫn thư mục lưu dữ liệu thiết bị
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEVICES_DB_FILE = DATA_DIR / "saved_devices.json"

def _ensure_data_dir():
    """Đảm bảo thư mục lưu trữ data tồn tại"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_saved_devices():
    """Đọc danh sách thiết bị đã lưu từ file JSON"""
    _ensure_data_dir()
    if not DEVICES_DB_FILE.exists():
        return []
    try:
        with open(DEVICES_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Lỗi đọc file saved_devices.json: {e}")
        return []

def save_device(name, ip, port=5555):
    """Lưu hoặc cập nhật thông tin thiết bị vào file JSON"""
    devices = load_saved_devices()
    
    # Kiểm tra xem IP đã tồn tại chưa, nếu có rồi thì cập nhật tên/cổng, nếu chưa thì thêm mới
    found = False
    for dev in devices:
        if dev.get("ip") == ip:
            dev["name"] = name
            dev["port"] = port
            found = True
            break
    
    if not found:
        devices.append({"name": name, "ip": ip, "port": port})
    
    _ensure_data_dir()
    try:
        with open(DEVICES_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(devices, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi ghi file saved_devices.json: {e}")
        
    return devices

def remove_saved_device(ip):
    """Xóa thiết bị khỏi danh sách đã lưu theo IP"""
    devices = load_saved_devices()
    devices = [dev for dev in devices if dev.get("ip") != ip]
    
    _ensure_data_dir()
    try:
        with open(DEVICES_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(devices, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi ghi file saved_devices.json sau khi xóa: {e}")
        
    return devices