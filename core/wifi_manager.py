import socket
import subprocess
import concurrent.futures

def run_adb_cmd(*args):
    """Hàm chạy lệnh adb nội bộ cho wifi_manager"""
    try:
        result = subprocess.run(["adb"] + list(args), capture_output=True, text=True, timeout=5)
        return result
    except Exception as e:
        print(f"Lỗi ADB trong wifi_manager: {e}")
        return None

def get_wifi_devices():
    """Tự động quét thông minh, loại bỏ mạng ảo (VirtualBox/VPN) để tìm điện thoại chung Wi-Fi"""
    found_devices = []
    subnets_to_scan = set()
    
    try:
        # Lấy dải IP thực tế của máy tính
        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        
        for ip in ip_addresses:
            if ip.startswith("127.") or ip.startswith("169.254.") or ip.startswith("192.168.56."):
                continue
            subnet = ".".join(ip.split(".")[:3]) + "."
            subnets_to_scan.add(subnet)
            
        if not subnets_to_scan:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            subnets_to_scan.add(".".join(local_ip.split(".")[:3]) + ".")

        def check_ip(ip):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex((ip, 5555))
                sock.close()
                if result == 0:
                    return ip
            except:
                pass
            return None

        for subnet in subnets_to_scan:
            ips_to_scan = [f"{subnet}{i}" for i in range(1, 255)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
                results = executor.map(check_ip, ips_to_scan)
                for ip in results:
                    if ip and not any(d['ip'] == ip for d in found_devices):
                        found_devices.append({
                            "ip": ip, 
                            "port": 5555, 
                            "name": f"Galaxy A06 / Android ({ip})"
                        })
    except Exception as e:
        print(f"⚠️ Lỗi quét thiết bị Wi-Fi: {e}")
        
    return found_devices

def switch_to_tcpip(port=5555):
    """Chuyển thiết bị đang cắm cáp USB sang chế độ kết nối TCP/IP"""
    res = run_adb_cmd("tcpip", str(port))
    if res and res.returncode == 0:
        return {"success": True, "message": f"Đã chuyển sang chế độ TCP/IP cổng {port} thành công! Bây giờ bạn có thể rút cáp."}
    return {"success": False, "error": res.stdout.strip() if res else "Không tìm thấy thiết bị cắm cáp USB."}

def connect_wifi_device(ip, port=5555):
    """Kết nối tới điện thoại qua địa chỉ IP Wi-Fi"""
    res = run_adb_cmd("connect", f"{ip}:{port}")
    output = res.stdout if res else ""
    if "connected" in output.lower():
        return {"success": True, "message": f"Đã kết nối thành công với {ip}:{port}"}
    return {"success": False, "error": output.strip() or "Kết nối thất bại."}

def disconnect_wifi_device(ip, port=5555):
    """Ngắt kết nối thiết bị Wi-Fi"""
    res = run_adb_cmd("disconnect", f"{ip}:{port}")
    return {"success": True, "message": f"Đã ngắt kết nối {ip}"}