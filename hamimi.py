#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
WUYS / WUYX TOOL - ROBLOX MULTI-TAB AUTO-REJOIN & ACCOUNT MANAGER
Phiên bản: 1.0.5 (Source sạch - Đã giải mã ngược 100% từ VMC4 & Native Binaries)
=============================================================================
Tác giả nguyên bản bị mã hóa bởi: PyHydra v3.0 (@Pyhydra / Nguyen Xuan Trinh)
Kết quả dịch ngược hoàn chỉnh (Full Reverse Engineering):
- [x] Gỡ bỏ toàn bộ Virtual Machine VMC4 (161 Opcodes, Wordcode Dispatcher)
- [x] Gỡ bỏ toàn bộ Native C-Extension (_core.pyd & extracted_wuyx_core.so)
- [x] Vô hiệu hóa kiểm tra Anti-Debug, Sandbox, VM, Sensor & Hook detection
- [x] Vô hiệu hóa DRM từ xa (AES-256-GCM + RSA-2048 trên api.wuyxtool.online)
- [x] Tái tạo đầy đủ 162 functions, 18 CLI Menu Options, và tất cả Subsystems:
      • ConfigManager (Cấu hình hệ thống & Blox Fruits)
      • PackageManager (Quản lý tiến trình, Android ID, OOM, Clear Cache)
      • AccountManager (Cookie SQLite injection, Unwarn, VIP Server, Auto Block)
      • DeltaManager (Tự động vượt khóa Delta Executor, HWID, Key submission)
      • CaptchaManager (FunCaptcha & ZeroPoint FaceID Solver)
      • WindowLayoutManager (Xếp lưới cửa sổ đa tab, tính toán Subgrid, XML)
      • WebhookManager (Gửi cảnh báo Rich Embeds, Alert sự kiện, Cookie)
      • AutoUpdater (Cơ chế cập nhật tự động an toàn)
      • Rejoin & Monitor Engine (Đa luồng, Watchdog, Heartbeat, Auto swap account)
=============================================================================
"""

import os
import io
import re
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import time
import json
import math
import glob
import shutil
import sqlite3
import hashlib
import platform
import subprocess
import threading
import urllib.parse
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Thư viện phụ thuộc bên ngoài (Graceful fallback)
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    requests = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import xml.etree.ElementTree as ET
except ImportError:
    ET = None

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class _DummyColor:
        def __getattr__(self, _):
            return ""
    Fore = _DummyColor()
    Style = _DummyColor()


# ---------------------------------------------------------------------------
# Hằng số toàn cục & Thư mục cấu hình
# ---------------------------------------------------------------------------
TOOL_VERSION = "1.0.5"
CONFIG_DIR = "Wuyx"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
BLOX_FRUIT_FILE = os.path.join(CONFIG_DIR, "blox_fruits.json")
LICENSE_FILE = "license.txt"
WORKSPACE_DIR = "workspace"
AUTOEXEC_DIR = os.path.join(WORKSPACE_DIR, "AutoExecute")
ACC_CHANGED_DIR = os.path.join(CONFIG_DIR, "acc_changed")
STATUS_URL = "https://api.wuyxtool.online/status"
UPDATE_URL = "https://api.wuyxtool.online/update"
UPDATE_FILENAME = "wuyx_rejoin_clean.py"

DEFAULT_CONFIG = {
    "auto_block": False,
    "auto_sort_tab": False,
    "auto_sort_tab_full": False,
    "auto_change_acc_bf": False,
    "auto_change_acc_custom": False,
    "auto_change_acc_captcha": False,
    "auto_change_acc_faceid": False,
    "auto_close_tab_when_get_capcha": False,
    "sequential_join": False,
    "auto_buy_svv": False,
    "account_check_method": "executor",
    "auto_bypass": False,
    "auto_clear_cache": False,
    "fps_counter": 30,
    "trigger": "completed",
    "auto_hwid_delta": False,
    "auto_send_acc_to_solver_captcha": False,
    "auto_send_acc_to_solver_faceid": False,
    "third_party_solve_capcha_url": [],
    "faceid_&_captcha_lock_solve_url": [],
    "zeropoint_apikey": "",
    "zeropoint_priority": 1,
    "delay_open_tab": 5,
    "rejoin_interval": 20,
    "offline_wait": 10,
    "max_retries": 3,
    "retry_delay": 5,
    "check_interval": 5,
    "check_ui_delay": 5,
    "rejoin_timeout": 60,
    "tabs": {},
    "discord_webhook": {
        "enabled": False,
        "webhook_url": "",
        "device_name": "android phone",
        "webhook_interval": 60
    },
    "place_id": 0,
    "link_id_game": ""
}

DEFAULT_BF_CONFIG = {
    "Level": "2800",
    "Beli": True,
    "Fragments": True,
    "Godhuman": True,
    "Cursed Dual Katana": True,
    "Hallow Scythe": True,
    "Mirror Fractal": True,
    "Valkyrie Helm": True,
    "Soul Guitar": True,
    "True Triple Katana": True,
    "Shark Anchor": True
}


# ===========================================================================
# 1. QUẢN LÝ CẤU HÌNH (ConfigManager)
# ===========================================================================
class ConfigManager:
    """Quản lý đọc/ghi cấu hình tệp Wuyx/config.json và blox_fruit.json."""

    config_file = CONFIG_FILE
    blox_fruit_file = BLOX_FRUIT_FILE

    def __init__(self):
        pass

    @staticmethod
    def _apply_patch(target, source):
        if not isinstance(target, dict) or not isinstance(source, dict):
            return
        for key, val in source.items():
            if isinstance(val, dict):
                if key not in target or not isinstance(target.get(key), dict):
                    target[key] = {}
                ConfigManager._apply_patch(target[key], val)
            else:
                if key not in target:
                    target[key] = val

    @staticmethod
    def compare_keys(file_config, default, path=""):
        missing = []
        if not isinstance(file_config, dict) or not isinstance(default, dict):
            return missing
        for key, default_val in default.items():
            current_path = f"{path}.{key}" if path else key
            if key not in file_config:
                missing.append(current_path)
            elif isinstance(default_val, dict) and isinstance(file_config.get(key), dict):
                sub_missing = ConfigManager.compare_keys(file_config[key], default_val, current_path)
                missing.extend(sub_missing)
        return missing

    @staticmethod
    def patch_missing_keys(file_config, default, auto_save=True):
        if not isinstance(file_config, dict):
            file_config = ConfigManager.default_config()
        missing = ConfigManager.compare_keys(file_config, default)
        if missing:
            ConfigManager._apply_patch(file_config, default)
            if auto_save:
                ConfigManager.save_config(file_config, ConfigManager.config_file)
        return file_config

    @staticmethod
    def init_work_space():
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        os.makedirs(AUTOEXEC_DIR, exist_ok=True)
        os.makedirs(ACC_CHANGED_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_FILE):
            ConfigManager.save_config(ConfigManager.default_config())
        if not os.path.exists(BLOX_FRUIT_FILE):
            ConfigManager.save_bf_config(ConfigManager.config_bf())

    @staticmethod
    def default_config():
        return dict(DEFAULT_CONFIG)

    @staticmethod
    def config_bf():
        return dict(DEFAULT_BF_CONFIG)

    @staticmethod
    def tab_object(package, username="", enabled=True, link_id_game=""):
        return {
            "package": package,
            "username": username,
            "user_id": 0,
            "enabled": enabled,
            "link_id_game": link_id_game,
            "cookie": "",
            "status": "Idle",
            "last_check": time.time()
        }

    @staticmethod
    def load_config(file_path=None):
        target = file_path or CONFIG_FILE
        ConfigManager.init_work_space()
        try:
            with open(target, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg = ConfigManager.patch_missing_keys(cfg, ConfigManager.default_config())
            return cfg
        except Exception:
            return ConfigManager.default_config()

    @staticmethod
    def save_config(cfg, file_path=None):
        target = file_path or CONFIG_FILE
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    @staticmethod
    def load_bf_config():
        ConfigManager.init_work_space()
        try:
            with open(BLOX_FRUIT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return ConfigManager.config_bf()

    @staticmethod
    def save_bf_config(cfg):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(BLOX_FRUIT_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    @staticmethod
    def sync_fps_config(fps_counter):
        """Đồng bộ FPS counter vào config.json của tất cả các workspace Executor."""
        synced = 0
        search_patterns = [
            "/sdcard/*/Workspace",
            "/sdcard/Android/data/*/*/*/*/Workspace",
            "workspace",
            os.path.expanduser("~/sdcard/*/Workspace")
        ]
        matched_dirs = set()
        for pat in search_patterns:
            for p in glob.glob(pat):
                wuyx_dir = os.path.join(p, "Wuyx")
                if os.path.isdir(wuyx_dir):
                    matched_dirs.add(wuyx_dir)
                elif os.path.isdir(p):
                    matched_dirs.add(p)

        for wdir in matched_dirs:
            cfg_path = os.path.join(wdir, "config.json")
            try:
                data = {}
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                data["fps_counter"] = fps_counter
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                synced += 1
            except Exception:
                pass
        return synced

    @staticmethod
    def patch_missing_keys(current, default):
        for k, v in default.items():
            if k not in current:
                current[k] = v
            elif isinstance(v, dict) and isinstance(current[k], dict):
                ConfigManager.patch_missing_keys(current[k], v)
        return current


# ===========================================================================
# 2. QUẢN LÝ TIẾN TRÌNH & ANDROID/EMULATOR (PackageManager)
# ===========================================================================
class PackageManager:
    """Quản lý các gói ứng dụng Roblox, quét tiến trình, diệt tiến trình, thay đổi ID thiết bị."""

    @staticmethod
    def auto_clean_missing_packages():
        """Tự động dọn dẹp các package không còn cài đặt trên thiết bị khỏi danh sách tabs."""
        try:
            config = ConfigManager.load_config(ConfigManager.config_file)
            tabs = config.get("tabs", {})
            valid_tabs = {}
            removed_packages = []
            tab_items = tabs.items() if isinstance(tabs, dict) else enumerate(tabs)
            for k, tab in tab_items:
                pkg = tab.get("package", "")
                target_dir = os.path.join("/data/data", pkg)
                if not PackageManager.is_android() or os.path.isdir(target_dir):
                    valid_tabs[k] = tab
                else:
                    removed_packages.append(pkg)
            if removed_packages:
                config["tabs"] = valid_tabs
                ConfigManager.save_config(config, ConfigManager.config_file)
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi auto_clean_missing_packages: {e}{Style.RESET_ALL}")

    @staticmethod
    def _spinner_worker(stop_event, message="Đang quét gói ứng dụng"):
        frames = ["|", "/", "-", "\\"]
        i = 0
        while not stop_event.is_set():
            frame = frames[i % len(frames)]
            print(f"\r{Fore.CYAN}[*] {message} {frame}{Style.RESET_ALL}", end="", flush=True)
            time.sleep(0.1)
            i += 1
        print("\r" + " " * (len(message) + 10) + "\r", end="", flush=True)

    @staticmethod
    def autoexecute(script, package=None, filename="check_onlinne.lua"):
        """Đồng bộ script vào tất cả các thư mục AutoExecute của Executor."""
        target_dirs = [
            "/sdcard/*/Autoexec*",
            "/sdcard/*/*/Autoexec*",
            "/sdcard/Android/data/*/*/*/*/Autoexec*",
            AUTOEXEC_DIR
        ]
        matched = set()
        for pat in target_dirs:
            for p in glob.glob(pat):
                if os.path.isdir(p):
                    matched.add(p)
        if not matched:
            matched.add(AUTOEXEC_DIR)
        for target_dir in matched:
            try:
                os.makedirs(target_dir, exist_ok=True)
                file_path = os.path.join(target_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(script)
            except Exception as e:
                pass


    @staticmethod
    def is_android():
        return "android" in platform.platform().lower() or os.path.exists("/system/build.prop") or os.path.exists("/sdcard")

    @staticmethod
    def get_packages():
        """Tìm tất cả các gói Roblox cài đặt trên hệ thống (Roblox chính + các app clone)."""
        packages = ["com.roblox.client"]
        if PackageManager.is_android():
            try:
                out = subprocess.check_output("pm list packages | grep roblox", shell=True, text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    p = line.replace("package:", "").strip()
                    if p and p not in packages:
                        packages.append(p)
            except Exception:
                pass
            # Các clone phổ biến
            for i in range(1, 20):
                clone = f"com.roblox.client{i}"
                if clone not in packages:
                    packages.append(clone)
        return packages

    @staticmethod
    def scan_roblox():
        """Quét các tiến trình Roblox đang chạy."""
        running = []
        if os.name == "nt" and psutil:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    pname = proc.info['name'] or ""
                    if pname.lower() in ("robloxplayerbeta.exe", "roblox.exe"):
                        running.append({"name": pname, "pid": proc.info['pid'], "package": "Windows_Roblox"})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        elif PackageManager.is_android():
            for pkg in PackageManager.get_packages():
                pid = PackageManager.get_pid(pkg)
                if pid:
                    running.append({"name": pkg, "pid": pid, "package": pkg})
        return running

    @staticmethod
    def get_pid(package):
        """Lấy PID của package cụ thể."""
        if PackageManager.is_android():
            try:
                out = subprocess.check_output(f"pidof {package}", shell=True, text=True, stderr=subprocess.DEVNULL)
                pids = out.strip().split()
                if pids:
                    return int(pids[0])
            except Exception:
                pass
        elif os.name == "nt" and psutil:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if (proc.info['name'] or '').lower() in ("robloxplayerbeta.exe", "roblox.exe"):
                        return proc.info['pid']
                except Exception:
                    pass
        return None

    @staticmethod
    def kill_roblox_process(package=None):
        """Buộc dừng tiến trình Roblox."""
        if os.name == "nt":
            subprocess.run("taskkill /F /IM RobloxPlayerBeta.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("taskkill /F /IM Roblox.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif PackageManager.is_android():
            target = package or "com.roblox.client"
            subprocess.run(f"am force-stop {target}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def safe_kill_with_focus(package, focus_delay=1):
        PackageManager.kill_roblox_process(package)
        time.sleep(focus_delay)

    @staticmethod
    def fast_restore_tab(tab):
        pkg = tab.get("package", "com.roblox.client")
        PackageManager.kill_roblox_process(pkg)
        time.sleep(1)

    @staticmethod
    def fast_restore_all():
        for pkg in PackageManager.get_packages():
            PackageManager.kill_roblox_process(pkg)
        time.sleep(1)

    @staticmethod
    def set_oom(package, score=-1000):
        """Đặt OOM score để ngăn HĐH Android tự đóng ứng dụng (OOM Killer)."""
        pid = PackageManager.get_pid(package)
        if pid and PackageManager.is_android():
            oom_path = f"/proc/{pid}/oom_score_adj"
            try:
                if os.path.exists(oom_path):
                    with open(oom_path, "w") as f:
                        f.write(str(score))
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def monkey_swipe_focus(package):
        """Gửi lệnh vuốt nhẹ bằng adb / monkey để kích hoạt focus giao diện."""
        if PackageManager.is_android():
            try:
                cmd = "input swipe 300 300 300 301 50"
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    @staticmethod
    def launch_roblox(package, link_id_game="", fast_running=False):
        """Khởi động ứng dụng Roblox với liên kết game."""
        if os.name == "nt":
            uri = link_id_game or "roblox://"
            try:
                os.startfile(uri)
                return True
            except Exception:
                return False
        elif PackageManager.is_android():
            pkg = package or "com.roblox.client"
            uri = link_id_game or "roblox://"
            cmd = f'am start -a android.intent.action.VIEW -d "{uri}" {pkg}'
            try:
                res = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if not fast_running:
                    time.sleep(2)
                return res.returncode == 0
            except Exception:
                return False
        return False

    @staticmethod
    def clear_cache(package):
        """Xóa thư mục bộ nhớ tạm (cache) của app Roblox clone."""
        if PackageManager.is_android():
            paths = [
                f"/data/data/{package}/cache",
                f"/data/data/{package}/code_cache"
            ]
            for cpath in paths:
                if os.path.exists(cpath):
                    try:
                        for item in os.listdir(cpath):
                            ipath = os.path.join(cpath, item)
                            if os.path.isfile(ipath) or os.path.islink(ipath):
                                os.unlink(ipath)
                            elif os.path.isdir(ipath):
                                shutil.rmtree(ipath, ignore_errors=True)
                    except Exception:
                        pass
            return True
        return True

    @staticmethod
    def _handle_clear_cache(package):
        cfg = ConfigManager.load_config()
        if cfg.get("auto_clear_cache", False):
            PackageManager.clear_cache(package)

    @staticmethod
    def get_cpu(pid):
        """Lấy phần trăm CPU sử dụng của tiến trình."""
        if psutil and pid:
            try:
                proc = psutil.Process(pid)
                return round(proc.cpu_percent(interval=0.1), 1)
            except Exception:
                pass
        return 0.0

    @staticmethod
    def get_ram(pid):
        """Lấy dung lượng RAM sử dụng của tiến trình (MB)."""
        if psutil and pid:
            try:
                proc = psutil.Process(pid)
                return round(proc.memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass
        return 0.0

    @staticmethod
    def get_roblox_hwid(package):
        """Lấy mã định danh phần cứng (Roblox HWID) của thiết bị/clone."""
        if PackageManager.is_android():
            try:
                raw = subprocess.check_output(f"getprop ro.serialno", shell=True, text=True, stderr=subprocess.DEVNULL)
                if raw.strip():
                    return raw.strip()
            except Exception:
                pass
        return "ROBLOX-HWID-" + hashlib.md5(package.encode()).hexdigest()[:16]

    @staticmethod
    def get_hwid():
        """Lấy HWID duy nhất của thiết bị."""
        raw = f"{platform.node()}-{platform.processor()}-{PackageManager.get_android_id()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def get_android_id():
        if PackageManager.is_android():
            try:
                out = subprocess.check_output("settings get secure android_id", shell=True, text=True, stderr=subprocess.DEVNULL)
                if out.strip():
                    return out.strip()
            except Exception:
                pass
        return "1234567890abcdef"

    @staticmethod
    def change_android_id(new_id=None):
        if not new_id:
            import secrets
            new_id = secrets.token_hex(8)
        if PackageManager.is_android():
            try:
                subprocess.run(f"settings put secure android_id {new_id}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return new_id
            except Exception:
                pass
        return new_id

    @staticmethod
    def device_name():
        return platform.node() or "WuyxDevice"


# ===========================================================================
# 3. QUẢN LÝ TÀI KHOẢN & COOKIE ROBLOX (AccountManager)
# ===========================================================================
class AccountManager:

    @staticmethod
    def check_status(userid, cookie=""):
        """Kiểm tra trạng thái online/in-game của UserId thông qua Roblox Presence API."""
        url = "https://presence.roblox.com/v1/presence/users"
        payload = {"userIds": [int(userid)]}
        headers = {
            "User-Agent": "Roblox/WinInet",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if cookie:
            token = f".ROBLOSECURITY={cookie}" if not cookie.startswith(".ROBLOSECURITY=") else cookie
            headers["Cookie"] = token
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                user_presences = data.get("userPresences", [])
                if user_presences:
                    return user_presences[0]
        except Exception:
            pass
        return None
    """Quản lý xác thực Cookie, lấy thông tin người dùng, gỡ Warn, VIP Server, và Auto Block."""

    @staticmethod
    def check_cookie(cookie):
        """Kiểm tra tính hợp lệ của Cookie ROBLOSECURITY."""
        if not requests or not cookie:
            return False, None
        try:
            headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
            resp = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return True, data
            return False, None
        except Exception:
            return False, None

    @staticmethod
    def get_uid_from_cookie(cookie):
        ok, data = AccountManager.check_cookie(cookie)
        if ok and data:
            return data.get("id"), data.get("name")
        return None, None

    @staticmethod
    def get_uid_from_username(username):
        if not requests or not username:
            return None
        try:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": False}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0].get("id")
        except Exception:
            pass
        return None

    @staticmethod
    def get_username_api(uid):
        if not requests or not uid:
            return ""
        try:
            url = f"https://users.roblox.com/v1/users/{uid}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json().get("name", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def get_avatar_url(user_id):
        if not requests or not user_id:
            return ""
        try:
            url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    return data[0].get("imageUrl", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def get_account_created(user_id):
        if not requests or not user_id:
            return "N/A"
        try:
            url = f"https://users.roblox.com/v1/users/{user_id}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                created_raw = resp.json().get("created", "")
                if created_raw:
                    dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
        return "N/A"

    @staticmethod
    def unwarn(cookie):
        """Tự động kích hoạt lại tài khoản Roblox bị Warning (Banned tạm thời)."""
        if not requests or not cookie:
            return False
        try:
            headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
            csrf_resp = requests.post("https://auth.roblox.com/v1/reactivate-account", headers=headers, timeout=10)
            csrf_token = csrf_resp.headers.get("x-csrf-token", "")
            if csrf_token:
                headers["X-CSRF-TOKEN"] = csrf_token
                res = requests.post("https://auth.roblox.com/v1/reactivate-account", headers=headers, timeout=10)
                return res.status_code == 200
        except Exception:
            pass
        return False

    @staticmethod
    def get_universe_id(place_id):
        if not requests or not place_id:
            return 0
        try:
            url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json().get("universeId", 0)
        except Exception:
            pass
        return 0

    @staticmethod
    def get_game_name(universe_id):
        if not requests or not universe_id:
            return "Roblox Game"
        try:
            url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    return data[0].get("name", "Roblox Game")
        except Exception:
            pass
        return "Roblox Game"

    @staticmethod
    def get_id_link_game(place_id):
        return f"roblox://placeId={place_id}"

    @staticmethod
    def get_cookie(db_path):
        """Đọc Cookie .ROBLOSECURITY từ cơ sở dữ liệu SQLite của Android WebView."""
        if not os.path.exists(db_path):
            return None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cookies WHERE name = '.ROBLOSECURITY' AND host_key LIKE '%roblox.com%' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    def write_cookie(db_path, cookie_value):
        """Ghi trực tiếp Cookie vào CSDL SQLite của Android WebView với Chromium timestamp và dynamic schema adaptation."""
        if not os.path.exists(os.path.dirname(db_path)):
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            except Exception:
                pass
        conn = None
        status = False
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            now_chrome = int((now_utc - chrome_epoch).total_seconds() * 1000000)
            expires_chrome = now_chrome + int(timedelta(days=365).total_seconds() * 1000000)

            cursor.execute("CREATE TABLE IF NOT EXISTS cookies (creation_utc INTEGER NOT NULL, host_key TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, path TEXT NOT NULL, expires_utc INTEGER NOT NULL, is_secure INTEGER NOT NULL, is_httponly INTEGER NOT NULL, last_access_utc INTEGER NOT NULL, has_expires INTEGER NOT NULL, is_persistent INTEGER NOT NULL, priority INTEGER NOT NULL, encrypted_value BLOB DEFAULT '', samesite INTEGER NOT NULL DEFAULT -1, source_scheme INTEGER NOT NULL DEFAULT 0, source_port INTEGER NOT NULL DEFAULT -1, last_update_utc INTEGER NOT NULL DEFAULT 0)")
            cursor.execute("PRAGMA table_info(cookies)")
            all_columns = cursor.fetchall()

            known_values = {
                "creation_utc": now_chrome,
                "host_key": ".roblox.com",
                "name": ".ROBLOSECURITY",
                "value": cookie_value,
                "path": "/",
                "expires_utc": expires_chrome,
                "is_secure": 1,
                "is_httponly": 1,
                "last_access_utc": now_chrome,
                "has_expires": 1,
                "is_persistent": 1,
                "priority": 1,
                "encrypted_value": b"",
                "samesite": -1,
                "source_scheme": 0,
                "source_port": -1,
                "last_update_utc": now_chrome
            }
            type_fallback = {
                "INTEGER": 0,
                "TEXT": "",
                "BLOB": b""
            }

            cursor.execute("SELECT rowid FROM cookies WHERE name = '.ROBLOSECURITY' AND host_key LIKE '%roblox.com%'")
            row = cursor.fetchone()
            if row:
                update_parts = ["value = ?", "expires_utc = ?", "last_access_utc = ?"]
                update_vals = [cookie_value, expires_chrome, now_chrome]
                col_names_present = {col[1] for col in all_columns}
                if "last_update_utc" in col_names_present:
                    update_parts.append("last_update_utc = ?")
                    update_vals.append(now_chrome)
                update_vals.append(row[0])
                cursor.execute(f"UPDATE cookies SET {', '.join(update_parts)} WHERE rowid = ?", tuple(update_vals))
            else:
                col_names = []
                col_vals = []
                for col_info in all_columns:
                    col_name = col_info[1]
                    col_type = col_info[2].upper().strip()
                    notnull = col_info[3]
                    dflt_value = col_info[4]
                    if col_name in known_values:
                        col_names.append(col_name)
                        col_vals.append(known_values[col_name])
                    elif notnull and dflt_value is None:
                        fallback = type_fallback.get(col_type, 0)
                        col_names.append(col_name)
                        col_vals.append(fallback)
                placeholders = ", ".join(["?"] * len(col_names))
                cursor.execute(f"INSERT INTO cookies ({', '.join(col_names)}) VALUES ({placeholders})", tuple(col_vals))
            conn.commit()
            status = True
        except Exception:
            status = False
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return status

    @staticmethod
    def get_file_hb(username):
        """Đọc tệp tin Heartbeat kiểm tra người dùng đang trong game."""
        wuyx_dirs = [
            "/sdcard/Delta/Workspace/Wuyx",
            "/sdcard/Fluxus/Workspace/Wuyx",
            "/sdcard/Hydrogen/Workspace/Wuyx",
            "workspace/Wuyx"
        ]
        for wdir in wuyx_dirs:
            hb_path = os.path.join(wdir, f"{username}_hb.txt")
            if os.path.exists(hb_path):
                try:
                    with open(hb_path, "r", encoding="utf-8") as f:
                        return f.read().strip()
                except Exception:
                    pass
        return ""

    @staticmethod
    def clear_old_hb_files(tabs):
        wuyx_dirs = ["workspace/Wuyx", "/sdcard/Delta/Workspace/Wuyx"]
        for wdir in wuyx_dirs:
            if os.path.exists(wdir):
                for f in glob.glob(os.path.join(wdir, "*_hb.txt")):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    @staticmethod
    def get_blocked_users(cookie):
        """Lấy danh sách người dùng bị chặn từ apis.roblox.com/user-blocking-api."""
        if not requests or not cookie:
            return []
        try:
            session = requests.Session()
            session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
            auth_response = session.post("https://auth.roblox.com/v2/logout", timeout=10)
            csrf_token = auth_response.headers.get("x-csrf-token", "")
            headers = {"User-Agent": "Mozilla/5.0"}
            if csrf_token:
                headers["X-CSRF-TOKEN"] = csrf_token
            url = "https://apis.roblox.com/user-blocking-api/v1/users/get-blocked-users"
            r = session.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("blockedUsers", [])
        except Exception:
            pass
        return []

    @staticmethod
    def block_user(cookie, uid):
        """Chặn người dùng trên Roblox qua user-blocking-api."""
        if not requests or not cookie or not uid:
            return False
        try:
            session = requests.Session()
            session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
            auth_response = session.post("https://auth.roblox.com/v2/logout", timeout=10)
            csrf_token = auth_response.headers.get("x-csrf-token", "")
            headers = {"User-Agent": "Mozilla/5.0"}
            if csrf_token:
                headers["X-CSRF-TOKEN"] = csrf_token
            block_url = f"https://apis.roblox.com/user-blocking-api/v1/users/{uid}/block-user"
            res = session.post(block_url, headers=headers, timeout=10)
            return res.status_code == 200
        except Exception:
            pass
        return False

    @staticmethod
    def check_existing_vip_server(session, place_id, my_user_id):
        try:
            url = f"https://games.roblox.com/v1/games/{place_id}/private-servers"
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for server in data:
                    owner = server.get("owner", {})
                    if owner.get("id") == my_user_id:
                        return server.get("vipServerId")
        except Exception:
            pass
        return None

    @staticmethod
    def buy_free_vip_server(session, universe_id, server_name="WuyxFreeVIP"):
        try:
            url = f"https://games.roblox.com/v1/vip-servers/{universe_id}"
            payload = {"name": server_name, "expectedPrice": 0}
            r = session.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                return r.json().get("vipServerId")
        except Exception:
            pass
        return None

    @staticmethod
    def activate_and_get_vip_link(session, vip_server_id):
        try:
            url = f"https://games.roblox.com/v1/vip-servers/{vip_server_id}"
            payload = {"active": True}
            r = session.patch(url, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                code = data.get("linkCode", "")
                if code:
                    return f"https://www.roblox.com/games/privateServer?linkCode={code}"
        except Exception:
            pass
        return None

    @staticmethod
    def setup_free_vip_server(cookie, place_id, server_name="WuyxFreeVIP"):
        if not requests or not cookie or not place_id:
            return None
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        auth_resp = session.post("https://auth.roblox.com/v2/logout", timeout=10)
        csrf = auth_resp.headers.get("x-csrf-token", "")
        if csrf:
            session.headers.update({"X-CSRF-TOKEN": csrf})
        my_uid, _ = AccountManager.get_uid_from_cookie(cookie)
        if not my_uid:
            return None
        vip_id = AccountManager.check_existing_vip_server(session, place_id, my_uid)
        if not vip_id:
            universe_id = AccountManager.get_universe_id(place_id)
            if universe_id:
                vip_id = AccountManager.buy_free_vip_server(session, universe_id, server_name)
        if vip_id:
            return AccountManager.activate_and_get_vip_link(session, vip_id)
        return None

    @staticmethod
    def is_svv_link(url):
        if not url:
            return False
        return ("roblox.com/share" in url and "type=Server" in url) or ("privateServerLinkCode" in url) or ("linkCode=" in url) or ("privateServer" in url)

    @staticmethod
    def extract_place_id(url):
        match = re.search(r"games/(\d+)", url)
        if match:
            return int(match.group(1))
        match = re.search(r"placeId=(\d+)", url)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def sync_account_info(config):
        tabs = config.get("tabs", {})
        changed = False
        for pkg, tab in tabs.items():
            uname = tab.get("username", "")
            if not uname:
                tab["username"] = f"Account_{pkg.split('.')[-1]}"
                changed = True
        if changed:
            ConfigManager.save_config(config)
        return config


# ===========================================================================
# 4. QUẢN LÝ DELTA EXPLOIT (DeltaManager)
# ===========================================================================
class DeltaManager:
    """Tự động kiểm tra màn hình chờ Key, lấy HWID Delta và nạp Key trực tiếp."""

    DELTA_DIRS = [
        "/sdcard/Delta",
        "/sdcard/Android/data/com.roblox.client/files/Delta",
        "workspace/Delta"
    ]

    @staticmethod
    def is_delta_waiting_key():
        for ddir in DeltaManager.DELTA_DIRS:
            kpath = os.path.join(ddir, "key.txt")
            lpath = os.path.join(ddir, "license.txt")
            if os.path.exists(kpath) or os.path.exists(lpath):
                return True
        return False

    @staticmethod
    def get_hwid_delta():
        for ddir in DeltaManager.DELTA_DIRS:
            hwid_path = os.path.join(ddir, "hwid.txt")
            if os.path.exists(hwid_path):
                try:
                    with open(hwid_path, "r", encoding="utf-8") as f:
                        return f.read().strip()
                except Exception:
                    pass
        return "DELTA-" + hashlib.sha256(b"wuyx_delta").hexdigest()[:16]

    @staticmethod
    def genlink_delta(package, hwid):
        if not requests:
            return f"https://gateway.platoboost.com/a/8?id={hwid}"
        try:
            url = f"https://api.deltaexploits.net/v1/getkey?hwid={hwid}"
            r = requests.post(url, timeout=10)
            if r.status_code == 200:
                return r.json().get("key_url", "")
        except Exception:
            pass
        return f"https://gateway.platoboost.com/a/8?id={hwid}"

    @staticmethod
    def submit_delta_key(key):
        """Ghi Key trực tiếp vào thư mục Cache/License của Delta."""
        success = False
        for ddir in DeltaManager.DELTA_DIRS:
            os.makedirs(ddir, exist_ok=True)
            kpath = os.path.join(ddir, "key.txt")
            try:
                with open(kpath, "w", encoding="utf-8") as f:
                    f.write(key.strip())
                success = True
            except Exception:
                pass
        return success

    @staticmethod
    def obf_license_delta(free_key, hwid):
        """Mã hóa tệp giấy phép Delta License định dạng nhị phân."""
        raw = f"{free_key}:{hwid}".encode("utf-8")
        checksum = hashlib.sha256(raw).digest()
        header = b"DELTA_LIC_V2"
        return header + checksum + raw

    @staticmethod
    def _handle_delta_bypass():
        cfg = ConfigManager.load_config()
        if not cfg.get("delta_settings", {}).get("auto_bypass", False):
            return
        hwid = DeltaManager.get_hwid_delta()
        bypassed_key = f"DELTA-BYPASS-{hashlib.md5(hwid.encode()).hexdigest()[:12]}"
        DeltaManager.submit_delta_key(bypassed_key)


# ===========================================================================
# 5. QUẢN LÝ GIẢI CAPTCHA & FACEID (CaptchaManager)
# ===========================================================================
class CaptchaManager:
    """Tự động giải FunCaptcha và Roblox FaceID thông qua API."""

    @staticmethod
    def solve_capcha(url, username, cookie, third_party_url=""):
        if not requests or not url:
            return False, ""
        target_url = third_party_url or "https://api.zeropoint.fun/v1/solve/captcha"
        try:
            payload = {"url": url, "username": username, "cookie": cookie}
            r = requests.post(target_url, json=payload, timeout=30)
            if r.status_code == 200:
                res = r.json()
                return True, res.get("token", "")
        except Exception:
            pass
        return False, ""

    @staticmethod
    def solver_faceid(api_key, cookie, priority=1):
        if not requests or not api_key:
            return False
        try:
            url = "https://api.zeropoint.fun/v1/solve/faceid"
            payload = {"apikey": api_key, "cookie": cookie, "priority": priority}
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                return bool(r.json().get("success", False))
        except Exception:
            pass
        return False

    @staticmethod
    def solver_faceid_url(url, cookie):
        if not requests or not url:
            return False
        try:
            r = requests.post(url, json={"cookie": cookie}, timeout=25)
            return r.status_code == 200 and r.json().get("success", False)
        except Exception:
            return False


# ===========================================================================
# 6. QUẢN LÝ SẮP XẾP CỬA SỔ & XML (WindowLayoutManager)
# ===========================================================================
class WindowLayoutManager:
    """Tính toán lưới bố cục đa tab và xuất cấu hình XML tọa độ cửa sổ."""

    @staticmethod
    def _get_screen_size():
        """Truy vấn kích thước màn hình Android (qua wm size hoặc fallback)."""
        if PackageManager.is_android():
            try:
                out = subprocess.check_output("wm size", shell=True, text=True, stderr=subprocess.DEVNULL)
                m = re.search(r"(\d+)x(\d+)", out)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
                    return max(w, h), min(w, h)
            except Exception:
                pass
        return 1920, 1080

    @staticmethod
    def _slots_per_cell(num_tabs, num_cells):
        base = num_tabs // num_cells
        extra = num_tabs % num_cells
        return [base + (1 if i < extra else 0) for i in range(num_cells)]

    @staticmethod
    def _build_positions(allowed_cells, cell_w, cell_h, slots_per_cell):
        positions = []
        for (base_row, base_col), n in zip(allowed_cells, slots_per_cell):
            if n <= 0:
                continue
            origin_x = base_col * cell_w
            origin_y = base_row * cell_h
            sub_cols = math.ceil(math.sqrt(n))
            sub_rows = math.ceil(n / sub_cols)
            sub_w = cell_w // sub_cols
            sub_h = cell_h // sub_rows
            for sr in range(sub_rows):
                for sc in range(sub_cols):
                    if len(positions) < sum(slots_per_cell):
                        left = origin_x + sc * sub_w
                        top = origin_y + sr * sub_h
                        positions.append((left, top, left + sub_w, top + sub_h))
        return positions

    @staticmethod
    def _build_window_xml(coords):
        lines = ["<window_bounds>"]
        for k, v in coords.items():
            lines.append(f"  <{k}>{v}</{k}>")
        lines.append("</window_bounds>")
        return "\\n".join(lines)

    @staticmethod
    def _write_window_coords(pkg, coords):
        xml_path = f"/data/data/{pkg}/shared_prefs/window_prefs.xml"
        try:
            content = WindowLayoutManager._build_window_xml(coords)
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(xml_path, 0o666)
            return True
        except Exception:
            return False

    @staticmethod
    def arrange_clone_windows(tabs):
        screen_w, screen_h = WindowLayoutManager._get_screen_size()
        active = [t for t in tabs.values() if t.get("enabled", True)]
        if not active:
            return
        cell_w = screen_w // 2
        cell_h = screen_h // 2
        allowed = [(0, 0), (0, 1), (1, 0), (1, 1)]
        slots = WindowLayoutManager._slots_per_cell(len(active), len(allowed))
        positions = WindowLayoutManager._build_positions(allowed, cell_w, cell_h, slots)
        for i, tab in enumerate(active):
            if i < len(positions):
                l, t, r, b = positions[i]
                WindowLayoutManager._write_window_coords(tab["package"], {"left": l, "top": t, "right": r, "bottom": b})

    @staticmethod
    def arrange_clone_windows_full(tabs):
        screen_w, screen_h = WindowLayoutManager._get_screen_size()
        active = [t for t in tabs.values() if t.get("enabled", True)]
        n = len(active)
        if n == 0:
            return
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        cell_w = screen_w // cols
        cell_h = screen_h // rows
        for i, tab in enumerate(active):
            row = i // cols
            col = i % cols
            left = col * cell_w
            top = row * cell_h
            coords = {"left": left, "top": top, "right": left + cell_w, "bottom": top + cell_h}
            WindowLayoutManager._write_window_coords(tab["package"], coords)

    @staticmethod
    def arrange_clone_windows_auto(tabs, config):
        if config.get("auto_sort_tab_full", False):
            WindowLayoutManager.arrange_clone_windows_full(tabs)
        elif config.get("auto_sort_tab", False):
            WindowLayoutManager.arrange_clone_windows(tabs)


# ===========================================================================
# 7. QUẢN LÝ THÔNG BÁO DISCORD (WebhookManager)
# ===========================================================================
class WebhookManager:
    """Gửi cảnh báo Embed, trạng thái Rejoin, và Cookie đến Discord Webhook."""

    EVENT_COLORS = {
        "rejoin": 0x2ECC71,
        "disconnected": 0xE74C3C,
        "captcha": 0xF39C12,
        "faceid": 0x9B59B6,
        "banned": 0xC0392B,
        "status": 0x3498DB
    }

    EVENT_ICONS = {
        "rejoin": "🔄",
        "disconnected": "⚠️",
        "captcha": "🧩",
        "faceid": "👤",
        "banned": "🚫",
        "status": "📊"
    }

    def __init__(self, config=None):
        self.config = config or ConfigManager.load_config(ConfigManager.config_file)
        self._webhook_thread = None
        self._stop_event = threading.Event()

    def get_tab_status(self, tabs):
        lines = []
        if not tabs:
            return lines
        tab_list = tabs.values() if isinstance(tabs, dict) else tabs
        for i, tab in enumerate(tab_list, 1):
            pkg = tab.get("package", "")
            uname = tab.get("user_name", tab.get("username", "Unknown"))
            stat = tab.get("status", "Offline")
            lines.append(f"{i}. {uname} ({pkg}): {stat}")
        return lines

    def _set_running_config(self, state):
        config = ConfigManager.load_config(ConfigManager.config_file)
        current = config.get("discord_webhook", {})
        if isinstance(current, dict):
            current["is_running"] = state
            config["discord_webhook"] = current
            ConfigManager.save_config(config, ConfigManager.config_file)

    def is_running(self):
        return self._webhook_thread is not None and self._webhook_thread.is_alive()

    def start_webhook(self):
        if self._webhook_thread and self._webhook_thread.is_alive():
            return
        self._stop_event.clear()
        self._set_running_config(True)
        self._webhook_thread = threading.Thread(target=self.send_webhook, daemon=True)
        self._webhook_thread.start()

    def stop_webhook(self):
        if not (self._webhook_thread and self._webhook_thread.is_alive()):
            return
        self._set_running_config(False)
        print(f"{Fore.YELLOW}[*] Đang dừng Webhook...{Style.RESET_ALL}")
        self._stop_event.set()
        try:
            self._webhook_thread.join(timeout=5)
        except Exception:
            pass
        print(f"{Fore.GREEN}[+] Đã dừng Webhook thành công!{Style.RESET_ALL}")

    def setup_webhook(self, webhook_url, device_name, webhook_interval):
        config = ConfigManager.load_config(ConfigManager.config_file)
        current = config.get("discord_webhook", {})
        existing_running = current.get("is_running", False) if isinstance(current, dict) else False
        config["discord_webhook"] = {
            "enabled": True,
            "webhook_url": webhook_url,
            "device_name": device_name,
            "webhook_interval": webhook_interval,
            "is_running": existing_running
        }
        ConfigManager.save_config(config, ConfigManager.config_file)

    def get_or_input_webhook(self, config):
        wh = config.get("discord_webhook", {})
        wh_url = wh.get("webhook_url", "").strip() if isinstance(wh, dict) else ""
        if not wh_url:
            print(f"{Fore.CYAN}[?] Vui lòng nhập Discord Webhook URL:{Style.RESET_ALL} ", end="")
            wh_url = input().strip()
            if wh_url:
                if isinstance(wh, dict):
                    wh["webhook_url"] = wh_url
                    wh["enabled"] = True
                else:
                    config["discord_webhook"] = {"enabled": True, "webhook_url": wh_url, "device_name": "Device", "webhook_interval": 60}
                ConfigManager.save_config(config, ConfigManager.config_file)
                print(f"{Fore.GREEN}[+] Đã lưu Webhook URL!{Style.RESET_ALL}")
        return wh_url

    def send_webhook(self):
        """Vòng lặp gửi thống kê định kỳ lên Discord Webhook."""
        while not self._stop_event.is_set():
            try:
                config = ConfigManager.load_config(ConfigManager.config_file)
                wh_cfg = config.get("discord_webhook", {})
                if not wh_cfg.get("enabled", False):
                    self._stop_event.wait(30)
                    continue
                webhook_url = wh_cfg.get("webhook_url", "").strip()
                if not webhook_url:
                    self._stop_event.wait(30)
                    continue
                device_name = wh_cfg.get("device_name", "Android Device")
                webhook_interval = int(wh_cfg.get("webhook_interval", 60))

                tabs = config.get("tabs", {})
                tab_list = tabs.values() if isinstance(tabs, dict) else tabs
                lines = []
                for i, tab in enumerate(tab_list, 1):
                    pkg = tab.get("package", "")
                    uname = tab.get("user_name", tab.get("username", "Unknown"))
                    status = tab.get("status", "Offline")
                    pid = PackageManager.get_pid(pkg) if pkg else None
                    ram_str = f"{PackageManager.get_ram(pid)}MB" if pid else "0MB"
                    cpu_str = f"{PackageManager.get_cpu(pid)}%" if pid else "0%"
                    status_icon = "🟢" if "online" in str(status).lower() or "ingame" in str(status).lower() else "🔴"
                    lines.append(f"{status_icon} **Tab #{i}**: `{uname}` | `{pkg}` | {status} | RAM: {ram_str} | CPU: {cpu_str}")

                mem = psutil.virtual_memory() if psutil else None
                total_ram = round(mem.total / (1024 ** 3), 1) if mem else 0
                used_ram = round(mem.used / (1024 ** 3), 1) if mem else 0

                embed = {
                    "title": f"📊 Báo Cáo Thiết Bị: {device_name}",
                    "color": 0x3498DB,
                    "description": "\n".join(lines) if lines else "Không có tab hoạt động.",
                    "fields": [
                        {"name": "RAM Sử Dụng", "value": f"{used_ram}/{total_ram} GB", "inline": True},
                        {"name": "CPU Usage", "value": f"{psutil.cpu_percent(interval=None) if psutil else 0}%", "inline": True},
                        {"name": "Tổng Số Tab", "value": str(len(tab_list)), "inline": True}
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": f"Wuyx Rejoin Tool • v{TOOL_VERSION}"}
                }

                files = {}
                if PackageManager.is_android():
                    try:
                        proc = subprocess.run("screencap -p", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        if proc.returncode == 0 and proc.stdout:
                            files["file"] = ("screenshot.png", io.BytesIO(proc.stdout), "image/png")
                            embed["image"] = {"url": "attachment://screenshot.png"}
                    except Exception:
                        pass

                if files:
                    requests.post(webhook_url, data={"payload_json": json.dumps({"embeds": [embed]})}, files=files, timeout=15)
                else:
                    requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)

            except Exception:
                pass

            self._stop_event.wait(max(10, webhook_interval))

    def send_event_alert(self, username, event_type, detail, package):
        color = self.EVENT_COLORS.get(event_type, 0x3498DB)
        icon = self.EVENT_ICONS.get(event_type, "📌")
        title = f"{icon} Cảnh Báo: {event_type.upper()}"
        description = f"**Tài khoản:** `{username}`\n**Gói ứng dụng:** `{package}`\n**Chi tiết:** {detail}"
        wh_cfg = self.config.get("discord_webhook", {})
        url = wh_cfg.get("webhook_url", "").strip() if isinstance(wh_cfg, dict) else ""
        if not url:
            return
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": f"Wuyx Rejoin Tool v{TOOL_VERSION}"}
        }
        try:
            requests.post(url, json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass

    def send_change_acc_alert(self, old_username, new_username, success, reason, pkg):
        title = "🔄 Đổi Tài Khoản Tự Động"
        color = 0x2ECC71 if success else 0xE74C3C
        fields = [
            {"name": "Tài khoản cũ", "value": f"`{old_username}`", "inline": True},
            {"name": "Tài khoản mới", "value": f"`{new_username or 'None'}`", "inline": True},
            {"name": "Lý do", "value": str(reason), "inline": False},
            {"name": "Package", "value": f"`{pkg}`", "inline": True}
        ]
        wh_cfg = self.config.get("discord_webhook", {})
        url = wh_cfg.get("webhook_url", "").strip() if isinstance(wh_cfg, dict) else ""
        if not url:
            return
        embed = {
            "title": title,
            "description": "Tiến trình xoay vòng tài khoản hoàn tất.",
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": f"Wuyx Rejoin Tool v{TOOL_VERSION}"}
        }
        try:
            requests.post(url, json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass

    def send_cookie_rich(self, username, uid, cookie, avatar_url, created_date, webhook_url=None):
        if not requests:
            return
        target_url = webhook_url or self.config.get("discord_webhook", {}).get("webhook_url", "")
        if not target_url:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        embed = {
            "title": f"🍪 Cookie Đã Xuất: {username}",
            "color": 0xF1C40F,
            "thumbnail": {"url": avatar_url} if avatar_url else {},
            "fields": [
                {"name": "User ID", "value": f"`{uid}`", "inline": True},
                {"name": "Ngày Tạo", "value": f"`{created_date}`", "inline": True},
                {"name": "Cookie Value", "value": f"```{cookie}```", "inline": False}
            ],
            "timestamp": timestamp,
            "footer": {"text": f"Wuyx Cookie Manager • v{TOOL_VERSION}"}
        }
        file_obj = io.BytesIO(cookie.encode("utf-8"))
        files = {"file": (f"{username}_cookie.txt", file_obj, "text/plain")}
        try:
            requests.post(target_url, data={"payload_json": json.dumps({"embeds": [embed]})}, files=files, timeout=10)
        except Exception:
            pass

    def send_all_cookie(self, webhook_url, all_accounts, all_cookie):
        if not requests or not webhook_url:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        embed = {
            "title": f"🍪 Xuất Toàn Bộ Cookie ({len(all_accounts)} Tài Khoản)",
            "color": 0x2ECC71,
            "description": f"Đã trích xuất thành công {len(all_accounts)} cookie từ tất cả clone.",
            "timestamp": timestamp,
            "footer": {"text": f"Wuyx Cookie Manager • v{TOOL_VERSION}"}
        }
        file_obj = io.BytesIO(all_cookie.encode("utf-8"))
        files = {"file": ("all_cookie.txt", file_obj, "text/plain")}
        try:
            requests.post(webhook_url, data={"payload_json": json.dumps({"embeds": [embed]})}, files=files, timeout=15)
            print(f"{Fore.GREEN}[+] Đã gửi all_cookie.txt lên Discord Webhook thành công!{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi gửi Webhook: {e}{Style.RESET_ALL}")


# ===========================================================================
# 8. QUẢN LÝ BẢN QUYỀN & CẬP NHẬT (LicenseManager & AutoUpdater)
# ===========================================================================
class LicenseManager:
    """Xác thực bản quyền đã mở khóa vĩnh viễn (VIP Lifetime Unlocked)."""

    def __init__(self):
        self.cached_key = None
        self._watchdog_thread = None

    def _ensure_secret_file(self):
        secret_file = os.path.join(CONFIG_DIR, ".secret")
        if not os.path.exists(secret_file):
            try:
                with open(secret_file, "w", encoding="utf-8") as f:
                    f.write(hashlib.sha256(os.urandom(32)).hexdigest())
            except Exception:
                pass
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "DEFAULT_SECRET_WUYX"

    def get_hwid(self):
        android_id = PackageManager.get_android_id()
        device_name = PackageManager.device_name()
        secret = self._ensure_secret_file()
        raw = f"{android_id}:{device_name}:{secret}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _aes_encrypt(self, plaintext):
        return plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext

    def _hybrid_decrypt(self, resp_body):
        return {"status": "success", "license_type": "lifetime", "valid": True}

    def verify(self, license_key=None, hwid=None):
        return True, "Valid"

    def _load_cached_key(self):
        for p in [LICENSE_FILE, os.path.join(CONFIG_DIR, ".license")]:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        k = f.read().strip()
                        if k:
                            return k
                except Exception:
                    pass
        return "VIP-LIFETIME-UNLOCKED"

    def _save_key(self, key):
        try:
            with open(os.path.join(CONFIG_DIR, ".license"), "w", encoding="utf-8") as f:
                f.write(key)
        except Exception:
            pass

    def authenticate(self):
        return True, "VIP LIFETIME UNLOCKED"

    def _check_tool_status(self):
        if not requests:
            return {"status": "ok", "message": "Normal"}
        try:
            r = requests.get(STATUS_URL, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {"status": "ok", "message": "Normal"}

    def _watchdog_loop(self):
        while True:
            time.sleep(300)

    def start_watchdog(self):
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    @staticmethod
    def compare_keys():
        return True


class AutoUpdater:
    """Kiểm tra và cập nhật ứng dụng."""

    @staticmethod
    def _parse_version(v_str):
        try:
            return tuple(int(x) for x in str(v_str).strip().split(".") if x.isdigit())
        except Exception:
            return (1, 0, 0)

    @staticmethod
    def _is_newer(remote_v, local_v):
        r = AutoUpdater._parse_version(remote_v)
        l = AutoUpdater._parse_version(local_v)
        return r > l

    @staticmethod
    def _get_remote_version():
        if not requests:
            return None
        try:
            r = requests.get(STATUS_URL, timeout=5)
            if r.status_code == 200:
                return r.json().get("version")
        except Exception:
            pass
        return None

    @staticmethod
    def _download_and_save(target_path):
        if not requests:
            return False
        try:
            headers = {"User-Agent": "WuyxTool-Updater"}
            r = requests.get(UPDATE_URL, headers=headers, timeout=15)
            if r.status_code == 200:
                with open(target_path, "wb") as f:
                    f.write(r.content)
                return True
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi tải cập nhật: {e}{Style.RESET_ALL}")
        return False

    @staticmethod
    def _restart(target_path):
        print(f"{Fore.GREEN}[+] Khởi động lại ứng dụng...{Style.RESET_ALL}")
        python = sys.executable
        os.execl(python, python, target_path, *sys.argv[1:])

    @staticmethod
    def check_and_update():
        print(f"{Fore.CYAN}[*] Kiểm tra phiên bản mới...")
        rem = AutoUpdater._get_remote_version()
        if rem and AutoUpdater._is_newer(rem, TOOL_VERSION):
            print(f"{Fore.GREEN}[+] Đã có phiên bản mới: v{rem} (Hiện tại: v{TOOL_VERSION})")
        else:
            print(f"{Fore.GREEN}[+] Bạn đang sử dụng phiên bản mới nhất (v{TOOL_VERSION})!")


# ===========================================================================
# 9. GIAO DIỆN CHÍNH & ENGINE VÒNG LẶP MENU (WuyxTool)
# ===========================================================================
def dim(text):
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


def _list_files_in(d):
    try:
        return sorted([f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))])
    except Exception:
        return []

def _write_file_to(d, filename, content):
    os.makedirs(d, exist_ok=True)
    fpath = os.path.join(d, filename)
    if os.path.exists(fpath):
        c = input(f"{Fore.YELLOW}[?] Tệp đã tồn tại. Ghi đè? (y/n): {Fore.WHITE}").strip().lower()
        if c != "y":
            return False
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"{Fore.RED}[!] Lỗi ghi tệp: {e}{Style.RESET_ALL}")
        return False

def _delete_file_from(d, fname):
    try:
        fpath = os.path.join(d, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
    except Exception as e:
        print(f"{Fore.RED}[!] Lỗi xóa tệp: {e}{Style.RESET_ALL}")
    return False


class WuyxTool:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.package_manager = PackageManager()
        self.account_manager = AccountManager()
        self.webhook_manager = WebhookManager(self.config)
        self.running = False
        self.stop_event = threading.Event()
        self._switching = set()
        self._captcha_tabs = set()
        self._banned_tabs = set()
        self._faceid_tabs = set()
        self._tab_cookies = {}
        self.tabs_status = {}
        self._launch_lock = threading.Lock()
        self._kill_lock = threading.Lock()

    def _set_status_by_packages(self, packages, status):
        """Cập nhật trạng thái hiển thị cho một hoặc nhiều package."""
        if isinstance(packages, (list, tuple, set)):
            for p in packages:
                self.tabs_status[p] = status
        else:
            self.tabs_status[packages] = status

    def get_tab_status(self, pkg):
        """Lấy trạng thái giám sát hiện tại của package."""
        return self.tabs_status.get(pkg, "Offline")

    def banner(self):
        os.system("cls" if os.name == "nt" else "clear")
        banner_art = """
    ◗◗┈    ◗◗┈◗◗┈   ◗◗┈◗◗┈   ◗◗┈◗◗┈  ◗◗┈          
    ◗◗┎    ◗◗┎◗◗┎   ◗◗┎┅◗◗┈ ◗◗┋│┅◗◗┈◗◗┋│          
    ◗◗┎ ◗┈ ◗◗┎◗◗┎   ◗◗┎ ┅◗◗◗◗┋│  ┅◗◗◗┋│           
    ◗◗┎◗◗◗┈◗◗┎◗◗┎   ◗◗┎  ┅◗◗┋│   ◗◗┋◗◗┈           
    ┅◗◗◗┋◗◗◗┋│┅◗◗◗◗◗◗┋│   ◗◗┎   ◗◗┋│ ◗◗┈          
     ┅┏┏│┅┏┏│  ┅┏┏┏┏┏│    ┅┏│   ┅┏│  ┅┏│          
                                                 
 ◗◗◗◗◗◗┈ ◗◗◗◗◗◗◗┈     ◗◗┈ ◗◗◗◗◗◗┈ ◗◗┈◗◗◗┈   ◗◗┈
 ◗◗┋┏┏◗◗┈◗◗┋┏┏┏┏│     ◗◗┎◗◗┋┏┏┏◗◗┈◗◗┎◗◗◗◗┈  ◗◗┎
 ◗◗◗◗◗◗┋│◗◗◗◗◗┈       ◗◗┎◗◗┎   ◗◗┎◗◗┎◗◗┋◗◗┈ ◗◗┎
 ◗◗┋┏┏◗◗┈◗◗┋┏┏│  ◗◗   ◗◗┎◗◗┎   ◗◗┎◗◗┎◗◗┎┅◗◗┈◗◗┎
 ◗◗┎  ◗◗┎◗◗◗◗◗◗◗┈┅◗◗◗◗◗┋│┅◗◗◗◗◗◗┋│◗◗┎◗◗┎ ┅◗◗◗◗┎
 ┅┏│  ┅┏│┅┏┏┏┏┏┏│ ┅┏┏┏┏│  ┅┏┏┏┏┏│ ┅┏│┅┏│  ┅┏┏┏│"""
        lines = banner_art.strip("\n").split("\n")
        total_lines = len(lines)
        start_color = (0, 200, 255)
        end_color = (0, 255, 128)
        colored_lines = []
        for i, line in enumerate(lines):
            ratio = i / max(1, total_lines - 1)
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            colored_lines.append(f"\033[38;2;{r};{g};{b}m{line}\033[0m")
        print("\n".join(colored_lines))
        print(f"{Fore.CYAN}            > > > Premium Version < < <")
        print(f"{Fore.LIGHTBLUE_EX}Discord: discord.gg/5G3cStpbcx\nmade by _g.huy{Style.RESET_ALL}\n")

    def tool_status(self):
        method = self.config.get("account_check_method", "executor")
        if method == "executor":
            check_method_text = "CHECK EXECUTOR METHOD"
        elif method == "online":
            check_method_text = "CHECK ONLINE METHOD"
        else:
            check_method_text = "CHECk UNKNOWN METHOD"

        wh = self.config.get("discord_webhook", {})
        wh_en = wh.get("enabled", False) if isinstance(wh, dict) else bool(self.config.get("discord_webhook"))
        webhook_text = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if wh_en else f"{Fore.RED}Disable{Style.RESET_ALL}"

        bp_en = self.config.get("auto_bypass", False)
        auto_bypass_text = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if bp_en else f"{Fore.RED}Disable{Style.RESET_ALL}"

        sort_en = self.config.get("auto_sort_tab", False) or self.config.get("auto_sort_tab_full", False)
        auto_sort_tab_text = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if sort_en else f"{Fore.RED}Disable{Style.RESET_ALL}"

        bf_en = self.config.get("auto_change_acc_bf", False) or self.config.get("auto_change_acc_custom", False)
        cap_en = self.config.get("auto_change_acc_captcha", False) or self.config.get("auto_change_acc_faceid", False)
        auto_change_acc_text = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if (bf_en or cap_en) else f"{Fore.RED}Disable{Style.RESET_ALL}"

        print(f"{Fore.CYAN}AUTO CHANGE ACCOUNT: {auto_change_acc_text}")
        print(f"{Fore.CYAN}WEBHOOK: {webhook_text}")
        print(f"{Fore.CYAN}AUTO BYPASS: {auto_bypass_text}")
        print(f"{Fore.CYAN}AUTO SORT TAB: {auto_sort_tab_text}")
        print(f"{Fore.YELLOW}[ {check_method_text} ]{Style.RESET_ALL}")
        print(f"{Fore.CYAN}-----------------------------------------------------{Style.RESET_ALL}")

    def status_banner(self):
        mem = psutil.virtual_memory() if psutil else None
        cpu = psutil.cpu_percent(interval=None) if psutil else 0
        total_ram = round(mem.total / (1024 ** 3), 1) if mem else 0
        used_ram = round(mem.used / (1024 ** 3), 1) if mem else 0

        tabs = self.config.get("tabs", {})
        enabled_tabs = [(i, t) for i, (k, t) in enumerate(tabs.items(), 1) if t.get("enabled", True)]

        print(f"{Fore.CYAN}----------------------------------------------------------------------------------")
        print(f"|  Cpu usage: {cpu}%      |  Ram usage: {used_ram}/{total_ram} GB                 |")
        print(f"----------------------------------------------------------------------------------")
        print(f"| No   | Username        | Package         | Status     | Game                   |")
        print(f"|------|-----------------|-----------------|------------|------------------------|")

        if enabled_tabs:
            for idx, (tab_idx, tab) in enumerate(enabled_tabs, 1):
                no = f"{idx:02d}"
                uname = tab.get("username", "Unknown")
                if len(uname) > 6:
                    hpart = "*" * (len(uname) - 6)
                    huname = f"{uname[:3]}{hpart}{uname[-3:]}"
                else:
                    huname = uname
                pkg = tab.get("package", "")
                stat = self.get_tab_status(pkg)
                game = tab.get("game", "Roblox")
                print(f"| {no:<4} | {huname:<15} | {pkg:<15} | {stat:<10} | {game:<22} |")
        else:
            print(f"|  {Fore.YELLOW}No active tabs configured.{Fore.CYAN}{' ' * 51}|")
        print(f"----------------------------------------------------------------------------------{Style.RESET_ALL}")

    def menu(self):
        self.banner()
        self.tool_status()
        self.status_banner()
        print(f"{Fore.CYAN}-----------------------------------------------------")
        print(f"|----+----------------------------------------------|")
        print(f"|               Command                             |")
        print(f"|----+----------------------------------------------|")
        print(f"| 1  | Start auto rejoin                            |")
        print(f"| 2  | Setup package                                |")
        print(f"| 3  | Setup package to run                         |")
        print(f"| 4  | Setup game and private sv                    |")
        print(f"| 5  | Setup webhook                                |")
        print(f"| 6  | Setup autoexecute                            |")
        print(f"| 7  | Get cookie account                           |")
        print(f"| 8  | Login via cookies                            |")
        print(f"| 9  | Log out account                              |")
        print(f"| 10 | Set config tool                              |")
        print(f"| 11 | Open all tab Roblox                          |")
        print(f"| 12 | Change android id                            |")
        print(f"| 13 | Toogle auto block                            |")
        print(f"| 14 | Toogle auto sort tab                         |")
        print(f"| 15 | Toogle auto change acc                       |")
        print(f"| 16 | Toogle auto bypass                           |")
        print(f"| 17 | Select account check method                  |")
        print(f"| 18 | Toggle auto solver captcha/FaceID            |")
        print(f"| 0  | Exit                                         |")
        print(f"|----+----------------------------------------------|{Style.RESET_ALL}")

    # -----------------------------------------------------------------------
    # CÁC HÀM TIỆN ÍCH & XỬ LÝ COOKIE (Cookie & Workspace Helpers)
    # -----------------------------------------------------------------------
    def _extract_cookie_from_line(self, line):
        parts = line.strip().split(":")
        for p in reversed(parts):
            if p.startswith("_|WARNING:-DO-NOT-SHARE-THIS"):
                return p
        for p in parts:
            if ".ROBLOSECURITY" in p:
                return p.split(".ROBLOSECURITY=")[-1].split(";")[0].strip()
        return line.strip()

    def _pop_cookie_from_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            if not lines:
                return None
            candidate = lines[0]
            cookie = self._extract_cookie_from_line(candidate)
            remaining = lines[1:]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(remaining) + ("\n" if remaining else ""))
            return cookie
        except Exception:
            return None

    def _write_bf_config_to_workspace(self):
        bf_path = getattr(ConfigManager, 'blox_fruit_file', BLOX_FRUIT_FILE)
        if not os.path.exists(bf_path):
            return
        try:
            with open(bf_path, "r", encoding="utf-8") as f:
                bf_data = json.load(f)
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi đọc config Blox Fruits: {e}{Style.RESET_ALL}")
            return

        workspace_dirs = [
            "/sdcard/*/Workspace",
            "/sdcard/Android/data/*/*/*/*/Workspace",
            "workspace",
            os.path.expanduser("~/sdcard/*/Workspace")
        ]
        matched = set()
        for pat in workspace_dirs:
            for p in glob.glob(pat):
                if os.path.isdir(p):
                    matched.add(p)
        for wdir in matched:
            out_dir = os.path.join(wdir, "Wuyx")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "blox_fruits.json")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(bf_data, f, indent=4)
            except Exception:
                pass
        print(f"{Fore.GREEN}[+] Đã đồng bộ config Blox Fruits vào các workspace!{Style.RESET_ALL}")

    def _kill_and_relaunch_all_tabs(self):
        config = ConfigManager.load_config(getattr(ConfigManager, 'config_file', CONFIG_FILE))
        tabs = self.config.get("tabs", {})
        enabled_tabs = [t for t in tabs.values() if t.get("enabled", True)]
        all_packages = [t.get("package") for t in enabled_tabs if t.get("package")]
        delay_open_tab = int(config.get("delay_open_tab", 5))
        auto_clear_cache = config.get("auto_clear_cache", False)

        for tab in enabled_tabs:
            pkg = tab.get("package")
            if pkg:
                with self._kill_lock:
                    PackageManager.safe_kill_with_focus(pkg, all_packages)
                time.sleep(1)

        WindowLayoutManager.arrange_clone_windows_auto(enabled_tabs, config)

        for tab in enabled_tabs:
            pkg = tab.get("package")
            if pkg:
                if auto_clear_cache:
                    PackageManager.clear_cache(pkg)
                with self._launch_lock:
                    PackageManager.launch_roblox(pkg, tab.get("link_id_game", config.get("link_id_game", "")))
                self.tabs_status[pkg] = "REJOINING"
                self._render_status()
                time.sleep(delay_open_tab)

    def _notify_event(self, tab_index, username, event_type, detail, package, once=False, cooldown=0):
        now = time.time()
        key = (tab_index, event_type)
        if not hasattr(self, '_event_sent'):
            self._event_sent = {}
        if not hasattr(self, '_event_lock'):
            self._event_lock = threading.Lock()
        with self._event_lock:
            last = self._event_sent.get(key, 0)
            if once and last > 0:
                return
            if cooldown > 0 and (now - last) < cooldown:
                return
            self._event_sent[key] = now
        try:
            self.webhook_manager.send_event_alert(username, event_type, detail, package)
        except Exception:
            pass

    def _clear_event_state(self, tab_index, event_types=None):
        if not hasattr(self, '_event_sent') or not hasattr(self, '_event_lock'):
            return
        with self._event_lock:
            if event_types is None:
                keys_to_del = [k for k in self._event_sent if k[0] == tab_index]
            else:
                keys_to_del = [k for k in self._event_sent if k[0] == tab_index and k[1] in event_types]
            for k in keys_to_del:
                self._event_sent.pop(k, None)

    def _clear_captcha_events(self, tab_index):
        self._clear_event_state(tab_index, ["captcha"])

    def _clear_faceid_events(self, tab_index):
        self._clear_event_state(tab_index, ["faceid"])

    def _handle_captcha_state(self, tab_index, tab, all_packages, check, check_interval, delay_open_tab, third_party_solve_capcha_url, auto_close_tab_when_get_capcha, auto_change_acc_captcha):
        user_name = tab.get("user_name", tab.get("username", "Unknown"))
        package = tab.get("package", "")
        link_id_game = tab.get("link_id_game", "")
        cookie = tab.get("cookie", "")
        self._notify_event(tab_index, user_name, "captcha", "Phát hiện Captcha trên tài khoản", package, once=True)
        print(f"{Fore.CYAN}[*] Tab #{tab_index} ({user_name}) phát hiện Captcha!{Style.RESET_ALL}")

        if third_party_solve_capcha_url:
            print(f"{Fore.YELLOW}[*] Đang gửi Captcha tới solver service...{Style.RESET_ALL}")
            solve = CaptchaManager.solve_capcha(third_party_solve_capcha_url, user_name, cookie)
            if solve:
                print(f"{Fore.GREEN}[+] Giải Captcha thành công! Khôi phục tab #{tab_index}...{Style.RESET_ALL}")
                self._captcha_tabs.discard(tab_index)
                self._clear_captcha_events(tab_index)
                self.tabs_status[package] = "ONLINE"
                self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                return

        if auto_change_acc_captcha:
            print(f"{Fore.YELLOW}[*] Tự động đổi tài khoản khi dính Captcha...{Style.RESET_ALL}")
            self._swap_account_on_block(tab_index, tab, all_packages, reason="Captcha")
            return

        if auto_close_tab_when_get_capcha:
            print(f"{Fore.RED}[!] Đóng tab #{tab_index} do phát hiện Captcha.{Style.RESET_ALL}")
            with self._kill_lock:
                PackageManager.safe_kill_with_focus(package, all_packages)
            self.tabs_status[package] = "CAPTCHA CLOSED"

    def _handle_faceid_state(self, tab_index, tab, all_packages, check_interval, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_faceid, faceid_solver_urls):
        user_name = tab.get("user_name", tab.get("username", "Unknown"))
        package = tab.get("package", "")
        link_id_game = tab.get("link_id_game", "")
        cookie = tab.get("cookie", "")
        self._notify_event(tab_index, user_name, "faceid", "Phát hiện FaceID lock", package, once=True)
        print(f"{Fore.CYAN}[*] Tab #{tab_index} ({user_name}) phát hiện FaceID lock!{Style.RESET_ALL}")

        if faceid_solver_apikey:
            print(f"{Fore.YELLOW}[*] Đang gửi yêu cầu mở khóa FaceID tới ZeroPoint API...{Style.RESET_ALL}")
            solved = CaptchaManager.solver_faceid(faceid_solver_apikey, cookie, faceid_solver_priority)
            if solved:
                print(f"{Fore.GREEN}[+] Giải FaceID thành công! Khôi phục tab #{tab_index}...{Style.RESET_ALL}")
                self._faceid_tabs.discard(tab_index)
                self._clear_faceid_events(tab_index)
                self.tabs_status[package] = "ONLINE"
                self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                return

        if faceid_solver_urls:
            solved_url = CaptchaManager.solver_faceid_url(faceid_solver_urls, cookie)
            if solved_url:
                print(f"{Fore.GREEN}[+] Mở khóa FaceID qua solver URL thành công!{Style.RESET_ALL}")
                self._faceid_tabs.discard(tab_index)
                self._clear_faceid_events(tab_index)
                self.tabs_status[package] = "ONLINE"
                self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                return

        if auto_change_acc_faceid:
            print(f"{Fore.YELLOW}[*] Tự động đổi tài khoản khi dính FaceID...{Style.RESET_ALL}")
            self._swap_account_on_block(tab_index, tab, all_packages, reason="FaceID")
            return

    def _handle_banned_state(self, tab_index, tab, user_name, package, cookie):
        self._notify_event(tab_index, user_name, "banned", "Tài khoản bị cảnh báo (Warned/Banned)", package, once=True)
        print(f"{Fore.CYAN}[*] Tab #{tab_index} ({user_name}) bị Warn, đang thử unwarn...{Style.RESET_ALL}")
        ok = AccountManager.unwarn(cookie)
        if ok:
            print(f"{Fore.GREEN}[+] Unwarn thành công cho {user_name}! Tiếp tục rejoin.{Style.RESET_ALL}")
            self._banned_tabs.discard(tab_index)
            self._clear_event_state(tab_index, ["banned"])
            self.tabs_status[package] = "ONLINE"
        else:
            print(f"{Fore.RED}[!] Unwarn thất bại cho {user_name}.{Style.RESET_ALL}")
            self.tabs_status[package] = "BANNED"

    def _try_recover_tab(self, tab_index, package, link_id_game, all_packages, delay_open_tab=5, user_name="", use_kill_lock=True, uname=None):
        cfg = ConfigManager.load_config(getattr(ConfigManager, 'config_file', CONFIG_FILE))
        auto_bypass = cfg.get("auto_bypass", False)
        if auto_bypass:
            self.delta_manager._handle_delta_bypass()
        if AccountManager.is_delta_waiting_key():
            self.tabs_status[package] = "WAIT DELTA KEY"
            return
        self.tabs_status[package] = "RECOVERING"
        print(f"{Fore.YELLOW}[!] Khôi phục Tab #{tab_index} ({package})...{Style.RESET_ALL}")
        if not hasattr(self, '_rejoin_started_at'):
            self._rejoin_started_at = {}
        self._rejoin_started_at[tab_index] = time.time()
        if use_kill_lock:
            with self._kill_lock:
                PackageManager.safe_kill_with_focus(package, all_packages)
        else:
            PackageManager.safe_kill_with_focus(package, all_packages)
        time.sleep(1)
        if cfg.get("auto_clear_cache", False):
            PackageManager.clear_cache(package)
        with self._launch_lock:
            PackageManager.launch_roblox(package, link_id_game)
        time.sleep(delay_open_tab)

    def _do_change_account(self, tab_index, tab, signal_file=None, all_packages=None, reason="Banned or Swapped"):
        pkg = tab.get("package", "com.roblox.client")
        old_user = tab.get("username", tab.get("user_name", "Unknown"))
        link_id_game = tab.get("link_id_game", self.config.get("link_id_game", ""))
        all_packages = all_packages or [t.get("package") for t in (self.config.get("tabs", {}).values() if isinstance(self.config.get("tabs"), dict) else self.config.get("tabs", []))]
        print(f"{Fore.CYAN}[*] Thực hiện đổi tài khoản Tab #{tab_index} ({pkg}) - Lý do: {reason}{Style.RESET_ALL}")
        self.tabs_status[pkg] = "CHANGING ACC"

        new_cookie = self._pop_cookie_from_file(os.path.join(WORKSPACE_DIR, "cookie.txt")) or self._pop_cookie_from_file("cookie.txt")
        if not new_cookie:
            print(f"{Fore.RED}[-] Hết cookie trong kho lưu trữ! Không thể đổi.{Style.RESET_ALL}")
            if not hasattr(self, '_change_account_stop'):
                self._change_account_stop = threading.Event()
            self._change_account_stop.set()
            self.webhook_manager.send_change_acc_alert(old_user, None, False, reason=reason, pkg=pkg)
            return False

        ck_status, data = AccountManager.check_cookie(new_cookie)
        if ck_status == "warned":
            AccountManager.unwarn(new_cookie)

        # Sao lưu cookie cũ
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_old_user = re.sub(r'[^\w\-]', '_', old_user)
        os.makedirs(ACC_CHANGED_DIR, exist_ok=True)
        backup_path = os.path.join(ACC_CHANGED_DIR, f"{safe_old_user}_{ts}.txt")
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(f"Package: {pkg}\nUser: {old_user}\nCookie: {tab.get('cookie', '')}\nReason: {reason}")
        except Exception:
            pass

        with self._kill_lock:
            PackageManager.safe_kill_with_focus(pkg, all_packages)

        db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
        ok = AccountManager.write_cookie(db_path, new_cookie)
        new_uid, new_username = AccountManager.get_uid_from_cookie(new_cookie)
        new_username = new_username or (data.get("name") if isinstance(data, dict) else f"User_{new_uid}")

        tab["cookie"] = new_cookie
        tab["user_id"] = new_uid
        tab["username"] = new_username
        tab["user_name"] = new_username
        ConfigManager.save_config(self.config, ConfigManager.config_file)

        if signal_file and os.path.exists(signal_file):
            try:
                os.remove(signal_file)
            except Exception:
                pass

        with self._launch_lock:
            PackageManager.launch_roblox(pkg, link_id_game)

        self.webhook_manager.send_change_acc_alert(old_user, new_username, True, reason=reason, pkg=pkg)
        print(f"{Fore.GREEN}[+] Đã đổi sang tài khoản mới: {new_username} ({new_uid})!{Style.RESET_ALL}")
        self.tabs_status[pkg] = "ONLINE"
        return True

    def _change_account_loop(self, tabs, stop_event, trigger="completed"):
        print(f"{Fore.GREEN}[*] Đã bật luồng lắng nghe đổi tài khoản ({trigger}).{Style.RESET_ALL}")
        workspace_dirs = [
            "/sdcard/*/Workspace",
            "/sdcard/Android/data/*/*/*/*/Workspace",
            "workspace",
            os.path.expanduser("~/sdcard/*/Workspace")
        ]
        if not hasattr(self, '_change_account_stop'):
            self._change_account_stop = threading.Event()
        if not hasattr(self, '_change_acc_lock'):
            self._change_acc_lock = threading.Lock()

        while not stop_event.is_set() and not self._change_account_stop.is_set():
            matched_dirs = set()
            for pat in workspace_dirs:
                for p in glob.glob(pat):
                    if os.path.isdir(p):
                        matched_dirs.add(p)
            for wdir in matched_dirs:
                signal_files = glob.glob(os.path.join(wdir, "change_account_*.txt")) + glob.glob(os.path.join(wdir, "Wuyx", "change_account_*.txt"))
                for sf in signal_files:
                    fname = os.path.basename(sf)
                    file_user = os.path.splitext(fname)[0].replace("change_account_", "").lower()
                    try:
                        with open(sf, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                    except Exception:
                        content = ""

                    matched_idx = None
                    matched_tab = None
                    tab_items = tabs.items() if isinstance(tabs, dict) else enumerate(tabs)
                    for i, (k, t) in enumerate(tab_items):
                        u = t.get("username", t.get("user_name", "")).lower()
                        if u == file_user or not file_user:
                            matched_idx = i
                            matched_tab = t
                            break
                    if matched_tab and matched_idx not in self._switching:
                        all_packages = [t.get("package") for t in (tabs.values() if isinstance(tabs, dict) else tabs)]
                        with self._change_acc_lock:
                            self._do_change_account(matched_idx, matched_tab, sf, all_packages, reason=content or trigger)
            time.sleep(2)

    def _swap_account_on_block(self, tab_index, tab, all_packages, reason):
        if tab_index in self._switching:
            return False
        if not hasattr(self, '_change_acc_lock'):
            self._change_acc_lock = threading.Lock()
        with self._change_acc_lock:
            self._switching.add(tab_index)
            try:
                print(f"{Fore.CYAN}[*] Bắt đầu đổi tài khoản cho Tab #{tab_index} - Lý do: {reason}{Style.RESET_ALL}")
                success = self._do_change_account(tab_index, tab, None, all_packages, reason=reason)
                self._captcha_tabs.discard(tab_index)
                self._faceid_tabs.discard(tab_index)
                self._clear_event_state(tab_index)
                return success
            except Exception as e:
                print(f"{Fore.RED}[!] Lỗi đổi tài khoản: {e}{Style.RESET_ALL}")
                return False
            finally:
                self._switching.discard(tab_index)

    def event_tracking(self):
        try:
            android_id = PackageManager.get_android_id()
            try:
                import logsnag
                logsnag.LogSnag(token="").track(project="wuyx", channel="starts", event="App Start", user_id=android_id)
            except Exception:
                pass
        except Exception:
            pass

    def _is_ingame(self, tab, account_check_method="executor", sequential_join=True, delay_open_tab=3):
        if account_check_method == "executor":
            uname = tab.get("username", tab.get("user_name", ""))
            if uname:
                hb = AccountManager.get_file_hb(uname)
                if hb:
                    return True
            return False
        elif account_check_method == "online":
            uid = tab.get("user_id")
            cookie = tab.get("cookie", "")
            if not uid and cookie:
                uid, _ = AccountManager.get_uid_from_cookie(cookie)
            if uid:
                presence = AccountManager.check_status(uid, cookie)
                if presence and presence.get("userPresenceType") in (2, 3):
                    return True
            return False
        return False

    def _wait_and_recover_ingame(self, tab, account_check_method, rejoin_timeout, delay_open_tab, sequential_join, all_packages, stop_event, status_idx=None, third_party_solve_capcha_url=None, check_interval=5, faceid_solver_apikey="", faceid_solver_priority=1, auto_change_acc_captcha=False, faceid_solver_urls=None):
        package = tab.get("package", "")
        link_id_game = tab.get("link_id_game", "")
        user_name = tab.get("username", tab.get("user_name", "Unknown"))
        deadline = time.time() + rejoin_timeout

        while not stop_event.is_set() and time.time() < deadline:
            if AccountManager.is_delta_waiting_key():
                self.tabs_status[package] = "WAIT DELTA KEY"
                self._render_status()
                time.sleep(check_interval)
                continue

            if self._is_ingame(tab, account_check_method, sequential_join, delay_open_tab):
                self.tabs_status[package] = "IN-GAME"
                return True

            time.sleep(check_interval)

        # Timeout reached, recover
        print(f"{Fore.YELLOW}[!] Hết hạn chờ vào game ({rejoin_timeout}s) cho {package}. Khởi động lại...{Style.RESET_ALL}")
        self._try_recover_tab(status_idx or 0, package, link_id_game, all_packages, delay_open_tab, user_name)
        return False

    def _render_status(self):
        self.banner()
        self.tool_status()
        self.status_banner(self.tabs_status)

    def _check_cookie_while_ingame(self, tab_index, tab, every=5):
        if not hasattr(self, '_ingame_check_count'):
            self._ingame_check_count = {}
        count = self._ingame_check_count.get(tab_index, 0) + 1
        self._ingame_check_count[tab_index] = count
        if count % every != 0:
            return True

        cookie = tab.get("cookie", "")
        package = tab.get("package", "")
        user_name = tab.get("username", tab.get("user_name", "Unknown"))
        if not cookie:
            return True

        status, _ = AccountManager.check_cookie(cookie)
        if status == "captcha":
            self._captcha_tabs.add(tab_index)
            self.tabs_status[package] = "CAPTCHA"
            self._notify_event(tab_index, user_name, "captcha", "Cookie bị khóa Captcha", package)
            return False
        elif status == "faceid":
            self._faceid_tabs.add(tab_index)
            self.tabs_status[package] = "FACEID"
            self._notify_event(tab_index, user_name, "faceid", "Cookie bị khóa FaceID", package)
            return False
        elif status in ("banned", "warned"):
            self._banned_tabs.add(tab_index)
            self.tabs_status[package] = "WARNED/BANNED"
            self._notify_event(tab_index, user_name, "banned", "Tài khoản bị Warn hoặc Ban", package)
            return False
        return True

    def _start_monitor_thread(self, idx, tab, account_check_method, all_packages, stop_event, check_interval, check_ui_delay, auto_close_tab_when_get_capcha, third_party_solve_capcha_url, rejoin_timeout, delay_open_tab, offline_wait, max_retries, retry_delay, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls):
        if account_check_method == "executor":
            t = threading.Thread(
                target=self._tab_monitor_loop_2,
                args=(idx, tab, all_packages, stop_event, check_interval, check_ui_delay, auto_close_tab_when_get_capcha, third_party_solve_capcha_url, rejoin_timeout, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls),
                daemon=True
            )
        else:
            t = threading.Thread(
                target=self._tab_monitor_loop,
                args=(idx, tab, all_packages, offline_wait, max_retries, retry_delay, check_interval, stop_event, third_party_solve_capcha_url, auto_close_tab_when_get_capcha, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls),
                daemon=True
            )
        t.start()
        return t

    def _tab_monitor_loop(self, tab_index, tab, all_packages, offline_wait, max_retries, retry_delay, check_interval, stop_event, third_party_solve_capcha_url, auto_close_tab_when_get_capcha, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls):
        package = tab.get("package", "")
        link_id_game = tab.get("link_id_game", self.config.get("link_id_game", ""))
        user_name = tab.get("username", tab.get("user_name", "Unknown"))
        user_id = tab.get("user_id", 0)
        cookie = tab.get("cookie", "")

        while not stop_event.is_set():
            if tab_index in self._switching:
                stop_event.wait(2)
                continue
            if tab_index in self._captcha_tabs:
                self._handle_captcha_state(tab_index, tab, all_packages, True, check_interval, delay_open_tab, third_party_solve_capcha_url, auto_close_tab_when_get_capcha, auto_change_acc_captcha)
                stop_event.wait(check_interval)
                continue
            if tab_index in self._banned_tabs:
                self._handle_banned_state(tab_index, tab, user_name, package, cookie)
                stop_event.wait(check_interval)
                continue
            if tab_index in self._faceid_tabs:
                self._handle_faceid_state(tab_index, tab, all_packages, check_interval, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_faceid, faceid_solver_urls)
                stop_event.wait(check_interval)
                continue

            pid = PackageManager.get_pid(package)
            if not pid:
                print(f"{Fore.YELLOW}[!] Tab #{tab_index} ({package}) bị offline. Khôi phục lại...{Style.RESET_ALL}")
                self._notify_event(tab_index, user_name, "disconnected", "Tiến trình bị ngắt", package)
                self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
            else:
                PackageManager.set_oom(package, -1000)
                presence = AccountManager.check_status(user_id, cookie) if user_id else None
                if presence:
                    ptype = presence.get("userPresenceType", 0)
                    if ptype == 2:
                        self.tabs_status[package] = "IN-GAME"
                    elif ptype == 1:
                        self.tabs_status[package] = "IN-APP"
                    else:
                        self.tabs_status[package] = "ONLINE"
                else:
                    self.tabs_status[package] = "RUNNING"

                self._check_cookie_while_ingame(tab_index, tab)

            stop_event.wait(check_interval)

    def _tab_monitor_loop_2(self, tab_index, tab, all_packages, stop_event, check_interval, check_ui_delay, auto_close_tab_when_get_capcha, third_party_solve_capcha_url, rejoin_timeout, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls):
        package = tab.get("package", "")
        link_id_game = tab.get("link_id_game", self.config.get("link_id_game", ""))
        user_name = tab.get("username", tab.get("user_name", "Unknown"))
        cookie = tab.get("cookie", "")
        started = time.time()

        while not stop_event.is_set():
            if tab_index in self._switching:
                stop_event.wait(2)
                continue
            if tab_index in self._captcha_tabs:
                self._handle_captcha_state(tab_index, tab, all_packages, True, check_interval, delay_open_tab, third_party_solve_capcha_url, auto_close_tab_when_get_capcha, auto_change_acc_captcha)
                stop_event.wait(check_interval)
                continue
            if tab_index in self._banned_tabs:
                self._handle_banned_state(tab_index, tab, user_name, package, cookie)
                stop_event.wait(check_interval)
                continue
            if tab_index in self._faceid_tabs:
                self._handle_faceid_state(tab_index, tab, all_packages, check_interval, delay_open_tab, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_faceid, faceid_solver_urls)
                stop_event.wait(check_interval)
                continue

            hb_file = AccountManager.get_file_hb(user_name)
            if not hb_file:
                elapsed = time.time() - started
                remaining = max(0, int(rejoin_timeout - elapsed))
                if elapsed > rejoin_timeout:
                    print(f"{Fore.YELLOW}[!] Tab #{tab_index} ({package}) quá thời gian chờ Heartbeat! Khôi phục...{Style.RESET_ALL}")
                    self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                    started = time.time()
                else:
                    self.tabs_status[package] = f"WAIT HB ({remaining}s)"
            else:
                try:
                    mtime = os.path.getmtime(hb_file)
                    if time.time() - mtime > rejoin_timeout:
                        print(f"{Fore.YELLOW}[!] Tab #{tab_index} ({package}) Heartbeat bị đóng băng! Khởi động lại...{Style.RESET_ALL}")
                        self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                        started = time.time()
                    else:
                        self.tabs_status[package] = "IN-GAME"
                        self._check_cookie_while_ingame(tab_index, tab)
                except Exception:
                    pass

            stop_event.wait(check_interval)

    def option(self):
        C = Fore.CYAN
        W = Fore.WHITE
        border = f"{C}+----+----------------------------------------------+{Style.RESET_ALL}"
        mid_sep = f"{C}|----+----------------------------------------------|{Style.RESET_ALL}"
        header = f"{C}|               Command                             |{Style.RESET_ALL}"
        print(border)
        print(header)
        print(mid_sep)
        rows = [
            ("1", "Start auto rejoin"),
            ("2", "Setup package"),
            ("3", "Setup package to run"),
            ("4", "Setup game and private sv"),
            ("5", "Setup webhook"),
            ("6", "Setup autoexecute"),
            ("7", "Get cookie account"),
            ("8", "Login via cookies"),
            ("9", "Log out account"),
            ("10", "Set config tool"),
            ("11", "Open all tab Roblox"),
            ("12", "Change android id"),
            ("13", "Toogle auto block"),
            ("14", "Toogle auto sort tab"),
            ("15", "Toogle auto change acc"),
            ("16", "Toogle auto bypass"),
            ("17", "Select account check method"),
            ("18", "Toggle auto solver captcha/FaceID"),
            ("0", "Exit")
        ]
        for num, cmd in rows:
            print(f"{C}| {W}{num:<2}{C} | {W}{cmd:<44}{C} |{Style.RESET_ALL}")
        print(border)

    # -----------------------------------------------------------------------
    # CÁC OPTION XỬ LÝ (Option 1 đến 18)
    # -----------------------------------------------------------------------
    def option_1(self):
        """Option 1: Bắt đầu vòng lặp Auto Rejoin & Multi-tab Monitor Loop."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.YELLOW}[~] Config file not found Please try run tool again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.RED}[!] No account information found. Please try again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        enabled_tabs = {k: v for k, v in tabs.items() if v.get("enabled", True)}
        if not enabled_tabs:
            print(f"{Fore.RED}[!] No packages are enabled. Please enable a package in option 3{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        link_id_game = self.config.get("link_id_game", "")
        if not link_id_game:
            print(f"{Fore.RED}[!] Game ID/server link not found. Please set it in option 4{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        # Đồng bộ script Autoexecute
        autoexec_dirs = [
            "/sdcard/*/Autoexec*",
            "/sdcard/*/*/Autoexec*",
            "/sdcard/Android/data/*/*/*/*/Autoexec*",
            AUTOEXEC_DIR
        ]
        target_autoexec = set()
        for pat in autoexec_dirs:
            for p in glob.glob(pat):
                if os.path.isdir(p):
                    target_autoexec.add(p)
        if not target_autoexec:
            target_autoexec.add(AUTOEXEC_DIR)

        check_online_script = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/g-huy128/Test/refs/heads/main/obfuscated.lua.txt"))()'
        for d in target_autoexec:
            try:
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "check_onlinne.lua"), "w", encoding="utf-8") as f:
                    f.write(check_online_script)
            except Exception:
                pass

        if self.config.get("auto_change_acc_bf", False):
            bf_script = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/g-huy128/Test/refs/heads/main/bf_change_acc.lua"))()'
            for d in target_autoexec:
                try:
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, "bf_change_acc.lua"), "w", encoding="utf-8") as f:
                        f.write(bf_script)
                except Exception:
                    pass

        # Rejoin interval prompt
        cur_rejoin = self.config.get("rejoin_interval", 20)
        print(f"{Fore.GREEN}[+] Default: {cur_rejoin} minutes{Style.RESET_ALL}")
        raw_rej = input(f"{Fore.YELLOW}[?] Enter rejoin interval (minutes): {Fore.WHITE}").strip()
        if raw_rej:
            if raw_rej.isdigit() and int(raw_rej) > 0:
                self.config["rejoin_interval"] = int(raw_rej)
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}[+] Rejoin interval set to: {raw_rej}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[!] Value must be greater than 0{Style.RESET_ALL}")

        # Đóng tất cả tab trước khi chạy
        for pkg in enabled_tabs:
            PackageManager.kill_roblox_process(pkg)
            print(f"{Fore.GREEN}[+] {pkg} closed successfully{Style.RESET_ALL}")

        # Tự động sắp xếp cửa sổ nếu bật
        if self.config.get("auto_sort_tab", False):
            print(f"{Fore.CYAN}Auto sort tab is on.Start auto sort tab{Style.RESET_ALL}")
            if self.config.get("auto_sort_tab_full", False):
                WindowLayoutManager.arrange_clone_windows_full(enabled_tabs)
            else:
                WindowLayoutManager.arrange_clone_windows(enabled_tabs)

        # Tự động chặn các clone khác nếu bật
        if self.config.get("auto_block", False):
            print(f"{Fore.CYAN}Auto block is on, start auto block...{Style.RESET_ALL}")
            for pkg, tab in enabled_tabs.items():
                cookie = tab.get("cookie", "")
                if not cookie:
                    print(f" {pkg}: no cookie, skipping")
                    continue
                print(f" {pkg}: checking blocked list...")
                blocked_list = AccountManager.get_blocked_users(cookie)
                blocked_ids = {u.get("blockedUserId") for u in blocked_list if isinstance(u, dict)}
                for other_pkg, other_tab in tabs.items():
                    if other_pkg == pkg:
                        continue
                    target_uid = other_tab.get("user_id")
                    if not target_uid:
                        continue
                    if target_uid in blocked_ids:
                        print(f"  [>] already blocked, skipping")
                    else:
                        ok = AccountManager.block_user(cookie, target_uid)
                        if ok:
                            print(f"  [>] blocked {target_uid}")
                        else:
                            print(f"  [>] failed to block")
            print(f"{Fore.GREEN}Auto block done{Style.RESET_ALL}")

        # Tự động mua/kích hoạt server VIP miễn phí nếu bật
        if self.config.get("auto_buy_svv", False):
            print(f"{Fore.CYAN}Auto buy private server is on, start auto buy...{Style.RESET_ALL}")
            if AccountManager.is_svv_link(link_id_game):
                print(f" already using private link, skipping")
            else:
                pid = AccountManager.extract_place_id(link_id_game)
                if not pid:
                    print(f" could not extract place_id from link, skipping")
                else:
                    svv_cookie = next((t.get("cookie") for t in enabled_tabs.values() if t.get("cookie")), None)
                    if not svv_cookie:
                        print(f" no cookie, skipping svv creation")
                    else:
                        vip_link = AccountManager.setup_free_vip_server(svv_cookie, pid)
                        if vip_link:
                            print(f" private created: {vip_link}")
                            self.config["link_id_game"] = vip_link
                            link_id_game = vip_link
                            ConfigManager.save_config(self.config, self.config_file)
                        else:
                            print(f" private creation failed, falling back to public server")
            print(f"{Fore.GREEN}Auto buy private done{Style.RESET_ALL}")

        # Khởi động từng tab
        delay_open = self.config.get("delay_open_tab", 5)
        for pkg, tab in enabled_tabs.items():
            print(f"{Fore.CYAN}Launching game for package {pkg}, delay {delay_open}s...{Style.RESET_ALL}")
            PackageManager.launch_roblox(pkg, link_id_game)
            time.sleep(delay_open)

        # Bắt đầu vòng lặp giám sát
        print(f"\n{Fore.GREEN}Monitoring started\nPress Ctrl+C to stop{Style.RESET_ALL}")
        self.stop_event.clear()
        rejoin_interval_sec = self.config.get("rejoin_interval", 20) * 60
        check_interval_sec = self.config.get("check_interval", 5)
        last_rejoin_time = time.time()

        try:
            while not self.stop_event.is_set():
                now = time.time()
                if now - last_rejoin_time >= rejoin_interval_sec:
                    print(f"\n{Fore.YELLOW}Time is over. Rejoining...{Style.RESET_ALL}")
                    for pkg in enabled_tabs:
                        PackageManager.kill_roblox_process(pkg)
                    time.sleep(2)
                    for pkg in enabled_tabs:
                        PackageManager.launch_roblox(pkg, link_id_game)
                        time.sleep(delay_open)
                    last_rejoin_time = time.time()

                for idx, (pkg, tab) in enumerate(enabled_tabs.items(), 1):
                    cookie = tab.get("cookie", "")
                    if cookie:
                        ok, data = AccountManager.check_cookie(cookie)
                        if not ok:
                            print(f"{Fore.RED}[!] Tab #{idx} ({pkg}): Cookie is dead/expired after launching tab{Style.RESET_ALL}")
                    pid = PackageManager.get_pid(pkg)
                    if not pid:
                        PackageManager.launch_roblox(pkg, link_id_game)

                time.sleep(check_interval_sec)
        except KeyboardInterrupt:
            self.stop_event.set()
            print(f"\n{Fore.YELLOW}Goodbye{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to exit{Style.RESET_ALL}")

    def option_2(self):
        """Option 2: Setup package."""
        print(f"\n{Fore.CYAN}=============== SETUP PACKAGE ==============={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Scanning for Roblox clones...{Style.RESET_ALL}")
        all_package = self.package_manager.get_packages()
        if not all_package:
            print(f"{Fore.RED}[-] No Roblox packages found.{Style.RESET_ALL}")
            time.sleep(1.5)
            return

        config = ConfigManager.load_config(self.config_file)
        existing_tabs = config.get("tabs", {})
        selected_set = set(existing_tabs.keys())

        C = Fore.CYAN
        W = Style.RESET_ALL
        print(f"\n{C}Available Packages:{W}")
        for i, pkg in enumerate(all_package, 1):
            if pkg in selected_set:
                idx_color = Fore.GREEN
                state_str = f"{Fore.GREEN}[SELECTED]{W}"
            else:
                idx_color = Fore.CYAN
                state_str = f"{Fore.RED}[NOT SELECTED]{W}"
            print(f" {idx_color}[{i:02d}]{W} {state_str} {pkg}")

        raw = input(f"\n{Fore.YELLOW}Select package number or 'ALL' to toggle (Enter to return): {Fore.WHITE}").strip()
        if not raw:
            return

        if raw.upper() == "ALL":
            if len(selected_set) == len(all_package):
                selected_set.clear()
            else:
                selected_set = set(all_package)
        elif raw.isdigit() and 1 <= int(raw) <= len(all_package):
            pkg = all_package[int(raw) - 1]
            if pkg in selected_set:
                selected_set.discard(pkg)
                print(f"{Fore.RED}[-] Removed: {pkg}{W}")
            else:
                selected_set.add(pkg)
                print(f"{Fore.GREEN}[+] Added: {pkg}{W}")

        new_tabs = {}
        for pkg in all_package:
            if pkg in selected_set:
                new_tabs[pkg] = existing_tabs.get(pkg, ConfigManager.tab_object(pkg))
        config["tabs"] = new_tabs
        ConfigManager.save_config(config, self.config_file)
        self.config = config
        time.sleep(1)

    def option_3(self):
        """Option 3: Setup package to run."""
        config_opt3 = ConfigManager.load_config(self.config_file)
        tabs_opt3 = config_opt3.get("tabs", {})
        if not tabs_opt3:
            print(f"\n{Fore.RED}[!] No packages configured in Option 2! Please add packages first.{Style.RESET_ALL}")
            time.sleep(1.5)
            return

        print(f"\n{Fore.CYAN}=============== SETUP PACKAGE TO RUN ==============={Style.RESET_ALL}")
        items = list(tabs_opt3.items())
        for i, (pkg, tab) in enumerate(items, 1):
            enabled = tab.get("enabled", True)
            state_str = f"{Fore.GREEN}[ON]{Style.RESET_ALL}" if enabled else f"{Fore.RED}[OFF]{Style.RESET_ALL}"
            num_color = Fore.GREEN if enabled else Fore.RED
            uname = tab.get("username", "No User")
            print(f" {num_color}[{i:02d}]{Style.RESET_ALL} {state_str} {pkg} ({uname})")

        raw = input(f"\n{Fore.YELLOW}Enter number to toggle, or 'ALL' (Enter to return): {Fore.WHITE}").strip()
        if not raw:
            return

        if raw.upper() == "ALL":
            all_on = all(t.get("enabled", True) for t in tabs_opt3.values())
            for t in tabs_opt3.values():
                t["enabled"] = not all_on
        elif raw.isdigit() and 1 <= int(raw) <= len(items):
            target_pkg = items[int(raw) - 1][0]
            tabs_opt3[target_pkg]["enabled"] = not tabs_opt3[target_pkg].get("enabled", True)

        ConfigManager.save_config(config_opt3, self.config_file)
        self.config = config_opt3
        print(f"{Fore.GREEN}[+] Configuration updated.{Style.RESET_ALL}")
        time.sleep(1)

    def select_games(self):
        """Option 4: Setup game and private sv."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.RED}[!] Config not found. Please try run tool again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.YELLOW}[~] No packages found. Please setup in option 2 first{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        enabled_tabs = {k: v for k, v in tabs.items() if v.get("enabled", True)}
        if not enabled_tabs:
            print(f"{Fore.RED}[!] No packages are enabled. Please enable a package in option 3{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}========== SETUP GAME AND PRIVATE SV =========={Style.RESET_ALL}")
        print("  [1] Set ID/link for each package")
        print("  [2] Set ID/link for all packages")
        c = input(f"{Fore.YELLOW}[?] Choose method(1/2): {Fore.WHITE}").strip()

        preset_games = {
            "1": ("Blox fruits", "2753915549"),
            "2": ("Blox fruits (Sea 2/3)", "77747658251236"),
            "3": ("King Legacy", "4520749081"),
            "4": ("King Legacy (Sea 2)", "1537690962"),
            "5": ("Pet simulator 99", "8737899170")
        }

        if c == "1":
            for pkg, tab in enabled_tabs.items():
                print(f"\n{Fore.CYAN}Enter your game for package {pkg}:{Style.RESET_ALL}")
                print("  [1] Blox fruits (2753915549)")
                print("  [2] Blox fruits Sea 2/3 (77747658251236)")
                print("  [3] King Legacy (4520749081)")
                print("  [4] King Legacy Sea 2 (1537690962)")
                print("  [5] Pet simulator 99 (8737899170)")
                print("  [6] Other game or private sv")
                choice = input(f"{Fore.YELLOW}[?] Enter choice: {Fore.WHITE}").strip()
                target_link = ""
                if choice in preset_games:
                    target_link = f"roblox://placeId={preset_games[choice][1]}"
                elif choice == "6":
                    inp = input(f"{Fore.YELLOW}Enter your id game or private server for {pkg}: {Fore.WHITE}").strip()
                    if inp:
                        target_link = inp
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    continue

                if target_link:
                    tab["link_id_game"] = target_link
                    pid = AccountManager.extract_place_id(target_link)
                    if pid:
                        tab["place_id"] = pid
                    print(f"{Fore.GREEN}[+] Set {target_link} for {pkg}{Style.RESET_ALL}")
            ConfigManager.save_config(self.config, self.config_file)
            print(f"{Fore.GREEN}[+] Config saved{Style.RESET_ALL}")
        elif c == "2":
            print(f"\n{Fore.CYAN}Enter your game for all package:{Style.RESET_ALL}")
            print("  [1] Blox fruits (2753915549)")
            print("  [2] Blox fruits Sea 2/3 (77747658251236)")
            print("  [3] King Legacy (4520749081)")
            print("  [4] King Legacy Sea 2 (1537690962)")
            print("  [5] Pet simulator 99 (8737899170)")
            print("  [6] Other game or private sv")
            choice = input(f"{Fore.YELLOW}[?] Enter choice: {Fore.WHITE}").strip()
            target_link = ""
            if choice in preset_games:
                target_link = f"roblox://placeId={preset_games[choice][1]}"
            elif choice == "6":
                inp = input(f"{Fore.YELLOW}Enter your id game or private server: {Fore.WHITE}").strip()
                if inp:
                    target_link = inp
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return

            if target_link:
                self.config["link_id_game"] = target_link
                pid = AccountManager.extract_place_id(target_link)
                if pid:
                    self.config["place_id"] = pid
                for tab in self.config.get("tabs", {}).values():
                    tab["link_id_game"] = target_link
                    if pid:
                        tab["place_id"] = pid
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}[+] Set {target_link} for all packages{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[+] Config saved{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Only choose 1 or 2{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_4(self):
        """Option 4: Setup game and private sv."""
        self.select_games()

    def option_5(self):
        """Option 5: Setup webhook."""
        config = ConfigManager.load_config(self.config_file)
        discord_webhook = config.setdefault("discord_webhook", {})
        webhook_url = discord_webhook.get("webhook_url", "")
        device_name = discord_webhook.get("device_name", "") or "android phone"
        webhook_interval = discord_webhook.get("webhook_interval", 60)
        is_running = discord_webhook.get("enabled", False)

        if not webhook_url:
            print(f"\n{Fore.CYAN}=============== SETUP WEBHOOK ==============={Style.RESET_ALL}")
            new_url = input(f"{Fore.YELLOW}[?] Enter Discord webhook URL: {Fore.WHITE}").strip()
            if not new_url or "discord.com" not in new_url:
                print(f"{Fore.RED}[!] Invalid webhook URL{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            dev_name = input(f"{Fore.YELLOW}[?] Enter device name (default: android phone): {Fore.WHITE}").strip() or "android phone"
            ivl = input(f"{Fore.YELLOW}[?] Enter webhook interval (minutes): {Fore.WHITE}").strip()
            if not ivl.isdigit() or int(ivl) <= 0:
                print(f"{Fore.RED}[!] Invalid interval{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            discord_webhook["webhook_url"] = new_url
            discord_webhook["device_name"] = dev_name
            discord_webhook["webhook_interval"] = int(ivl)
            discord_webhook["enabled"] = True
            ConfigManager.save_config(config, self.config_file)
            self.config = config
            print(f"{Fore.GREEN}[+] Webhook started{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to continue{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}=============== WEBHOOK MANAGER ==============={Style.RESET_ALL}")
        status_str = f"{Fore.GREEN}RUNNING{Style.RESET_ALL}" if is_running else f"{Fore.RED}STOPPED{Style.RESET_ALL}"
        print(f" Status   : {status_str}")
        print(f" URL      : {webhook_url}")
        print(f" Device   : {device_name}")
        print(f" Interval : {webhook_interval} minutes")
        print(f"\n  [1] {'Stop webhook' if is_running else 'Start webhook'}")
        print(f"  [2] Edit webhook settings")
        print(f"  [0] Back")

        c = input(f"{Fore.YELLOW}J[?] Enter choice: {Fore.WHITE}").strip()
        if c == "1":
            discord_webhook["enabled"] = not is_running
            ConfigManager.save_config(config, self.config_file)
            self.config = config
            if discord_webhook["enabled"]:
                print(f"{Fore.GREEN}Webhook started{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Webhook stopped{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to continue{Style.RESET_ALL}")
        elif c == "2":
            print(f"\n{Fore.CYAN}=============== EDIT WEBHOOK ==============={Style.RESET_ALL}")
            nu = input(f"{Fore.YELLOW}New webhook URL (Enter to keep): {Fore.WHITE}").strip()
            if nu:
                if "discord.com" not in nu:
                    print(f"{Fore.RED}Invalid URL, keeping old{Style.RESET_ALL}")
                else:
                    discord_webhook["webhook_url"] = nu
            nd = input(f"{Fore.YELLOW}New device name (Enter to keep '{device_name}'): {Fore.WHITE}").strip()
            if nd:
                discord_webhook["device_name"] = nd
            ni = input(f"{Fore.YELLOW}New interval minutes (Enter to keep {webhook_interval}): {Fore.WHITE}").strip()
            if ni.isdigit() and int(ni) > 0:
                discord_webhook["webhook_interval"] = int(ni)
            ConfigManager.save_config(config, self.config_file)
            self.config = config
            print(f"{Fore.GREEN}Settings updated{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to continue{Style.RESET_ALL}")

    def option_6(self):
        """Option 6: Autoexecute Manager."""
        search_dirs = [
            "/sdcard/*/Autoexec*",
            "/sdcard/*/*/Autoexec*",
            "/sdcard/Android/data/*/*/*/*/Autoexec*",
            AUTOEXEC_DIR
        ]
        matched_folders = []
        for pat in search_dirs:
            for p in glob.glob(pat):
                if os.path.isdir(p) and p not in matched_folders:
                    matched_folders.append(p)
        if not matched_folders:
            os.makedirs(AUTOEXEC_DIR, exist_ok=True)
            matched_folders.append(AUTOEXEC_DIR)

        print(f"\n{Fore.CYAN}==========Autoexecute Manager=========={Style.RESET_ALL}")
        print(f"{Fore.GREEN}[+] Found {len(matched_folders)} Autoexec folder(s){Style.RESET_ALL}")
        print(f"  [A] Apply to ALL folders")
        for i, fld in enumerate(matched_folders, 1):
            print(f"  [{i:02d}] {fld}")
        print(f"  [0] Back")

        c = input(f"{Fore.YELLOW}[?] Select folder: {Fore.WHITE}").strip()
        if c.upper() == "A":
            print(f"\n{Fore.CYAN}==========Autoexecute Manager (ALL FOLDERS)=========={Style.RESET_ALL}")
            print(f"  [1] Add file to ALL folders")
            print(f"  [2] Delete file from ALL folders")
            print(f"  [0] Back")
            sub_c = input(f"{Fore.YELLOW}Enter your option: {Fore.WHITE}").strip()
            if sub_c == "1":
                fname = input(f"{Fore.YELLOW}Enter file name: {Fore.WHITE}").strip()
                if not fname:
                    return
                if not fname.endswith(".txt") and not fname.endswith(".lua"):
                    fname += ".txt"
                print(f"{Fore.CYAN}Enter your script:\nType 'end' to save{Style.RESET_ALL}")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "end":
                        break
                    lines.append(line)
                content = "\n".join(lines)
                saved_cnt = 0
                for fld in matched_folders:
                    try:
                        os.makedirs(fld, exist_ok=True)
                        with open(os.path.join(fld, fname), "w", encoding="utf-8") as f:
                            f.write(content)
                        saved_cnt += 1
                    except Exception as e:
                        print(f"{Fore.RED}Write error in {fld}: {e}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Saved ⇍ Written to {saved_cnt} folder(s){Style.RESET_ALL}")
            elif sub_c == "2":
                all_files = set()
                for fld in matched_folders:
                    if os.path.exists(fld):
                        all_files.update(os.listdir(fld))
                if not all_files:
                    print(f"{Fore.YELLOW}[~] No files found in any folder{Style.RESET_ALL}")
                else:
                    file_list = sorted(list(all_files))
                    print(f"{Fore.CYAN}Files across all folders:{Style.RESET_ALL}")
                    for idx, f in enumerate(file_list, 1):
                        print(f"  [{idx:02d}] {f}")
                    del_idx = input(f"{Fore.YELLOW}Select file to delete from ALL: {Fore.WHITE}").strip()
                    if del_idx.isdigit() and 1 <= int(del_idx) <= len(file_list):
                        target_file = file_list[int(del_idx) - 1]
                        conf = input(f"{Fore.YELLOW}Delete '{target_file}' from ALL folders? (y/n): {Fore.WHITE}").strip().lower()
                        if conf == "y":
                            del_cnt = 0
                            for fld in matched_folders:
                                fp = os.path.join(fld, target_file)
                                if os.path.exists(fp):
                                    try:
                                        os.remove(fp)
                                        del_cnt += 1
                                    except Exception as e:
                                        print(f"{Fore.RED}Delete error in {fld}: {e}{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}Deleted from {del_cnt} folder(s){Style.RESET_ALL}")
        elif c.isdigit() and 1 <= int(c) <= len(matched_folders):
            target_fld = matched_folders[int(c) - 1]
            os.makedirs(target_fld, exist_ok=True)
            files = os.listdir(target_fld)
            print(f"\n{Fore.CYAN}Folder: {target_fld} ({len(files)} file(s)){Style.RESET_ALL}")
            for idx, f in enumerate(files, 1):
                sz = os.path.getsize(os.path.join(target_fld, f))
                print(f"  [{idx:02d}] {f} ({sz} bytes)")
            print(f"\n  [1] Add new file")
            print(f"  [2] Delete file")
            print(f"  [0] Back")
            sub_c = input(f"{Fore.YELLOW}Enter your option: {Fore.WHITE}").strip()
            if sub_c == "1":
                fname = input(f"{Fore.YELLOW}Enter file name: {Fore.WHITE}").strip()
                if fname:
                    if not fname.endswith(".txt") and not fname.endswith(".lua"):
                        fname += ".txt"
                    fpath = os.path.join(target_fld, fname)
                    if os.path.exists(fpath):
                        ovr = input(f"{Fore.YELLOW}File already exists. Overwrite? (y/n): {Fore.WHITE}").strip().lower()
                        if ovr != "y":
                            print(f"{Fore.RED}Overwrite cancelled{Style.RESET_ALL}")
                            return
                    print(f"{Fore.CYAN}Enter your script:\nType 'end' to save{Style.RESET_ALL}")
                    lines = []
                    while True:
                        line = input()
                        if line.strip() == "end":
                            break
                        lines.append(line)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    print(f"{Fore.GREEN}Saved{Style.RESET_ALL}")
            elif sub_c == "2":
                if not files:
                    print(f"{Fore.YELLOW}No files found to delete{Style.RESET_ALL}")
                else:
                    del_idx = input(f"{Fore.YELLOW}Select file to delete: {Fore.WHITE}").strip()
                    if del_idx.isdigit() and 1 <= int(del_idx) <= len(files):
                        target_file = files[int(del_idx) - 1]
                        conf = input(f"{Fore.YELLOW}Are you sure (y/n): {Fore.WHITE}").strip().lower()
                        if conf == "y":
                            os.remove(os.path.join(target_fld, target_file))
                            print(f"{Fore.GREEN}Deleted{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_7(self):
        """Option 7: Get cookie account."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.YELLOW}[~] Config not found. Please try run tool again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.RED}[!] No packages found{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}========== GET COOKIE ACCOUNT =========={Style.RESET_ALL}")
        print(f"  [1] Get cookie for individual account")
        print(f"  [2] Get cookie for all accounts")
        c = input(f"{Fore.YELLOW}[?] Enter your choice (1/2): {Fore.WHITE}").strip()

        items = list(tabs.items())
        if c == "1":
            for i, (pkg, tab) in enumerate(items, 1):
                uname = tab.get("username", "No User")
                print(f"  [{i:02d}] {pkg} ({uname})")
            raw = input(f"{Fore.YELLOW}Select account to get cookie: {Fore.WHITE}").strip()
            if not raw.isdigit() or not (1 <= int(raw) <= len(items)):
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            pkg, tab = items[int(raw) - 1]
            uname = tab.get("username", "Unknown")
            print(f"{Fore.GREEN}[+] Selected: {pkg} ({uname}){Style.RESET_ALL}")
            send_wh = input(f"{Fore.YELLOW}Send cookie via webhook? (y/n): {Fore.WHITE}").strip().lower()

            db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
            cookie = AccountManager.get_cookie(db_path) or tab.get("cookie", "")
            if not cookie:
                print(f"{Fore.RED}Failed to retrieve cookie{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Fetching Roblox info from cookie...{Style.RESET_ALL}")
                uid, uname_api = AccountManager.get_uid_from_cookie(cookie)
                created = AccountManager.get_account_created(uid)
                uname_final = uname_api or uname or "Unknown"
                print(f"{Fore.GREEN}Username: {uname_final} | UID: {uid or 'Unknown'} | Created: {created}{Style.RESET_ALL}")
                if send_wh == "y":
                    avatar = AccountManager.get_avatar_url(uid)
                    ok_wh = self.webhook_manager.send_cookie_rich(uname_final, uid, cookie, avatar, created)
                    if ok_wh:
                        print(f"{Fore.GREEN}Cookie sent via webhook successfully{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}An error occurred. Please try again{Style.RESET_ALL}")
                try:
                    out_name = f"{uname_final}_cookie.txt"
                    with open(out_name, "w", encoding="utf-8") as f:
                        f.write(cookie)
                    print(f"{Fore.GREEN}Cookie saved to file: {out_name}{Style.RESET_ALL}")
                except Exception:
                    print(f"{Fore.RED}Failed to save cookie file{Style.RESET_ALL}")
        elif c == "2":
            print(f"{Fore.YELLOW}Getting cookies for {len(items)} account(s)...{Style.RESET_ALL}")
            send_wh = input(f"{Fore.YELLOW}Send cookie via webhook? (y/n): {Fore.WHITE}").strip().lower()
            cookies_retrieved = []
            for pkg, tab in items:
                db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                cookie = AccountManager.get_cookie(db_path) or tab.get("cookie", "")
                uname = tab.get("username", "Unknown")
                if cookie:
                    uid, uname_api = AccountManager.get_uid_from_cookie(cookie)
                    uname_final = uname_api or uname
                    tab["cookie"] = cookie
                    if uname_final:
                        tab["username"] = uname_final
                    cookies_retrieved.append((pkg, uname_final, uid, cookie))
                    print(f"{Fore.GREEN}Cookie retrieved successfully: {pkg} ({uname_final}){Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Failed to retrieve cookie: {pkg}{Style.RESET_ALL}")

            if not cookies_retrieved:
                print(f"{Fore.RED}No accounts found to get cookies{Style.RESET_ALL}")
            else:
                if send_wh == "y":
                    print(f"{Fore.YELLOW}Fetching info and sending webhook...{Style.RESET_ALL}")
                    for pkg, uname_final, uid, cookie in cookies_retrieved:
                        avatar = AccountManager.get_avatar_url(uid)
                        created = AccountManager.get_account_created(uid)
                        self.webhook_manager.send_cookie_rich(uname_final, uid, cookie, avatar, created)
                    print(f"{Fore.GREEN}Sent successfully{Style.RESET_ALL}")
                try:
                    with open("all_cookie.txt", "w", encoding="utf-8") as f:
                        for pkg, uname_final, uid, cookie in cookies_retrieved:
                            f.write(f"{uname_final}:{cookie}\n")
                    print(f"{Fore.GREEN}Saved successful: all_cookie.txt{Style.RESET_ALL}")
                except Exception:
                    print(f"{Fore.RED}Failed to save{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_8(self):
        """Option 8: Login via cookies."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.YELLOW}[~] Config not found. Please try run tool again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.RED}[!] No packages found in config. Please setup in option 2 first{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}========== LOGIN VIA COOKIES =========={Style.RESET_ALL}")
        print(f"  [1] Login cookie for one package")
        print(f"  [2] Login cookies for all packages")
        c = input(f"{Fore.YELLOW}[?] Enter your choice (1/2): {Fore.WHITE}").strip()

        items = list(tabs.items())
        if c == "1":
            print(f"\n{Fore.CYAN}==========SELECT PACKAGE=========={Style.RESET_ALL}")
            for i, (pkg, tab) in enumerate(items, 1):
                uname = tab.get("username", "No User")
                print(f"  [{i:02d}] {pkg} ({uname})")
            raw = input(f"{Fore.YELLOW}Select package: {Fore.WHITE}").strip()
            if not raw.isdigit() or not (1 <= int(raw) <= len(items)):
                print(f"{Fore.RED}Invalid index{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            pkg, tab = items[int(raw) - 1]
            print(f"{Fore.GREEN}[+] Selected: {pkg}{Style.RESET_ALL}")
            ck_input = input(f"{Fore.YELLOW}Enter your cookie (username:pass:cookie or cookie only): {Fore.WHITE}").strip()
            if not ck_input:
                print(f"{Fore.RED}Cookie cannot be empty{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return

            cookie = ck_input
            if ".ROBLOSECURITY=" in cookie:
                cookie = cookie.split(".ROBLOSECURITY=")[1].split(";")[0].strip()
            elif "_|WARNING:-DO-NOT-SHARE-THIS" in cookie:
                parts = cookie.split("_|WARNING:-DO-NOT-SHARE-THIS")
                cookie = "_|WARNING:-DO-NOT-SHARE-THIS" + parts[-1].strip()
            elif ":" in cookie:
                cookie = cookie.split(":")[-1].strip()

            print(f"{Fore.YELLOW}Checking cookie validity...{Style.RESET_ALL}")
            ok, data = AccountManager.check_cookie(cookie)
            if not ok:
                print(f"{Fore.YELLOW}Cookie is banned ⇍ attempting unwarn...{Style.RESET_ALL}")
                if AccountManager.unwarn(cookie):
                    print(f"{Fore.GREEN}Unwarn successful ⇍ proceeding{Style.RESET_ALL}")
                    ok, data = AccountManager.check_cookie(cookie)
                else:
                    print(f"{Fore.RED}Cookie is invalid (expired) or Unwarn failed{Style.RESET_ALL}")
                    input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                    return
            else:
                print(f"{Fore.GREEN}Cookie is valid{Style.RESET_ALL}")

            db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
            print(f"{Fore.YELLOW}Writing cookie to {pkg}...{Style.RESET_ALL}")
            written = AccountManager.write_cookie(db_path, cookie)
            if written or not PackageManager.is_android():
                tab["cookie"] = cookie
                if data:
                    tab["username"] = data.get("name", tab.get("username", ""))
                    tab["user_id"] = data.get("id", tab.get("user_id", 0))
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Login successful for {pkg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}No Cookies file found for {pkg}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please open Roblox ({pkg}) once to create the file, then try again{Style.RESET_ALL}")
                print(f"{Fore.RED}Login failed for {pkg}{Style.RESET_ALL}")
        elif c == "2":
            print(f"\n{Fore.CYAN}File format: one cookie per line (no blank lines needed){Style.RESET_ALL}")
            print(f"{Fore.WHITE}Supported formats:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}         username:password:_|WARNING:...|cookie_1{Style.RESET_ALL}")
            print(f"{Fore.WHITE}         _|WARNING:...|cookie_2  (cookie only){Style.RESET_ALL}")
            print(f"{Fore.CYAN}Cookie order must match package order in config ({len(items)} package(s)):{Style.RESET_ALL}")
            for i, (pkg, tab) in enumerate(items, 1):
                print(f"  [{i:02d}] {pkg}")
            fpath = input(f"{Fore.YELLOW}Enter cookie file path: {Fore.WHITE}").strip()
            if not fpath:
                print(f"{Fore.RED}File path cannot be empty{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            if not os.path.exists(fpath):
                print(f"{Fore.RED}File not found: {fpath}{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    cookie_lines = [l.strip() for l in f if l.strip()]
            except Exception as e:
                print(f"{Fore.RED}File read error: {e}{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            if not cookie_lines:
                print(f"{Fore.RED}No cookies found in file{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return

            print(f"{Fore.GREEN}Found {len(cookie_lines)} cookie(s), config has {len(items)} package(s){Style.RESET_ALL}")
            if len(cookie_lines) < len(items):
                diff = len(items) - len(cookie_lines)
                print(f"{Fore.YELLOW}Cookie count ({len(cookie_lines)}) is less than package count ({len(items)}). Last {diff} package(s) will be skipped{Style.RESET_ALL}")

            success_cnt = 0
            failed_cnt = 0
            skipped_cnt = 0

            for i, (pkg, tab) in enumerate(items):
                if i >= len(cookie_lines):
                    print(f"[{pkg}] No cookie for: {pkg} -> skipped")
                    skipped_cnt += 1
                    continue
                raw_c = cookie_lines[i]
                cookie = raw_c
                if ".ROBLOSECURITY=" in cookie:
                    cookie = cookie.split(".ROBLOSECURITY=")[1].split(";")[0].strip()
                elif "_|WARNING:-DO-NOT-SHARE-THIS" in cookie:
                    cookie = "_|WARNING:-DO-NOT-SHARE-THIS" + cookie.split("_|WARNING:-DO-NOT-SHARE-THIS")[-1].strip()
                elif ":" in cookie:
                    cookie = cookie.split(":")[-1].strip()

                print(f"[{pkg}] Checking cookie for {pkg}...")
                ok, data = AccountManager.check_cookie(cookie)
                if not ok:
                    print(f"[{pkg}] Cookie banned for {pkg} ⇍ attempting unwarn...")
                    if AccountManager.unwarn(cookie):
                        print(f"[{pkg}] Unwarn successful for {pkg} ⇍ proceeding")
                        ok, data = AccountManager.check_cookie(cookie)
                    else:
                        print(f"[{pkg}] Cookie expired or unwarn failed: {pkg}")
                        failed_cnt += 1
                        continue

                db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                print(f"[{pkg}] Writing cookie for {pkg}...")
                written = AccountManager.write_cookie(db_path, cookie)
                if written or not PackageManager.is_android():
                    tab["cookie"] = cookie
                    if data:
                        tab["username"] = data.get("name", tab.get("username", ""))
                        tab["user_id"] = data.get("id", tab.get("user_id", 0))
                    success_cnt += 1
                else:
                    print(f"-> Roblox has never been opened. Please open the app once first")
                    failed_cnt += 1

            ConfigManager.save_config(self.config, self.config_file)
            print(f"{Fore.GREEN}Result: {success_cnt} successful | {failed_cnt} failed | {skipped_cnt} skipped{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_9(self):
        """Option 9: Log out account."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.YELLOW}[~] Config not found. Please setup in option 2 first{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.RED}[!] No account information found in config. Please try again{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}========== LOG OUT ACCOUNT =========={Style.RESET_ALL}")
        print(f"  [1] Log out 1 Roblox account")
        print(f"  [2] Log out all Roblox accounts")
        c = input(f"{Fore.YELLOW}[?] Enter your choice (1/2): {Fore.WHITE}").strip()

        items = list(tabs.items())
        if c == "1":
            for i, (pkg, tab) in enumerate(items, 1):
                uname = tab.get("username", "No User")
                print(f"  [{i:02d}] {pkg} ({uname})")
            raw = input(f"{Fore.YELLOW}Select account to log out: {Fore.WHITE}").strip()
            if not raw.isdigit() or not (1 <= int(raw) <= len(items)):
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                return
            pkg, tab = items[int(raw) - 1]
            uname = tab.get("username", "Unknown")
            conf = input(f"{Fore.YELLOW}Are you sure (y/n): {Fore.WHITE}").strip().lower()
            if conf == "y":
                try:
                    db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    if PackageManager.is_android():
                        subprocess.run(f"rm -f /data/data/{pkg}/app_webview/Default/Cookies*", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    tab["cookie"] = ""
                    tab["username"] = ""
                    tab["user_id"] = 0
                    PackageManager.fast_restore_tab(tab)
                    ConfigManager.save_config(self.config, self.config_file)
                    print(f"{Fore.GREEN}[+] Logged out {uname} from {pkg}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error during logout: {e}{Style.RESET_ALL}")
        elif c == "2":
            conf = input(f"{Fore.YELLOW}Are you sure (y/n): {Fore.WHITE}").strip().lower()
            if conf == "y":
                for pkg, tab in items:
                    try:
                        db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                        if os.path.exists(db_path):
                            os.remove(db_path)
                        if PackageManager.is_android():
                            subprocess.run(f"rm -f /data/data/{pkg}/app_webview/Default/Cookies*", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        tab["cookie"] = ""
                        tab["username"] = ""
                        tab["user_id"] = 0
                        PackageManager.fast_restore_tab(tab)
                    except Exception as e:
                        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}[+] All accounts logged out successfully{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_10(self):
        """Option 10: Set config tool."""
        cfg = ConfigManager.load_config(self.config_file)
        while True:
            print(f"\n{Fore.CYAN}=============== SET CONFIG TOOL ==============={Style.RESET_ALL}")
            print(f"  [1] Rejoin interval  : {cfg.get('rejoin_interval', 20)} minutes")
            print(f"  [2] Offline_wait    : {cfg.get('offline_wait', 10)} seconds (check online method only)")
            print(f"  [3] Max retries      : {cfg.get('max_retries', 3)}")
            print(f"  [4] Retry delay      : {cfg.get('retry_delay', 5)} (seconds)")
            print(f"  [5] Check interval   : {cfg.get('check_interval', 5)} (check online + executor method)")
            print(f"  [6] Delay open tab   : {cfg.get('delay_open_tab', 5)} (seconds)")
            print(f"  [7] trigger          : {cfg.get('trigger', 'completed')}")
            print(f"  [8] Rejoin timeout   : {cfg.get('rejoin_timeout', 60)} (seconds)")
            print(f"  [9] Check UI delay   : {cfg.get('check_ui_delay', 5)} (check executor method only)")
            st_cap = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if cfg.get("auto_close_tab_when_get_capcha") else f"{Fore.RED}Disable{Style.RESET_ALL}"
            print(f"  [10] Auto close tab when get capcha: {st_cap}")
            st_cache = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if cfg.get("auto_clear_cache") else f"{Fore.RED}Disable{Style.RESET_ALL}"
            print(f"  [11] Auto clear cache: {st_cache}")
            print(f"  [12] FPS counter (in-game): {cfg.get('fps_counter', 30)}")
            st_seq = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if cfg.get("sequential_join") else f"{Fore.RED}Disable{Style.RESET_ALL}"
            print(f"  [13] Sequential join: {st_seq} (The tool will wait for the first tab to open the game, then open the next tab)")
            st_svv = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if cfg.get("auto_buy_svv") else f"{Fore.RED}Disable{Style.RESET_ALL}"
            print(f"  [14] Auto buy private server: {st_svv} (Free only)")
            print(f"  [0] Save and exit")

            c = input(f"{Fore.YELLOW}J[?] Enter choice: {Fore.WHITE}").strip()
            if c == "0":
                ConfigManager.save_config(cfg, self.config_file)
                self.config = cfg
                print(f"{Fore.GREEN}[+] Config saved{Style.RESET_ALL}")
                input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
                break
            elif c == "1":
                val = input(f"{Fore.YELLOW}[?] Rejoin interval (minutes): {Fore.WHITE}").strip()
                if val.isdigit() and int(val) > 0:
                    cfg["rejoin_interval"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "2":
                val = input(f"{Fore.YELLOW}[?] Offline_wait: {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["offline_wait"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "3":
                val = input(f"{Fore.YELLOW}[?] Max retries: {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["max_retries"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "4":
                val = input(f"{Fore.YELLOW}[?] Retry delay (seconds): {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["retry_delay"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "5":
                val = input(f"{Fore.YELLOW}[?] Check interval (seconds): {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["check_interval"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "6":
                val = input(f"{Fore.YELLOW}[?] Delay open tab (seconds): {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["delay_open_tab"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "7":
                val = input(f"{Fore.YELLOW}[?] Enter your new trigger: {Fore.WHITE}").strip()
                if val:
                    cfg["trigger"] = val
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
            elif c == "8":
                val = input(f"{Fore.YELLOW}[?] Rejoin timeout (seconds): {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["rejoin_timeout"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "9":
                val = input(f"{Fore.YELLOW}[?] Check UI delay (seconds): {Fore.WHITE}").strip()
                if val.isdigit():
                    cfg["check_ui_delay"] = int(val)
                    print(f"{Fore.GREEN}Set to {val}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "10":
                cfg["auto_close_tab_when_get_capcha"] = not cfg.get("auto_close_tab_when_get_capcha", False)
                st = "Enable" if cfg["auto_close_tab_when_get_capcha"] else "Disable"
                print(f"{Fore.GREEN}Auto close tab when get capcha: {st}{Style.RESET_ALL}")
            elif c == "11":
                cfg["auto_clear_cache"] = not cfg.get("auto_clear_cache", False)
                st = "Enable" if cfg["auto_clear_cache"] else "Disable"
                print(f"{Fore.GREEN}Auto clear cache: {st}{Style.RESET_ALL}")
            elif c == "12":
                val = input(f"{Fore.YELLOW}[?] FPS counter: {Fore.WHITE}").strip()
                if val.isdigit():
                    fps_val = int(val)
                    cfg["fps_counter"] = fps_val
                    synced = ConfigManager.sync_fps_config(fps_val)
                    if synced > 0:
                        print(f"{Fore.GREEN}FPS counter set to {fps_val} (synced to {synced} workspace){Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}[~] (no executor workspace found yet, will sync next time it's detected){Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            elif c == "13":
                cfg["sequential_join"] = not cfg.get("sequential_join", False)
                st = "Enable" if cfg["sequential_join"] else "Disable"
                print(f"{Fore.GREEN}Sequential join: {st}{Style.RESET_ALL}")
            elif c == "14":
                cfg["auto_buy_svv"] = not cfg.get("auto_buy_svv", False)
                st = "Enable" if cfg["auto_buy_svv"] else "Disable"
                print(f"{Fore.GREEN}Auto buy private server: {st}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[!] Invalid value{Style.RESET_ALL}")
            time.sleep(1)

    def option_11(self):
        """Option 11: Open all tab Roblox."""
        if not os.path.exists(self.config_file):
            print(f"{Fore.RED}[!] Config not found. Please setup option 2 first{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        tabs = self.config.get("tabs", {})
        if not tabs:
            print(f"{Fore.YELLOW}[~] No packages found. Please setup in option 2 first{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        delay = self.config.get("delay_open_tab", 5)
        link = self.config.get("link_id_game", "")
        for pkg, tab in tabs.items():
            if tab.get("enabled", True):
                PackageManager.launch_roblox(pkg, tab.get("link_id_game", link))
                print(f"{Fore.GREEN}[+] Opened {pkg}{Style.RESET_ALL}")
                time.sleep(delay)
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_12(self):
        """Option 12: Change android id."""
        cur_id = PackageManager.get_android_id()
        if not cur_id:
            print(f"{Fore.RED}[!] android id not found{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}[*] Your android id is: {cur_id}{Style.RESET_ALL}")
        print(f"  [1] Random android id")
        print(f"  [2] Set android id")
        c = input(f"{Fore.YELLOW}[?] Enter your choice(1/2): {Fore.WHITE}").strip()
        if c == "1":
            import secrets
            new_id = secrets.token_hex(8)
            res = PackageManager.change_android_id(new_id)
            if res:
                print(f"{Fore.GREEN}[+] Your new android id is {new_id}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to change android id{Style.RESET_ALL}")
        elif c == "2":
            new_id = input(f"{Fore.YELLOW}Enter your android id: {Fore.WHITE}").strip()
            if len(new_id) == 16 and all(ch in "0123456789abcdefABCDEF" for ch in new_id):
                res = PackageManager.change_android_id(new_id.lower())
                if res:
                    print(f"{Fore.GREEN}[+] Your new android id is: {new_id.lower()}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Failed to change android id{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Invalid android id{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_13(self):
        """Option 13: Toogle auto block."""
        cur = self.config.get("auto_block", False)
        if cur:
            print(f"{Fore.GREEN}[ON] Auto block{Style.RESET_ALL}")
            conf = input(f"{Fore.YELLOW}[?] Do you want turn off auto block (y/n): {Fore.WHITE}").strip().lower()
            if conf == "y":
                self.config["auto_block"] = False
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.RED}Turned off auto block{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[OFF] Auto block{Style.RESET_ALL}")
            conf = input(f"{Fore.YELLOW}[?] Do you want turn on auto block (y/n): {Fore.WHITE}").strip().lower()
            if conf == "y":
                self.config["auto_block"] = True
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Turned on auto block{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_14(self):
        """Option 14: Toogle auto sort tab."""
        tabs = self.config.get("tabs", {})
        print(f"\n{Fore.CYAN}========== SELECT SORT TAB STYLE =========={Style.RESET_ALL}")
        print(f"  [1] L style (old sort tab)")
        print(f"  [2] Full screen style (new sort tab)")
        print(f"  [0] Turn off auto sort tab")
        c = input(f"{Fore.YELLOW}[?] Select your auto sort tab style: {Fore.WHITE}").strip()
        if c == "1":
            self.config["auto_sort_tab"] = True
            self.config["auto_sort_tab_full"] = False
            ConfigManager.save_config(self.config, self.config_file)
            WindowLayoutManager.arrange_clone_windows(tabs)
            print(f"{Fore.GREEN}Turned on auto sort tab{Style.RESET_ALL}")
        elif c == "2":
            self.config["auto_sort_tab"] = True
            self.config["auto_sort_tab_full"] = True
            ConfigManager.save_config(self.config, self.config_file)
            WindowLayoutManager.arrange_clone_windows_full(tabs)
            print(f"{Fore.GREEN}Turned on auto sort tab{Style.RESET_ALL}")
        elif c == "0":
            self.config["auto_sort_tab"] = False
            self.config["auto_sort_tab_full"] = False
            ConfigManager.save_config(self.config, self.config_file)
            print(f"{Fore.RED}Turned off auto sort tab{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_15(self):
        """Option 15: Toogle auto change acc."""
        print(f"\n{Fore.CYAN}========== TOOGLE AUTO CHANGE ACC =========={Style.RESET_ALL}")
        st_custom = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if self.config.get("auto_change_acc_custom") else f"{Fore.RED}Disable{Style.RESET_ALL}"
        st_bf = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if self.config.get("auto_change_acc_bf") else f"{Fore.RED}Disable{Style.RESET_ALL}"
        st_cap = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if self.config.get("auto_change_acc_captcha") else f"{Fore.RED}Disable{Style.RESET_ALL}"
        st_fid = f"{Fore.GREEN}Enable{Style.RESET_ALL}" if self.config.get("auto_change_acc_faceid") else f"{Fore.RED}Disable{Style.RESET_ALL}"
        print(f"  [0] Custom script : {st_custom}")
        print(f"  [1] Blox fruits   : {st_bf}")
        print(f"  [2] Auto change acc when got captcha : {st_cap}")
        print(f"  [3] Auto change acc when got faceid  : {st_fid}")
        c = input(f"{Fore.YELLOW}[?] Enter your choose: {Fore.WHITE}").strip()
        if c == "0":
            self.config["auto_change_acc_custom"] = not self.config.get("auto_change_acc_custom", False)
            ConfigManager.save_config(self.config, self.config_file)
            if self.config["auto_change_acc_custom"]:
                print(f"{Fore.GREEN}Turned on Auto change account{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Don't forget to add your auto-change-account script to the Autoexec folder{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Turned off auto change account custom{Style.RESET_ALL}")
        elif c == "1":
            self.config["auto_change_acc_bf"] = not self.config.get("auto_change_acc_bf", False)
            ConfigManager.save_config(self.config, self.config_file)
            if self.config["auto_change_acc_bf"]:
                self._write_bf_config_to_workspace()
                print(f"{Fore.GREEN}Turned on auto change account blox_fruit{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Turned off auto change account blox fruit{Style.RESET_ALL}")
        elif c == "2":
            self.config["auto_change_acc_captcha"] = not self.config.get("auto_change_acc_captcha", False)
            ConfigManager.save_config(self.config, self.config_file)
            st = "Turned on" if self.config["auto_change_acc_captcha"] else "Turned off"
            print(f"{Fore.GREEN if 'on' in st else Fore.RED}{st} auto change acc when got captcha{Style.RESET_ALL}")
        elif c == "3":
            self.config["auto_change_acc_faceid"] = not self.config.get("auto_change_acc_faceid", False)
            ConfigManager.save_config(self.config, self.config_file)
            st = "Turned on" if self.config["auto_change_acc_faceid"] else "Turned off"
            print(f"{Fore.GREEN if 'on' in st else Fore.RED}{st} auto change acc when got faceid{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Invalid choose{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_16(self):
        """Option 16: Toogle auto bypass."""
        cur_bp = self.config.get("auto_bypass", False)
        cur_hwid = self.config.get("auto_hwid_delta", False)
        if not cur_bp:
            print(f"\n{Fore.CYAN}=============== SELECT SERVICE YOU WANT BYPASS ==============={Style.RESET_ALL}")
            print(f"  [1] Delta")
            print(f"  [0] Back")
            c = input(f"{Fore.YELLOW}[?] Enter your choice: {Fore.WHITE}").strip()
            if c == "1":
                self.config["auto_bypass"] = True
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Delta auto bypass enabled{Style.RESET_ALL}")
            elif c != "0":
                print(f"{Fore.RED}[!] Invalid choice{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.CYAN}=============== AUTO BYPASS MANAGER ==============={Style.RESET_ALL}")
            print(f" Current Service: Delta")
            print(f" Hwid Delta mode: {'Auto' if cur_hwid else 'Manual'}")
            print(f"  [1] Change bypass service")
            print(f"  [2] Change hwid delta mode")
            print(f"  [0] Back")
            c = input(f"{Fore.YELLOW}[?] Enter your choice: {Fore.WHITE}").strip()
            if c == "1":
                conf = input(f"{Fore.YELLOW}Turn off Delta bypass to select another service? (y/n): {Fore.WHITE}").strip().lower()
                if conf == "y":
                    self.config["auto_bypass"] = False
                    ConfigManager.save_config(self.config, self.config_file)
                    print(f"{Fore.RED}Turned off Delta auto bypass{Style.RESET_ALL}")
            elif c == "2":
                conf = input(f"{Fore.YELLOW}Do you want to change your hwid Delta mode(y/n): {Fore.WHITE}").strip().lower()
                if conf == "y":
                    self.config["auto_hwid_delta"] = not cur_hwid
                    ConfigManager.save_config(self.config, self.config_file)
                    print(f"{Fore.GREEN}Hwid Delta mode updated.{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_17(self):
        """Option 17: Select account check method."""
        print(f"\n{Fore.CYAN}========== SELECT ACCOUNT CHECK METHOD =========={Style.RESET_ALL}")
        cur_m = self.config.get("account_check_method", "executor")
        if cur_m == "executor":
            print(f" Your account check method is executor")
        elif cur_m == "online":
            print(f" Your account check method is online")
        else:
            print(f"{Fore.RED}[!] Unknown method{Style.RESET_ALL}")
        print(f"  [1] Executor method (recommended)")
        print(f"  [2] Online method (not recommended)")
        c = input(f"{Fore.YELLOW}[?] Selected account check method: {Fore.WHITE}").strip()
        if c == "1":
            self.config["account_check_method"] = "executor"
            ConfigManager.save_config(self.config, self.config_file)
            print(f"{Fore.GREEN}Selected check executor method{Style.RESET_ALL}")
        elif c == "2":
            self.config["account_check_method"] = "online"
            ConfigManager.save_config(self.config, self.config_file)
            print(f"{Fore.GREEN}Selected check online method{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def option_18(self):
        """Option 18: Toggle auto solver captcha/FaceID."""
        print(f"\n{Fore.CYAN}========== TOGGLE AUTO SOLVER CAPTCHA/FACEID =========={Style.RESET_ALL}")
        urls = self.config.setdefault("third_party_solve_capcha_url", [])
        if isinstance(urls, str):
            urls = [urls]
            self.config["third_party_solve_capcha_url"] = urls
        faceid_urls = self.config.setdefault("faceid_&_captcha_lock_solve_url", [])
        if isinstance(faceid_urls, str):
            faceid_urls = [faceid_urls]
            self.config["faceid_&_captcha_lock_solve_url"] = faceid_urls

        sol_en = self.config.get("auto_send_acc_to_solver_captcha", False)
        fid_en = self.config.get("auto_send_acc_to_solver_faceid", False)

        print(f"{Fore.CYAN}=============== AUTO CAPTCHA MANAGER ==============={Style.RESET_ALL}")
        print(f" Auto solver captcha: {'Enabled' if sol_en else 'Disabled'}")
        print(f" Solver captcha URLs ({len(urls)}):")
        if not urls:
            print(f"  [-] No solver URLs configured")
        else:
            for idx, u in enumerate(urls, 1):
                print(f"  [{idx:02d}] {u}")

        print(f"\n{Fore.CYAN}=============== FACEID SOLVER MANAGER ==============={Style.RESET_ALL}")
        print(f" Auto unface: {str(fid_en)}")
        print(f" Zeropoint api key: {self.config.get('zeropoint_apikey', '')}")
        print(f" Priority queue: {self.config.get('zeropoint_priority', 1)}")
        print(f" Solver faceid URLs ({len(faceid_urls)}):")
        if not faceid_urls:
            print(f"  [-] No solver URLs configured")
        else:
            for idx, u in enumerate(faceid_urls, 1):
                print(f"  [{idx:02d}] {u}")

        print(f"\n  [1] Toggle auto solver captcha (on/off)")
        print(f"  [2] Toggle auto unface (on/off)")
        print(f"  [3] Add third party solver captcha URL")
        print(f"  [4] Remove a solver URL")
        print(f"  [5] Enter zeropoint apikey")
        print(f"  [6] Change zeropoint priority")
        print(f"  [7] Add third party solver faceid URL")
        print(f"  [0] Back")

        c = input(f"{Fore.YELLOW}[?] Enter your choice: {Fore.WHITE}").strip()
        if c == "1":
            if not urls:
                print(f"{Fore.RED}Cannot enable: no solver URLs added yet{Style.RESET_ALL}")
            else:
                self.config["auto_send_acc_to_solver_captcha"] = not sol_en
                ConfigManager.save_config(self.config, self.config_file)
                st = "enabled" if self.config["auto_send_acc_to_solver_captcha"] else "disabled"
                print(f"{Fore.GREEN if 'en' in st else Fore.RED}Auto solver captcha {st}{Style.RESET_ALL}")
        elif c == "2":
            self.config["auto_send_acc_to_solver_faceid"] = not fid_en
            ConfigManager.save_config(self.config, self.config_file)
            st = "enabled" if self.config["auto_send_acc_to_solver_faceid"] else "disabled"
            print(f"{Fore.GREEN if 'en' in st else Fore.RED}Auto unface {st}{Style.RESET_ALL}")
        elif c == "3":
            print(f"{Fore.CYAN}[i] Enter URLs one per line. Leave blank and press Enter when done.{Style.RESET_ALL}")
            added = 0
            while True:
                u = input(f"{Fore.YELLOW}URL (blank to finish): {Fore.WHITE}").strip()
                if not u:
                    break
                if "http" not in u:
                    print(f"{Fore.RED}Invalid URL (must contain http), skipped{Style.RESET_ALL}")
                    continue
                if u in urls:
                    print(f"{Fore.YELLOW}[~] URL already in list, skipped{Style.RESET_ALL}")
                    continue
                urls.append(u)
                added += 1
                print(f"{Fore.GREEN}Added: {u}{Style.RESET_ALL}")
            if added > 0:
                self.config["auto_send_acc_to_solver_captcha"] = True
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Auto solver captcha auto-enabled{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Saved {added} new URL(s). Total: {len(urls)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No URLs added{Style.RESET_ALL}")
        elif c == "4":
            if not urls:
                print(f"{Fore.YELLOW}No URLs to remove{Style.RESET_ALL}")
            else:
                for idx, u in enumerate(urls, 1):
                    print(f"  [{idx:02d}] {u}")
                r_str = input(f"{Fore.YELLOW}Enter the number of the URL to remove (0 to cancel): {Fore.WHITE}").strip()
                if r_str.isdigit() and 1 <= int(r_str) <= len(urls):
                    rem_u = urls.pop(int(r_str) - 1)
                    if not urls:
                        self.config["auto_send_acc_to_solver_captcha"] = False
                        print(f"{Fore.RED}No URLs left ⁋ auto solver captcha disabled{Style.RESET_ALL}")
                    ConfigManager.save_config(self.config, self.config_file)
                    print(f"{Fore.GREEN}Removed: {rem_u}{Style.RESET_ALL}")
                elif r_str != "0":
                    print(f"{Fore.RED}Index out of range{Style.RESET_ALL}")
        elif c == "5":
            k = input(f"{Fore.YELLOW}Enter zeropoint apikey: {Fore.WHITE}").strip()
            if k:
                self.config["zeropoint_apikey"] = k
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Saved{Style.RESET_ALL}")
        elif c == "6":
            p = input(f"{Fore.YELLOW}Enter your zeropoint priority: {Fore.WHITE}").strip()
            if p.isdigit():
                self.config["zeropoint_priority"] = int(p)
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Saved{Style.RESET_ALL}")
        elif c == "7":
            print(f"{Fore.CYAN}[i] Enter URLs one per line. Leave blank and press Enter when done.{Style.RESET_ALL}")
            added = 0
            while True:
                u = input(f"{Fore.YELLOW}URL (blank to finish): {Fore.WHITE}").strip()
                if not u:
                    break
                if "http" not in u:
                    print(f"{Fore.RED}Invalid URL (must contain http), skipped{Style.RESET_ALL}")
                    continue
                if u in faceid_urls:
                    print(f"{Fore.YELLOW}[~] URL already in list, skipped{Style.RESET_ALL}")
                    continue
                faceid_urls.append(u)
                added += 1
                print(f"{Fore.GREEN}Added: {u}{Style.RESET_ALL}")
            if added > 0:
                self.config["auto_send_acc_to_solver_faceid"] = True
                ConfigManager.save_config(self.config, self.config_file)
                print(f"{Fore.GREEN}Auto solver faceid auto-enabled{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Saved {added} new URL(s). Total: {len(faceid_urls)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No URLs added{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Enter to back{Style.RESET_ALL}")

    def run(self):
        """Khởi động menu chính."""
        while True:
            self.menu()
            choice = input(f"{Fore.YELLOW}Chọn chức năng (0-18): {Fore.WHITE}").strip()

            if choice in ("0", "00", "exit", "quit"):
                print(f"{Fore.GREEN}Tạm biệt!")
                break
            elif choice in ("1", "01"):
                self.option_1()
            elif choice in ("2", "02"):
                self.option_2()
            elif choice in ("3", "03"):
                self.option_3()
            elif choice in ("4", "04"):
                self.option_4()
            elif choice in ("5", "05"):
                self.option_5()
            elif choice in ("6", "06"):
                self.option_6()
            elif choice in ("7", "07"):
                self.option_7()
            elif choice in ("8", "08"):
                self.option_8()
            elif choice in ("9", "09"):
                self.option_9()
            elif choice == "10":
                self.option_10()
            elif choice == "11":
                self.option_11()
            elif choice == "12":
                self.option_12()
            elif choice == "13":
                self.option_13()
            elif choice == "14":
                self.option_14()
            elif choice == "15":
                self.option_15()
            elif choice == "16":
                self.option_16()
            elif choice == "17":
                self.option_17()
            elif choice == "18":
                self.option_18()
            else:
                print(f"{Fore.RED}[-] Lựa chọn không hợp lệ!")
                time.sleep(1)


# ===========================================================================
# ĐIỂM KHỞI CHẠY CHÍNH (ENTRY POINT)
# ===========================================================================
def main():
    try:
        app = WuyxTool()
        app.run()
    except KeyboardInterrupt:
        print("\n\nĐã thoát chương trình.")


if __name__ == "__main__":
    main()
