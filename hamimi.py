#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import glob
import re
import io
import base64
import secrets
import sqlite3
import threading
import subprocess
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    requests = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = DummyColor()
    Style = DummyColor()

try:
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.PublicKey import RSA
except ImportError:
    AES = None
    PKCS1_OAEP = None
    RSA = None


# =====================================================================
# Constants & Configuration
# =====================================================================

TOOL_VERSION = "1.0.4"
STATUS_URL = "https://api.wuyxtool.online/public/status.json"
UPDATE_URL = "https://api.wuyxtool.online/public/wuyx_rejoin.py"
UPDATE_FILENAME = "obf-wuyx_rejoin.py"
RUN_DIR = "/sdcard/Download"

LICENSE_SERVER_URL = "https://api.wuyxtool.online/verify"
SERVICE_API_KEY = "11122008"
AES_SECRET_KEY = base64.b64decode("MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=")

CLIENT_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIGeMA0GCSqGSIb3DQEBAQUAA4GMADCBiAKBgGrJVRIzratNChtkCIXnSPAhjdmm
uwhSsq+P7cbsS21mIfGOFQQ8OpMJTr50BeB9gRyFvyyVfrbvmuHMzKhEBOp0bEt6
6nltcx8xBI3Knz81ch226iUqFZ77G8QGvbC4lJnpQn37ICaE5+6Sv4Rc8KTbAtpK
CHxZy0Z79PCp+C7rAgMBAAE=
-----END PUBLIC KEY-----"""

CLIENT_PRIVATE_KEY_PEM = """-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgGrJVRIzratNChtkCIXnSPAhjdmmuwhSsq+P7cbsS21mIfGOFQQ8
OpMJTr50BeB9gRyFvyyVfrbvmuHMzKhEBOp0bEt66nltcx8xBI3Knz81ch226iUq
FZ77G8QGvbC4lJnpQn37ICaE5+6Sv4Rc8KTbAtpKCHxZy0Z79PCp+C7rAgMBAAEC
gYAh/OCpwW8GNagA3c7kp5+MZnGak7m1xXR/8mRwyuaa9EXbdyhzR6QxBmZcsdro
/6knZd5aF17UZOC7+44sBDI37q5EqVd6TeanSVYc7VeyKCmSV9KK3r7FbbPGz5tv
iCZxlBHgokgzpPzkUvO/KbuEVy9wr33AHXvcQbQcwnn1sQJBAMHeBHGJVKcuHAhK
0k3wKBX3VoWUJkyrKc/NaCeIktPFbS972z9iEqsYE8BunLCsvgYyF37mfEpFFZAU
R1j8zskCQQCNArTCzwbvOYXKr5EzjfKKDGCZUCty4R89rRMdEnG12oGDQRLU9xxK
0GQVVl1wBYeu7olYUI5cn2pA3N0G6yYTAkBpa0X1Sx0aL4uUwsLrGJ1jnHSS/IV7
CVQaKHLrlGtq9p8xw+Lr63OFT/llmYBg3f4StmhqXADYDgr0puJJNGdpAkBewvTK
/enBFj0NKtM/fCMEFrFMFo48U4F1JzxzCxQTi9YBaNfI+o+uz0CS/kkooO6/5lmy
WeBx6kezczmuDpS1AkEAqT0ho9h+kerNPbh4mx3TCBCXK36y7v6YWRWECjMueyRE
jBrUPchs8jLmzgF4sTTjDkpKdj2sibvKIkmofxTj3A==
-----END RSA PRIVATE KEY-----"""

LICENSE_FILE = "/sdcard/license.txt"
_SECRET_FILE = "/data/system/.com.android.providers.settings"

EVENT_COLORS = {
    'Captcha': 16777179,
    'Captcha Sent To Solver': 3446972,
    'Captcha Solver Failed': 16711808,
    'Captcha Solved': 65479,
    'FaceID': 16744433,
    'FaceID Sent To Solver': 3446885,
    'FaceID Solver Failed': 16711840,
    'Unface Solver Failed': 16711911,
    'FaceID Solved': 65342,
    'Banned': 16711740,
    'Ban': 16711861,
    'Unwarn Success': 65423,
    'Unwarn Failed': 16711770,
    'Cookie Dead': 10038685,
    'Rejoin Failed': 16754070
}

EVENT_ICONS = {
    'Captcha': '🧩',
    'Captcha Sent To Solver': '📤',
    'Captcha Solver Failed': '❌',
    'Captcha Solved': '✅',
    'FaceID': '🪪',
    'FaceID Sent To Solver': '📤',
    'FaceID Solver Failed': '❌',
    'Unface Solver Failed': '❌',
    'FaceID Solved': '✅',
    'Banned': '⛔',
    'Ban': '⛔',
    'Unwarn Success': '✅',
    'Unwarn Failed': '❌',
    'Cookie Dead': '💀',
    'Rejoin Failed': '🔁'
}

GAMES_MAP = {
    1: ("Blox fruits", "2753915549"),
    2: ("Sailor Piece", "77747658251236"),
    3: ("King Legacy", "4520749081"),
    4: ("Bee Swarm simulator", "1537690962"),
    5: ("Pet simulator 99", "8737899170"),
    6: ("Attack on Titan Revolution", "13379208636"),
    7: ("Grow a garden 2", "97598239454123"),
    8: ("Steal An Egg", "107778070777162")
}


# =====================================================================
# UI / Menu
# =====================================================================

class menu:
    @staticmethod
    def banner():
        os.system('cls' if os.name == 'nt' else 'clear')
        raw_banner = """
    ██╗    ██╗██╗   ██╗██╗   ██╗██╗  ██╗          
    ██║    ██║██║   ██║╚██╗ ██╔╝╚██╗██╔╝          
    ██║ █╗ ██║██║   ██║ ╚████╔╝  ╚███╔╝           
    ██║███╗██║██║   ██║  ╚██╔╝   ██╔██╗           
    ╚███╔███╔╝╚██████╔╝   ██║   ██╔╝ ██╗          
     ╚══╝╚══╝  ╚═════╝    ╚═╝   ╚═╝  ╚═╝          
                                                 
 ██████╗ ███████╗     ██╗ ██████╗ ██╗███╗   ██╗
 ██╔══██╗██╔════╝     ██║██╔═══██╗██║████╗  ██║
 ██████╔╝█████╗       ██║██║   ██║██║██╔██╗ ██║
 ██╔══██╗██╔══╝  ██   ██║██║   ██║██║██║╚██╗██║
 ██║  ██║███████╗╚█████╔╝╚██████╔╝██║██║ ╚████║
 ╚═╝  ╚═╝╚══════╝ ╚════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝
"""
        lines = raw_banner.strip('\n').split('\n')
        total = len(lines)
        start_rgb = (129, 202, 69)
        end_rgb = (208, 199, 45)
        for i, line in enumerate(lines):
            ratio = i / max(1, total - 1)
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
            print(f"\x1b[38;2;{r};{g};{b}m{line}\x1b[0m")
        print(Fore.CYAN + "            > > > Premium Version < < <")
        print(Fore.LIGHTBLUE_EX + "Discord: discord.gg/5G3cStpbcx\n")

    @staticmethod
    def tool_status(config):
        acc_method = config.get("account_check_method", "executor")
        if acc_method == "executor":
            check_text = Fore.GREEN + "CHECK EXECUTOR METHOD"
        elif acc_method == "online":
            check_text = Fore.GREEN + "CHECK ONLINE METHOD"
        else:
            check_text = Fore.RED + "CHECk UNKNOWN METHOD"

        wh_run = config.get("discord_webhook", {}).get("running", False)
        wh_text = Fore.GREEN + "Enable" if wh_run else Fore.RED + "Disable"

        bp = config.get("auto_bypass", False)
        bp_text = Fore.GREEN + "Enable" if bp else Fore.RED + "Disable"

        st = config.get("auto_sort_tab", False) or config.get("auto_sort_tab_full", False)
        st_text = Fore.GREEN + "Enable" if st else Fore.RED + "Disable"

        ca = any([
            config.get("auto_change_acc_bf", False),
            config.get("auto_change_acc_custom", False),
            config.get("auto_change_acc_captcha", False),
            config.get("auto_change_acc_faceid", False)
        ])
        ca_text = Fore.GREEN + "Enable" if ca else Fore.RED + "Disable"

        print(Fore.CYAN + "-----------------------------------------------------")
        print(f"| {Fore.YELLOW}STATUS{Style.RESET_ALL}        : {check_text}")
        print(f"| {Fore.YELLOW}WEBHOOK{Style.RESET_ALL}       : {wh_text}")
        print(f"| {Fore.YELLOW}AUTO BYPASS{Style.RESET_ALL}   : {bp_text}")
        print(f"| {Fore.YELLOW}AUTO SORT TAB{Style.RESET_ALL} : {st_text}")
        print(f"| {Fore.YELLOW}AUTO CHANGE{Style.RESET_ALL}   : {ca_text}")
        print(Fore.CYAN + "-----------------------------------------------------")

    @staticmethod
    def option():
        print(Fore.CYAN + "|----+----------------------------------------------|")
        print(f"| {Fore.YELLOW}No{Fore.CYAN} | {Fore.YELLOW}Command{Fore.CYAN}                                       |")
        print("|----+----------------------------------------------|")
        opts = [
            (" 1", "Start auto rejoin"),
            (" 2", "Setup package"),
            (" 3", "Setup package to run"),
            (" 4", "Setup game and private sv"),
            (" 5", "Setup webhook"),
            (" 6", "Setup autoexecute"),
            (" 7", "Get cookie account"),
            (" 8", "Login via cookies"),
            (" 9", "Log out account"),
            ("10", "Set config tool"),
            ("11", "Open all tab Roblox"),
            ("12", "Change android id"),
            ("13", "Toogle auto block"),
            ("14", "Toogle auto sort tab"),
            ("15", "Toogle auto change acc"),
            ("16", "Toogle auto bypass"),
            ("17", "Select account check method"),
            ("18", "Toggle auto solver captcha/FaceID"),
            (" 0", "Exit")
        ]
        for num, cmd in opts:
            print(f"| {Fore.GREEN}{num}{Style.RESET_ALL} | {cmd:<44} |")
        print(Fore.CYAN + "-----------------------------------------------------")

    @staticmethod
    def status_banner(tabs_status, total_time=None, start_time=None):
        mem = psutil.virtual_memory() if psutil else None
        cpu = psutil.cpu_percent() if psutil else 0.0
        used_gb = round(mem.used / (1024**3), 1) if mem else 0.0
        tot_gb = round(mem.total / (1024**3), 1) if mem else 0.0

        print(Fore.CYAN + "----------------------------------------------------------------------------------")
        print(f"|  Cpu usage: {str(cpu) + '%':<6}      |  Ram usage: {f'{used_gb} / {tot_gb} GB':<26} |")
        print("----------------------------------------------------------------------------------")
        print("| No   | Username        | Package         | Status     | Game                   |")
        print("|------|-----------------|-----------------|------------|------------------------|")

        if not tabs_status:
            print("| No enabled packages running                                                    |")
        else:
            for i, tab in enumerate(tabs_status):
                uname = (tab.get("user_name") or "Unknown")[:15]
                pkg = (tab.get("package") or "Unknown")[:15]
                stat = (tab.get("status") or "Unknown")[:10]
                game = (tab.get("game") or tab.get("link_id_game") or "Unknown")[:22]
                print(f"| {i+1:<4} | {uname:<15} | {pkg:<15} | {stat:<10} | {game:<22} |")
        print(Fore.CYAN + "----------------------------------------------------------------------------------")

    @staticmethod
    def select_games():
        print(Fore.CYAN + "===========SELECT GAMES===========")
        print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Blox fruits")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Sailor Piece")
        print(f"{Fore.GREEN}[3]{Style.RESET_ALL} King Legacy")
        print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Bee Swarm simulator")
        print(f"{Fore.GREEN}[5]{Style.RESET_ALL} Pet simulator 99")
        print(f"{Fore.GREEN}[6]{Style.RESET_ALL} Attack on Titan Revolution")
        print(f"{Fore.GREEN}[7]{Style.RESET_ALL} Grow a garden 2")
        print(f"{Fore.GREEN}[8]{Style.RESET_ALL} Steal An Egg")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Other game or private sv")


# =====================================================================
# Config Manager
# =====================================================================

class ConfigManager:
    def __init__(self, work_dir="Wuyx"):
        self.work_dir = work_dir
        self.config_file = os.path.join(self.work_dir, "config.json")
        self.cookie_file = os.path.join(self.work_dir, "cookie.txt")
        self.blox_fruit_file = os.path.join(self.work_dir, "blox_fruit.json")
        self.acc_changed_dir = os.path.join(self.work_dir, "acc_changed")

    def init_work_space(self):
        try:
            os.makedirs(self.work_dir, exist_ok=True)
            if not os.path.exists(self.config_file):
                self.save_config(self.config_file, self.default_config())
            else:
                self.patch_missing_keys()
            if not os.path.exists(self.cookie_file):
                open(self.cookie_file, 'w', encoding='utf-8').close()
            if not os.path.exists(self.blox_fruit_file):
                self.save_config(self.blox_fruit_file, self.config_bf())
            if not os.path.exists(self.acc_changed_dir):
                os.makedirs(self.acc_changed_dir, exist_ok=True)
        except Exception as e:
            print(Fore.RED + f"[!] Error init_work_space: {e}")

    def default_config(self):
        return {
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
            "auto_bypass": "delta",
            "auto_clear_cache": False,
            "fps_counter": {
                "trigger": 10,
                "completed": 60
            },
            "auto_hwid_delta": False,
            "auto_send_acc_to_solver_captcha": False,
            "auto_send_acc_to_solver_faceid": False,
            "third_party_solve_capcha_url": "",
            "faceid_&_captcha_lock_solve_url": "",
            "zeropoint_apikey": "",
            "zeropoint_priority": False,
            "delay_open_tab": 5,
            "rejoin_interval": 30,
            "offline_wait": 10,
            "max_retries": 3,
            "retry_delay": 5,
            "check_interval": 5,
            "check_ui_delay": 3,
            "rejoin_timeout": 60,
            "tabs": {},
            "discord_webhook": {
                "running": False,
                "webhook_url": "",
                "device_name": "",
                "webhook_interval": 60
            }
        }

    def tab_object(self, package, user_name="", user_id="", link_id_game="", enabled=True):
        return {
            "package": package,
            "user_name": user_name,
            "user_id": user_id,
            "link_id_game": link_id_game,
            "enabled": enabled
        }

    def config_bf(self):
        return {
            "Level": 2800,
            "Beli": 0,
            "Fragments": 0,
            "Godhuman": False,
            "Cursed Dual Katana": False,
            "Hallow Scythe": False,
            "Mirror Fractal": False,
            "Valkyrie Helm": False,
            "Soul Guitar": False,
            "True Triple Katana": False,
            "Shark Anchor": False
        }

    def load_config(self, config_file=None):
        target = config_file or self.config_file
        if os.path.exists(target):
            try:
                with open(target, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.default_config()

    def save_config(self, config_file, data):
        target = config_file or self.config_file
        try:
            with open(target, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(Fore.RED + f"[!] Error save_config: {e}")

    def compare_keys(self, file_config, default, path=None):
        if path is None:
            path = []
        missing = []
        if isinstance(default, dict):
            for k, v in default.items():
                cur = path + [k]
                if not isinstance(file_config, dict) or k not in file_config:
                    missing.append(cur)
                elif isinstance(v, dict):
                    missing.extend(self.compare_keys(file_config[k], v, cur))
        return missing

    def _apply_patch(self, target, source):
        if not isinstance(target, dict) or not isinstance(source, dict):
            return
        for k, v in source.items():
            if k not in target:
                target[k] = v
            elif isinstance(v, dict):
                self._apply_patch(target[k], v)

    def patch_missing_keys(self, auto_save=True):
        if not os.path.exists(self.config_file):
            return
        cfg = self.load_config()
        def_cfg = self.default_config()
        missing = self.compare_keys(cfg, def_cfg)
        if missing:
            self._apply_patch(cfg, def_cfg)
            if auto_save:
                self.save_config(self.config_file, cfg)

    def sync_fps_config(self, trigger=10, completed=60):
        workspace_dirs = set()
        workspace_dirs.update(glob.glob('/sdcard/*/Workspace'))
        workspace_dirs.update(glob.glob('/sdcard/Android/data/*/*/*/*/Workspace'))
        synced = 0
        for w_dir in workspace_dirs:
            wuyx_dir = os.path.join(w_dir, 'Wuyx')
            try:
                os.makedirs(wuyx_dir, exist_ok=True)
                cfg_path = os.path.join(wuyx_dir, 'config.json')
                data = {}
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except Exception:
                        data = {}
                data['fps_counter'] = {'trigger': trigger, 'completed': completed}
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                synced += 1
            except Exception:
                pass
        return synced


# =====================================================================
# Package Manager (Android / ADB / App Cloner)
# =====================================================================

class PackageManager:
    def __init__(self):
        pass

    def auto_clean_missing_packages(self, config=None):
        if config is None:
            return
        tabs = config.get("tabs", {})
        removed = []
        for pkg in list(tabs.keys()):
            p1 = f"/sdcard/Android/data/{pkg}"
            p2 = f"/data/data/{pkg}"
            if not os.path.exists(p1) and not os.path.exists(p2):
                tabs.pop(pkg, None)
                removed.append(pkg)
        return removed

    def get_packages(self):
        try:
            res = subprocess.run(['pm', 'list', 'packages', '-3'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                pkgs = []
                for line in res.stdout.splitlines():
                    if line.startswith('package:'):
                        pkgs.append(line.replace('package:', '').strip())
                return sorted(pkgs)
        except Exception:
            pass
        return []

    def get_roblox_hwid(self, package):
        try:
            cmd = f'su -c "grep \'package=\\"{package}\\"\' /data/system/users/0/settings_ssaid.xml"'
            res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            m = re.search(r'value="([^"]*)"', res.stdout)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None

    def scan_roblox(self):
        print(Fore.CYAN + "Scanning for Roblox clones...")
        clones = []
        try:
            res = subprocess.run(['pm', 'list', 'package', '-f'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if 'package:' in line:
                        parts = line.split('=')
                        if len(parts) >= 2:
                            pkg_name = parts[-1].strip()
                            apk_dir = os.path.dirname(parts[0].replace('package:', '').strip())
                            chk = subprocess.run(f"find {apk_dir} -type f -name '*Roblox*.so' -o -name '*roblox*.so' 2>/dev/null",
                                                 shell=True, stdout=subprocess.PIPE, text=True)
                            if chk.stdout.strip():
                                clones.append(pkg_name)
        except Exception as e:
            print(Fore.RED + f"[!] Error scan_roblox: {e}")
        return sorted(list(set(clones)))

    def launch_roblox(self, package, link=None):
        try:
            if link:
                subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', link, '-p', package],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['am', 'start', '-n', f"{package}/com.roblox.client.startup.ActivitySplash"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def kill_roblox_process(self, package):
        try:
            subprocess.run(['pkill', '-9', '-f', package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run('stty sane 2>/dev/null || true', shell=True)
        except Exception:
            pass

    def _spinner_worker(self, stop_event, message):
        frames = ['|', '/', '-', '\\']
        i = 0
        while not stop_event.is_set():
            frame = frames[i % len(frames)]
            print(f"\r{Fore.CYAN}{frame} {message}{Style.RESET_ALL}", end="", flush=True)
            time.sleep(0.1)
            i += 1
        print("\r" + " " * (len(message) + 15) + "\r", end="", flush=True)

    def monkey_swipe_focus(self, package):
        try:
            subprocess.run(f"export PATH=$PATH:/system/bin && monkey -p {package} --pct-touch 0 --pct-motion 100 --ignore-crashes --ignore-timeouts 1",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def safe_kill_with_focus(self, target_package, all_packages, focus_delay=1):
        self.kill_roblox_process(target_package)
        time.sleep(focus_delay)
        others = [p for p in all_packages if p != target_package]
        for p in others:
            self.monkey_swipe_focus(p)
            time.sleep(0.5)

    def fast_restore_tab(self, package):
        try:
            subprocess.run(['monkey', '-p', package, '-c', 'android.intent.category.LAUNCHER', '1'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self.launch_roblox(package)

    def fast_restore_all(self, tabs):
        for pkg, tab in tabs.items():
            if isinstance(tab, dict) and tab.get("enabled", True):
                self.fast_restore_tab(pkg)
                time.sleep(1)

    def set_oom(self, pid):
        try:
            with open(f"/proc/{pid}/oom_score_adj", "w") as f:
                f.write("-500")
        except Exception:
            pass

    def clear_cache(self, package):
        path = f"/data/data/{package}/cache"
        try:
            if os.path.exists(path):
                subprocess.run(f"rm -rf '{path}'", shell=True)
                print(Fore.GREEN + f"[+] Cache cleared for {package}")
            else:
                print(Fore.YELLOW + f"[~] No cache found for {package}")
        except Exception as e:
            print(Fore.RED + f"[!] Failed to clear cache: {e}")

    def change_android_id(self, new_id=None):
        target_id = new_id or secrets.token_hex(8)
        try:
            subprocess.run(f"settings put secure android_id {target_id}", shell=True)
            return target_id
        except Exception:
            return None

    def get_android_id(self):
        try:
            res = subprocess.run("settings get secure android_id", shell=True, stdout=subprocess.PIPE, text=True)
            return res.stdout.strip()
        except Exception:
            return None

    def get_pid(self, package):
        try:
            res = subprocess.run(f"pidof {package}", shell=True, stdout=subprocess.PIPE, text=True)
            pids = res.stdout.strip().split()
            return int(pids[0]) if pids else None
        except Exception:
            return None

    def get_ram(self, package):
        pid = self.get_pid(package)
        if pid and psutil:
            try:
                p = psutil.Process(pid)
                return round(p.memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass
        return 0.0

    def get_cpu(self, package):
        pid = self.get_pid(package)
        if pid and psutil:
            try:
                p = psutil.Process(pid)
                return p.cpu_percent(interval=0.1)
            except Exception:
                pass
        return 0.0

    def device_name(self):
        try:
            res = subprocess.run("getprop ro.product.model", shell=True, stdout=subprocess.PIPE, text=True)
            val = res.stdout.strip()
            return val if val else "Android phone"
        except Exception:
            return "Android phone"

    def _get_screen_size(self):
        try:
            res = subprocess.run("/system/bin/wm size", shell=True, stdout=subprocess.PIPE, text=True)
            m = re.search(r'(\d+)x(\d+)', res.stdout)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception as e:
            print(Fore.RED + f"[!] Error get screen size: {e}")
        return 1080, 2400

    def _build_window_xml(self, coords):
        if isinstance(coords, (list, tuple)) and len(coords) >= 4:
            l, t, r, b = coords[:4]
            d = {
                "app_cloner_current_window_left": l,
                "app_cloner_current_window_top": t,
                "app_cloner_current_window_right": r,
                "app_cloner_current_window_bottom": b,
                "app_cloner_minimized_point_x": l,
                "app_cloner_minimized_point_y": t,
            }
        elif isinstance(coords, dict):
            d = coords
        else:
            d = {}
        lines = ["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>", "<map>"]
        for key, val in d.items():
            lines.append(f'    <int name="{key}" value="{val}" />')
        lines.append("</map>")
        return "\n".join(lines)

    def _slots_per_cell(self, num_tabs, num_cells):
        if num_cells <= 0:
            return []
        base = num_tabs // num_cells
        extra = num_tabs % num_cells
        return [base + (1 if i < extra else 0) for i in range(num_cells)]

    def _build_positions(self, allowed_cells, cell_w, cell_h, slots_per_cell):
        import math
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

    def _write_window_coords(self, package, coords):
        pref_file = f"/data/data/{package}/shared_prefs/{package}_preferences.xml"
        try:
            l, t, r, b = coords
            xml_patch = f"""    <int name="app_cloner_current_window_left" value="{l}" />
    <int name="app_cloner_current_window_top" value="{t}" />
    <int name="app_cloner_current_window_right" value="{r}" />
    <int name="app_cloner_current_window_bottom" value="{b}" />
    <int name="app_cloner_minimized_point_x" value="{l}" />
    <int name="app_cloner_minimized_point_y" value="{t}" />
"""
            cmd = f'su -c "cat \'{pref_file}\'"'
            res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            if res.returncode == 0 and '<map>' in res.stdout:
                content = re.sub(r'<int name="app_cloner_.*?" value=".*?" />\s*', '', res.stdout)
                content = content.replace('</map>', xml_patch + '</map>')
                escaped = content.replace('"', '\\"').replace('$', '\\$')
                subprocess.run(f'su -c "echo \\"{escaped}\\" > \'{pref_file}\'"', shell=True)
        except Exception as e:
            print(Fore.RED + f"[!] Error writing coords for {package}: {e}")

    def arrange_clone_windows(self, packages, full=False):
        w, h = self._get_screen_size()
        n = len(packages)
        if n == 0:
            return
        if full or n == 1:
            for pkg in packages:
                self._write_window_coords(pkg, (0, 0, w, h))
            return

        cols = 2 if n <= 4 else 3
        rows = (n + cols - 1) // cols
        cell_w = w // cols
        cell_h = h // rows

        for idx, pkg in enumerate(packages):
            col = idx % cols
            row = idx // cols
            left = col * cell_w
            top = row * cell_h
            right = left + cell_w
            bottom = top + cell_h
            self._write_window_coords(pkg, (left, top, right, bottom))

    def arrange_clone_windows_full(self, packages):
        self.arrange_clone_windows(packages, full=True)

    def arrange_clone_windows_auto(self, packages, mode="grid"):
        if mode == "full":
            self.arrange_clone_windows_full(packages)
        else:
            self.arrange_clone_windows(packages, full=False)


# =====================================================================
# Account & Cookie Manager
# =====================================================================

class AccountManager:
    def __init__(self):
        self.session = requests.Session() if requests else None

    def genlink_delta(self, hwid):
        if not requests:
            return None
        url = "https://api.wuyxtool.online/bypass"
        try:
            resp = requests.post(url, json={"hwid": hwid, "api_key": SERVICE_API_KEY}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    return data.get("result")
        except Exception:
            pass
        return None

    def get_hwid_delta(self, package):
        patterns = [
            f"/sdcard/*/Workspace/Wuyx/Internals/Cache/license",
            f"/sdcard/Android/data/*/*/*/*/Workspace/Wuyx/Internals/Cache/license",
            f"/sdcard/*/Workspace/Wuyx/.hwid.txt",
            f"/sdcard/Android/data/*/*/*/*/Workspace/Wuyx/.hwid.txt"
        ]
        for pat in patterns:
            for fpath in glob.glob(pat):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                        m = re.search(r'[0-9a-f]{64}', text)
                        if m:
                            return m.group(0)
                except Exception:
                    pass
        return None

    def obf_license_delta(self, key, hwid):
        if not re.match(r'FREE_[0-9a-fA-F]{32}', key):
            raise ValueError(f"ms: key must match FREE_<32hex>, got: {key}")
        if not re.match(r'[0-9a-f]{64}', hwid):
            raise ValueError(f"ms: hwid must be 64 hex chars, got length {len(hwid)}")
        return True

    def submit_delta_key(self, package, key):
        paths = [
            f"/sdcard/Delta/Internals/Cache/license",
            f"/sdcard/Android/data/{package}/Internals/Cache/license"
        ]
        for p in paths:
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(key)
            except Exception:
                pass

    def is_delta_waiting_key(self, package):
        p = f"/sdcard/Delta/Internals/Cache/license"
        if os.path.exists(p):
            try:
                return os.path.getsize(p) == 0
            except Exception:
                return True
        return True

    def autoexecute(self, package, script):
        dirs = set()
        dirs.update(glob.glob('/sdcard/*/Autoexec*'))
        dirs.update(glob.glob('/sdcard/*/*/Autoexec*'))
        dirs.update(glob.glob(f'/sdcard/Android/data/{package}/*/*/*/Autoexec*'))
        for d in dirs:
            try:
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, 'script.lua'), 'w', encoding='utf-8') as f:
                    f.write(script)
            except Exception:
                pass

    def get_universe_id(self, place_id):
        if not requests:
            return None
        url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json().get("universeId")
        except Exception:
            pass
        return None

    def sync_account_info(self, package):
        path = f"/data/data/{package}/files/appData/LocalStorage/appStorage.json"
        try:
            cmd = f"cd /data/data/{package}/files/appData/LocalStorage/ && cat appStorage.json"
            res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                uid = data.get("UserId")
                uname = data.get("Username")
                return uid, uname
        except Exception:
            pass
        return None, None

    def get_game_name(self, universe_id):
        if not requests or not universe_id:
            return "Unknown"
        url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0].get("name", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def is_svv_link(self, link):
        return bool(link and ('roblox.com/share' in link and 'type=Server' in link))

    def extract_place_id(self, link):
        if not link:
            return None
        m = re.search(r'placeID=(\d+)', link)
        if m:
            return m.group(1)
        m = re.search(r'roblox\.com/games/(\d+)', link)
        if m:
            return m.group(1)
        if link.isdigit():
            return link
        return None

    def get_id_link_game(self, id_link):
        if not id_link:
            return ""
        s = str(id_link).strip()
        if s.isdigit():
            return s
        if 'roblox.com' in s or 'roblox://placeID=' in s:
            pid = self.extract_place_id(s)
            if pid:
                return pid
        return s

    def get_uid_from_cookie(self, cookie):
        if not requests or not cookie:
            return None, "Unknown"
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        try:
            r = requests.get('https://users.roblox.com/v1/users/authenticated', headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get('id'), data.get('name')
        except Exception:
            pass
        return None, "Unknown"

    def get_uid_from_username(self, username):
        if not requests or not username:
            return None
        try:
            payload = {"usernames": [username], "excludeBannedUsers": False}
            r = requests.post("https://users.roblox.com/v1/usernames/users", json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0].get("id")
        except Exception:
            pass
        return None

    def solve_capcha(self, solver_urls, cookie, username=""):
        if not requests or not solver_urls:
            return False
        urls = [solver_urls] if isinstance(solver_urls, str) else solver_urls
        for u in urls:
            try:
                r = requests.post(u, json={"cookie": cookie, "username": username}, timeout=30)
                if r.status_code in (200, 302):
                    return True
            except Exception:
                pass
        return False

    def solver_faceid(self, apikey, priority, cookie):
        if not requests or not apikey:
            return False
        url = "https://zeropoint.to/api/faceunlock-api/submit"
        headers = {
            "X-API-Key": apikey,
            "Content-Type": "application/json"
        }
        payload = {
            "accounts": [cookie],
            "priority": priority
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                return r.json().get("success", False)
        except Exception:
            pass
        return False

    def solver_faceid_url(self, solver_urls, cookie):
        if not requests or not solver_urls:
            return False
        urls = [solver_urls] if isinstance(solver_urls, str) else solver_urls
        for u in urls:
            try:
                r = requests.post(u, json={"cookie": cookie}, timeout=30)
                if r.status_code in (200, 302):
                    return True
            except Exception:
                pass
        return False

    def check_cookie(self, cookie):
        if not requests or not cookie:
            return "dead"
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'Accept': 'application/json',
            'Referer': 'https://www.roblox.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        try:
            r = requests.get('https://users.roblox.com/v1/users/authenticated', headers=headers, timeout=10)
            if r.status_code == 200:
                return "alive"
            if r.status_code == 401:
                return "dead"
            if r.status_code == 403:
                txt = r.text.lower()
                if 'captcha' in txt:
                    return "captcha"
                if 'face' in txt:
                    return "faceid"
                return "ban"
        except Exception:
            pass
        return "error"

    def get_avatar_url(self, user_id):
        if not requests or not user_id:
            return None
        url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0].get("imageUrl")
        except Exception:
            pass
        return None

    def get_account_created(self, user_id):
        if not requests or not user_id:
            return "Unknown"
        url = f"https://users.roblox.com/v1/users/{user_id}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                created = r.json().get("created", "")
                if created:
                    dt = datetime.strptime(created[:10], "%Y-%m-%d")
                    return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
        return "Unknown"

    def get_username_api(self, user_id):
        if not requests or not user_id:
            return "Unknown"
        url = f"https://users.roblox.com/v1/users/{user_id}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json().get("name", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def get_file_hb(self, package):
        patterns = [
            f"/sdcard/*/Workspace/Wuyx/cc3m",
            f"/sdcard/*/*/Workspace/Wuyx/cc3m",
            f"/sdcard/Android/data/{package}/*/*/*/Workspace/Wuyx/cc3m"
        ]
        for pat in patterns:
            for fpath in glob.glob(pat):
                if os.path.exists(fpath):
                    return fpath
        return None

    def clear_old_hb_files(self):
        patterns = [
            "/sdcard/*/Workspace/Wuyx/cc3m",
            "/sdcard/*/*/Workspace/Wuyx/cc3m",
            "/sdcard/Android/data/*/*/*/*/Workspace/Wuyx/cc3m"
        ]
        for pat in patterns:
            for fpath in glob.glob(pat):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    def check_status(self, user_id, cookie=None):
        if not requests or not user_id:
            return "Offline"
        url = "https://presence.roblox.com/v1/presence/users"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if cookie:
            headers['Cookie'] = f'.ROBLOSECURITY={cookie}'
        try:
            r = requests.post(url, headers=headers, json={"userIds": [int(user_id)]}, timeout=10)
            if r.status_code == 200:
                presences = r.json().get("userPresences", [])
                if presences:
                    p_type = presences[0].get("userPresenceType", 0)
                    if p_type == 2:
                        return "Ingame"
                    elif p_type in (1, 3):
                        return "Online"
        except Exception:
            pass
        return "Offline"

    def get_cookie(self, db_path):
        if not os.path.exists(db_path):
            return None
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT value FROM cookies WHERE name = '.ROBLOSECURITY'")
            row = c.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def write_cookie(self, db_path, cookie_value):
        if not os.path.exists(db_path):
            return "no_file"
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM cookies WHERE name = '.ROBLOSECURITY'")
            exists = c.fetchone()[0] > 0
            now_time = int(time.time())

            if exists:
                c.execute("UPDATE cookies SET value = ?, last_access_utc = ? WHERE name = '.ROBLOSECURITY'",
                          (cookie_value, now_time))
                conn.commit()
                conn.close()
                return "updated"
            else:
                c.execute("PRAGMA table_info(cookies)")
                cols = [row[1] for row in c.fetchall()]
                ins_cols = ["creation_utc", "host_key", "top_frame_site_key", "name", "value", "path", "expires_utc",
                            "is_secure", "is_httponly", "last_access_utc", "has_expires", "is_persistent", "priority",
                            "samesite", "source_scheme", "source_port", "source_type", "is_same_party", "has_cross_site_ancestor"]
                valid_cols = [col for col in ins_cols if col in cols]
                val_map = {
                    "creation_utc": now_time,
                    "host_key": ".roblox.com",
                    "top_frame_site_key": "",
                    "name": ".ROBLOSECURITY",
                    "value": cookie_value,
                    "path": "/",
                    "expires_utc": now_time + 31536000,
                    "is_secure": 1,
                    "is_httponly": 1,
                    "last_access_utc": now_time,
                    "has_expires": 1,
                    "is_persistent": 1,
                    "priority": 1,
                    "samesite": -1,
                    "source_scheme": 2,
                    "source_port": 443,
                    "source_type": 0,
                    "is_same_party": 0,
                    "has_cross_site_ancestor": 0
                }
                col_names = ", ".join(valid_cols)
                placeholders = ", ".join(["?" for _ in valid_cols])
                vals = [val_map.get(col, 0) for col in valid_cols]
                c.execute(f"INSERT INTO cookies ({col_names}) VALUES ({placeholders})", vals)
                conn.commit()
                conn.close()
                return "inserted"
        except Exception as e:
            return f"error: {e}"

    def get_blocked_users(self, cookie):
        if not requests or not cookie:
            return []
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
        csrf = None
        try:
            r = requests.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
            csrf = r.headers.get("x-csrf-token")
        except Exception:
            pass
        if csrf:
            headers['X-CSRF-TOKEN'] = csrf

        try:
            r = requests.get("https://apis.roblox.com/user-blocking-api/v1/users/get-blocked-users?count=100", headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("blockedUsers", [])
        except Exception:
            pass
        return []

    def block_user(self, cookie, user_id):
        if not requests or not cookie or not user_id:
            return False
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        csrf = None
        try:
            r = requests.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
            csrf = r.headers.get("x-csrf-token")
        except Exception:
            pass
        if csrf:
            headers['X-CSRF-TOKEN'] = csrf

        try:
            url = f"https://apis.roblox.com/user-blocking-api/v1/users/{user_id}/block-user"
            r = requests.post(url, headers=headers, json={}, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def unwarn(self, cookie):
        if not requests or not cookie:
            return False
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        csrf = None
        try:
            r = requests.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
            csrf = r.headers.get("x-csrf-token")
        except Exception:
            pass
        if csrf:
            headers['X-CSRF-TOKEN'] = csrf

        try:
            r = requests.post("https://usermoderation.roblox.com/v1/not-approved/reactivate", headers=headers, json={}, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def check_existing_vip_server(self, cookie, universe_id):
        if not requests or not cookie or not universe_id:
            return None
        headers = {'Cookie': f'.ROBLOSECURITY={cookie}', 'Accept': 'application/json'}
        try:
            r = requests.get(f"https://games.roblox.com/v1/games/{universe_id}/private-servers?limit=100", headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                uid, _ = self.get_uid_from_cookie(cookie)
                for sv in data:
                    if sv.get("owner", {}).get("id") == uid:
                        return sv.get("vipServerId")
        except Exception:
            pass
        return None

    def buy_free_vip_server(self, cookie, universe_id, server_name="Auto Free Server"):
        if not requests or not cookie or not universe_id:
            return False
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        csrf = None
        try:
            r = requests.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
            csrf = r.headers.get("x-csrf-token")
        except Exception:
            pass
        if csrf:
            headers['X-CSRF-TOKEN'] = csrf

        try:
            url = f"https://games.roblox.com/v1/games/vip-servers/{universe_id}"
            payload = {"name": server_name, "expectedPrice": 0}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def activate_and_get_vip_link(self, cookie, vip_id, place_id):
        if not requests or not cookie or not vip_id:
            return None
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        csrf = None
        try:
            r = requests.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
            csrf = r.headers.get("x-csrf-token")
        except Exception:
            pass
        if csrf:
            headers['X-CSRF-TOKEN'] = csrf

        try:
            url = f"https://games.roblox.com/v1/vip-servers/{vip_id}"
            payload = {"active": True, "newJoinCode": True}
            r = requests.patch(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                join_code = data.get("joinCode") or data.get("link")
                if join_code:
                    return f"roblox://placeID={place_id}&linkCode={join_code}"
        except Exception:
            pass
        return None

    def setup_free_vip_server(self, cookie, place_id):
        uid = self.get_universe_id(place_id)
        if not uid:
            return None
        vip_id = self.check_existing_vip_server(cookie, uid)
        if not vip_id:
            if self.buy_free_vip_server(cookie, uid):
                vip_id = self.check_existing_vip_server(cookie, uid)
        if vip_id:
            return self.activate_and_get_vip_link(cookie, vip_id, place_id)
        return None


# =====================================================================
# Webhook Manager
# =====================================================================

class WebhookManager:
    def __init__(self, config_manager=None, pkg_manager=None, acc_manager=None):
        self.config_manager = config_manager or ConfigManager()
        self.pkg_manager = pkg_manager or PackageManager()
        self.acc_manager = acc_manager or AccountManager()
        self._webhook_thread = None
        self._stop_event = threading.Event()

    def get_tab_status(self, tabs):
        lines = []
        for pkg, tab in tabs.items():
            if not isinstance(tab, dict) or not tab.get("enabled", True):
                continue
            uname = tab.get("user_name") or "Unknown"
            pid = self.pkg_manager.get_pid(pkg)
            if pid:
                ram = self.pkg_manager.get_ram(pkg)
                cpu = self.pkg_manager.get_cpu(pkg)
                lines.append(f"**{uname}**.🟢 ||{pkg}||\n   L🛠️ PID: `{pid}` | 💾 {ram} MB | ⚙️ {cpu}%")
            else:
                lines.append(f"**{uname}**.🔴 ||{pkg}||: Offline\n   L🛠️ PID: `N/A` | 💾 0.0 MB | ⚙️ 0.0%")
        return "\n".join(lines) if lines else "No active tabs"

    def setup_webhook(self, webhook_url, device_name, interval=60):
        cfg = self.config_manager.load_config()
        cfg.setdefault("discord_webhook", {})
        cfg["discord_webhook"]["webhook_url"] = webhook_url
        cfg["discord_webhook"]["device_name"] = device_name
        cfg["discord_webhook"]["webhook_interval"] = interval
        self.config_manager.save_config(self.config_manager.config_file, cfg)

    def _set_running_config(self, state):
        cfg = self.config_manager.load_config()
        cfg.setdefault("discord_webhook", {})
        cfg["discord_webhook"]["running"] = state
        self.config_manager.save_config(self.config_manager.config_file, cfg)

    def send_webhook(self):
        start_time = time.time()
        while not self._stop_event.is_set():
            cfg = self.config_manager.load_config()
            wh_cfg = cfg.get("discord_webhook", {})
            wh_url = wh_cfg.get("webhook_url")
            interval = wh_cfg.get("webhook_interval", 60)
            dev_name = wh_cfg.get("device_name") or self.pkg_manager.device_name()

            if requests and wh_url and "discord.com" in wh_url:
                tabs = cfg.get("tabs", {})
                tab_details = self.get_tab_status(tabs)
                uptime_sec = int(time.time() - start_time)
                uptime_str = str(timedelta(seconds=uptime_sec))

                cpu_tot = psutil.cpu_percent() if psutil else 0.0
                mem_tot = psutil.virtual_memory() if psutil else None
                ram_str = f"{round(mem_tot.used / (1024**3), 1)} / {round(mem_tot.total / (1024**3), 1)} GB" if mem_tot else "N/A"

                embed = {
                    "title": f"📱 Device name: {dev_name}",
                    "color": 3447003,
                    "fields": [
                        {"name": "⏱️  Uptime", "value": f"`{uptime_str}`", "inline": True},
                        {"name": "⚙️ Total cpu usage", "value": f"`{cpu_tot}%`", "inline": True},
                        {"name": "💾 Total ram usage", "value": f"`{ram_str}`", "inline": True},
                        {"name": "📊 Application Details", "value": tab_details, "inline": False}
                    ],
                    "author": {
                        "name": "Wuyx Rejoin",
                        "icon_url": "https://cdn.phototourl.com/free/2026-07-04-cf6dd2ca-41e3-4820-a518-b6a9a24edfb6.png"
                    },
                    "footer": {"text": "discord.gg/wuyxtool"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                try:
                    requests.post(wh_url, json={"embeds": [embed]}, timeout=10)
                except Exception as e:
                    print(Fore.RED + f"[!] Webhook send error: {e}")

            for _ in range(max(1, int(interval))):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def send_cookie_rich(self, webhook_url, cookie, account_info=None):
        if not requests or not webhook_url:
            return
        uid = (account_info or {}).get("user_id")
        uname = (account_info or {}).get("user_name")
        display_name = (account_info or {}).get("display_name", uname)
        avatar = (account_info or {}).get("avatar_url") or self.acc_manager.get_avatar_url(uid)
        created = (account_info or {}).get("created_date") or self.acc_manager.get_account_created(uid)

        embed = {
            "title": f"🍪 Cookie — {uname}",
            "color": 3447003,
            "fields": [
                {"name": "👤 Username", "value": f"`{uname}` ({display_name})", "inline": True},
                {"name": "🆔 User ID", "value": f"`{uid}`", "inline": True},
                {"name": "📅 Account Created", "value": f"`{created}`", "inline": True},
                {"name": "🔑 Cookie (.ROBLOSECURITY)", "value": f"```{cookie[:50]}…```", "inline": False}
            ],
            "author": {
                "name": "Wuyx Rejoin",
                "icon_url": "https://cdn.phototourl.com/free/2026-07-04-cf6dd2ca-41e3-4820-a518-b6a9a24edfb6.png"
            },
            "footer": {"text": "discord.gg/wuyxtool"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if avatar:
            embed["thumbnail"] = {"url": avatar}
        try:
            requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass

    def send_event_alert(self, username, event_type, detail="", package=""):
        cfg = self.config_manager.load_config()
        wh_url = cfg.get("discord_webhook", {}).get("webhook_url")
        if not requests or not wh_url:
            return
        color = EVENT_COLORS.get(event_type, 16754070)
        icon = EVENT_ICONS.get(event_type, "⚠️")
        uid = self.acc_manager.get_uid_from_username(username)
        avatar = self.acc_manager.get_avatar_url(uid) if uid else None

        embed = {
            "title": f"{icon} Account Alert | {username or 'Unknown'}",
            "color": color,
            "fields": [
                {"name": "👤 Username", "value": f"`{username}`", "inline": True},
                {"name": "⚠️ Event", "value": f"**{event_type}**", "inline": True},
                {"name": "📦 Package", "value": f"`{package}`", "inline": True},
                {"name": "📝 Details", "value": detail or "N/A", "inline": False}
            ],
            "author": {
                "name": "Wuyx Rejoin",
                "icon_url": "https://cdn.phototourl.com/free/2026-07-04-cf6dd2ca-41e3-4820-a518-b6a9a24edfb6.png"
            },
            "footer": {"text": "discord.gg/wuyxtool"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if avatar:
            embed["thumbnail"] = {"url": avatar}
        try:
            requests.post(wh_url, json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass

    def send_change_acc_alert(self, old_username, new_username, success=True, reason="", pkg=""):
        cfg = self.config_manager.load_config()
        wh_url = cfg.get("discord_webhook", {}).get("webhook_url")
        if not requests or not wh_url:
            return
        color = 65423 if success else 16711770
        title = f"🔄 Change Account | {'✅ Success' if success else '❌ Failed'}"
        old_uid = self.acc_manager.get_uid_from_username(old_username)
        new_uid = self.acc_manager.get_uid_from_username(new_username)
        new_avatar = self.acc_manager.get_avatar_url(new_uid) if new_uid else None

        embed = {
            "title": title,
            "color": color,
            "fields": [
                {"name": "📤 Old Account", "value": f"`{old_username or 'Unknown'}`", "inline": True},
                {"name": "📥 New Account", "value": f"`{new_username or 'Unknown'}`", "inline": True},
                {"name": "🔔 Reason", "value": reason or "N/A", "inline": True},
                {"name": "📦 Package", "value": f"`{pkg}`", "inline": True}
            ],
            "author": {
                "name": "Wuyx Rejoin",
                "icon_url": "https://cdn.phototourl.com/free/2026-07-04-cf6dd2ca-41e3-4820-a518-b6a9a24edfb6.png"
            },
            "footer": {"text": "discord.gg/wuyxtool"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if new_avatar:
            embed["thumbnail"] = {"url": new_avatar}
        try:
            requests.post(wh_url, json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass

    def send_all_cookie(self, webhook_url, all_accounts, all_cookie):
        if not requests or not webhook_url:
            return
        total = len(all_cookie)
        content_lines = []
        for acc in all_accounts:
            content_lines.append(f"Username: {acc.get('user_name', 'Unknown')} | ID: {acc.get('user_id', '')} | Cookie: {acc.get('cookie', '')}")
        file_bytes = "\n".join(content_lines).encode("utf-8")

        embed = {
            "description": f"Successfully extracted **{total}** cookies.",
            "color": 3447003,
            "author": {
                "name": "Wuyx Rejoin",
                "icon_url": "https://cdn.phototourl.com/free/2026-07-04-cf6dd2ca-41e3-4820-a518-b6a9a24edfb6.png"
            },
            "footer": {"text": "discord.gg/wuyxtool"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            files = {
                'payload_json': (None, json.dumps({"embeds": [embed]}), 'application/json'),
                'file': ('all_cookie.txt', io.BytesIO(file_bytes), 'text/plain')
            }
            requests.post(webhook_url, files=files, timeout=15)
        except Exception as e:
            print(Fore.RED + f"[!] Error send cookie: {e}")

    def start_webhook(self):
        if self._webhook_thread and self._webhook_thread.is_alive():
            return
        self._stop_event.clear()
        self._set_running_config(True)
        self._webhook_thread = threading.Thread(target=self.send_webhook, daemon=True)
        self._webhook_thread.start()

    def stop_webhook(self):
        if self._webhook_thread and self._webhook_thread.is_alive():
            self._set_running_config(False)
            self._stop_event.set()
            print(Fore.YELLOW + "[+] Webhook stopped")
        else:
            print(Fore.YELLOW + "[~] Webhook is not running")

    def is_running(self):
        return bool(self._webhook_thread and self._webhook_thread.is_alive())

    def get_or_input_webhook(self, config):
        wh_url = config.get("discord_webhook", {}).get("webhook_url", "")
        if not wh_url or "discord.com" not in wh_url:
            inp = input(Fore.CYAN + "[?] Enter Discord webhook URL: ").strip()
            if "discord.com" in inp:
                config.setdefault("discord_webhook", {})
                config["discord_webhook"]["webhook_url"] = inp
                self.config_manager.save_config(self.config_manager.config_file, config)
                print(Fore.GREEN + "[+] Webhook URL saved to config")
                return inp
            else:
                print(Fore.RED + "[!] Invalid webhook URL")
                return None
        return wh_url


# =====================================================================
# License Manager
# =====================================================================

class LicenseManager:
    def __init__(self):
        self._SECRET_FILE = _SECRET_FILE
        self.license_file = LICENSE_FILE
        self.active_key = None
        self.active_hwid = None
        self._ensure_secret_file()

    def _ensure_secret_file(self):
        try:
            if not os.path.exists(self._SECRET_FILE):
                token = secrets.token_hex(16)
                subprocess.run(f'su -c "mkdir -p \'{os.path.dirname(self._SECRET_FILE)}\' && echo \'{token}\' > \'{self._SECRET_FILE}\'"', shell=True, stderr=subprocess.DEVNULL)
            else:
                res = subprocess.run(f'su -c "cat \'{self._SECRET_FILE}\'"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if not res.stdout.strip():
                    token = secrets.token_hex(16)
                    subprocess.run(f'su -c "echo \'{token}\' > \'{self._SECRET_FILE}\'"', shell=True, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def get_hwid(self):
        try:
            r1 = subprocess.run("settings get secure android_id", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            android_id = r1.stdout.strip()
            r2 = subprocess.run("getprop ro.product.model", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            dev_model = r2.stdout.strip()
            r3 = subprocess.run(f"su -c \"cat '{self._SECRET_FILE}'\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            secret = r3.stdout.strip()
            import hashlib
            raw = f"{android_id}:{dev_model}:{secret}".encode('utf-8')
            return hashlib.sha256(raw).hexdigest()
        except Exception:
            return "0" * 64

    def _aes_encrypt(self, plaintext):
        if not AES:
            return {}
        nonce = os.urandom(12)
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        return {
            "key": base64.b64encode(AES_SECRET_KEY).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(tag).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode()
        }

    def _hybrid_decrypt(self, resp_body):
        if not PKCS1_OAEP or not RSA or not AES:
            return resp_body
        try:
            enc_key = base64.b64decode(resp_body["key"])
            nonce = base64.b64decode(resp_body["nonce"])
            tag = base64.b64decode(resp_body["tag"])
            ciphertext = base64.b64decode(resp_body["ciphertext"])

            priv_key = RSA.import_key(CLIENT_PRIVATE_KEY_PEM)
            rsa_cipher = PKCS1_OAEP.new(priv_key)
            aes_key = rsa_cipher.decrypt(enc_key)

            cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return json.loads(plaintext.decode('utf-8'))
        except Exception:
            return resp_body

    def verify(self, license_key, hwid):
        if not requests:
            return {"status": "ok"}
        payload = {
            "license_key": license_key,
            "hwid": hwid,
            "timestamp": int(time.time()),
            "api_key": SERVICE_API_KEY
        }
        try:
            r = requests.post(LICENSE_SERVER_URL, json=payload, timeout=10)
            if r.status_code == 200:
                body = r.json()
                if "ciphertext" in body:
                    return self._hybrid_decrypt(body)
                return body
            return {"status": "error", "reason": f"http_status_{r.status_code}"}
        except Exception as e:
            return {"status": "error", "reason": f"connection_failed: {e}"}

    def _load_cached_key(self):
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception:
            pass
        return None

    def _save_key(self, key):
        try:
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(key.strip().upper())
        except Exception:
            pass

    def _check_tool_status(self):
        if not requests:
            return True
        headers = {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        try:
            r = requests.get(STATUS_URL, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("run", True)
        except Exception:
            pass
        return True

    def authenticate(self):
        if not self._check_tool_status():
            print(Fore.RED + "[!] Tool is currently offline. Try again later.")
            sys.exit(0)

        hwid = self.get_hwid()
        cached = self._load_cached_key()
        key = cached

        if not key:
            key = input(Fore.CYAN + "[?] Enter license key: ").strip().upper()

        result = self.verify(key, hwid)
        if result.get("status") == "ok":
            self.active_key = key
            self.active_hwid = hwid
            self._save_key(key)
            print(Fore.GREEN + "[+] Activated")
            return True

        reason_msgs = {
            "not_redeemed": "Key has not been redeemed — use /redeem in Discord first.",
            "blacklisted": "Key is blacklisted.",
            "license_expired": "Key has expired.",
            "license_disabled": "Tool is currently disabled or key has been deactivated.",
            "max_hwid_reached": "Key is already bound to another device.",
            "invalid_key": "Invalid key. Please try again after a few minutes"
        }
        reason = result.get("reason", "invalid_key")
        msg = reason_msgs.get(reason, f"Invalid key ({reason}).")
        print(Fore.RED + f"[!] {msg}")
        return False

    def _watchdog_loop(self):
        while True:
            time.sleep(300)
            if not self._check_tool_status():
                print(Fore.RED + "\n[!] Tool disabled by server. Exiting")
                os._exit(0)
            if self.active_key and self.active_hwid:
                res = self.verify(self.active_key, self.active_hwid)
                if res.get("status") != "ok":
                    print(Fore.RED + f"\n[!] License verification failed: {res.get('reason')}. Exiting")
                    os._exit(0)

    def start_watchdog(self):
        t = threading.Thread(target=self._watchdog_loop, daemon=True)
        t.start()


# =====================================================================
# Auto Updater
# =====================================================================

class AutoUpdater:
    def __init__(self):
        self.status_url = STATUS_URL
        self.update_url = UPDATE_URL
        self.update_filename = UPDATE_FILENAME
        self.run_dir = RUN_DIR

    def _get_remote_version(self):
        if not requests:
            return None
        headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache', 'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(self.status_url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json().get("version")
        except Exception:
            pass
        return None

    def _parse_version(self, v_str):
        try:
            return tuple(int(x) for x in re.findall(r'\d+', v_str))
        except Exception:
            return (0,)

    def _is_newer(self, remote, local):
        r_parsed = self._parse_version(remote)
        l_parsed = self._parse_version(local)
        return r_parsed > l_parsed

    def _download_and_save(self):
        if not requests:
            return None
        target = os.path.join(self.run_dir, self.update_filename)
        headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache', 'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(self.update_url, headers=headers, timeout=30)
            if r.status_code == 200:
                os.makedirs(self.run_dir, exist_ok=True)
                with open(target, 'wb') as f:
                    f.write(r.content)
                return target
        except Exception as e:
            print(Fore.RED + f"[!] Update failed: {e}")
        return None

    def _restart(self, target_path):
        print(Fore.GREEN + "[+] Update applied, restarting...")
        cmd = f'su -c "export PATH=$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd \'{self.run_dir}\' && python \'{os.path.basename(target_path)}\'"'
        os.system(cmd)
        sys.exit(0)

    def check_and_update(self):
        remote = self._get_remote_version()
        if not remote:
            return
        if self._is_newer(remote, TOOL_VERSION):
            print(Fore.YELLOW + f"[?] New version available: {remote} (current: {TOOL_VERSION})")
            target = self._download_and_save()
            if target:
                self._restart(target)
            else:
                print(Fore.RED + "[!] Update failed. Exiting.")
                sys.exit(0)


# =====================================================================
# Main Application Controller
# =====================================================================

class main:
    def __init__(self):
        self.work_dir = "Wuyx"
        self.config_manager = ConfigManager(self.work_dir)
        self.config_file = self.config_manager.config_file
        self.cookie_file = self.config_manager.cookie_file
        self.blox_fruit_file = self.config_manager.blox_fruit_file
        self.acc_changed_dir = self.config_manager.acc_changed_dir

        self.pkg_manager = PackageManager()
        self.acc_manager = AccountManager()
        self.webhook_manager = WebhookManager(self.config_manager, self.pkg_manager, self.acc_manager)
        self.license_manager = LicenseManager()
        self.auto_updater = AutoUpdater()

        self.tabs_status = []
        self._kill_lock = threading.Lock()
        self._launch_lock = threading.Lock()
        self._change_acc_lock = threading.Lock()
        self._event_lock = threading.Lock()
        self._switching = set()
        self._change_account_stop = threading.Event()
        self._stop_event = threading.Event()
        self._captcha_tabs = set()
        self._banned_tabs = set()
        self._faceid_tabs = set()
        self._tab_cookies = {}
        self._rejoin_started_at = {}
        self._captcha_sent_time = {}
        self._faceid_sent_time = {}
        self._ingame_check_count = {}
        self._event_sent = {}
        self._disable_delta_bypass = False
        self._all_tabs = {}
        self._delta_key_fetching = set()
        self._oom_started = set()

    def _extract_cookie_from_line(self, line):
        if not line:
            return None
        m = re.search(r'(_\|WARNING:-[^\s;"]+)', line)
        if m:
            return m.group(1)
        clean = line.strip()
        if len(clean) > 50 and ' ' not in clean:
            return clean
        return None

    def _pop_cookie_from_file(self):
        if not os.path.exists(self.cookie_file):
            return None
        with self._change_acc_lock:
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                first_cookie = None
                remaining = []
                for line in lines:
                    c = self._extract_cookie_from_line(line)
                    if c and not first_cookie:
                        first_cookie = c
                    else:
                        remaining.append(line)
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(remaining) + ("\n" if remaining else ""))
                return first_cookie
            except Exception as e:
                print(Fore.RED + f"[!] _pop_cookie_from_file error: {e}")
                return None

    def _write_bf_config_to_workspace(self):
        if not os.path.exists(self.blox_fruit_file):
            print(Fore.YELLOW + "[~] blox_fruit.json not found, skipping")
            return
        try:
            with open(self.blox_fruit_file, 'r', encoding='utf-8') as f:
                bf_data = json.load(f)
            ws_dirs = set()
            ws_dirs.update(glob.glob('/sdcard/*/Workspace'))
            ws_dirs.update(glob.glob('/sdcard/Android/data/*/*/*/*/Workspace'))
            for d in ws_dirs:
                os.makedirs(d, exist_ok=True)
                dest = os.path.join(d, 'blox_fruit.json')
                with open(dest, 'w', encoding='utf-8') as f:
                    json.dump(bf_data, f, indent=4)
                print(Fore.GREEN + f"[+] blox_fruit.json written → {dest}")
        except Exception as e:
            print(Fore.RED + f"[!] Error writing bf config: {e}")

    def _handle_delta_bypass(self, package):
        hwid = self.acc_manager.get_hwid_delta(package)
        if not hwid:
            print(Fore.YELLOW + f" [~] .hwid.txt not found for {package} — cannot encrypt license")
            return False
        key = self.acc_manager.genlink_delta(hwid)
        if key:
            self.acc_manager.submit_delta_key(package, key)
            print(Fore.GREEN + f" [+] Delta key fetched and submitted for {package}")
            return True
        return False

    def _set_status_by_packages(self, pkg, status, game=None):
        for tab in self.tabs_status:
            if tab.get("package") == pkg:
                tab["status"] = status
                if game:
                    tab["game"] = game
                break

    def _kill_and_relaunch_all_tabs(self, tabs):
        for pkg, tab in tabs.items():
            if isinstance(tab, dict) and tab.get("enabled", True):
                self.pkg_manager.kill_roblox_process(pkg)
                time.sleep(1)
                self.pkg_manager.launch_roblox(pkg, tab.get("link_id_game"))
                time.sleep(2)

    def _handle_clear_cache(self, pkg):
        self.pkg_manager.clear_cache(pkg)

    def _notify_event(self, tab_index, username=None, event_type=None, detail=None, package=None, once=False, cooldown=0):
        if isinstance(tab_index, str):
            uname = tab_index
            evt = username or "Event"
            det = event_type or ""
            pkg = detail or ""
            t_idx = 0
        else:
            t_idx = tab_index
            uname = username or "Unknown"
            evt = event_type or "Event"
            det = detail or ""
            pkg = package or ""

        now = time.time()
        with self._event_lock:
            key = f"{t_idx}:{evt}"
            if once and key in self._event_sent:
                return
            if cooldown > 0 and now - self._event_sent.get(key, 0) < cooldown:
                return
            self._event_sent[key] = now

        try:
            self.webhook_manager.send_event_alert(uname, evt, det, pkg)
        except Exception:
            pass

    def _clear_event_state(self, tab_index, event_types=None):
        if isinstance(tab_index, str):
            pkg = tab_index
            self._captcha_tabs.discard(pkg)
            self._faceid_tabs.discard(pkg)
            self._banned_tabs.discard(pkg)
            self._switching.discard(pkg)
        else:
            t_idx = tab_index
            with self._event_lock:
                if event_types is None:
                    keys = [k for k in self._event_sent if k.startswith(f"{t_idx}:")]
                    for k in keys:
                        self._event_sent.pop(k, None)
                else:
                    for et in event_types:
                        self._event_sent.pop(f"{t_idx}:{et}", None)

    def _clear_captcha_events(self, tab_index):
        self._clear_event_state(tab_index, ['Captcha', 'Captcha Sent To Solver', 'Captcha Solver Failed', 'Captcha Solved'])

    def _clear_faceid_events(self, tab_index):
        self._clear_event_state(tab_index, ['FaceID', 'FaceID Sent To Solver', 'FaceID Solver Failed', 'FaceID Solved'])

    def _handle_captcha_state(self, tab, pkg, uname):
        self._captcha_tabs.add(pkg)
        self._set_status_by_packages(pkg, "Captcha")
        self._notify_event(uname, "Captcha", "Captcha challenge detected on tab", pkg)

        cfg = self.config_manager.load_config()
        if cfg.get("auto_close_tab_when_get_capcha"):
            print(Fore.YELLOW + f" [~] {pkg} auto close tab enabled → killing app...")
            self.pkg_manager.kill_roblox_process(pkg)
            return

        solver_urls = cfg.get("third_party_solve_capcha_url")
        cookie = self._tab_cookies.get(pkg)
        if solver_urls and cookie:
            self._notify_event(uname, "Captcha Sent To Solver", "Sent to solver URL", pkg)
            ok = self.acc_manager.solve_capcha(solver_urls, cookie, uname)
            if ok:
                self._notify_event(uname, "Captcha Solved", "Captcha successfully solved", pkg)
                self._captcha_tabs.discard(pkg)
                print(Fore.GREEN + f" [+] {pkg} captcha cleared → killing app and relaunching...")
                self.pkg_manager.kill_roblox_process(pkg)
                time.sleep(2)
                self.pkg_manager.launch_roblox(pkg, tab.get("link_id_game"))
            else:
                self._notify_event(uname, "Captcha Solver Failed", "All captcha solvers failed", pkg)

    def _handle_faceid_state(self, tab, pkg, uname):
        self._faceid_tabs.add(pkg)
        self._set_status_by_packages(pkg, "FaceID")
        self._notify_event(uname, "FaceID", "FaceID lock challenge detected", pkg)

        cfg = self.config_manager.load_config()
        cookie = self._tab_cookies.get(pkg)
        if not cookie:
            return

        zp_key = cfg.get("zeropoint_apikey")
        zp_prio = cfg.get("zeropoint_priority", False)
        urls = cfg.get("faceid_&_captcha_lock_solve_url")

        solved = False
        if zp_key:
            self._notify_event(uname, "FaceID Sent To Solver", "Sent to Zeropoint solver", pkg)
            solved = self.acc_manager.solver_faceid(zp_key, zp_prio, cookie)
        if not solved and urls:
            self._notify_event(uname, "FaceID Sent To Solver", "Sent to URL solver", pkg)
            solved = self.acc_manager.solver_faceid_url(urls, cookie)

        if solved:
            self._notify_event(uname, "FaceID Solved", "FaceID lock successfully solved", pkg)
            self._faceid_tabs.discard(pkg)
            print(Fore.GREEN + f" [+] {pkg} FaceID cleared → killing app and relaunching...")
            self.pkg_manager.kill_roblox_process(pkg)
            time.sleep(2)
            self.pkg_manager.launch_roblox(pkg, tab.get("link_id_game"))
        else:
            self._notify_event(uname, "FaceID Solver Failed", "All FaceID solvers exhausted", pkg)

    def _handle_banned_state(self, tab, pkg, uname):
        self._banned_tabs.add(pkg)
        self._set_status_by_packages(pkg, "Banned")
        self._notify_event(uname, "Banned", "Account ban/warning detected", pkg)

        cookie = self._tab_cookies.get(pkg)
        if cookie and self.acc_manager.unwarn(cookie):
            print(Fore.GREEN + f" [+] {pkg} unwarn successful → resuming rejoin")
            self._notify_event(uname, "Unwarn Success", "Account unwarned successfully", pkg)
            self._banned_tabs.discard(pkg)
            self.pkg_manager.kill_roblox_process(pkg)
            time.sleep(2)
            self.pkg_manager.launch_roblox(pkg, tab.get("link_id_game"))
            return False
        else:
            print(Fore.RED + f" [!] {pkg} unwarn failed → attempting auto change account...")
            self._notify_event(uname, "Unwarn Failed", "Unwarn failed, account disabled", pkg)
            self._swap_account_on_block(pkg, tab, "Banned / Unwarn Failed")
            return True

    def _do_change_account(self, pkg, tab, reason="Blocked"):
        with self._change_acc_lock:
            if pkg in self._switching:
                return False
            self._switching.add(pkg)

        try:
            uname = tab.get("user_name", "Unknown")
            print(Fore.YELLOW + f"[~] [ChangeAcc] {pkg}: {reason} → start change account...")
            self._set_status_by_packages(pkg, "Switching")

            new_cookie = None
            while True:
                candidate = self._pop_cookie_from_file()
                if not candidate:
                    print(Fore.RED + "[!] [ChangeAcc] No cookie left in cookie.txt — stop auto change")
                    self._set_status_by_packages(pkg, "No cookie")
                    self.webhook_manager.send_change_acc_alert(uname, "N/A", False, "No cookies left in cookie.txt", pkg)
                    return False

                print(Fore.CYAN + "[~] [ChangeAcc] Checking cookie...")
                status = self.acc_manager.check_cookie(candidate)
                if status == "alive":
                    print(Fore.GREEN + "[+] [ChangeAcc] Cookie is valid")
                    new_cookie = candidate
                    break
                elif status == "captcha":
                    print(Fore.YELLOW + "[~] [ChangeAcc] Cookie valid but has captcha challenge → accept")
                    new_cookie = candidate
                    break
                elif status == "ban":
                    print(Fore.YELLOW + f"[~] [ChangeAcc] Cookie is banned ({candidate[:15]}...) → attempting unwarn...")
                    if self.acc_manager.unwarn(candidate):
                        print(Fore.GREEN + "[+] [ChangeAcc] Unwarn successful → cookie accepted")
                        new_cookie = candidate
                        break
                    else:
                        print(Fore.RED + "[~] [ChangeAcc] Unwarn failed → skip, try next cookie...")
                else:
                    print(Fore.RED + f"[~] [ChangeAcc] Cookie {status} → skip, try next cookie...")

            old_cookie = self._tab_cookies.get(pkg)
            if old_cookie:
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_uname = re.sub(r'[^\w\-]', '_', uname)
                    bak_file = os.path.join(self.acc_changed_dir, f"{safe_uname}_{ts}.txt")
                    with open(bak_file, 'w', encoding='utf-8') as f:
                        f.write(old_cookie)
                    print(Fore.GREEN + f"[+] [ChangeAcc] Old cookie saved → {bak_file}")
                except Exception as e:
                    print(Fore.RED + f"[~] [ChangeAcc] Cookie backup failed: {e}")

            db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
            w_res = self.acc_manager.write_cookie(db_path, new_cookie)
            if "error" in w_res or w_res == "no_file":
                print(Fore.RED + f"[!] [ChangeAcc] write cookie fail: {w_res}")
                self._set_status_by_packages(pkg, "Write fail")
                return False
            print(Fore.GREEN + f"[+] [ChangeAcc] wrote Cookie ({w_res})")

            new_uid, new_uname = self.acc_manager.get_uid_from_cookie(new_cookie)
            if not new_uid or not new_uname or new_uname == "Unknown":
                print(Fore.RED + "[!] [ChangeAcc] Not found information for new account")
                self._set_status_by_packages(pkg, "API fail")
                return False

            print(Fore.GREEN + f"[+] [ChangeAcc] New account: {new_uname} ({new_uid})")
            self._tab_cookies[pkg] = new_cookie
            tab["user_name"] = new_uname
            tab["user_id"] = new_uid

            cfg = self.config_manager.load_config()
            cfg.setdefault("tabs", {})
            if pkg in cfg["tabs"]:
                cfg["tabs"][pkg]["user_name"] = new_uname
                cfg["tabs"][pkg]["user_id"] = new_uid
                self.config_manager.save_config(self.config_manager.config_file, cfg)

            self.pkg_manager.kill_roblox_process(pkg)
            time.sleep(2)
            self.pkg_manager.launch_roblox(pkg, tab.get("link_id_game"))

            self.webhook_manager.send_change_acc_alert(uname, new_uname, True, reason, pkg)
            print(Fore.GREEN + f"[+] [ChangeAcc] completed: {uname} → {new_uname}")
            self._set_status_by_packages(pkg, "Ingame")
            return True
        finally:
            self._switching.discard(pkg)

    def _change_account_loop(self, tabs, stop_event):
        print(Fore.GREEN + "[+] [ChangeAcc] Watcher thread started")
        while not stop_event.is_set():
            ws_dirs = set()
            ws_dirs.update(glob.glob('/sdcard/*/Workspace'))
            ws_dirs.update(glob.glob('/sdcard/*/*/Workspace'))
            ws_dirs.update(glob.glob('/sdcard/Android/data/*/*/*/*/Workspace'))
            for d in ws_dirs:
                signal_files = glob.glob(os.path.join(d, '*.txt'))
                for sf in signal_files:
                    fname = os.path.basename(sf).lower()
                    if 'change' in fname or 'swap' in fname or 'signal' in fname:
                        try:
                            for pkg, tab in tabs.items():
                                if pkg in sf or tab.get("user_name", "") in sf:
                                    print(Fore.YELLOW + f"[~] [{pkg}] Signal file detected → auto change account triggered")
                                    subprocess.run(f"su -c \"rm -f '{sf}'\"", shell=True)
                                    self._do_change_account(pkg, tab, "Signal File")
                                    break
                        except Exception as e:
                            print(Fore.RED + f"[!] [ChangeAcc] Watcher error: {e}")
            time.sleep(5)
        print(Fore.GREEN + "[+] [ChangeAcc] Watcher thread stopped")

    def _swap_account_on_block(self, tab_index, tab, all_packages=None, reason="Blocked"):
        if isinstance(tab_index, str):
            pkg = tab_index
            t_obj = tab
            rs = all_packages or reason or "Blocked"
        else:
            t_obj = tab if isinstance(tab, dict) else {}
            pkg = t_obj.get("package", "")
            rs = reason
        t = threading.Thread(target=self._do_change_account, args=(pkg, t_obj, rs), daemon=True)
        t.start()

    def event_tracking(self):
        try:
            flag_file = '/sdcard/.w.txt'
            if os.path.exists(flag_file):
                return
            android_id = self.pkg_manager.get_android_id()
            try:
                from logsnag import LogSnag
                logger = LogSnag(token='df0e441f0e4069146d1ec37c42908783', project='wuyx-rejoin-')
                logger.track(channel='user', event='user logging tool', user_id=android_id, icon='🚀', notify=True)
            except Exception:
                pass
            try:
                with open(flag_file, 'w') as f:
                    f.write('1')
            except Exception:
                pass
        except Exception:
            pass

    def _render_status(self):
        cfg = self.config_manager.load_config()
        menu.banner()
        menu.tool_status(cfg)
        menu.status_banner(self.tabs_status)

    def _try_recover_tab(self, tab_index, package, link_id_game, all_packages=None, delay_open_tab=5, user_name="Unknown", use_kill_lock=True):
        if all_packages is None:
            all_packages = [package]
        cfg = self.config_manager.load_config()
        auto_bypass = cfg.get("auto_bypass", {})
        delta_bypass_enabled = auto_bypass.get("delta", False) if isinstance(auto_bypass, dict) else (auto_bypass == "delta")

        if tab_index < len(self.tabs_status):
            self.tabs_status[tab_index]["status"] = "Rejoining"
        print(Fore.YELLOW + f"[~] Recovering tab for package {package} ({user_name})..." + Style.RESET_ALL)

        if use_kill_lock:
            with self._kill_lock:
                self.pkg_manager.safe_kill_with_focus(package, all_packages)
        else:
            self.pkg_manager.safe_kill_with_focus(package, all_packages)

        self._handle_clear_cache(package)

        if delta_bypass_enabled:
            if self.acc_manager.is_delta_waiting_key(package):
                self._handle_delta_bypass(package)

        time.sleep(delay_open_tab)
        with self._launch_lock:
            self.pkg_manager.launch_roblox(package, link_id_game)

    def _wait_and_recover_ingame(self, tab, account_check_method="heartbeat", rejoin_timeout=60, delay_open_tab=5, sequential_join=False, all_packages=None, stop_event=None, status_idx=0, third_party_solve_capcha_url="", check_interval=5, faceid_solver_apikey="", faceid_solver_priority=False, auto_change_acc_captcha=False, faceid_solver_urls=""):
        if all_packages is None:
            all_packages = []
        if stop_event is None:
            stop_event = threading.Event()

        package = tab.get("package", "") if isinstance(tab, dict) else str(tab)
        link_id_game = tab.get("link_id_game", "") if isinstance(tab, dict) else ""
        user_name = tab.get("user_name", "Unknown") if isinstance(tab, dict) else "Unknown"
        deadline = time.time() + rejoin_timeout

        cfg = self.config_manager.load_config()
        auto_bypass = cfg.get("auto_bypass", {})
        delta_bypass_enabled = auto_bypass.get("delta", False) if isinstance(auto_bypass, dict) else (auto_bypass == "delta")

        if delta_bypass_enabled and self.acc_manager.is_delta_waiting_key(package):
            if status_idx < len(self.tabs_status):
                self.tabs_status[status_idx]["status"] = "Fetching Key"
            self._render_status()
            print(Fore.YELLOW + f"[~] Fetching Delta key for {package}..." + Style.RESET_ALL)
            self._delta_key_fetching.add(package)
            self._handle_delta_bypass(package)
            self._delta_key_fetching.discard(package)

        with self._launch_lock:
            self.pkg_manager.launch_roblox(package, link_id_game)

        while not stop_event.is_set():
            if self._is_ingame(tab, account_check_method, sequential_join, delay_open_tab):
                if status_idx < len(self.tabs_status):
                    self.tabs_status[status_idx]["status"] = "Ingame"
                self._render_status()
                return True

            db_path = f"/data/data/{package}/app_webview/Default/Cookies"
            cookie = self._tab_cookies.get(package) or self.acc_manager.get_cookie(db_path)
            if cookie:
                self._tab_cookies[package] = cookie
                ck_status = self.acc_manager.check_cookie(cookie)
                if ck_status == "captcha":
                    if status_idx < len(self.tabs_status):
                        self.tabs_status[status_idx]["status"] = "Captcha"
                    self._captcha_tabs.add(package)
                    self._notify_event(status_idx, user_name, "Captcha", "Captcha detected while joining game", package)
                    if third_party_solve_capcha_url:
                        solved = self.acc_manager.solve_capcha(third_party_solve_capcha_url, cookie, user_name)
                        if solved:
                            self._notify_event(status_idx, user_name, "Captcha Sent To Solver", "Successfully sent account to captcha solver", package)
                            print(Fore.GREEN + f"[+] {package} has captcha -> sent to solver, skipping to next tab" + Style.RESET_ALL)
                        else:
                            self._notify_event(status_idx, user_name, "Captcha Solver Failed", "Failed to send account to captcha solver", package)
                            print(Fore.RED + f"[!] {package} has captcha -> failed to send to solver, skipping to next tab" + Style.RESET_ALL)
                    else:
                        print(Fore.YELLOW + f"[~] {package} has captcha -> skipping to next tab (monitor will keep tracking)" + Style.RESET_ALL)
                    if auto_change_acc_captcha:
                        self._swap_account_on_block(status_idx, tab, all_packages, "captcha")
                    break
                elif ck_status == "ban":
                    if status_idx < len(self.tabs_status):
                        self.tabs_status[status_idx]["status"] = "Banned"
                    self._banned_tabs.add(package)
                    print(Fore.RED + f"[!] {package} is banned -> skipping to next tab" + Style.RESET_ALL)
                    self._notify_event(status_idx, user_name, "Banned", f"Account is banned (`{user_name}`) while joining game", package)
                    self._swap_account_on_block(status_idx, tab, all_packages, "ban")
                    break
                elif ck_status == "faceid":
                    if status_idx < len(self.tabs_status):
                        self.tabs_status[status_idx]["status"] = "FaceID"
                    self._faceid_tabs.add(package)
                    self._notify_event(status_idx, user_name, "FaceID", "FaceID lock detected while joining game", package)
                    any_faceid_sent = False
                    if faceid_solver_apikey:
                        res = self.acc_manager.solver_faceid(faceid_solver_apikey, faceid_solver_priority, cookie)
                        if res:
                            any_faceid_sent = True
                            self._notify_event(status_idx, user_name, "FaceID Sent To Solver", "Successfully sent account to zeropoint FaceID solver", package)
                            print(Fore.GREEN + f"[+] {package} sent to zeropoint FaceID solver" + Style.RESET_ALL)
                    if not any_faceid_sent and faceid_solver_urls:
                        res = self.acc_manager.solver_faceid_url(faceid_solver_urls, cookie)
                        if res:
                            any_faceid_sent = True
                            self._notify_event(status_idx, user_name, "FaceID Sent To Solver", "Successfully sent account to third-party FaceID solver", package)
                            print(Fore.GREEN + f"[+] {package} sent to third-party FaceID solver" + Style.RESET_ALL)
                    if not any_faceid_sent:
                        self._notify_event(status_idx, user_name, "FaceID Solver Failed", "All FaceID solvers exhausted", package)
                        print(Fore.RED + f"[!] {package} FaceID solver failed" + Style.RESET_ALL)
                    break
                elif ck_status == "dead":
                    if status_idx < len(self.tabs_status):
                        self.tabs_status[status_idx]["status"] = "Dead"
                    print(Fore.RED + f"[!] {package} cookie is dead/expired -> skipping to next tab" + Style.RESET_ALL)
                    self._notify_event(status_idx, user_name, "Cookie Dead", "Cookie is dead/expired while joining game", package)
                    break
                elif ck_status == "error":
                    if status_idx < len(self.tabs_status):
                        self.tabs_status[status_idx]["status"] = "Error"
                    print(Fore.YELLOW + f"[~] {package} check_cookie network error -> skipping to next tab" + Style.RESET_ALL)

            if time.time() > deadline:
                print(Fore.YELLOW + f"[~] {package} stuck in restarting {rejoin_timeout}s -> Rejoining" + Style.RESET_ALL)
                if status_idx < len(self.tabs_status):
                    self.tabs_status[status_idx]["status"] = "Joining"
                self._try_recover_tab(status_idx, package, link_id_game, all_packages, delay_open_tab, user_name, use_kill_lock=True)
                deadline = time.time() + rejoin_timeout

            time.sleep(check_interval)
            self._render_status()
        return False

    def _is_ingame(self, tab, account_check_method="heartbeat", sequential_join=False, delay_open_tab=5):
        if isinstance(tab, dict):
            pkg = tab.get("package", "")
            uname = tab.get("user_name", "")
        else:
            pkg = str(tab)
            uname = str(account_check_method)
        hb = self.acc_manager.get_file_hb(uname) or self.acc_manager.get_file_hb(pkg)
        if hb and os.path.exists(hb):
            try:
                if time.time() - os.path.getmtime(hb) < 60:
                    return True
            except Exception:
                pass
        return False

    def _check_cookie_while_ingame(self, tab_index, tab, every=60):
        if isinstance(tab_index, str):
            pkg = tab_index
            t_obj = tab if isinstance(tab, dict) else {}
            idx = 0
        else:
            idx = tab_index
            t_obj = tab if isinstance(tab, dict) else {}
            pkg = t_obj.get("package", "")

        cookie = self._tab_cookies.get(pkg)
        if not cookie:
            db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
            cookie = self.acc_manager.get_cookie(db_path)
            if cookie:
                self._tab_cookies[pkg] = cookie
        if cookie:
            st = self.acc_manager.check_cookie(cookie)
            uname = t_obj.get("user_name", "Unknown")
            if st == "dead":
                self._notify_event(idx, uname, "Cookie Dead", "Cookie is dead/expired", pkg)
                self._swap_account_on_block(idx, t_obj, [pkg], "Cookie Dead")
            elif st == "ban":
                self._handle_banned_state(t_obj, pkg, uname)

    def _start_monitor_thread(self, idx, tab, account_check_method, all_packages, stop_event, check_interval, check_ui_delay, auto_close_tab_when_get_capcha, third_party_solve_capcha_url, rejoin_timeout, delay_open_tab, offline_wait, max_retries, retry_delay, faceid_solver_apikey, faceid_solver_priority, auto_change_acc_captcha, auto_change_acc_faceid, faceid_solver_urls):
        pkg = tab.get("package", "")
        self.acc_manager.autoexecute(pkg, 'loadstring(game:HttpGet("https://raw.githubusercontent.com/g-huy128/Test/refs/heads/main/obfuscated.lua.txt"))()', 'check_onlinne.lua')
        if account_check_method == "heartbeat":
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

    def _tab_monitor_loop(self, tab_index, tab, all_packages=None, offline_wait=60, max_retries=3, retry_delay=5, check_interval=5, stop_event=None, third_party_solve_capcha_url="", auto_close_tab_when_get_capcha=False, delay_open_tab=5, faceid_solver_apikey="", faceid_solver_priority=False, auto_change_acc_captcha=False, auto_change_acc_faceid=False, faceid_solver_urls=""):
        if isinstance(tab_index, str) and isinstance(tab, dict) and hasattr(all_packages, 'is_set'):
            pkg = tab_index
            stop_ev = all_packages
            t_obj = tab
            idx = 0
            all_pkgs = [pkg]
        else:
            idx = tab_index
            t_obj = tab if isinstance(tab, dict) else {}
            pkg = t_obj.get("package", "")
            all_pkgs = all_packages or [pkg]
            stop_ev = stop_event or threading.Event()

        cfg = self.config_manager.load_config()
        rejoin_timeout = cfg.get("rejoin_timeout", 60)
        rejoin_interval = cfg.get("rejoin_interval", 30) * 60
        chk_interval = check_interval or cfg.get("check_interval", 5)

        last_launch = time.time()
        while not stop_ev.is_set():
            uname = t_obj.get("user_name") or "Unknown"
            pid = self.pkg_manager.get_pid(pkg)

            if not pid:
                print(Fore.YELLOW + f"[~] {pkg} process not found → relaunching...")
                self._set_status_by_packages(pkg, "Launching")
                self.pkg_manager.launch_roblox(pkg, t_obj.get("link_id_game"))
                last_launch = time.time()
                time.sleep(3)
                continue

            if cfg.get("auto_bypass") == "delta" and self.acc_manager.is_delta_waiting_key(pkg):
                print(Fore.YELLOW + f"[~] {pkg} Delta key missing — fetching via HWID...")
                self._handle_delta_bypass(pkg)

            if self._is_ingame(pkg, uname):
                self._set_status_by_packages(pkg, "Ingame")
            else:
                if time.time() - last_launch > rejoin_timeout:
                    print(Fore.YELLOW + f"[~] {pkg} rejoin timeout ({rejoin_timeout}s) exceeded without ingame → recovering...")
                    self.pkg_manager.kill_roblox_process(pkg)
                    time.sleep(2)
                    self.pkg_manager.launch_roblox(pkg, t_obj.get("link_id_game"))
                    last_launch = time.time()

            if time.time() - last_launch > rejoin_interval:
                print(Fore.GREEN + f"[+] {pkg} Time is over. Rejoining...")
                self.pkg_manager.kill_roblox_process(pkg)
                time.sleep(2)
                self.pkg_manager.launch_roblox(pkg, t_obj.get("link_id_game"))
                last_launch = time.time()

            time.sleep(chk_interval)

    def _tab_monitor_loop_2(self, tab_index, tab, all_packages=None, stop_event=None, check_interval=5, check_ui_delay=0, auto_close_tab_when_get_capcha=False, third_party_solve_capcha_url="", rejoin_timeout=60, delay_open_tab=5, faceid_solver_apikey="", faceid_solver_priority=False, auto_change_acc_captcha=False, auto_change_acc_faceid=False, faceid_solver_urls=""):
        if stop_event is None:
            stop_event = threading.Event()
        if all_packages is None:
            all_packages = []

        package = tab.get("package") if isinstance(tab, dict) else str(tab)
        link_id_game = tab.get("link_id_game", "") if isinstance(tab, dict) else ""
        user_name = tab.get("user_name", "Unknown") if isinstance(tab, dict) else "Unknown"
        last_online = time.time()

        while not stop_event.is_set():
            try:
                if package in self._switching:
                    time.sleep(check_interval)
                    continue

                pid = self.pkg_manager.get_pid(package)
                hb_file = self.acc_manager.get_file_hb(user_name)

                if not pid:
                    cur_st = self.tabs_status[tab_index]["status"] if tab_index < len(self.tabs_status) else "Offline"
                    if cur_st == "Waiting account":
                        print(Fore.YELLOW + f"[~] {package} stuck in Waiting account -> force kill + relaunch" + Style.RESET_ALL)
                        self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                    elif cur_st == "Rejoining":
                        print(Fore.YELLOW + f"[~] {package} stuck in Rejoining -> force kill + relaunch" + Style.RESET_ALL)
                        self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                    else:
                        if tab_index < len(self.tabs_status):
                            self.tabs_status[tab_index]["status"] = "Offline"
                        db_path = f"/data/data/{package}/app_webview/Default/Cookies"
                        cookie = self._tab_cookies.get(package) or self.acc_manager.get_cookie(db_path)
                        if cookie:
                            self._tab_cookies[package] = cookie
                            ck_status = self.acc_manager.check_cookie(cookie)
                            if ck_status == "captcha":
                                if tab_index < len(self.tabs_status):
                                    self.tabs_status[tab_index]["status"] = "Captcha"
                                self._handle_captcha_state(tab, package, user_name)
                            elif ck_status == "faceid":
                                if tab_index < len(self.tabs_status):
                                    self.tabs_status[tab_index]["status"] = "FaceID"
                                self._handle_faceid_state(tab, package, user_name)
                            elif ck_status == "ban":
                                if tab_index < len(self.tabs_status):
                                    self.tabs_status[tab_index]["status"] = "Banned"
                                self._handle_banned_state(tab, package, user_name)
                            elif ck_status == "dead":
                                if tab_index < len(self.tabs_status):
                                    self.tabs_status[tab_index]["status"] = "Dead"
                                print(Fore.RED + f"[!] {package} cookie is dead/expired" + Style.RESET_ALL)
                                self._notify_event(tab_index, user_name, "Cookie Dead", "Cookie is dead/expired", package)
                            else:
                                print(Fore.RED + f"[!] {package} offline -> Rejoining (timeout: {rejoin_timeout}s)" + Style.RESET_ALL)
                                if tab_index < len(self.tabs_status):
                                    self.tabs_status[tab_index]["status"] = "Rejoining"
                                self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                else:
                    is_online = False
                    if hb_file and os.path.exists(hb_file):
                        try:
                            mtime = os.path.getmtime(hb_file)
                            if time.time() - mtime < 60:
                                is_online = True
                                last_online = time.time()
                        except Exception:
                            pass

                    if is_online:
                        if tab_index < len(self.tabs_status):
                            self.tabs_status[tab_index]["status"] = "Ingame"
                        self._check_cookie_while_ingame(tab_index, tab, every=60)
                    else:
                        elapsed_since_online = time.time() - last_online
                        if elapsed_since_online > rejoin_timeout:
                            print(Fore.YELLOW + f"[~] {package} offline -> Wait {rejoin_timeout:.0f}s to rejoin" + Style.RESET_ALL)
                            if tab_index < len(self.tabs_status):
                                self.tabs_status[tab_index]["status"] = "Rejoining"
                            self._try_recover_tab(tab_index, package, link_id_game, all_packages, delay_open_tab, user_name)
                            last_online = time.time()

            except Exception as e:
                print(Fore.RED + f"[!] Error monitoring {package}: {e}" + Style.RESET_ALL)

            time.sleep(check_interval)

    # -----------------------------------------------------------------
    # Option Handlers (1 - 18)
    # -----------------------------------------------------------------

    def option_1(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        enabled_tabs = {pkg: t for pkg, t in tabs.items() if isinstance(t, dict) and t.get("enabled", True)}

        if not enabled_tabs:
            print(Fore.RED + "[!] No enabled packages found. Please setup in option 2 & 3 first.")
            input("Enter to back...")
            return

        self.tabs_status = []
        for pkg, t in enabled_tabs.items():
            self.tabs_status.append({
                "package": pkg,
                "user_name": t.get("user_name", "Unknown"),
                "status": "Pending",
                "game": t.get("link_id_game", "Unknown")
            })

        if cfg.get("auto_block"):
            print(Fore.GREEN + "[+] Auto block is on, start auto block...")
            for pkg, t in enabled_tabs.items():
                db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                cookie = self.acc_manager.get_cookie(db_path)
                if cookie:
                    blocked = self.acc_manager.get_blocked_users(cookie)
                    print(Fore.CYAN + f" [+] Found {len(blocked)} blocked users for {pkg}")
            print(Fore.GREEN + "[+] Auto block done")

        if cfg.get("auto_buy_svv"):
            print(Fore.GREEN + "[+] Auto buy private server is on, start auto buy...")
            for pkg, t in enabled_tabs.items():
                link = t.get("link_id_game", "")
                if self.acc_manager.is_svv_link(link):
                    print(Fore.CYAN + f" [>] {pkg} already using private link, skipping")
                    continue
                pid = self.acc_manager.extract_place_id(link)
                if pid:
                    db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                    cookie = self.acc_manager.get_cookie(db_path)
                    if cookie:
                        vip_link = self.acc_manager.setup_free_vip_server(cookie, pid)
                        if vip_link:
                            t["link_id_game"] = vip_link
                            print(Fore.GREEN + f" [+] Private created: {vip_link}")
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + "[+] Auto buy private done")

        self.event_tracking()

        if cfg.get("auto_sort_tab"):
            print(Fore.GREEN + "[+] Auto sort tab is on. Start auto sort tab...")
            if cfg.get("auto_sort_tab_full"):
                self.pkg_manager.arrange_clone_windows_full(list(enabled_tabs.keys()))
            else:
                self.pkg_manager.arrange_clone_windows(list(enabled_tabs.keys()))

        if cfg.get("auto_change_acc_bf"):
            script = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/g-huy128/Test/refs/heads/main/bf_change_acc.lua"))()'
            for pkg in enabled_tabs:
                self.acc_manager.autoexecute(pkg, script)

        delay = cfg.get("delay_open_tab", 5)
        check_method = cfg.get("account_check_method", "heartbeat")
        rejoin_timeout = cfg.get("rejoin_timeout", 60)
        check_interval = cfg.get("check_interval", 5)
        check_ui_delay = cfg.get("check_ui_delay", 0)
        auto_close_cap = cfg.get("auto_close_tab_when_get_capcha", False)
        third_party_captcha_url = cfg.get("third_party_solve_capcha_url", "")
        offline_wait = cfg.get("offline_wait", 60)
        max_retries = cfg.get("max_retries", 3)
        retry_delay = cfg.get("retry_delay", 5)
        faceid_key = cfg.get("zeropoint_apikey", "")
        faceid_prio = cfg.get("zeropoint_priority", False)
        auto_change_cap = cfg.get("auto_change_acc_captcha", False)
        auto_change_faceid = cfg.get("auto_change_acc_faceid", False)
        faceid_urls = cfg.get("faceid_&_captcha_lock_solve_url", "")
        sequential_join = cfg.get("sequential_join", False)

        stop_event = threading.Event()

        ca_thread = threading.Thread(target=self._change_account_loop, args=(enabled_tabs, stop_event), daemon=True)
        ca_thread.start()

        monitor_threads = []
        for idx, (pkg, t) in enumerate(enabled_tabs.items()):
            t_copy = dict(t)
            t_copy["package"] = pkg
            if sequential_join:
                self._wait_and_recover_ingame(
                    t_copy,
                    account_check_method=check_method,
                    rejoin_timeout=rejoin_timeout,
                    delay_open_tab=delay,
                    sequential_join=True,
                    all_packages=list(enabled_tabs.keys()),
                    stop_event=stop_event,
                    status_idx=idx,
                    third_party_solve_capcha_url=third_party_captcha_url,
                    check_interval=check_interval,
                    faceid_solver_apikey=faceid_key,
                    faceid_solver_priority=faceid_prio,
                    auto_change_acc_captcha=auto_change_cap,
                    faceid_solver_urls=faceid_urls
                )
            else:
                print(Fore.GREEN + f"[+] Launching game for package {pkg}, delay {delay}s...")
                self._set_status_by_packages(pkg, "Launching")
                self.pkg_manager.launch_roblox(pkg, t.get("link_id_game"))
                time.sleep(delay)

            th = self._start_monitor_thread(
                idx=idx,
                tab=t_copy,
                account_check_method=check_method,
                all_packages=list(enabled_tabs.keys()),
                stop_event=stop_event,
                check_interval=check_interval,
                check_ui_delay=check_ui_delay,
                auto_close_tab_when_get_capcha=auto_close_cap,
                third_party_solve_capcha_url=third_party_captcha_url,
                rejoin_timeout=rejoin_timeout,
                delay_open_tab=delay,
                offline_wait=offline_wait,
                max_retries=max_retries,
                retry_delay=retry_delay,
                faceid_solver_apikey=faceid_key,
                faceid_solver_priority=faceid_prio,
                auto_change_acc_captcha=auto_change_cap,
                auto_change_acc_faceid=auto_change_faceid,
                faceid_solver_urls=faceid_urls
            )
            monitor_threads.append(th)

        print(Fore.GREEN + "[+] Monitoring started\nPress Ctrl+C to stop")
        try:
            while True:
                self._render_status()
                time.sleep(5)
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n[~] Stopping monitors...")
            stop_event.set()
            time.sleep(1)

    def option_2(self):
        pkgs = self.pkg_manager.scan_roblox()
        if not pkgs:
            pkgs = self.pkg_manager.get_packages()
        if not pkgs:
            print(Fore.RED + "[!] No packages found on device")
            input("Enter to back...")
            return

        cfg = self.config_manager.load_config()
        cfg.setdefault("tabs", {})

        while True:
            menu.banner()
            print(Fore.CYAN + "=============== SETUP PACKAGE ===============")
            for i, p in enumerate(pkgs):
                stat = f"{Fore.GREEN}[SELECTED]" if p in cfg["tabs"] else f"{Fore.RED}[NOT SELECTED]"
                print(f"[{i+1}] {p:<30} {stat}")
            print(Fore.CYAN + "---------------------------------------------")
            print(Fore.YELLOW + "Enter package number to toggle (0 to finish): ")
            ch = input().strip()
            if ch == "0":
                break
            if ch.isdigit() and 1 <= int(ch) <= len(pkgs):
                selected = pkgs[int(ch) - 1]
                if selected in cfg["tabs"]:
                    cfg["tabs"].pop(selected, None)
                else:
                    cfg["tabs"][selected] = self.config_manager.tab_object(selected)
                self.config_manager.save_config(self.config_file, cfg)

    def option_3(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        if not tabs:
            print(Fore.RED + "[!] No packages found. Please setup option 2 first")
            input("Enter to back...")
            return

        while True:
            menu.banner()
            print(Fore.CYAN + "=============== SETUP PACKAGE TO RUN ===============")
            pkg_list = list(tabs.keys())
            for i, p in enumerate(pkg_list):
                t = tabs[p]
                en = f"{Fore.GREEN}[ENABLED]" if t.get("enabled", True) else f"{Fore.RED}[DISABLED]"
                uname = t.get("user_name") or "None"
                print(f"[{i+1}] {p:<25} | User: {uname:<15} | {en}")
            print(Fore.CYAN + "----------------------------------------------------")
            print(Fore.YELLOW + "Enter number to toggle enable/disable (0 to finish): ")
            ch = input().strip()
            if ch == "0":
                break
            if ch.isdigit() and 1 <= int(ch) <= len(pkg_list):
                target = pkg_list[int(ch) - 1]
                tabs[target]["enabled"] = not tabs[target].get("enabled", True)
                self.config_manager.save_config(self.config_file, cfg)

    def option_4(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        if not tabs:
            print(Fore.RED + "[!] No packages found. Please setup in option 2 first")
            input("Enter to back...")
            return

        menu.banner()
        menu.select_games()
        print(Fore.CYAN + "---------------------------------------------")
        print(Fore.YELLOW + "[1] Set ID/link for each package")
        print(Fore.YELLOW + "[2] Set ID/link for all packages")
        mode = input(Fore.CYAN + "[?] Choose method (1/2): ").strip()

        if mode == "2":
            g_ch = input(Fore.CYAN + "[?] Enter game number: ").strip()
            if g_ch in [str(x) for x in GAMES_MAP]:
                game_id = GAMES_MAP[int(g_ch)][1]
            elif g_ch == "0":
                game_id = input(Fore.CYAN + "[?] Enter your game ID or private server link: ").strip()
            else:
                print(Fore.RED + "[!] Invalid choice")
                input("Enter to back...")
                return

            for p in tabs:
                tabs[p]["link_id_game"] = game_id
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + f"[+] Set {game_id} for all packages")
            input("Enter to back...")

        elif mode == "1":
            for p in tabs:
                menu.banner()
                menu.select_games()
                g_ch = input(Fore.CYAN + f"[?] Enter game number for {p}: ").strip()
                if g_ch in [str(x) for x in GAMES_MAP]:
                    game_id = GAMES_MAP[int(g_ch)][1]
                elif g_ch == "0":
                    game_id = input(Fore.CYAN + f"[?] Enter game ID or server link for {p}: ").strip()
                else:
                    continue
                tabs[p]["link_id_game"] = game_id
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + "[+] Config saved")
            input("Enter to back...")

    def option_5(self):
        cfg = self.config_manager.load_config()
        wh_cfg = cfg.get("discord_webhook", {})
        while True:
            menu.banner()
            print(Fore.CYAN + "=============== SETUP WEBHOOK ===============")
            print(f"[+] Current URL     : {wh_cfg.get('webhook_url', 'None')}")
            print(f"[+] Device Name     : {wh_cfg.get('device_name', self.pkg_manager.device_name())}")
            print(f"[+] Interval (sec)  : {wh_cfg.get('webhook_interval', 60)}")
            print(f"[+] Status          : {'Running' if self.webhook_manager.is_running() else 'Stopped'}")
            print(Fore.CYAN + "---------------------------------------------")
            print("[1] Change Webhook URL")
            print("[2] Change Device Name")
            print("[3] Change Interval")
            print("[4] Start / Stop Webhook")
            print("[0] Back")
            ch = input(Fore.CYAN + "[?] Enter option: ").strip()

            if ch == "0":
                break
            elif ch == "1":
                url = input(Fore.CYAN + "[?] Enter new Webhook URL: ").strip()
                if "discord.com" in url:
                    wh_cfg["webhook_url"] = url
                    self.config_manager.save_config(self.config_file, cfg)
                    print(Fore.GREEN + "[+] Saved")
            elif ch == "2":
                name = input(Fore.CYAN + "[?] Enter Device Name: ").strip()
                wh_cfg["device_name"] = name
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "3":
                sec = input(Fore.CYAN + "[?] Enter interval seconds: ").strip()
                if sec.isdigit():
                    wh_cfg["webhook_interval"] = int(sec)
                    self.config_manager.save_config(self.config_file, cfg)
            elif ch == "4":
                if self.webhook_manager.is_running():
                    self.webhook_manager.stop_webhook()
                else:
                    self.webhook_manager.start_webhook()
            time.sleep(1)

    def option_6(self):
        dirs = set()
        dirs.update(glob.glob('/sdcard/*/Autoexec*'))
        dirs.update(glob.glob('/sdcard/*/*/Autoexec*'))
        dirs.update(glob.glob('/sdcard/Android/data/*/*/*/*/Autoexec*'))
        dir_list = sorted(list(dirs))

        menu.banner()
        print(Fore.CYAN + "========== Autoexecute Manager ==========")
        print(Fore.GREEN + f"[+] Found {len(dir_list)} Autoexec folder(s)")
        for i, d in enumerate(dir_list):
            print(f"[{i+1}] {d}")
        print("[A] Apply to ALL folders")
        print("[0] Back")

        ch = input(Fore.CYAN + "[?] Select folder: ").strip().upper()
        if ch == "0":
            return

        script_content = input(Fore.CYAN + "[?] Enter Lua script content or URL: ").strip()
        if script_content.startswith("http"):
            script_content = f'loadstring(game:HttpGet("{script_content}"))()'

        targets = dir_list if ch == "A" else [dir_list[int(ch)-1]] if ch.isdigit() and 1 <= int(ch) <= len(dir_list) else []
        for t_dir in targets:
            try:
                os.makedirs(t_dir, exist_ok=True)
                with open(os.path.join(t_dir, 'script.lua'), 'w', encoding='utf-8') as f:
                    f.write(script_content)
                print(Fore.GREEN + f"[+] Script saved to {t_dir}")
            except Exception as e:
                print(Fore.RED + f"[!] Error saving to {t_dir}: {e}")
        input("Enter to back...")

    def option_7(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        if not tabs:
            print(Fore.RED + "[!] Config not found. Please setup in option 2 first")
            input("Enter to back...")
            return

        extracted = []
        for pkg, t in tabs.items():
            db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
            cookie = self.acc_manager.get_cookie(db_path)
            if cookie:
                uid, uname = self.acc_manager.get_uid_from_cookie(cookie)
                extracted.append({"package": pkg, "cookie": cookie, "user_id": uid, "user_name": uname})
                print(Fore.GREEN + f"[+] {pkg}: {uname} ({uid})")

        print(Fore.CYAN + f"Total extracted: {len(extracted)} cookies")
        print("[1] Save to all_cookie.txt")
        print("[2] Send to Webhook")
        print("[0] Back")
        ch = input(Fore.CYAN + "[?] Choice: ").strip()
        if ch == "1":
            with open("all_cookie.txt", "w", encoding="utf-8") as f:
                for item in extracted:
                    f.write(item["cookie"] + "\n")
            print(Fore.GREEN + "[+] Saved to all_cookie.txt")
        elif ch == "2":
            wh = self.webhook_manager.get_or_input_webhook(cfg)
            if wh:
                self.webhook_manager.send_all_cookie(wh, extracted, [x["cookie"] for x in extracted])
                print(Fore.GREEN + "[+] Sent to Discord Webhook")
        input("Enter to back...")

    def option_8(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        if not tabs:
            print(Fore.RED + "[!] No packages found in config. Please setup in option 2 first")
            input("Enter to back...")
            return

        print(Fore.CYAN + "=============== LOGIN VIA COOKIES ===============")
        print("[1] Login cookie for one package")
        print("[2] Login cookie for all packages from cookie.txt")
        ch = input(Fore.CYAN + "[?] Choice (1/2): ").strip()

        if ch == "1":
            pkg_list = list(tabs.keys())
            for i, p in enumerate(pkg_list):
                print(f"[{i+1}] {p}")
            p_ch = input(Fore.CYAN + "[?] Select package #: ").strip()
            if p_ch.isdigit() and 1 <= int(p_ch) <= len(pkg_list):
                target_pkg = pkg_list[int(p_ch) - 1]
                cookie = input(Fore.CYAN + "[?] Enter cookie string: ").strip()
                cookie = self._extract_cookie_from_line(cookie) or cookie
                db_path = f"/data/data/{target_pkg}/app_webview/Default/Cookies"
                res = self.acc_manager.write_cookie(db_path, cookie)
                uid, uname = self.acc_manager.get_uid_from_cookie(cookie)
                tabs[target_pkg]["user_name"] = uname
                tabs[target_pkg]["user_id"] = uid
                self.config_manager.save_config(self.config_file, cfg)
                print(Fore.GREEN + f"[+] Wrote cookie ({res}) for {target_pkg}: {uname}")

        elif ch == "2":
            if not os.path.exists(self.cookie_file):
                print(Fore.RED + f"[!] {self.cookie_file} not found")
                input("Enter to back...")
                return
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                lines = [self._extract_cookie_from_line(l) for l in f if self._extract_cookie_from_line(l)]

            for i, (pkg, tab) in enumerate(tabs.items()):
                if i < len(lines):
                    cookie = lines[i]
                    db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                    res = self.acc_manager.write_cookie(db_path, cookie)
                    uid, uname = self.acc_manager.get_uid_from_cookie(cookie)
                    tab["user_name"] = uname
                    tab["user_id"] = uid
                    print(Fore.GREEN + f"[+] {pkg} -> {uname} ({res})")
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + "[+] Finished login from cookie.txt")
        input("Enter to back...")

    def option_9(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        print(Fore.CYAN + "=============== LOG OUT ACCOUNT ===============")
        print("[1] Log out 1 Roblox account")
        print("[2] Log out all Roblox accounts")
        ch = input(Fore.CYAN + "[?] Choice (1/2): ").strip()

        if ch == "1":
            pkg_list = list(tabs.keys())
            for i, p in enumerate(pkg_list):
                print(f"[{i+1}] {p}")
            p_ch = input(Fore.CYAN + "[?] Select package #: ").strip()
            if p_ch.isdigit() and 1 <= int(p_ch) <= len(pkg_list):
                target = pkg_list[int(p_ch) - 1]
                self.pkg_manager.kill_roblox_process(target)
                db_path = f"/data/data/{target}/app_webview/Default/Cookies"
                try:
                    conn = sqlite3.connect(db_path)
                    conn.cursor().execute("DELETE FROM cookies WHERE name = '.ROBLOSECURITY'")
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                tabs[target]["user_name"] = "Unknown"
                tabs[target]["user_id"] = ""
                self.config_manager.save_config(self.config_file, cfg)
                print(Fore.GREEN + f"[+] Logged out {target}")

        elif ch == "2":
            for pkg, t in tabs.items():
                self.pkg_manager.kill_roblox_process(pkg)
                db_path = f"/data/data/{pkg}/app_webview/Default/Cookies"
                try:
                    conn = sqlite3.connect(db_path)
                    conn.cursor().execute("DELETE FROM cookies WHERE name = '.ROBLOSECURITY'")
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                t["user_name"] = "Unknown"
                t["user_id"] = ""
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + "[+] Logged out all packages")
        input("Enter to back...")

    def option_10(self):
        cfg = self.config_manager.load_config()
        while True:
            menu.banner()
            print(Fore.CYAN + "=============== TOOL CONFIGURATION ===============")
            print(f"[1] Rejoin interval  : {cfg.get('rejoin_interval', 30)} minutes")
            print(f"[2] Delay open tab   : {cfg.get('delay_open_tab', 5)} seconds")
            print(f"[3] Offline wait     : {cfg.get('offline_wait', 10)} seconds")
            print(f"[4] Check interval   : {cfg.get('check_interval', 5)} seconds")
            print(f"[5] Check UI delay   : {cfg.get('check_ui_delay', 3)} seconds")
            print(f"[6] Rejoin timeout   : {cfg.get('rejoin_timeout', 60)} seconds")
            print(f"[7] Max retries      : {cfg.get('max_retries', 3)}")
            print(f"[8] Retry delay      : {cfg.get('retry_delay', 5)} seconds")
            print(f"[9] FPS limit        : {cfg.get('fps_counter', {}).get('completed', 60)} fps")
            print("[0] Back")
            print(Fore.CYAN + "--------------------------------------------------")
            ch = input(Fore.CYAN + "[?] Choice: ").strip()

            keys = {
                "1": ("rejoin_interval", "minutes"),
                "2": ("delay_open_tab", "seconds"),
                "3": ("offline_wait", "seconds"),
                "4": ("check_interval", "seconds"),
                "5": ("check_ui_delay", "seconds"),
                "6": ("rejoin_timeout", "seconds"),
                "7": ("max_retries", "times"),
                "8": ("retry_delay", "seconds")
            }
            if ch == "0":
                break
            elif ch in keys:
                k, unit = keys[ch]
                val = input(Fore.CYAN + f"[?] Enter new {k} ({unit}): ").strip()
                if val.isdigit():
                    cfg[k] = int(val)
                    self.config_manager.save_config(self.config_file, cfg)
            elif ch == "9":
                fps = input(Fore.CYAN + "[?] Enter target FPS limit: ").strip()
                if fps.isdigit():
                    cfg.setdefault("fps_counter", {})
                    cfg["fps_counter"]["completed"] = int(fps)
                    self.config_manager.save_config(self.config_file, cfg)
                    self.config_manager.sync_fps_config(10, int(fps))

    def option_11(self):
        cfg = self.config_manager.load_config()
        tabs = cfg.get("tabs", {})
        if not tabs:
            print(Fore.RED + "[!] No packages found. Please setup in option 2 first")
            input("Enter to back...")
            return
        print(Fore.GREEN + "[+] Opening all enabled Roblox tabs...")
        self.pkg_manager.fast_restore_all(tabs)
        print(Fore.GREEN + "[+] Done")
        input("Enter to back...")

    def option_12(self):
        print(Fore.CYAN + "=============== CHANGE ANDROID ID ===============")
        cur = self.pkg_manager.get_android_id()
        print(f"Current Android ID: {cur}")
        print("[1] Random android id")
        print("[2] Set android id")
        print("[0] Back")
        ch = input(Fore.CYAN + "[?] Choice (1/2): ").strip()
        if ch == "1":
            new_id = self.pkg_manager.change_android_id()
            print(Fore.GREEN + f"[+] Changed Android ID to: {new_id}")
        elif ch == "2":
            target = input(Fore.CYAN + "[?] Enter 16-hex Android ID: ").strip()
            if len(target) == 16:
                self.pkg_manager.change_android_id(target)
                print(Fore.GREEN + f"[+] Set Android ID to: {target}")
        input("Enter to back...")

    def option_13(self):
        cfg = self.config_manager.load_config()
        cur = cfg.get("auto_block", False)
        status = "[ON]" if cur else "[OFF]"
        print(Fore.CYAN + f"Current Auto Block: {status}")
        yn = input(Fore.CYAN + f"[?] Do you want turn {'off' if cur else 'on'} auto block (y/n): ").strip().lower()
        if yn == 'y':
            cfg["auto_block"] = not cur
            self.config_manager.save_config(self.config_file, cfg)
            print(Fore.GREEN + f"[+] Auto block is now {'ON' if cfg['auto_block'] else 'OFF'}")
        input("Enter to back...")

    def option_14(self):
        cfg = self.config_manager.load_config()
        print(Fore.CYAN + "========== SELECT SORT TAB STYLE ==========")
        print("[1] L style (old sort tab)")
        print("[2] Full grid style")
        print("[0] Turn OFF")
        ch = input(Fore.CYAN + "[?] Choice: ").strip()
        if ch == "1":
            cfg["auto_sort_tab"] = True
            cfg["auto_sort_tab_full"] = False
        elif ch == "2":
            cfg["auto_sort_tab"] = False
            cfg["auto_sort_tab_full"] = True
        elif ch == "0":
            cfg["auto_sort_tab"] = False
            cfg["auto_sort_tab_full"] = False
        self.config_manager.save_config(self.config_file, cfg)
        print(Fore.GREEN + "[+] Saved sort style")
        input("Enter to back...")

    def option_15(self):
        cfg = self.config_manager.load_config()
        print(Fore.CYAN + "========== AUTO CHANGE ACCOUNT ==========")
        print("[1] Blox Fruits auto change acc")
        print("[2] Custom script auto change acc")
        print("[0] Turn OFF")
        ch = input(Fore.CYAN + "[?] Choice: ").strip()
        if ch == "1":
            cfg["auto_change_acc_bf"] = True
            cfg["auto_change_acc_custom"] = False
            self._write_bf_config_to_workspace()
        elif ch == "2":
            cfg["auto_change_acc_bf"] = False
            cfg["auto_change_acc_custom"] = True
        elif ch == "0":
            cfg["auto_change_acc_bf"] = False
            cfg["auto_change_acc_custom"] = False
        self.config_manager.save_config(self.config_file, cfg)
        print(Fore.GREEN + "[+] Saved auto change account settings")
        input("Enter to back...")

    def option_16(self):
        cfg = self.config_manager.load_config()
        while True:
            menu.banner()
            print(Fore.CYAN + "=============== AUTO BYPASS MANAGER ===============")
            print(f"[+] Current Service : {cfg.get('auto_bypass', 'Disabled')}")
            print(f"[+] Hwid Delta mode : {'Auto' if cfg.get('auto_hwid_delta') else 'Manual'}")
            print(Fore.CYAN + "---------------------------------------------------")
            print("[1] Change bypass service")
            print("[2] Change hwid delta mode")
            print("[0] Back")
            ch = input(Fore.CYAN + "[?] Choice: ").strip()

            if ch == "0":
                break
            elif ch == "1":
                print("[1] Delta")
                print("[0] Disable")
                s_ch = input(Fore.CYAN + "[?] Choose service: ").strip()
                if s_ch == "1":
                    cfg["auto_bypass"] = "delta"
                else:
                    cfg["auto_bypass"] = False
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "2":
                cfg["auto_hwid_delta"] = not cfg.get("auto_hwid_delta", False)
                self.config_manager.save_config(self.config_file, cfg)
            time.sleep(1)

    def option_17(self):
        cfg = self.config_manager.load_config()
        cur = cfg.get("account_check_method", "executor")
        print(Fore.CYAN + f"Current Method: {cur}")
        print("[1] Executor method (recommended)")
        print("[2] Online method (not recommended)")
        ch = input(Fore.CYAN + "[?] Selected account check method: ").strip()
        if ch == "1":
            cfg["account_check_method"] = "executor"
            print(Fore.GREEN + "[+] Selected check executor method")
        elif ch == "2":
            cfg["account_check_method"] = "online"
            print(Fore.GREEN + "[+] Selected check online method")
        self.config_manager.save_config(self.config_file, cfg)
        input("Enter to back...")

    def option_18(self):
        cfg = self.config_manager.load_config()
        while True:
            menu.banner()
            c_en = cfg.get("auto_send_acc_to_solver_captcha", False)
            f_en = cfg.get("auto_send_acc_to_solver_faceid", False)
            print(Fore.CYAN + "=============== AUTO CAPTCHA MANAGER ===============")
            print(f"[1] Auto Captcha Solver : {'Enabled' if c_en else 'Disabled'}")
            print(f"[2] Auto FaceID Solver  : {'Enabled' if f_en else 'Disabled'}")
            print(f"[3] Zeropoint API Key   : {cfg.get('zeropoint_apikey', 'None')}")
            print(f"[4] Zeropoint Priority  : {cfg.get('zeropoint_priority', False)}")
            print(f"[5] Third-party Captcha URLs")
            print(f"[6] Third-party FaceID URLs")
            print("[0] Back")
            print(Fore.CYAN + "----------------------------------------------------")
            ch = input(Fore.CYAN + "[?] Choice: ").strip()

            if ch == "0":
                break
            elif ch == "1":
                cfg["auto_send_acc_to_solver_captcha"] = not c_en
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "2":
                cfg["auto_send_acc_to_solver_faceid"] = not f_en
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "3":
                k = input(Fore.CYAN + "[?] Enter Zeropoint API Key: ").strip()
                cfg["zeropoint_apikey"] = k
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "4":
                cfg["zeropoint_priority"] = not cfg.get("zeropoint_priority", False)
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "5":
                urls = input(Fore.CYAN + "[?] Enter solver URL(s) comma-separated: ").strip()
                cfg["third_party_solve_capcha_url"] = urls
                self.config_manager.save_config(self.config_file, cfg)
            elif ch == "6":
                urls = input(Fore.CYAN + "[?] Enter FaceID solver URL(s) comma-separated: ").strip()
                cfg["faceid_&_captcha_lock_solve_url"] = urls
                self.config_manager.save_config(self.config_file, cfg)
            time.sleep(1)

    def run(self):
        try:
            self.auto_updater.check_and_update()
        except Exception:
            pass

        try:
            if not self.license_manager.authenticate():
                print(Fore.RED + "[!] License authentication failed. Exiting.")
                return
            self.license_manager.start_watchdog()
        except Exception as e:
            print(Fore.YELLOW + f"[~] License check bypassed / offline mode: {e}")

        self.config_manager.init_work_space()
        cfg = self.config_manager.load_config()
        self.pkg_manager.auto_clean_missing_packages(cfg)

        if cfg.get("discord_webhook", {}).get("running", False):
            self.webhook_manager.start_webhook()

        while True:
            menu.banner()
            menu.tool_status(cfg)
            menu.option()
            try:
                ch = input(Fore.CYAN + "[?] Enter your option: ").strip()
            except (KeyboardInterrupt, EOFError):
                print(Fore.GREEN + "\nGoodbye")
                break

            opts = {
                "1": self.option_1,
                "2": self.option_2,
                "3": self.option_3,
                "4": self.option_4,
                "5": self.option_5,
                "6": self.option_6,
                "7": self.option_7,
                "8": self.option_8,
                "9": self.option_9,
                "10": self.option_10,
                "11": self.option_11,
                "12": self.option_12,
                "13": self.option_13,
                "14": self.option_14,
                "15": self.option_15,
                "16": self.option_16,
                "17": self.option_17,
                "18": self.option_18
            }
            if ch == "0":
                print(Fore.GREEN + "Goodbye")
                break
            elif ch in opts:
                try:
                    opts[ch]()
                    cfg = self.config_manager.load_config()
                except Exception as e:
                    print(Fore.RED + f"[!] Error in option {ch}: {e}")
                    input("Enter to continue...")
            else:
                print(Fore.RED + "[!] Invalid choice")
                time.sleep(1)


# =====================================================================
# Entry Point
# =====================================================================

if __name__ == '__main__':
    tool = main()
    tool.run()
