# -*- coding: utf-8 -*-
"""
HTCT Engine v7.3 - Python Port (Multi-Task Automation)
Port y nguyen co che tu ban Go (chromedp) sang Python (Playwright CDP).
UI Banner: VNBYPASS style (rainbow gradient + credits).

Cach chay:
  pip install playwright requests
  python -m playwright install chromium
  python HTCT.py [--url <link>] [--threads N] [--dev]
"""

import argparse
import base64
import hmac
import json
import math
import os
import queue
import random
import re
import shutil
import socket
import struct
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

try:
    import requests
    # Tach pool Kiot va Octolink de khong chung keep-alive gay 10053/SSLEOF + rate limit
    _KIOT_SESSION = requests.Session()
    _KIOT_SESSION.headers.update({"Connection": "close"})
    try:
        _KIOT_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=3, pool_maxsize=3, max_retries=0, pool_block=False)
        _KIOT_SESSION.mount("https://", _KIOT_ADAPTER)
        _KIOT_SESSION.mount("http://", _KIOT_ADAPTER)
    except Exception:
        pass
    _OCTO_SESSION = requests.Session()
    try:
        _OCTO_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=1, pool_block=False)
        _OCTO_SESSION.mount("https://", _OCTO_ADAPTER)
        _OCTO_SESSION.mount("http://", _OCTO_ADAPTER)
    except Exception:
        pass
except ImportError:
    print("Thieu thu vien 'requests'. Chay: pip install requests")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Thieu thu vien 'playwright'. Chay: pip install playwright && python -m playwright install chromium")
    sys.exit(1)

urllib3 = None
try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

# Windows console: ep buoc UTF-8 de in banner/list Unicode
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "v7.3 (HTCT Engine - Multi-Task Automation)"
BridgePort = "8080"
VIEW_MODE = False  # --view: mo Chrome that de xem qua trinh giai
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
GATE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, "hkt_debug.log")
LOG_TXT_PATH = os.path.join(LOG_DIR, "htct_error.txt")

SettingsFileName = ".octo_settings"
ProxiesFileName = "proxies.txt"
BlacklistCampsFileName = "blacklist_camps.txt"
CampaignDomainsFileName = "campaign_domains.txt"

MoneyTaskCampaignsURL = "https://moneytask.top/api/tasks/uptolink-campaigns"
# KHONG hardcode secret: token rieng dat qua env OCTO_MONEYTASK_TOKEN hoac file moneytask_token.txt
defaultMoneyTaskBearer = ""
GitHubToken = ""
GitHubRepo = "nasanoper/my-octo-cache"
GitHubFile = "link.json"

maxBridgeBodyBytes = 10 << 20

# ============================================================================
# PATH HELPERS (uu tien file canh .py -> ./ -> thu muc cha)
# ============================================================================

def resolve_path(filename):
    p1 = os.path.join(BASE_DIR, filename)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(os.getcwd(), filename)
    if os.path.exists(p2):
        return p2
    p3 = os.path.join(os.path.dirname(BASE_DIR), filename)
    if os.path.exists(p3):
        return p3
    return p1


def load_js(name):
    path = os.path.join(SCRIPTS_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

STEALTH_JS = load_js("stealth.js")
HOOK_JS = load_js("hook.js")
SOLVER_CHECK_JS = load_js("solver_check.js")
GIAI_CAP_JS = load_js("giai_cap.js")
ENGINE_JS = load_js("engine.js")

# ============================================================================
# COLORS + BANNER (VNBYPASS style - tu vip.py)
# ============================================================================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    LOGO = "\033[38;2;0;255;65m"
    P_PURPLE = "\033[38;2;168;85;247m"
    P_PINK   = "\033[38;2;236;72;153m"
    P_CYAN   = "\033[38;2;6;182;212m"
    P_BLUE   = "\033[38;2;59;130;246m"
    P_SKY    = "\033[38;2;14;165;233m"
    P_MINT   = "\033[38;2;16;185;129m"
    P_GOLD   = "\033[38;2;245;158;11m"
    P_RED    = "\033[38;2;239;68;68m"
    P_GRAY   = "\033[38;2;148;163;184m"
    P_DARK   = "\033[38;2;71;85;105m"
    P_WHITE  = "\033[38;2;248;250;252m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

# --- THEME MOI 2025 - CYBER NEON (khac han ban goc) ---
Reset = "\033[0m"
Bold = "\033[1m"
Dim = "\033[2m"
Italic = "\033[3m"
Underline = "\033[4m"

ColorH = "\033[38;2;0;255;136m"
ColorT1 = "\033[38;2;255;107;53m"
ColorC = "\033[38;2;110;0;255m"
ColorT2 = "\033[38;2;0;242;255m"

ColorCyan1 = "\033[38;2;0;242;255m"
ColorCyan2 = "\033[38;2;120;255;255m"
ColorGreen1 = "\033[38;2;0;255;136m"
ColorGreen2 = "\033[38;2;120;255;180m"
ColorYellow1 = "\033[38;2;255;214;0m"
ColorYellow2 = "\033[38;2;255;232;120m"
ColorRed1 = "\033[38;2;255;45;85m"
ColorRed2 = "\033[38;2;255;120;140m"
ColorPurple1 = "\033[38;2;110;0;255m"
ColorPurple2 = "\033[38;2;192;132;252m"
ColorWhite = "\033[38;2;248;250;252m"
ColorGray = "\033[38;2;148;163;184m"
ColorDarkGray = "\033[38;2;100;116;139m"
ColorMuted = "\033[38;2;100;116;139m"
ColorBorder = "\033[38;2;51;65;85m"
ColorCardLine = "\033[38;2;71;85;105m"

BgCyan = "\033[48;2;0;229;255m\033[38;2;0;0;0m"
BgT2 = "\033[48;2;0;229;255m\033[38;2;0;0;0m"

_SPINNER_FRAMES = ["⟳", "↻", "⟲", "↺"]
_SPINNER_COLORS = [
    "\033[38;2;6;182;212m",
    "\033[38;2;14;165;233m",
    "\033[38;2;59;130;246m",
    "\033[38;2;168;85;247m",
    "\033[38;2;236;72;153m",
    "\033[38;2;16;185;129m",
    "\033[38;2;245;158;11m",
]
_spinner_idx = 0
_spinner_lock = threading.Lock()

_RAINBOW_STOPS = [
    (255, 64, 64),
    (255, 150, 0),
    (255, 230, 0),
    (64, 240, 64),
    (0, 200, 255),
    (170, 80, 255),
]

print_lock = threading.RLock()
_stats_lock = threading.Lock()
_log_lock = threading.Lock()
_log_file = None
_is_dev_mode = False


def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rainbow_gradient_text(text):
    n_vis = sum(1 for ch in text if ch != ' ')
    if n_vis <= 1:
        return text
    stops = _RAINBOW_STOPS
    out = []
    vi = 0
    for ch in text:
        if ch == ' ':
            out.append(ch)
            continue
        p = vi / (n_vis - 1) if n_vis > 1 else 0
        pos = p * (len(stops) - 1)
        i0 = int(pos)
        i1 = min(i0 + 1, len(stops) - 1)
        r, g, b = _lerp_color(stops[i0], stops[i1], pos - i0)
        out.append(f"\033[38;2;{r};{g};{b}m{ch}")
        vi += 1
    out.append(Colors.RESET)
    return "".join(out)


def vn_time_now():
    try:
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        return now.strftime("%H:%M:%S"), now.strftime("%d/%m/%Y")
    except Exception:
        return time.strftime("%H:%M:%S"), time.strftime("%d/%m/%Y")


def get_spin_prefix():
    global _spinner_idx
    with _spinner_lock:
        char = _SPINNER_FRAMES[_spinner_idx % len(_SPINNER_FRAMES)]
        col = _SPINNER_COLORS[_spinner_idx % len(_SPINNER_COLORS)]
        _spinner_idx += 1
    return f"{Colors.BOLD}{col}{char}{Colors.RESET}"


# ============================================================================
# ANSI HELPERS (port tu console.go: StripANSI / VisibleWidth / PadRight)
# ============================================================================

ANSI_RE = re.compile(
    r"\x1b\[[0-9;]*[A-Za-z]"                       # CSI
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?"          # OSC
    r"|\x1b.",                                       # 2-byte escape
    re.DOTALL,
)


def strip_ansi(s):
    return ANSI_RE.sub("", s)


def is_wide_char(ch):
    o = ord(ch)
    return (
        (0x1100 <= o <= 0x115F) or o in (0x2329, 0x232A) or
        (0x2E80 <= o <= 0xA4CF and o != 0x303F) or
        (0xAC00 <= o <= 0xD7A3) or
        (0xF900 <= o <= 0xFAFF) or
        (0xFE10 <= o <= 0xFE19) or
        (0xFE30 <= o <= 0xFE6F) or
        (0xFF00 <= o <= 0xFF60) or
        (0xFFE0 <= o <= 0xFFE6) or
        (0x1F300 <= o <= 0x1F64F) or
        (0x1F680 <= o <= 0x1F6FF) or
        (0x1F900 <= o <= 0x1F9FF)
    )


def visible_width(s):
    clean = strip_ansi(s)
    width = 0
    for ch in clean:
        o = ord(ch)
        if o == 0x200B or o == 0xFEFF or (0x0300 <= o <= 0x036F):
            continue
        width += 2 if is_wide_char(ch) else 1
    return width


def pad_right(s, target_width):
    w = visible_width(s)
    if w >= target_width:
        return s
    return s + " " * (target_width - w)


def slot_badge(slot_id):
    if not slot_id or slot_id <= 0:
        return ColorDarkGray + "[SYS]" + Reset
    colors = [ColorCyan1, ColorPurple1, ColorGreen1, ColorYellow1, ColorH]
    c = colors[(slot_id - 1) % len(colors)]
    return f"{c}{Bold}[#{slot_id:02d}]{Reset}"


def timestamp_now():
    return time.strftime("%H:%M:%S")


_log_txt = None

def write_log_file(line):
    global _log_file, _log_txt
    clean = strip_ansi(line)
    with _log_lock:
        if _log_file is not None:
            try:
                _log_file.write(clean + "\n")
                _log_file.flush()
            except Exception:
                pass
        if _log_txt is not None:
            try:
                _log_txt.write(clean + "\n")
                _log_txt.flush()
            except Exception:
                pass


def init_logger(dev_mode):
    global _log_file, _log_txt, _is_dev_mode
    _is_dev_mode = dev_mode
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        _log_file = open(LOG_FILE_PATH, "a", encoding="utf-8")
        _log_txt = open(LOG_TXT_PATH, "a", encoding="utf-8")
        mode_str = "BẢN THƯỜNG (UI SẠCH SẼ)" if not dev_mode else "BẢN DEV (FULL LOG DEBUG)"
        header = ("\n=======================================================\n"
                  f"  PHIÊN HOẠT ĐỘNG: {time.strftime('%Y-%m-%d %H:%M:%S')} [{mode_str}]\n"
                  "=======================================================\n")
        _log_file.write(header)
        _log_txt.write(header)
        _log_file.flush()
        _log_txt.flush()
    except Exception:
        _log_file = None
        _log_txt = None


def is_dev_mode():
    return _is_dev_mode


def sleep_with_spinner(seconds, message="Đang xử lý"):
    try:
        secs = int(float(seconds))
    except Exception:
        secs = 5
    if secs <= 0:
        secs = 1
    try:
        # Tranh spam log khi goi tu Bridge thread - chi log 1 lan
        if secs > 5:
            print_info(f"{message}... {secs}s")
            time.sleep(secs)
        else:
            time.sleep(secs)
    except Exception:
        try:
            time.sleep(secs)
        except Exception:
            pass


def format_log(level_tag, level_color, slot_str, msg):
    raw_line = f"[{timestamp_now()}] {strip_ansi(slot_str)} │ {level_tag:<4} │ {strip_ansi(msg)}"
    write_log_file(raw_line)
    ts = ColorDarkGray + timestamp_now() + Reset
    lvl = level_color + Bold + f"{level_tag:<4}" + Reset
    if not slot_str:
        slot_str = ColorDarkGray + "[SYS]" + Reset
    return f"  {ts} │ {slot_str} │ {lvl} │ {msg}"


def log_engine(level_tag, level_color, msg, slot_id=0, msg_color=""):
    with print_lock:
        print(format_log(level_tag, level_color, slot_badge(slot_id) if slot_id else "", msg_color + msg + Reset if msg_color else msg))


def print_info(msg, *args):
    if args:
        msg = msg % args
    log_engine("INFO", ColorCyan1, msg)


def print_success(msg, *args):
    if args:
        msg = msg % args
    log_engine("PASS", ColorGreen1, msg, msg_color=ColorGreen2)


def print_warning(msg, *args):
    if args:
        msg = msg % args
    log_engine("WARN", ColorYellow1, msg, msg_color=ColorYellow2)


def print_error(msg, *args):
    if args:
        msg = msg % args
    log_engine("FAIL", ColorRed1, msg, msg_color=ColorRed2 + Bold)


def print_slot_info(slot_id, msg, *args):
    if args:
        msg = msg % args
    log_engine("INFO", ColorCyan1, msg, slot_id=slot_id)


def print_slot_success(slot_id, msg, *args):
    if args:
        msg = msg % args
    log_engine("PASS", ColorGreen1, msg, slot_id=slot_id, msg_color=ColorGreen2)


def print_slot_warning(slot_id, msg, *args):
    if args:
        msg = msg % args
    log_engine("WARN", ColorYellow1, msg, slot_id=slot_id, msg_color=ColorYellow2)


def print_slot_error(slot_id, msg, *args):
    if args:
        msg = msg % args
    log_engine("FAIL", ColorRed1, msg, slot_id=slot_id, msg_color=ColorRed2 + Bold)


# ============================================================================
# BANNER (VNBYPASS nguyen ban tu vip.py)
# ============================================================================

VNBYPASS_FONT = {
    'V': ["██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "],
    'N': ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    'B': ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "],
    'Y': ["██╗   ██╗", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚██╔╝  ", "   ██║   ", "   ╚═╝   "],
    'P': ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "],
    'A': [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    'S': ["███████╗", "██╔════╝", "███████║", "╚════██║", "███████║", "╚══════╝"],
}


def print_prime_banner(version=VERSION):
    vn_text = "NASA"
    lines = []
    for row in range(6):
        line_parts = []
        for ch in vn_text:
            line_parts.append(VNBYPASS_FONT[ch][row])
        lines.append("  ".join(line_parts))

    with print_lock:
        print("\n" + "\033[97m" + "━" * 80 + Colors.RESET)
        for line in lines:
            print(f"{Colors.BOLD}{rainbow_gradient_text(line)}{Colors.RESET}")
        print("\033[97m" + "─" * 80 + Colors.RESET)
        print(f" \033[38;5;141m❖ \033[97mDiscord 1: \033[38;2;0;255;200mdiscord.gg/RJ3BBWePg{Colors.RESET}")
        print(f" \033[38;5;141m❖ \033[97mDiscord 2: \033[38;2;0;255;200mdsc.gg/meobypass{Colors.RESET}")
        print(f" \033[38;5;141m❖ \033[97mCode by:  \033[38;5;141mNASA{Colors.RESET}")
        t, d = vn_time_now()
        print(f" \033[38;5;141m❖ \033[97mThời gian: {Colors.BOLD}{rainbow_gradient_text(t)}{Colors.RESET} ")
        print('\033[97m' + "━" * 80 + Colors.RESET + '\n')


# ============================================================================
# SESSION STATS (port tu console.go)
# ============================================================================

class SessionStats:
    def __init__(self):
        self.start_time = time.time()
        self.total_tasks = 0
        self.success_count = 0
        self.fail_count = 0
        self.passcodes_found = 0
        self.redirects_found = 0
        self.total_duration_ms = 0


global_stats = SessionStats()


def record_task_success(is_passcode, duration_s):
    with _stats_lock:
        global_stats.total_tasks += 1
        global_stats.success_count += 1
        if is_passcode:
            global_stats.passcodes_found += 1
        else:
            global_stats.redirects_found += 1
        global_stats.total_duration_ms += int(duration_s * 1000)


def record_task_failure():
    with _stats_lock:
        global_stats.total_tasks += 1
        global_stats.fail_count += 1


def print_session_summary():
    with _stats_lock:
        uptime = int(time.time() - global_stats.start_time)
        total = global_stats.total_tasks
        success_rate = (global_stats.success_count / total * 100.0) if total > 0 else 0.0
        avg_speed = "0s"
        if global_stats.success_count > 0:
            avg_ms = global_stats.total_duration_ms // global_stats.success_count
            avg_speed = f"{avg_ms / 1000.0:.2f}s"

    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h{m}m{s}s" if h else (f"{m}m{s}s" if m else f"{s}s")

    with print_lock:
        print()
        print(f"  {ColorCyan1}─── SESSION SUMMARY ─────────────────────────────────────{Reset}")
        print(f"    {ColorDarkGray}• Uptime        :{Reset} {ColorWhite}{Bold}{uptime_str}{Reset}")
        print(f"    {ColorDarkGray}• Total tasks   :{Reset} {ColorT2}{Bold}{total}{Reset}")
        print(f"    {ColorDarkGray}• Success rate  :{Reset} {ColorGreen1}{Bold}{global_stats.success_count} ok{Reset} ({success_rate:.1f}%)")
        print(f"    {ColorDarkGray}• Codes         :{Reset} {ColorGreen2}{Bold}{global_stats.passcodes_found}{Reset}")
        print(f"    {ColorDarkGray}• Links         :{Reset} {ColorYellow1}{Bold}{global_stats.redirects_found}{Reset}")
        print(f"    {ColorDarkGray}• Avg speed     :{Reset} {ColorYellow2}{Bold}{avg_speed}{Reset} / task")
        print(f"  {ColorCardLine}──────────────────────────────────────────────────────────────────{Reset}")
        print()


# ============================================================================
# UI BOXES
# ============================================================================

def print_dashboard(info):
    threads = info.get("threads", 1)
    proxy_count = info.get("proxy_count", 0)
    rotate_tasks = info.get("rotate_tasks", 0)
    target_tasks = info.get("target_tasks", 0)
    completed_tasks = info.get("completed_tasks", 0)
    bridge_port = info.get("bridge_port", BridgePort)

    hostname = socket.gethostname()
    display_dev = hostname if len(hostname) <= 18 else hostname[:8] + "••••" + hostname[-4:]

    if FORCE_DIRECT:
        proxy_status = ColorYellow1 + Bold + "DIRECT (tắt proxy)" + Reset
    elif proxy_count > 0:
        proxy_status = f"{ColorYellow1}{Bold}{proxy_count} Proxies{Reset} {ColorDarkGray}({rotate_tasks}t/rot){Reset}"
    else:
        proxy_status = ColorMuted + "Direct Net (Trực tiếp)" + Reset

    worker_label = f"{ColorPurple1}{Bold}{threads} Worker{Reset}" if threads <= 1 else f"{ColorPurple1}{Bold}{threads} Workers{Reset}"
    bridge_url = f"http://127.0.0.1:{bridge_port}"

    if target_tasks > 0:
        target_label = f"{ColorYellow1}{Bold}{target_tasks} Nhiệm vụ{Reset}"
    else:
        target_label = ColorGreen1 + Bold + "Không giới hạn" + Reset
    done_label = f"{ColorCyan1}{Bold}{completed_tasks} Hoàn thành{Reset}"

    c1_1 = pad_right(f"{ColorDarkGray}• Host      :{Reset} {ColorH}{display_dev}{Reset}", 38)
    c1_2 = f"{ColorDarkGray}• Status    :{Reset} {ColorGreen1}{Bold}● READY{Reset}"
    c2_1 = pad_right(f"{ColorDarkGray}• Workers   :{Reset} {worker_label}", 38)
    c2_2 = f"{ColorDarkGray}• API       :{Reset} {ColorT2}{Underline}{bridge_url}{Reset}"
    c3_1 = pad_right(f"{ColorDarkGray}• Network   :{Reset} {proxy_status}", 38)
    c3_2 = f"{ColorDarkGray}• Core      :{Reset} {ColorC}{Bold}Playwright{Reset}"
    c4_1 = pad_right(f"{ColorDarkGray}• Target    :{Reset} {target_label}", 38)
    c4_2 = f"{ColorDarkGray}• Done      :{Reset} {done_label}"

    with print_lock:
        print()
        print(f"  {ColorGreen1}┌─ ENGINE ──────────────────────────────────────────┐{Reset}")
        print(f"  {ColorGreen1}│{Reset} {c1_1} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}│{Reset} {c2_1} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}│{Reset} {c3_1} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}│{Reset} {c4_1} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}└───────────────────────────────────────────────────┘{Reset}")
        print()


def print_slot_result_box(slot_id, result, is_passcode, elapsed):
    tag = "CODE" if is_passcode else "LINK"
    val_color = (ColorGreen1 + Bold) if is_passcode else (ColorT2 + Bold)
    with print_lock:
        print()
        print(f"  {ColorGreen1}{Bold}● TASK DONE{Reset} {slot_badge(slot_id)}")
        print(f"    {ColorDarkGray}• {tag:<10}:{Reset} {val_color}{result}{Reset}")
        print(f"    {ColorDarkGray}• Time       :{Reset} {ColorYellow1}{Bold}{elapsed}{Reset} {ColorDarkGray}(auto){Reset}")
        print()


def print_diagnostic_box(slot_id, stage, err_code, detail, suggestion=""):
    with print_lock:
        print()
        print(f"  {ColorRed1}{Bold}■ TASK ERROR{Reset} {slot_badge(slot_id)} {ColorRed2}{Bold}[{err_code}]{Reset}")
        print(f"    {ColorDarkGray}• Stage    :{Reset} {ColorYellow1}{Bold}{stage}{Reset}")
        print(f"    {ColorDarkGray}• Detail   :{Reset} {ColorWhite}{detail}{Reset}")
        if suggestion:
            print(f"    {ColorDarkGray}• Fix      :{Reset} {ColorCyan1}{suggestion}{Reset}")
        print()


def print_prompt_box(slot_id, title, issue, guide_url=""):
    with print_lock:
        print()
        print(f"  {ColorYellow1}{Bold}● {title}{Reset} {slot_badge(slot_id)}")
        print(f"    {ColorDarkGray}• Note     :{Reset} {issue}")
        if guide_url:
            print(f"    {ColorDarkGray}• Guide    :{Reset} {ColorCyan2}{Underline}{guide_url}{Reset}")
        print()


def print_target_tasks_prompt_box():
    with print_lock:
        print()
        print(f"  {ColorYellow1}┌─ TARGET ──────────────────────────────────────────┐{Reset}")
        print(f"  {ColorYellow1}│{Reset} {ColorGreen1}Enter{Reset}       : Unlimited run (all tasks)              {ColorYellow1}│{Reset}")
        print(f"  {ColorYellow1}│{Reset} {ColorCyan1}Number 50{Reset}    : Run exactly 50 tasks then auto-stop   {ColorYellow1}│{Reset}")
        print(f"  {ColorYellow1}│{Reset} {ColorRed1}N / exit{Reset}     : Quit immediately                      {ColorYellow1}│{Reset}")
        print(f"  {ColorYellow1}└───────────────────────────────────────────────────┘{Reset}")


def print_saved_settings_box(threads, rotate_tasks):
    with print_lock:
        print()
        print(f"  {ColorGreen1}┌─ SAVED ───────────────────────────────────────┐{Reset}")
        print(f"  {ColorGreen1}│{Reset} Workers: {ColorCyan1}{Bold}{threads}{Reset}  Rotate: {ColorYellow1}{Bold}{rotate_tasks} tasks{Reset} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}└───────────────────────────────────────────────┘{Reset}")
        print()


def print_ready_listening(port):
    bridge_url = f"http://127.0.0.1:{port}"
    with print_lock:
        print()
        print(f"  {ColorGreen1}┌─ LISTENING ───────────────────────────────────────┐{Reset}")
        print(f"  {ColorGreen1}│{Reset} {ColorGreen1}{Bold}● {Reset}{ColorT2}{Underline}{bridge_url}{Reset} {ColorGreen1}(active){Reset} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}│{Reset} {ColorDarkGray}State: Waiting for links from browser or manual input...{Reset} {ColorGreen1}│{Reset}")
        print(f"  {ColorGreen1}└───────────────────────────────────────────────────┘{Reset}")
        print()


def print_countdown_progress(slot_id, remaining_sec, total_sec, label="WAIT"):
    if total_sec <= 0:
        total_sec = 60
    remaining_sec = max(0, min(remaining_sec, total_sec))
    elapsed = total_sec - remaining_sec
    pct = elapsed / total_sec
    bar_width = 16
    filled = int(round(pct * bar_width))
    empty = bar_width - filled
    bar = ColorCyan1 + "█" * filled + ColorDarkGray + "░" * empty + Reset
    with print_lock:
        sys.stdout.write(
            f"\r  {ColorDarkGray}{timestamp_now()}{Reset} │ {slot_badge(slot_id)} │ {ColorYellow1}{Bold}{label}{Reset} │ [{bar}] "
            f"{ColorYellow1}{Bold}{remaining_sec:2d}s/{total_sec}s{Reset} ({ColorCyan1}{Bold}{int(pct * 100):3d}%{Reset})..."
        )
        sys.stdout.flush()


def clear_countdown_line():
    with print_lock:
        sys.stdout.write("\r" + " " * 110 + "\r")
        sys.stdout.flush()


# ============================================================================
# STDIN READER (port tu input.go - 1 reader duy nhất, EOF token)
# ============================================================================

EOF_TOKEN = "\x00__OCTO_EOF__"
_stdin_queue = queue.Queue()
_stdin_started = False
_stdin_eof = False
_stdin_lock = threading.Lock()


def _stdin_feed():
    global _stdin_eof
    try:
        for line in sys.stdin:
            _stdin_queue.put(line.rstrip("\n").rstrip("\r"))
    except Exception:
        pass
    _stdin_eof = True
    _stdin_queue.put(EOF_TOKEN)


def ensure_stdin():
    global _stdin_started
    with _stdin_lock:
        if not _stdin_started:
            t = threading.Thread(target=_stdin_feed, daemon=True)
            t.start()
            _stdin_started = True


def read_line_eof():
    """Tra ve (text, ok). ok=False neu stdin da dong (EOF)."""
    ensure_stdin()
    global _stdin_eof
    try:
        s = _stdin_queue.get_nowait()
    except queue.Empty:
        if _stdin_eof:
            return "", False
        try:
            s = _stdin_queue.get()
        except Exception:
            return "", False
    if s == EOF_TOKEN:
        return "", False
    return s.strip(), True


def read_line():
    s, _ = read_line_eof()
    return s


# ============================================================================
# SETTINGS (.octo_settings)
# ============================================================================

def load_saved_settings():
    path = resolve_path(SettingsFileName)
    try:
        with open(path, "r", encoding="utf-8") as f:
            s = json.load(f)
        if s.get("threads", 0) > 0 and s.get("rotate_tasks", 0) > 0:
            if s["rotate_tasks"] < s["threads"]:
                s["rotate_tasks"] = s["threads"]
            return s
    except Exception:
        pass
    return None


def save_settings(threads, rotate_tasks):
    path = resolve_path(SettingsFileName)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"threads": threads, "rotate_tasks": rotate_tasks}, f, indent=2)
        return True
    except Exception:
        return False


def prompt_setting_int(label, default_val, min_val, max_val):
    while True:
        sys.stdout.write(f"  {ColorT2}{Bold}• {label} {ColorDarkGray}[Mặc định: {default_val}]: {Reset}")
        sys.stdout.flush()
        raw, ok = read_line_eof()
        if not ok:
            return default_val
        text = raw.strip()
        if text == "":
            return default_val
        try:
            val = int(text)
        except ValueError:
            print_warning("Giá trị không hợp lệ! Vui lòng chỉ nhập số nguyên.")
            continue
        if min_val > 0 and val < min_val:
            print_warning(f"Giá trị phải lớn hơn hoặc bằng {min_val}!")
            continue
        if max_val > 0 and val > max_val:
            print_warning(f"Giá trị không được vượt quá {max_val}!")
            continue
        return val


def interactive_setup(flag_threads):
    if flag_threads > 0:
        saved = load_saved_settings()
        rotate_tasks = flag_threads
        if saved and saved.get("rotate_tasks", 0) >= flag_threads:
            rotate_tasks = saved["rotate_tasks"]
        return flag_threads, rotate_tasks

    saved = load_saved_settings()
    if saved:
        print_saved_settings_box(saved["threads"], saved["rotate_tasks"])
        sys.stdout.write(f"  {ColorYellow1}{Bold}Bạn có muốn sử dụng lại cấu hình này không? (Y/n) [Mặc định: Y]: {Reset}")
        sys.stdout.flush()
        ans, has_input = read_line_eof()
        ans = ans.strip().lower()
        if not has_input or ans in ("", "y", "yes", "c", "co", "có"):
            print_success(f"Tiếp tục với cấu hình đã lưu ({saved['threads']} luồng | xoay sau {saved['rotate_tasks']} task).")
            return saved["threads"], saved["rotate_tasks"]
        print()
        print_info("Thiết lập lại cấu hình mới (.octo_settings):")
    else:
        print()
        print_info("Chưa có cấu hình. Vui lòng thiết lập thông số ban đầu (.octo_settings):")

    def_threads = saved["threads"] if saved and saved.get("threads", 0) > 0 else 1
    def_rotate = saved["rotate_tasks"] if saved and saved.get("rotate_tasks", 0) > 0 else 2

    threads = prompt_setting_int("Số luồng chạy song song (1-10)", def_threads, 1, 10)
    if def_rotate < threads:
        def_rotate = threads
    rotate_tasks = prompt_setting_int(f"Số nhiệm vụ đổi Proxy một lần (>={threads})", def_rotate, threads, 1000)

    if save_settings(threads, rotate_tasks):
        print_success(f"Đã lưu cấu hình mới vào {SettingsFileName} thành công!")
    else:
        print_warning(f"Không thể lưu cấu hình vào {SettingsFileName}!")
    return threads, rotate_tasks


# ============================================================================
# PROXY MANAGER (port tu proxy_manager.go)
# ============================================================================

PROXY_TEMPLATE = """# ========================================================
# DANH SACH PROXY (Moi dong 1 proxy)
# Ho tro cac dinh dang:
#   1. ip:port (Vi du: 123.45.67.89:8080)
#   2. ip:port:user:pass (Vi du: 123.45.67.89:8080:admin:123456)
#   3. http://user:pass@ip:port
#   4. socks5://user:pass@ip:port
# ========================================================
"""


def normalize_proxy(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("socks5://"):
        return raw
    parts = raw.split(":", 3)
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"http://{user}:{pwd}@{ip}:{port}"
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    return "http://" + raw


def safe_proxy_string(raw):
    if not raw:
        return "Direct"
    try:
        u = urlparse(raw)
        if u.username:
            return f"{u.scheme}://{u.username}:***@{u.hostname}:{u.port}"
        return raw
    except Exception:
        return raw


class ProxyManager:
    def __init__(self, rotate_tasks):
        if rotate_tasks <= 0:
            rotate_tasks = 2
        self.rotate_tasks = rotate_tasks
        self.task_counter = 0
        self.current_index = 0
        self.proxies = []
        self.cooldowns = {}
        self.mu = threading.Lock()
        self._load_proxies_from_file()

    def _load_proxies_from_file(self):
        found = None
        p = resolve_path(ProxiesFileName)
        if os.path.exists(p):
            found = p
        if not found:
            try:
                with open(ProxiesFileName, "w", encoding="utf-8") as f:
                    f.write(PROXY_TEMPLATE)
                found = ProxiesFileName
            except Exception:
                pass
        if not found:
            return
        lst = []
        try:
            with open(found, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    norm = normalize_proxy(line)
                    if norm:
                        lst.append(norm)
        except Exception:
            pass
        self.proxies = lst
        if lst:
            print_success(f"Đã nạp {len(lst)} Proxy từ file {ProxiesFileName}! (Tự động xoay sau mỗi {self.rotate_tasks} task)")
        else:
            print_info(f"File {ProxiesFileName} trống -> Sử dụng kết nối mạng trực tiếp (Direct Connection).")

    def get_proxy_count(self):
        with self.mu:
            return len(self.proxies)

    def mark_proxy_failed(self, proxy_str):
        if not proxy_str:
            return
        with self.mu:
            for i, p in enumerate(self.proxies):
                if p == proxy_str:
                    until = self.cooldowns.get(i)
                    if until and time.time() < until:
                        return
                    self.cooldowns[i] = time.time() + 300
                    print_warning(f"🚫 [Proxy] #{i + 1} gặp lỗi mạng — tạm nghỉ 5 phút: {safe_proxy_string(p)}")
                    break

    def get_next_proxy(self, slot_id=0):
        with self.mu:
            if not self.proxies:
                return ""
            now = time.time()
            chosen = -1
            for off in range(len(self.proxies)):
                idx = (self.current_index + off) % len(self.proxies)
                until = self.cooldowns.get(idx)
                if until and now < until:
                    continue
                chosen = idx
                break
            if chosen == -1:
                print_slot_warning(slot_id, "Tất cả proxy đang trong thời gian nghỉ lỗi -> Dùng kết nối trực tiếp (Direct) cho task này")
                return ""
            proxy = self.proxies[chosen]
            self.task_counter += 1
            rotate_now = self.task_counter >= self.rotate_tasks
            progress = self.task_counter
            old_idx = chosen
            if rotate_now:
                self.task_counter = 0
                self.current_index = (chosen + 1) % len(self.proxies)
            new_idx = self.current_index if rotate_now else chosen
            rotate_limit = self.rotate_tasks
            multi = len(self.proxies) > 1

        if rotate_now:
            if multi:
                nxt = self.proxies[new_idx] if 0 <= new_idx < len(self.proxies) else proxy
                print_info(f"🔄 [Xoay Proxy] Đã hoàn thành {rotate_limit} task! Chuyển từ Proxy #{old_idx + 1} sang Proxy #{new_idx + 1} ({safe_proxy_string(nxt)})")
        else:
            print_slot_info(slot_id, f"🌐 Dùng Proxy #{chosen + 1} (Tiến độ: {progress}/{rotate_limit} task): {safe_proxy_string(proxy)}")
        return proxy


# ============================================================================
ROTATING_PROXY_PROVIDERS = {
    "1": {
        "id": "kiotproxy",
        "name": "KiotProxy",
        "url": "https://api.kiotproxy.com/api/v1/proxies"
    },
    "2": {
        "id": "androidmodvip",
        "name": "AndroidModVip",
        "url": "https://proxy.androidmodvip.io.vn/api/v3/users/rotatev2"
    },
    "3": {
        "id": "nestproxy",
        "name": "NestProxy",
        "url": "https://nestproxy.com/api/client/proxy"
    },
    "4": {
        "id": "5starsproxy",
        "name": "5StarsProxy.vn",
        "url": "https://5starsproxy.vn/apiv2/doiproxy.php"
    },
    "5": {
        "id": "mproxy",
        "name": "MProxy.vn",
        "url": "https://mproxy.vn/capi"
    },
    "6": {
        "id": "proxyxoay",
        "name": "ProxyXoay.shop / Proxy.vn",
        "url": "https://proxyxoay.shop/api/get.php"
    }
}

FIVE_STARS_PROXY_TYPES = ["Viettel", "FPT", "VNPT"]

def get_provider_label(provider_id, loaiproxy=""):
    for p in ROTATING_PROXY_PROVIDERS.values():
        if p["id"] == provider_id:
            if provider_id == "5starsproxy":
                return f"{p['name']} (Random: Viettel/FPT/VNPT)"
            elif provider_id == "mproxy":
                return f"{p['name']} (4G VN: Viettel/Vina/Mobi)"
            elif provider_id == "proxyxoay":
                return f"{p['name']} (Random ISP / Tỉnh thành)"
            return p["name"]
    return "KiotProxy"

def detect_proxy_provider(token):
    if not token:
        return "kiotproxy"
    t_str = str(token).strip().lower()
    if "proxyxoay" in t_str or "proxy.vn" in t_str:
        return "proxyxoay"
    if "androidmodvip" in t_str:
        return "androidmodvip"
    if "kiot" in t_str:
        return "kiotproxy"
    if "nest" in t_str:
        return "nestproxy"
    if "5stars" in t_str or "5star" in t_str:
        return "5starsproxy"
    if "mproxy" in t_str:
        return "mproxy"
    raw = str(token).strip()
    if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', raw):
        return "nestproxy"
    if raw.startswith("K") and len(raw) >= 10 and not ("=" in raw or "_" in raw or ";" in raw or "-" in raw):
        return "kiotproxy"
    if len(raw) >= 40 and not ("=" in raw or ";" in raw) and "_" in raw:
        return "mproxy"
    try:
        if "_" in token:
            b64_part = token.split("_")[0]
            decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore').lower()
            if "proxyxoay" in decoded or "proxy.vn" in decoded:
                return "proxyxoay"
            if "androidmodvip" in decoded:
                return "androidmodvip"
            if "kiot" in decoded:
                return "kiotproxy"
            if "nest" in decoded:
                return "nestproxy"
            if "5stars" in decoded or "5star" in decoded:
                return "5starsproxy"
            if "mproxy" in decoded:
                return "mproxy"
    except Exception:
        pass
    return "kiotproxy"

def select_proxy_provider_interactive(default_id="kiotproxy"):
    print(f"\n {Colors.BOLD}{Colors.P_CYAN}[Dịch Vụ Proxy Key]{Colors.RESET} {Colors.P_WHITE}Chọn nhà cung cấp cho Key Xoay:{Colors.RESET}")
    print(f"   {Colors.P_PINK}[1]{Colors.RESET} {Colors.P_WHITE}KiotProxy (https://api.kiotproxy.com) - {Colors.P_GOLD}Mặc định{Colors.RESET}")
    print(f"   {Colors.P_CYAN}[2]{Colors.RESET} {Colors.P_WHITE}AndroidModVip (https://proxy.androidmodvip.io.vn){Colors.RESET}")
    print(f"   {Colors.P_GOLD}[3]{Colors.RESET} {Colors.P_WHITE}NestProxy (https://nestproxy.com){Colors.RESET}")
    print(f"   {Colors.P_PURPLE}[4]{Colors.RESET} {Colors.P_WHITE}5StarsProxy.vn (Random xoay: Viettel / FPT / VNPT){Colors.RESET}")
    print(f"   {Colors.P_CYAN}[5]{Colors.RESET} {Colors.P_WHITE}MProxy.vn (4G Mobile VN: Viettel / Vina / Mobi){Colors.RESET}")
    print(f"   {Colors.P_MINT}[6]{Colors.RESET} {Colors.P_WHITE}ProxyXoay.shop / Proxy.vn (https://proxyxoay.shop){Colors.RESET}")
    def_num = "1" if default_id == "kiotproxy" else ("2" if default_id == "androidmodvip" else ("3" if default_id == "nestproxy" else ("4" if default_id == "5starsproxy" else ("5" if default_id == "mproxy" else ("6" if default_id == "proxyxoay" else "1")))))
    choice = input(f" {Colors.P_PINK}→{Colors.RESET} {Colors.P_WHITE}Nhập lựa chọn [1/2/3/4/5/6] (Enter = {def_num}): {Colors.RESET}").strip()
    if choice == "2":
        return "androidmodvip"
    elif choice == "3":
        return "nestproxy"
    elif choice == "4":
        return "5starsproxy"
    elif choice == "5":
        return "mproxy"
    elif choice == "6":
        return "proxyxoay"
    elif choice == "1":
        return "kiotproxy"
    return default_id

def get_kiotproxy_proxy(token, rotate=True, wait_if_cooldown=False):
    """
    Gọi API Key Xoay KiotProxy:
    - rotate=True: https://api.kiotproxy.com/api/v1/proxies/new?key={key}&region=random
    - rotate=False: https://api.kiotproxy.com/api/v1/proxies/current?key={key}
    """
    if not token:
        return None
    token = str(token).strip()
    
    if rotate:
        url = f"https://api.kiotproxy.com/api/v1/proxies/new?key={token}&region=random"
        try:
            res = requests.get(url, timeout=15, verify=False)
            data = res.json() if res.text else {}
            if res.status_code == 200 and data.get("success") and data.get("data"):
                d = data["data"]
                proxy = d.get("http") or f"{d.get('host')}:{d.get('httpPort')}"
                loc = d.get("location") or ""
                ttc = d.get("ttc", 0)
                info_str = f" [{loc}]" if loc else ""
                log_success(f"[KiotProxy] Lấy Proxy mới thành công: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str} (Đổi tiếp sau {ttc}s)")
                sleep_with_spinner(5, "Chờ Proxy khởi tạo đường truyền")
                return proxy
            else:
                cur_url = f"https://api.kiotproxy.com/api/v1/proxies/current?key={token}"
                cur_res = requests.get(cur_url, timeout=15, verify=False)
                cur_data = cur_res.json() if cur_res.text else {}
                if cur_res.status_code == 200 and cur_data.get("success") and cur_data.get("data"):
                    cd = cur_data["data"]
                    proxy = cd.get("http") or f"{cd.get('host')}:{cd.get('httpPort')}"
                    loc = cd.get("location") or ""
                    ttc = cd.get("ttc", 0)
                    info_str = f" [{loc}]" if loc else ""
                    if wait_if_cooldown and ttc > 0:
                        log_warn(f"[KiotProxy] Chưa tới thời gian đổi IP (còn {ttc}s). Đang đợi {ttc}s để đổi IP mới...")
                        sleep_with_spinner(ttc, "Đang chờ đổi IP KiotProxy")
                        return get_kiotproxy_proxy(token, rotate=True, wait_if_cooldown=False)
                    if proxy:
                        log_warn(f"[KiotProxy] Chưa tới thời gian đổi IP (còn {ttc}s). Dùng Proxy hiện tại: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                        return proxy
                        
                msg = data.get("message") or data.get("error") or "Không thể lấy proxy từ KiotProxy"
                log_error(f"[KiotProxy] Lỗi: {msg}")
                return None
        except Exception as e:
            log_warn(f"Lỗi khi kết nối API KiotProxy: {e}")
            return None
    else:
        url = f"https://api.kiotproxy.com/api/v1/proxies/current?key={token}"
        try:
            res = requests.get(url, timeout=15, verify=False)
            data = res.json() if res.text else {}
            if res.status_code == 200 and data.get("success") and data.get("data"):
                d = data["data"]
                proxy = d.get("http") or f"{d.get('host')}:{d.get('httpPort')}"
                loc = d.get("location") or ""
                ttc = d.get("ttc", 0)
                info_str = f" [{loc}]" if loc else ""
                log_info(f"[KiotProxy] Proxy hiện tại: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str} (Đổi tiếp sau {ttc}s)")
                return proxy
            else:
                return get_kiotproxy_proxy(token, rotate=True, wait_if_cooldown=wait_if_cooldown)
        except Exception as e:
            log_warn(f"Lỗi khi kết nối API KiotProxy: {e}")
            return None

def get_nestproxy_proxy(token, rotate=True, wait_if_cooldown=False):
    """
    Gọi API Key Xoay NestProxy (nestproxy.com):
    - rotate=True: 
        1. POST https://nestproxy.com/api/client/proxy/remove?proxy_key={key}
        2. GET https://nestproxy.com/api/client/proxy/available?proxy_key={key}
    - rotate=False:
        GET https://nestproxy.com/api/client/proxy/available?proxy_key={key}
    """
    if not token:
        return None
    token = str(token).strip()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    if rotate:
        remove_url = f"https://nestproxy.com/api/client/proxy/remove?proxy_key={token}"
        try:
            _KIOT_SESSION.post(remove_url, headers=headers, timeout=15, verify=False)
            time.sleep(1)
        except Exception:
            pass
            
    avail_url = f"https://nestproxy.com/api/client/proxy/available?proxy_key={token}"
    try:
        res = _KIOT_SESSION.get(avail_url, headers=headers, timeout=15, verify=False)
        data = res.json() if res.text else {}
        
        proxy_info = data.get("data") if (isinstance(data, dict) and "data" in data and isinstance(data["data"], dict)) else data
        
        if isinstance(proxy_info, dict) and proxy_info.get("proxy"):
            proxy = proxy_info["proxy"]
            province = proxy_info.get("province", "")
            info_str = f" [{province}]" if province else ""
            if rotate:
                log_success(f"[NestProxy] Lấy Proxy mới thành công: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                sleep_with_spinner(5, "Chờ Proxy khởi tạo đường truyền")
            else:
                log_info(f"[NestProxy] Proxy hiện tại: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
            return proxy
        else:
            msg = data.get("message") or data.get("error") or "Không thể lấy proxy từ NestProxy"
            log_error(f"[NestProxy] Lỗi: {msg}")
            return None
    except Exception as e:
        log_warn(f"Lỗi khi kết nối API NestProxy: {e}")
        return None

_cached_5stars_proxy = None

def get_5starsproxy_proxy(token, loaiproxy="", rotate=True, wait_if_cooldown=False):
    """
    Gọi API Key Xoay 5StarsProxy (5starsproxy.vn):
    - URL: https://5starsproxy.vn/apiv2/doiproxy.php
    - Tự động Random xoay ngẫu nhiên giữa 3 nhà mạng: Viettel, FPT, VNPT
    - Trạng thái thành công: status=100
    - Trạng thái lỗi: 101 (Khóa không tồn tại), 102 (Không đủ tiền), 103 (Hết hàng), 104 (Lỗi không xác định)
    """
    global _cached_5stars_proxy
    if not token:
        return None
    token = str(token).strip()

    if not rotate and _cached_5stars_proxy:
        log_info(f"[5StarsProxy] Sử dụng Proxy hiện tại: {Colors.P_CYAN}{_cached_5stars_proxy}{Colors.RESET}")
        return _cached_5stars_proxy

    if loaiproxy and loaiproxy in FIVE_STARS_PROXY_TYPES:
        types_to_try = [loaiproxy] + [t for t in FIVE_STARS_PROXY_TYPES if t != loaiproxy]
    else:
        types_to_try = random.sample(FIVE_STARS_PROXY_TYPES, len(FIVE_STARS_PROXY_TYPES))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    last_error_msg = None
    for target_isp in types_to_try:
        url = f"https://5starsproxy.vn/apiv2/doiproxy.php?key={token}&loaiproxy={target_isp}"
        try:
            res = requests.get(url, headers=headers, timeout=15, verify=False)
            try:
                data = res.json() if res.text else {}
            except Exception:
                data = {}

            status = data.get("status")
            if status == 100 or str(status) == "100":
                proxy = data.get("proxy")
                ip = data.get("ip")
                port = data.get("port")
                user = data.get("user")
                password = data.get("password")
                loaiproxy_ret = data.get("loaiproxy", "") or target_isp
                idproxy = data.get("idproxy", "")

                if not proxy and ip and port:
                    if user and password:
                        proxy = f"{ip}:{port}:{user}:{password}"
                    else:
                        proxy = f"{ip}:{port}"

                if proxy:
                    _cached_5stars_proxy = proxy
                    info_parts = [f"Mạng: {loaiproxy_ret}"]
                    if idproxy:
                        info_parts.append(f"ID: {idproxy}")
                    info_str = f" [{', '.join(info_parts)}]"

                    prov_tag = f"[5StarsProxy ({loaiproxy_ret})]"
                    if rotate:
                        log_success(f"{prov_tag} Đổi Proxy mới thành công: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                        sleep_with_spinner(5, "Chờ Proxy khởi tạo đường truyền")
                    else:
                        log_info(f"{prov_tag} Proxy hiện tại: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                    return proxy
                else:
                    log_error("[5StarsProxy] Phản hồi thành công nhưng không tìm thấy thông tin Proxy.")
                    return None
            else:
                err_map = {
                    101: "Khóa (Key) không tồn tại hoặc đã hết hạn",
                    102: "Tài khoản không đủ tiền",
                    103: f"Nhà mạng {target_isp} hiện đang hết hàng",
                    104: "Lỗi không xác định từ máy chủ 5StarsProxy"
                }
                status_int = int(status) if str(status).isdigit() else None
                msg = err_map.get(status_int) or data.get("message") or data.get("error") or data.get("msg") or f"Mã trạng thái lỗi: {status}"
                last_error_msg = msg

                ttc = data.get("timeRemaining") or data.get("time") or data.get("next_change") or 0
                if isinstance(ttc, (int, float)) and ttc > 0:
                    if wait_if_cooldown:
                        log_warn(f"[5StarsProxy] Chưa tới thời gian đổi IP (còn {int(ttc)}s). Đang đợi {int(ttc)}s để đổi IP mới...")
                        sleep_with_spinner(int(ttc), "Đang chờ đổi IP 5StarsProxy")
                        return get_5starsproxy_proxy(token, loaiproxy="", rotate=True, wait_if_cooldown=False)
                    elif _cached_5stars_proxy:
                        log_warn(f"[5StarsProxy] Chưa tới thời gian đổi IP (còn {int(ttc)}s). Dùng Proxy hiện tại: {Colors.P_CYAN}{_cached_5stars_proxy}{Colors.RESET}")
                        return _cached_5stars_proxy

                if status_int == 103:
                    log_warn(f"[5StarsProxy] Nhà mạng {target_isp} hết hàng. Đang tự động thử nhà mạng VN khác...")
                    continue
                else:
                    log_error(f"[5StarsProxy] Lỗi ({target_isp}): {msg}")
                    break
        except Exception as e:
            log_warn(f"Lỗi khi kết nối API 5StarsProxy ({target_isp}): {e}")
            last_error_msg = str(e)

    if last_error_msg:
        log_error(f"[5StarsProxy] Không thể lấy proxy: {last_error_msg}")
    return _cached_5stars_proxy if _cached_5stars_proxy else None

_mproxy_cache = {}

def get_mproxy_proxy(token, rotate=True, wait_if_cooldown=False):
    """
    Gọi API Key Xoay MProxy (mproxy.vn):
    - token có thể là API_TOKEN hoặc API_TOKEN|KEY_CODE
    - Lấy danh sách keys: GET https://mproxy.vn/capi/{token}/keys
    - Cấu hình chỉ xoay nhà mạng VN: POST https://mproxy.vn/capi/{token}/key/{key_code}/config (priority_telco: VTT,VIN,MOB)
    - Reset IP: GET https://mproxy.vn/capi/{token}/key/{key_code}/resetIp
    """
    global _mproxy_cache
    if not token:
        return None
    token = str(token).strip()

    api_token = token
    key_code = None
    if "|" in token:
        api_token, key_code = token.split("|", 1)
    elif ":" in token and not ("@" in token or "/" in token):
        parts = token.split(":")
        if len(parts) == 2 and len(parts[0]) > 20:
            api_token, key_code = parts

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    if not key_code or api_token not in _mproxy_cache:
        try:
            keys_url = f"https://mproxy.vn/capi/{api_token}/keys"
            res = requests.get(keys_url, headers=headers, timeout=15, verify=False)
            data = res.json() if res.text else {}
            if data.get("status") == 1 and data.get("data"):
                key_list = data["data"]
                selected_item = None
                if key_code:
                    for item in key_list:
                        if item.get("key_code") == key_code:
                            selected_item = item
                            break
                if not selected_item:
                    for item in key_list:
                        if item.get("status") == 1 and not item.get("finished"):
                            selected_item = item
                            break
                if not selected_item and key_list:
                    selected_item = key_list[0]

                if selected_item:
                    key_code = selected_item.get("key_code")
                    proxy_str = selected_item.get("proxy")
                    _mproxy_cache[api_token] = {
                        "key_code": key_code,
                        "proxy": proxy_str,
                        "server": selected_item.get("server"),
                        "port": selected_item.get("server_port"),
                        "user": selected_item.get("user")
                    }
                    
                    try:
                        cfg_url = f"https://mproxy.vn/capi/{api_token}/key/{key_code}/config"
                        cfg_payload = {"priority_telco": "VTT,VIN,MOB"}
                        requests.post(cfg_url, json=cfg_payload, headers=headers, timeout=10, verify=False)
                    except Exception:
                        pass
                else:
                    log_error("[MProxy.vn] Không tìm thấy Key Proxy nào đang hoạt động trong tài khoản.")
                    return None
            else:
                msg = data.get("message") or "Không thể lấy danh sách key từ MProxy.vn"
                log_error(f"[MProxy.vn] Lỗi API: {msg}")
                return None
        except Exception as e:
            log_warn(f"Lỗi khi kết nối API MProxy.vn: {e}")
            return None

    cached_info = _mproxy_cache.get(api_token, {})
    active_kcode = key_code or cached_info.get("key_code")

    if not rotate and cached_info.get("proxy"):
        cur_p = cached_info["proxy"]
        log_info(f"[MProxy.vn (4G VN)] Proxy hiện tại: {Colors.P_CYAN}{cur_p}{Colors.RESET}")
        return cur_p

    if active_kcode:
        reset_url = f"https://mproxy.vn/capi/{api_token}/key/{active_kcode}/resetIp"
        try:
            res = requests.get(reset_url, headers=headers, timeout=15, verify=False)
            data = res.json() if res.text else {}
            if data.get("status") == 1:
                ret_data = data.get("data") or {}
                proxy_str = ret_data.get("proxy") or cached_info.get("proxy")
                if proxy_str:
                    cached_info["proxy"] = proxy_str
                    _mproxy_cache[api_token] = cached_info
                log_success(f"[MProxy.vn (4G VN: Viettel/Vina/Mobi)] Reset IP thành công: {Colors.P_CYAN}{proxy_str}{Colors.RESET}")
                sleep_with_spinner(5, "Chờ MProxy 4G kết nối lại đường truyền")
                return proxy_str
            else:
                msg = data.get("message") or "Không thể reset IP"
                log_error(f"[MProxy.vn] Lỗi: {msg}")
                if cached_info.get("proxy"):
                    return cached_info["proxy"]
                return None
        except Exception as e:
            log_warn(f"Lỗi khi gọi Reset IP MProxy.vn: {e}")
            return cached_info.get("proxy")

    return cached_info.get("proxy")

_cached_proxyxoay_proxy = None

def get_proxyxoay_proxy(token, nhamang="Random", tinhthanh="0", whitelist="", rotate=True, wait_if_cooldown=False):
    """
    Gọi API Key Xoay ProxyXoay.shop / Proxy.vn:
    https://proxyxoay.shop/api/get.php?key=[keyxoay]&nhamang=[nhamang]&tinhthanh=[tinhthanh]&whitelist=[whitelist]
    - Status 100: Thành công
    - Status 101, 102: Lỗi Key hoặc chưa đủ thời gian đổi
    """
    global _cached_proxyxoay_proxy
    if not token:
        return None
    token = str(token).strip()

    active_key = token
    if "|" in token:
        parts = token.split("|")
        active_key = parts[0].strip()
        if len(parts) > 1 and parts[1].strip():
            nhamang = parts[1].strip()
        if len(parts) > 2 and parts[2].strip():
            tinhthanh = parts[2].strip()
        if len(parts) > 3 and parts[3].strip():
            whitelist = parts[3].strip()

    params = {
        "key": active_key,
        "nhamang": nhamang or "Random",
        "tinhthanh": tinhthanh if tinhthanh is not None else "0",
        "whitelist": whitelist or ""
    }

    url = "https://proxyxoay.shop/api/get.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
        data = res.json() if res.text else {}
        status = data.get("status")

        if status == 100 or str(status) == "100":
            proxy_raw = data.get("proxyhttp") or data.get("proxysocks5") or ""
            if proxy_raw:
                parts = proxy_raw.split(":")
                if len(parts) >= 2 and parts[0] and parts[1]:
                    if len(parts) >= 4 and parts[2] and parts[3]:
                        proxy_clean = f"{parts[0]}:{parts[1]}:{parts[2]}:{parts[3]}"
                    else:
                        proxy_clean = f"{parts[0]}:{parts[1]}"
                else:
                    proxy_clean = proxy_raw.rstrip(":")
            else:
                proxy_clean = None

            if proxy_clean:
                _cached_proxyxoay_proxy = proxy_clean
                isp_ret = data.get("Nha Mang") or nhamang
                loc_ret = data.get("Vi Tri") or ""
                msg_ret = data.get("message") or ""
                exp_ret = data.get("Token expiration date") or ""

                info_items = []
                if isp_ret: info_items.append(f"Mạng: {isp_ret}")
                if loc_ret: info_items.append(f"Vị trí: {loc_ret}")
                if exp_ret: info_items.append(f"Hết hạn: {exp_ret}")
                info_str = f" [{', '.join(info_items)}]" if info_items else ""

                prov_tag = "[ProxyXoay.shop]"
                if rotate:
                    log_success(f"{prov_tag} Lấy Proxy xoay thành công: {Colors.P_CYAN}{proxy_clean}{Colors.RESET}{info_str}")
                    if msg_ret:
                        log_info(f"{prov_tag} Thông báo: {msg_ret}")
                    sleep_with_spinner(5, "Chờ ProxyXoay khởi tạo đường truyền")
                else:
                    log_info(f"{prov_tag} Proxy hiện tại: {Colors.P_CYAN}{proxy_clean}{Colors.RESET}{info_str}")
                return proxy_clean
            else:
                log_error("[ProxyXoay.shop] Phản hồi status 100 nhưng không tìm thấy trường proxyhttp.")
                return None
        else:
            msg = data.get("message") or data.get("msg") or data.get("error") or ""
            ttc_match = re.search(r'(\d+)\s*s', str(msg), re.IGNORECASE)
            ttc = int(ttc_match.group(1)) if ttc_match else 0

            err_map = {
                101: "Key không tồn tại hoặc đã hết hạn (status 101)",
                102: "Key chưa đến thời gian đổi IP hoặc hết lượt (status 102)"
            }
            status_int = int(status) if str(status).isdigit() else None
            err_desc = err_map.get(status_int, f"Mã trạng thái lỗi: {status}")
            if msg:
                err_desc += f" - {msg}"

            if status_int == 102 or ttc > 0:
                if wait_if_cooldown and ttc > 0:
                    log_warn(f"[ProxyXoay.shop] {err_desc}. Đang đợi {ttc}s để đổi IP mới...")
                    sleep_with_spinner(ttc, "Đang chờ đổi IP ProxyXoay")
                    return get_proxyxoay_proxy(token, nhamang=nhamang, tinhthanh=tinhthanh, whitelist=whitelist, rotate=True, wait_if_cooldown=False)
                elif _cached_proxyxoay_proxy:
                    log_warn(f"[ProxyXoay.shop] {err_desc}. Dùng Proxy hiện tại: {Colors.P_CYAN}{_cached_proxyxoay_proxy}{Colors.RESET}")
                    return _cached_proxyxoay_proxy

            log_error(f"[ProxyXoay.shop] Lỗi: {err_desc}")
            return _cached_proxyxoay_proxy if _cached_proxyxoay_proxy else None
    except Exception as e:
        log_warn(f"Lỗi khi kết nối API ProxyXoay.shop: {e}")
        return _cached_proxyxoay_proxy if _cached_proxyxoay_proxy else None

def get_rotating_key_proxy(token, provider="kiotproxy", rotate=True, wait_if_cooldown=False, loaiproxy=None):
    """
    Gọi API Key Xoay theo từng nhà cung cấp (KiotProxy, AndroidModVip, NestProxy, 5StarsProxy, MProxy.vn, ProxyXoay.shop,...):
    - rotate=True: {endpoint}?token={token} hoặc API new/remove+available/doiproxy/resetIp/get.php
    - rotate=False: {endpoint}?token={token}&checkOnly=true hoặc API current/available/keys/get.php
    """
    if not token:
        return None
    token = str(token).strip()
    
    if provider == "kiotproxy":
        return get_kiotproxy_proxy(token, rotate=rotate, wait_if_cooldown=wait_if_cooldown)
    elif provider == "nestproxy":
        return get_nestproxy_proxy(token, rotate=rotate, wait_if_cooldown=wait_if_cooldown)
    elif provider == "5starsproxy":
        if loaiproxy is None:
            try:
                with open(resolve_path('settings.json'), 'r', encoding='utf-8') as f:
                    st = json.load(f)
                    loaiproxy = st.get('5stars_loaiproxy') or st.get('loaiproxy') or ''
            except Exception:
                loaiproxy = ''
        return get_5starsproxy_proxy(token, loaiproxy=loaiproxy or "", rotate=rotate, wait_if_cooldown=wait_if_cooldown)
    elif provider == "mproxy":
        return get_mproxy_proxy(token, rotate=rotate, wait_if_cooldown=wait_if_cooldown)
    elif provider == "proxyxoay":
        return get_proxyxoay_proxy(token, rotate=rotate, wait_if_cooldown=wait_if_cooldown)
        
    provider_info = None
    for p in ROTATING_PROXY_PROVIDERS.values():
        if p["id"] == provider:
            provider_info = p
            break
    if not provider_info:
        provider = "kiotproxy"
        for p in ROTATING_PROXY_PROVIDERS.values():
            if p["id"] == "kiotproxy":
                provider_info = p
                break
        
    prov_name = provider_info["name"]
    base_endpoint = provider_info["url"]
    
    url = f"{base_endpoint}?token={token}"
    if not rotate:
        url += "&checkOnly=true"
        
    try:
        res = requests.get(url, timeout=15, verify=False)
        if res.status_code == 200:
            try:
                data = res.json()
            except Exception:
                log_error(f"[{prov_name}] Không thể đọc dữ liệu JSON từ API.")
                return None
                
            proxy = data.get("proxy")
            msg = data.get("message", "Thành công")
            time_rem = data.get("timeRemaining", 0)
            loc = data.get("location") or ""
            prov_isp = data.get("provider") or ""
            info_parts = [p for p in [loc, prov_isp] if p]
            info_str = f" [{', '.join(info_parts)}]" if info_parts else ""
            
            if data.get("status") == "success":
                if rotate:
                    log_success(f"[{prov_name}] {msg}: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                    sleep_with_spinner(5, "Chờ Proxy khởi tạo đường truyền")
                else:
                    log_info(f"[{prov_name}] {msg}: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                return proxy
            else:
                if wait_if_cooldown and time_rem > 0:
                    log_warn(f"[{prov_name}] Chưa tới thời gian xoay (còn {time_rem}s). Đang đợi {time_rem}s để xoay IP mới...")
                    sleep_with_spinner(time_rem, "Đang chờ xoay IP mới")
                    return get_rotating_key_proxy(token, provider=provider, rotate=True, wait_if_cooldown=False)
                
                if proxy:
                    log_warn(f"[{prov_name}] {msg} (còn {time_rem}s). Sử dụng Proxy hiện tại: {Colors.P_CYAN}{proxy}{Colors.RESET}{info_str}")
                    return proxy
                else:
                    log_error(f"[{prov_name}] Lỗi: {msg}")
                    return None
                    
        elif res.status_code == 400:
            log_error(f"[{prov_name}] Dữ liệu yêu cầu không hợp lệ (Mã 400).")
        elif res.status_code == 401:
            log_error(f"[{prov_name}] Token không hợp lệ hoặc chưa xác thực / hết hạn (Mã 401).")
        elif res.status_code == 403:
            log_error(f"[{prov_name}] Token không có quyền truy cập (Mã 403).")
        elif res.status_code == 404:
            log_error(f"[{prov_name}] Không tìm thấy tài nguyên API (Mã 404).")
        elif res.status_code == 422:
            log_error(f"[{prov_name}] Dữ liệu không hợp lệ (Mã 422).")
        elif res.status_code == 429:
            log_warn(f"[{prov_name}] Quá giới hạn yêu cầu (Mã 429). Đang thử lấy thông tin proxy...")
            if rotate:
                return get_rotating_key_proxy(token, provider=provider, rotate=False)
        elif res.status_code >= 500:
            log_error(f"[{prov_name}] Lỗi Server nhà cung cấp ({res.status_code}).")
    except Exception as e:
        log_warn(f"Lỗi khi kết nối API [{prov_name}]: {e}")
    return None



def get_rotating_key_proxy_vip(token, provider="kiotproxy", rotate=True):
    return get_rotating_key_proxy(token, provider=provider, rotate=rotate)

def detect_proxy_provider_vip(token):
    return detect_proxy_provider(token)


# ============================================================================
# PER-SLOT UA + KEY (luong 1/2 UA Chrome khac nhau, van spoof manh; key rieng)
# ============================================================================
CHROME_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
]


def ua_for_slot(slot_id=1):
    try:
        i = (int(slot_id or 1) - 1) % len(CHROME_UA_POOL)
    except Exception:
        i = 0
    return CHROME_UA_POOL[i]


def slot_key_no(slot_id=1):
    try:
        return 1 if (int(slot_id or 1) % 2 == 1) else 2
    except Exception:
        return 1


def slot_proxy_key(slots, active, slot_id=1):
    n = slot_key_no(slot_id)
    try:
        e = (slots or {}).get(n) or {}
        if e.get("key"):
            return e["key"], e.get("provider") or ""
    except Exception:
        pass
    try:
        e2 = (slots or {}).get(active) or {}
        return e2.get("key", ""), e2.get("provider", "")
    except Exception:
        return "", ""


# ============================================================================
# 2 SLOT KEY PROXY DOC LAP (key 1 / key 2) - chon 1 lan, khoi lon
# ============================================================================
def load_proxy_slots(path=None):
    p = path or resolve_path('settings.json')
    try:
        with open(p, 'r', encoding='utf-8') as f:
            st = json.load(f)
    except Exception:
        st = {}
    slots = {1: {"key": "", "provider": ""}, 2: {"key": "", "provider": ""}}
    for n in (1, 2):
        k = (st.get(f'key_xoay_{n}') or "").strip()
        pr = (st.get(f'proxy_provider_{n}') or "").strip()
        if k:
            slots[n] = {"key": k, "provider": pr or detect_proxy_provider_vip(k)}
    legacy_key = (st.get('key_xoay') or st.get('proxy_api_key') or "").strip()
    if legacy_key and not slots[1]["key"]:
        slots[1] = {"key": legacy_key,
                    "provider": (st.get('proxy_provider') or "").strip() or detect_proxy_provider_vip(legacy_key)}
    try:
        active = int(st.get('active_key_slot', 1))
    except Exception:
        active = 1
    if active not in (1, 2):
        active = 1
    return slots, active


def save_proxy_slot(n, key, provider, path=None):
    p = path or resolve_path('settings.json')
    try:
        with open(p, 'r', encoding='utf-8') as f:
            st = json.load(f)
    except Exception:
        st = {}
    n = 1 if n != 2 else 2
    st.pop('key_xoay', None)
    st.pop('proxy_api_key', None)
    st.pop('proxy_provider', None)
    st[f'key_xoay_{n}'] = (key or "").strip()
    st[f'proxy_provider_{n}'] = (provider or "").strip()
    try:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(st, f, indent=4)
    except Exception:
        pass


def set_active_slot(n, path=None):
    p = path or resolve_path('settings.json')
    try:
        with open(p, 'r', encoding='utf-8') as f:
            st = json.load(f)
    except Exception:
        st = {}
    st['active_key_slot'] = 1 if n != 2 else 2
    try:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(st, f, indent=4)
    except Exception:
        pass


def prompt_proxy_key_selection():
    """Hien 2 slot, cho chon 1/2 hoac dan key moi vao slot active. Tra (key, provider)."""
    slots, active = load_proxy_slots()
    def _short(k):
        k = (k or "").strip()
        return (k[:20] + "...") if k else "trống"
    print()
    print(f"  {ColorPurple1}┌─ PROXY KEY (1 / 2) ───────────────────────────────┐{Reset}")
    for n in (1, 2):
        mark = "●" if n == active else "○"
        k = slots[n]["key"]
        pr = slots[n]["provider"] or (detect_proxy_provider_vip(k) if k else "")
        print(f"  {ColorPurple1}│{Reset} [{mark}] Key {n}: {ColorGreen1}{_short(k)}{Reset} {ColorDarkGray}({pr or '-'}){Reset} {ColorPurple1}│{Reset}")
    print(f"  {ColorPurple1}│{Reset} [3] Direct: {ColorYellow1}không dùng proxy (đi thẳng){Reset} {ColorPurple1}│{Reset}")
    print(f"  {ColorPurple1}│{Reset} {ColorDarkGray}Enter: dùng slot {active} | 1/2: chọn slot | 3: Direct | dán key mới: lưu slot {active} | x: xóa slot {active}{Reset} {ColorPurple1}│{Reset}")
    print(f"  {ColorPurple1}└───────────────────────────────────────────────────┘{Reset}")
    try:
        global FORCE_DIRECT
        sys.stdout.write(f"  {ColorCyan2}{Bold}>> Chọn key [1/2/3/Enter]: {Reset}")
        sys.stdout.flush()
        inp, ok = read_line_eof()
        inp = (inp or "").strip()
        if not ok:
            inp = ""
        if inp == "3":
            FORCE_DIRECT = True
            print_warning("Đã chọn DIRECT - tắt hết proxy (key + file), đi thẳng mạng thật.")
            return "", ""
        FORCE_DIRECT = False
        if inp == "1" or inp == "2":
            set_active_slot(int(inp))
            slots, active = load_proxy_slots()
            k = slots[active]["key"]
            if not k:
                # Slot trong -> hoi co muon nhap key khong (Enter = bo qua)
                try:
                    sys.stdout.write(f"  {ColorYellow1}{Bold}Slot {active} đang trống. Nhập API Key mới (Enter = bỏ qua, dùng Direct): {Reset}")
                    sys.stdout.flush()
                    nk, ok2 = read_line_eof()
                    nk = (nk or "").strip()
                    if ok2 and nk:
                        prov2 = detect_proxy_provider_vip(nk)
                        save_proxy_slot(active, nk, prov2)
                        print_success(f"Đã lưu API Key vào slot {active} ({prov2})")
                        return nk, prov2
                except Exception:
                    pass
                print_info(f"Slot {active} trống - dùng file proxies.txt / Direct")
                return "", ""
            print_success(f"Đã chọn Key {active} ({slots[active]['provider'] or '-'})")
            return k, slots[active]["provider"]
        if inp.lower() == 'x':
            save_proxy_slot(active, "", "")
            print_warning(f"Đã xóa Key {active}, dùng file/Direct.")
            return "", ""
        if inp:
            prov = detect_proxy_provider_vip(inp)
            save_proxy_slot(active, inp, prov)
            print_success(f"Đã lưu API Key vào slot {active} ({prov})")
            return inp, prov
        k = slots[active]["key"]
        if k:
            print_info(f"Dùng Key {active} đã lưu: {k[:12]}...")
        else:
            print_info("Slot trống - dùng file proxies.txt / Direct")
        return k, slots[active]["provider"]
    except Exception:
        pass
    k = slots[active]["key"]
    return k, slots[active]["provider"]

# Alias log vip -> HTCT de khong NameError khi goi tu Bridge thread
try:
    log_info
except NameError:
    log_info = print_info
try:
    log_success
except NameError:
    log_success = print_success
try:
    log_warn
except NameError:
    log_warn = print_warning
try:
    log_error
except NameError:
    log_error = print_error
try:
    log_step
except NameError:
    def log_step(n, m=""):
        print_info(f"[{n}] {m}" if m else f"[{n}]")

_BAD_KEY_UNTIL = {}
_FORCE_ROTATE = set()


def force_slot_rotate(slot_id=1):
    """Bat lan fetch proxy ke tiep cua slot phai xoay IP moi (rotate=True truoc)."""
    try:
        _FORCE_ROTATE.add(slot_key_no(slot_id))
    except Exception:
        pass


def _take_force_rotate(slot_id=1):
    try:
        n = slot_key_no(slot_id)
    except Exception:
        n = 1
    if n in _FORCE_ROTATE:
        try:
            _FORCE_ROTATE.discard(n)
        except Exception:
            pass
        return True
    return False


def _key_cooldown(k):
    try:
        return time.time() < _BAD_KEY_UNTIL.get(k or "", 0)
    except Exception:
        return False


def get_proxy_with_api_fallback(slot=1):
    if FORCE_DIRECT:
        return ""
    try:
        _slots, _act = load_proxy_slots()
    except Exception:
        _slots, _act = None, 1
    cands = []
    if _slots:
        _k, _pr = slot_proxy_key(_slots, _act, slot)
        if _k:
            cands.append((_k, _pr))
    if ACTIVE_KEY_XOAY_VIP and ACTIVE_KEY_XOAY_VIP not in [c[0] for c in cands]:
        cands.append((ACTIVE_KEY_XOAY_VIP, ACTIVE_PROVIDER_VIP))
    force = _take_force_rotate(slot)
    for _k, _pr in cands:
        if _key_cooldown(_k):
            continue  # key vua loi (sai/het han) -> di Direct, khong spam API
        if force:
            p = get_rotating_key_proxy_vip(_k, provider=_pr, rotate=True)
            if p:
                try:
                    _BAD_KEY_UNTIL.pop(_k, None)
                except Exception:
                    pass
                return p
        p = get_rotating_key_proxy_vip(_k, provider=_pr, rotate=False)
        if p:
            try:
                _BAD_KEY_UNTIL.pop(_k, None)
            except Exception:
                pass
            return p
        p2 = get_rotating_key_proxy_vip(_k, provider=_pr, rotate=True)
        if p2:
            try:
                _BAD_KEY_UNTIL.pop(_k, None)
            except Exception:
                pass
            return p2
        try:
            _BAD_KEY_UNTIL[_k] = time.time() + 300
        except Exception:
            pass
    return ""


def rotate_slot_key(slot_id=1):
    try:
        _slots, _act = load_proxy_slots()
    except Exception:
        _slots, _act = None, 1
    if _slots:
        _k, _pr = slot_proxy_key(_slots, _act, slot_id)
        if _k:
            try:
                get_rotating_key_proxy_vip(_k, provider=_pr, rotate=True)
            except Exception:
                pass

# BLACKLIST (port tu blacklist.go - hot reload)
# ============================================================================

BLACKLIST_TEMPLATE = """# ========================================================
# DANH SÁCH MÃ CAMP LỖI / BỎ QUA (BLACKLIST)
# Phân tách bằng dấu phẩy, khoảng trắng hoặc mỗi dòng 1 mã
# Tool tự động cập nhật ngay khi bạn sửa file mà không cần bật lại
# Ví dụ: 199-2, 237-3, 216-2
# ========================================================
"""

_blacklist_lock = threading.Lock()
_blacklist_cache = None
_blacklist_mtime = 0.0


def _blacklist_file_path():
    return resolve_path(BlacklistCampsFileName)


def _load_blacklist_from_disk():
    global _blacklist_mtime
    path = _blacklist_file_path()
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(BLACKLIST_TEMPLATE)
        except Exception:
            pass
        return []
    try:
        st = os.stat(path)
        _blacklist_mtime = st.st_mtime
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    tokens = []
    seen = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        for p in re.split(r"[,;\t ]+", line):
            p = p.strip().lower()
            if len(p) >= 3 and p not in seen:
                seen.add(p)
                tokens.append(p)
    return tokens


def get_blacklist_tokens():
    global _blacklist_cache, _blacklist_mtime
    path = _blacklist_file_path()
    try:
        mtime = os.stat(path).st_mtime
    except Exception:
        mtime = 0.0
    with _blacklist_lock:
        if _blacklist_cache is None or mtime > _blacklist_mtime:
            _blacklist_cache = _load_blacklist_from_disk()
        return list(_blacklist_cache)


def is_campaign_blacklisted(task_key, *extra_args):
    tokens = get_blacklist_tokens()
    if not tokens:
        return False, ""
    clean_target = (task_key or "").strip().lower()
    for token in tokens:
        if not token:
            continue
        if clean_target and (clean_target == token or token in clean_target):
            return True, token
        for arg in extra_args:
            clean_arg = (arg or "").strip().lower()
            if clean_arg and token in clean_arg:
                return True, token
    return False, ""


def add_blacklist_tokens(raw_input):
    parts = re.split(r"[,;\r\n\t ]+", raw_input or "")
    existing = get_blacklist_tokens()
    seen = set(existing)
    new_tokens = []
    for p in parts:
        p = p.strip().lower()
        if len(p) >= 3 and p not in seen:
            seen.add(p)
            new_tokens.append(p)
    if not new_tokens:
        return 0
    path = _blacklist_file_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n" + ", ".join(new_tokens) + "\n")
    except Exception:
        return 0
    global _blacklist_mtime
    with _blacklist_lock:
        _blacklist_cache = list(_blacklist_cache or []) + new_tokens
        try:
            _blacklist_mtime = os.stat(path).st_mtime
        except Exception:
            pass
    return len(new_tokens)


def print_blacklist_summary():
    tokens = get_blacklist_tokens()
    if tokens:
        preview = ", ".join(tokens)
        if len(preview) > 30:
            preview = preview[:27] + "..."
        print_info(f"Blacklist: Đang chặn {len(tokens)} camp [{preview}]")
    else:
        print_info("Blacklist: 0 camp (thêm vào blacklist_camps.txt)")


# ============================================================================
# CAMPAIGN DOMAINS (port tu custom_domains.go - che do manual nhu ban Go hien tai)
# ============================================================================

CAMPAIGN_TEMPLATE = """# ========================================================
# DANH SÁCH TÊN MIỀN CAMPAIGN (Mỗi dòng: Mã_Camp|Tên_Miền)
# Dữ liệu được lưu vĩnh viễn và tự động cập nhật khi bạn nhập
# Ví dụ:
#   199-2|https://linfen.me
#   237-2|https://example.com
# ========================================================
"""

_campaign_lock = threading.Lock()
_skipped_lock = threading.Lock()
_skipped_campaigns = {}
GLOBAL_SKIP_COOLDOWN = 600  # 10 phut (giay)
_moneytask_lock = threading.Lock()
_moneytask_cache = []
_moneytask_last_fetch = 0.0
_github_lock = threading.Lock()
_github_cache = {}
_github_last_fetch = 0.0
prompt_lock = threading.Lock()


def is_system_domain(raw):
    raw = (raw or "").lower().strip()
    for h in ("octolink.", "uptolink.", "linkhuongdan.", "shortearn."):
        if h in raw:
            return True
    return False


def money_task_bearer():
    v = os.environ.get("OCTO_MONEYTASK_TOKEN", "").strip()
    if v:
        if not v.startswith("Bearer "):
            v = "Bearer " + v
        return v
    tok = os.path.join(BASE_DIR, "moneytask_token.txt")
    try:
        if os.path.exists(tok):
            with open(tok, "r", encoding="utf-8") as f:
                s = f.read().strip()
            if s:
                if not s.startswith("Bearer "):
                    s = "Bearer " + s
                return s
    except Exception:
        pass
    # Fallback: JWT token= trong moneytask_cookie.txt user da dan (het han thi bo).
    # Can thiet vi GitHub nasanoper da chet 404 - MT API la nguon camp song duy nhat.
    try:
        c = _mt_load_cookie()
        for part in (c or "").split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, vv = part.split("=", 1)
            if k.strip().lower() == "token" and vv.strip():
                exp = _mt_jwt_exp(c)
                if exp and exp < time.time():
                    break
                return "Bearer " + vv.strip()
    except Exception:
        pass
    return defaultMoneyTaskBearer


def _domain_from_moneytask_alias(alias):
    """Tra domain truc tiep tu alias octo (XtQr) qua guild_link MoneyTask. Tra domain hoac ''."""
    a = (alias or "").strip().lower()
    if not a:
        return ""
    try:
        camps = fetch_money_task_campaigns()
    except Exception:
        return ""
    for c in camps or []:
        try:
            gl = (c.get("guild_link") or "").strip()
            if not gl:
                continue
            if urlparse(gl).path.strip("/").lower() == a:
                web_url = (c.get("website_url") or "").strip()
                if web_url and web_url.lower() != "n/a" and not is_system_domain(web_url):
                    if not web_url.startswith("http://") and not web_url.startswith("https://"):
                        web_url = "https://" + web_url
                    return web_url.rstrip("/")
        except Exception:
            continue
    return ""


def _campaign_file_path():
    return resolve_path(CampaignDomainsFileName)


def load_campaign_domains():
    with _campaign_lock:
        result = {}
        path = _campaign_file_path()
        if not os.path.exists(path):
            try:
                with open(CampaignDomainsFileName, "w", encoding="utf-8") as f:
                    f.write(CAMPAIGN_TEMPLATE)
            except Exception:
                pass
            return result
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    parts = line.split("|", 1)
                    if len(parts) >= 2:
                        key = parts[0].strip()
                        raw_dom = parts[1].strip()
                        norm = _normalize_domain(raw_dom)
                        if key and norm:
                            result[key] = norm
        except Exception:
            pass
        return result


def fetch_money_task_campaigns():
    global _moneytask_cache, _moneytask_last_fetch
    with _moneytask_lock:
        if time.time() - _moneytask_last_fetch < 120 and _moneytask_cache:
            return list(_moneytask_cache)
        try:
            bearer = money_task_bearer()
            r = requests.get(MoneyTaskCampaignsURL, timeout=8, headers={
                "Authorization": bearer,
                "Cookie": "token=" + bearer.replace("Bearer ", ""),
                "Accept": "application/json",
                "User-Agent": GATE_UA,
            }, verify=False)
            if r.status_code == 200:
                data = r.json().get("data") or []
                if data:
                    _moneytask_cache = data
                    _moneytask_last_fetch = time.time()
                    return list(data)
        except Exception:
            pass
        return list(_moneytask_cache)


def fetch_github_domain_cache():
    global _github_cache, _github_last_fetch
    with _github_lock:
        if time.time() - _github_last_fetch < 180 and _github_cache:
            return dict(_github_cache)
        for branch in ("master", "main"):
            raw_url = f"https://raw.githubusercontent.com/{GitHubRepo}/{branch}/{GitHubFile}"
            try:
                r = requests.get(raw_url, timeout=8, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    redirects = data.get("redirects") or {}
                    if redirects:
                        _github_cache = redirects
                        _github_last_fetch = time.time()
                        return dict(redirects)
            except Exception:
                continue
        try:
            api_url = f"https://api.github.com/repos/{GitHubRepo}/contents/{GitHubFile}"
            _gh_headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OctoTool/7.3",
            }
            if GitHubToken:
                _gh_headers["Authorization"] = "token " + GitHubToken
            r = requests.get(api_url, timeout=8, headers=_gh_headers, verify=False)
            if r.status_code == 200:
                content = r.json().get("content", "").replace("\n", "").replace("\r", "")
                decoded = base64.b64decode(content).decode("utf-8", "ignore")
                redirects = json.loads(decoded).get("redirects") or {}
                if redirects:
                    _github_cache = redirects
                    _github_last_fetch = time.time()
                    return dict(redirects)
        except Exception:
            pass
        return dict(_github_cache)


def get_domain_from_money_task(task_key):
    task_key = (task_key or "").strip()
    if not task_key:
        return "", False
    path_norm = task_key.lower()
    for suf in (".html", ".htm"):
        if path_norm.endswith(suf):
            path_norm = path_norm[:-len(suf)]
    camps = fetch_money_task_campaigns()
    if not camps:
        return "", False

    matched = None
    for c in camps:
        gl = (c.get("guild_link") or "").strip()
        if not gl:
            continue
        try:
            gl_path = urlparse(gl).path.strip("/").lower()
        except Exception:
            continue
        if gl_path == path_norm:
            matched = c
            break
    if matched is None:
        for c in camps:
            gl = (c.get("guild_link") or "").strip()
            if not gl:
                continue
            try:
                gl_path = urlparse(gl).path.strip("/").lower()
            except Exception:
                continue
            if path_norm in gl_path or gl_path in path_norm:
                matched = c
                break
    if matched is None:
        for c in camps:
            if (c.get("name") or "").strip().lower() == path_norm or (c.get("keyword") or "").strip().lower() == path_norm:
                matched = c
                break

    if matched:
        web_url = (matched.get("website_url") or "").strip()
        if web_url and web_url.lower() != "n/a" and not is_system_domain(web_url):
            if not web_url.startswith("http://") and not web_url.startswith("https://"):
                web_url = "https://" + web_url
            web_url = web_url.rstrip("/")
            try:
                pu = urlparse(web_url)
                if pu.hostname:
                    return f"{pu.scheme}://{pu.hostname}", True
            except Exception:
                pass
            return web_url, True
    return "", False


def _alias_to_camp_id(alias):
    """Noi alias octo (XtQr) -> camp id (140-2) qua GitHub redirects. Tra camp id hoac ''."""
    a = (alias or "").strip()
    if not a:
        return ""
    try:
        cache = fetch_github_domain_cache()
    except Exception:
        return ""
    for k, v in ((cache or {}).items()):
        try:
            if str(k).strip().lower() == a.lower():
                vv = str(v or "").strip()
                if is_strict_task_key(vv):
                    return vv
                return ""
        except Exception:
            continue
    return ""


def get_domain_from_github_cache(task_key):
    task_key = (task_key or "").strip()
    if not task_key:
        return "", False
    cache = fetch_github_domain_cache()
    dom = cache.get(task_key, "")
    if dom and not is_system_domain(dom):
        if not dom.startswith("http://") and not dom.startswith("https://"):
            dom = "https://" + dom
        return dom.rstrip("/"), True
    return "", False


def _normalize_domain(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    # strip markdown **  vd: **heynode.io** -> heynode.io
    raw = raw.strip("*").strip()
    if not raw:
        return ""
    # loai bo ky tu rac dau/cuoi
    raw = raw.strip().strip("'\"").strip()
    if not raw or is_system_domain(raw):
        return ""
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw
    raw = raw.rstrip("/")
    try:
        pu = urlparse(raw)
        host = (pu.hostname or "").strip().lower()
        if not host or "." not in host or host.endswith(".") or len(host) < 4:
            return ""
        # loai domain rac nhu valcc. (thieu TLD day du)
        if host.count(".") == 1 and len(host.split(".")[-1]) < 2:
            return ""
        return f"{pu.scheme}://{host}"
    except Exception:
        return ""


_camp_domains_cache = {}
_camp_domains_mtime = 0.0
_camp_domains_lock = threading.Lock()


def _load_camp_domains_dict():
    global _camp_domains_mtime
    # Thu tu: file goc Downloads truoc, file htct_py sau de sua trong htct_py se thang (last wins)
    candidates = [
        r"C:\Users\hnqhs\Downloads\camp id url.md",
        os.path.join(BASE_DIR, "camp id url.md"),
        resolve_path(CampaignDomainsFileName),
        resolve_path("camp id url.md"),
    ]
    merged = {}
    latest_mtime = 0.0
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            mtime = os.stat(path).st_mtime
            latest_mtime = max(latest_mtime, mtime)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    if "|" not in line:
                        continue
                    parts = line.split("|", 1)
                    key = parts[0].strip()
                    raw_dom = parts[1].strip() if len(parts) > 1 else ""
                    if not key or not raw_dom:
                        continue
                    norm = _normalize_domain(raw_dom)
                    if norm:
                        merged[key] = norm
        except Exception:
            continue
    _camp_domains_mtime = latest_mtime
    return merged, latest_mtime


def _get_domain_from_local_file(task_key):
    global _camp_domains_cache, _camp_domains_mtime
    task_key = (task_key or "").strip()
    if not task_key:
        return ""
    # hot-reload khi file doi
    try:
        cur_mtime = 0.0
        for p in [resolve_path("camp id url.md"), resolve_path(CampaignDomainsFileName), r"C:\Users\hnqhs\Downloads\camp id url.md"]:
            if p and os.path.exists(p):
                cur_mtime = max(cur_mtime, os.stat(p).st_mtime)
        need_reload = cur_mtime > _camp_domains_mtime or not _camp_domains_cache
    except Exception:
        need_reload = not _camp_domains_cache

    if need_reload:
        with _camp_domains_lock:
            # double-check
            try:
                cur2 = 0.0
                for p in [resolve_path("camp id url.md"), resolve_path(CampaignDomainsFileName), r"C:\Users\hnqhs\Downloads\camp id url.md"]:
                    if p and os.path.exists(p):
                        cur2 = max(cur2, os.stat(p).st_mtime)
                if cur2 > _camp_domains_mtime or not _camp_domains_cache:
                    d, mt = _load_camp_domains_dict()
                    _camp_domains_cache = d
                    _camp_domains_mtime = mt
            except Exception:
                pass

    # tim chinh xac, khong phan biet hoa thuong
    for k, v in _camp_domains_cache.items():
        if k.strip().lower() == task_key.lower():
            return v
    return ""


def get_campaign_domain(task_key):
    task_key = (task_key or "").strip()
    if not task_key:
        return "", False
    # 1. File local camp id url.md / campaign_domains.txt (uu tien so 1)
    dom = _get_domain_from_local_file(task_key)
    if dom:
        return dom, True
    # 2. Thu xem totreview bien the
    alt = ""
    if task_key.startswith("totreview-"):
        alt = task_key[len("totreview-"):]
    else:
        alt = "totreview-" + task_key
    dom2 = _get_domain_from_local_file(alt)
    if dom2:
        return dom2, True
    # 3. GitHub cache (fallback)
    dom3, ok3 = get_domain_from_github_cache(task_key)
    if ok3 and dom3:
        return dom3, True
    # 4. MoneyTask API (fallback)
    dom4, ok4 = get_domain_from_money_task(task_key)
    if ok4 and dom4:
        return dom4, True
    return "", False


def _read_campaign_file_raw():
    path = _campaign_file_path()
    header_lines = []
    doms = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        header_lines.append(raw_line.rstrip("\n"))
                        continue
                    parts = line.split("|")
                    if len(parts) >= 2:
                        k = parts[0].strip()
                        v = parts[1].strip()
                        if k and v:
                            doms[k] = v
        except Exception:
            pass
    return path, header_lines, doms


def save_campaign_domain(task_key, domain):
    if not task_key or not domain or is_system_domain(domain):
        return
    domain = domain.strip()
    if not domain.startswith("http://") and not domain.startswith("https://"):
        domain = "https://" + domain
    domain = domain.rstrip("/")

    with _campaign_lock:
        path, header_lines, doms = _read_campaign_file_raw()
        doms[task_key] = domain
        try:
            with open(path, "w", encoding="utf-8") as f:
                if header_lines:
                    f.write("\n".join(header_lines) + "\n")
                else:
                    f.write("# ========================================================\n")
                    f.write("# DANH SÁCH TÊN MIỀN CAMPAIGN (Mỗi dòng: Mã_Camp|Tên_Miền)\n")
                    f.write("# ========================================================\n")
                for k, v in doms.items():
                    f.write(f"{k}|{v}\n")
        except Exception:
            pass


def delete_campaign_domain(task_key):
    if not task_key:
        return
    with _campaign_lock:
        path, header_lines, doms = _read_campaign_file_raw()
        if task_key in doms:
            del doms[task_key]
        try:
            with open(path, "w", encoding="utf-8") as f:
                for h in header_lines:
                    f.write(h + "\n")
                for k, v in doms.items():
                    f.write(f"{k}|{v}\n")
        except Exception:
            pass


def _is_skipped_locked(key):
    t = _skipped_campaigns.get(key)
    if t is None:
        return False
    if time.time() - t < GLOBAL_SKIP_COOLDOWN:
        return True
    del _skipped_campaigns[key]
    return False


def is_campaign_temporarily_skipped(task_key):
    if not task_key:
        return False
    with _skipped_lock:
        if _is_skipped_locked(task_key):
            return True
        if task_key.startswith("totreview-"):
            return _is_skipped_locked(task_key[len("totreview-"):])
        return _is_skipped_locked("totreview-" + task_key)


def mark_campaign_skipped(task_key):
    if not task_key:
        return
    now = time.time()
    with _skipped_lock:
        _skipped_campaigns[task_key] = now
        if task_key.startswith("totreview-"):
            _skipped_campaigns[task_key[len("totreview-"):]] = now
        else:
            _skipped_campaigns["totreview-" + task_key] = now


def prompt_manual_domain(slot_id, task_key, failed_domain="", guide_url=""):
    with prompt_lock:
        dom_saved, _ok = get_campaign_domain(task_key)
        if dom_saved and dom_saved != failed_domain:
            print_slot_info(slot_id, f"📂 Đã tìm thấy domain [{dom_saved}] cho camp [{task_key}] từ slot khác!")
            return dom_saved, True
        if is_campaign_temporarily_skipped(task_key):
            print_slot_warning(slot_id, f"⛔ Camp [{task_key}] đã bị bỏ qua bởi slot khác -> Bỏ qua ngay.")
            return "", False

        issue = f"Nhiệm vụ [{task_key}] chưa có web đích trong danh sách!"
        if failed_domain:
            issue = f"Tên miền cũ [{failed_domain}] không phản hồi!"
        print_prompt_box(slot_id, "CẦN NHẬP TÊN MIỀN WEB ĐÍCH", issue, guide_url)

        cooldown_min = int(GLOBAL_SKIP_COOLDOWN / 60)
        print_slot_info(slot_id, f"Cho nhap domain web dich (KHONG gioi han thoi gian). Go 'skip' de bo qua camp [{task_key}].")
        sys.stdout.write(f"  {ColorCyan2}{Bold}>> Nhập domain: {Reset}")
        sys.stdout.flush()
        text, got_input = read_line_eof()
        if not got_input:
            print()
            print_slot_warning(slot_id, f"Stdin dong -> Tu dong bo qua campaign [{task_key}] trong {cooldown_min} phut.")
            mark_campaign_skipped(task_key)
            return "", False

        input_domain = text.strip()
        low = input_domain.lower()
        if not input_domain or low in ("skip", "s", "b", "2", "bo qua", "bỏ qua"):
            print_slot_warning(slot_id, f"Đã chọn bỏ qua campaign [{task_key}] trong {cooldown_min} phút.")
            mark_campaign_skipped(task_key)
            return "", False

        if is_system_domain(input_domain):
            print_slot_warning(slot_id, f"Domain [{input_domain}] là link hệ thống, không phải web đích! Tự động bỏ qua.")
            mark_campaign_skipped(task_key)
            return "", False

        dom = input_domain
        if not dom.startswith("http://") and not dom.startswith("https://"):
            dom = "https://" + dom
        dom = dom.rstrip("/")
        try:
            pu = urlparse(dom)
            if pu.hostname:
                clean_input = f"{pu.scheme}://{pu.hostname}"
                save_campaign_domain(task_key, clean_input)
                print_slot_success(slot_id, f"Đã lưu vĩnh viễn: [{task_key}|{clean_input}] vào {CampaignDomainsFileName}!")
                return clean_input, True
        except Exception:
            pass

        print_slot_warning(slot_id, f"Định dạng domain [{dom}] không hợp lệ -> Bỏ qua.")
        mark_campaign_skipped(task_key)
        return "", False


# ============================================================================
# MONEYTASK AUTO FETCH (tu dong lay url octolink nhiem vu - nhu moi truong that)
# GET /api/tasks tra pubcrypto.cjk ma hoa + can x-pubcrypto-envelope/x-ac-token
# dong -> KHONG goi requests thu cong; mo Playwright + cookie that de chinh
# page JS handshake/giai ma, minh chi bat POST /api/tasks/accept JSON
# {shortenedUrl, taskUrl, waitSeconds, endTime} roi nem vao run_with_slot.
# ============================================================================

MT_TASKS_URL = "https://moneytask.top/app/tasks/link-rut-gon"
MT_COOKIE_FILE = "moneytask_cookie.txt"
MT_PROFILE_DIR = os.path.join(BASE_DIR, "mt_profile")


def _mt_launch_ctx(pw, extra_args=None, headed=None):
    """Chromium PERSISTENT profile cho MoneyTask: giu cf_clearance sau khi giai tay 1 lan.
    headed=True/False ep hien/an; None = theo --view (VIEW_MODE)."""
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--mute-audio",
            "--disable-blink-features=AutomationControlled",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
    for a in (extra_args or []):
        if a not in args:
            args.append(a)
    try:
        os.makedirs(MT_PROFILE_DIR, exist_ok=True)
    except Exception:
        pass
    show = VIEW_MODE if headed is None else bool(headed)
    ctx = pw.chromium.launch_persistent_context(
        MT_PROFILE_DIR,
        headless=not show,
        args=args,
        user_agent=MT_REAL_UA,
        viewport={"width": 1920, "height": 1080},
        locale="vi-VN",
        timezone_id="Asia/Ho_Chi_Minh",
        ignore_https_errors=True,
    )
    # CF solver: scan + tag widget Turnstile ngay tu document-start (chi tag, khong click gia)
    try:
        _cfp = os.path.join(SCRIPTS_DIR, "cf_solver.js")
        if os.path.exists(_cfp):
            with open(_cfp, "r", encoding="utf-8") as _f:
                ctx.add_init_script(_f.read())
    except Exception:
        pass
    return ctx
# UA that lay tu log trinh duyet that (Chrome 152 Win64) - khop sec-ch-ua
MT_REAL_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")
MT_SEC_CH_UA = '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"'
# DEPRECATED: nut that la canvas (khong chu) -> do text se vo trung honeypot.
# Giu hang so cho tuong thich; list/click that dung _MT_LIST_JS + [data-mt-idx].
MT_ACCEPT_RE = re.compile("Nhận|Nhận nhiệm vụ|Thực Hiện|Thực hiện|thuc hien|Accept|làm nhiệm vụ|lam nhiem vu", re.I)
MT_ACCEPT_JS_RE = "nhận|nhan|accept|thực hiện|thuc hien|làm nhiệm vụ|lam nhiem vu"

_mt_cookie_cache = {"value": "", "loaded": False}
_mt_cookie_lock = threading.Lock()


def _mt_load_cookie():
    with _mt_cookie_lock:
        if _mt_cookie_cache["loaded"]:
            return _mt_cookie_cache["value"]
        p = resolve_path(MT_COOKIE_FILE)
        v = ""
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    v = f.read().strip()
        except Exception:
            v = ""
        _mt_cookie_cache["value"] = v
        _mt_cookie_cache["loaded"] = True
        return v


def _mt_cache_cookie(v):
    """Chi nap RAM (khong ghi file) - file chi ghi sau khi cookie chay duoc."""
    v = (v or "").strip()
    with _mt_cookie_lock:
        _mt_cookie_cache["value"] = v
        _mt_cookie_cache["loaded"] = True


def _mt_save_cookie(v):
    v = (v or "").strip()
    _mt_cache_cookie(v)
    try:
        with open(resolve_path(MT_COOKIE_FILE), "w", encoding="utf-8") as f:
            f.write(v)
    except Exception:
        pass


def _mt_jwt_exp(cookie_str):
    """Doc han exp tu JWT token= trong cookie (khong verify). Tra timestamp hoac None."""
    try:
        for part in (cookie_str or "").split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            if k.strip().lower() != "token":
                continue
            segs = v.strip().split(".")
            if len(segs) != 3:
                return None
            import base64 as _b64
            pay = segs[1] + "=" * (-len(segs[1]) % 4)
            data = json.loads(_b64.urlsafe_b64decode(pay).decode("utf-8", "ignore"))
            exp = int(data.get("exp") or 0)
            return exp or None
    except Exception:
        return None


def _mt_parse_cookie(s):
    out = []
    for part in (s or "").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k or k.startswith("$"):
            continue
        if k.lower() in ("expires", "max-age", "path", "domain", "samesite", "secure", "httponly"):
            continue
        out.append({"name": k, "value": v, "url": "https://moneytask.top"})
    return out


def _mt_prompt_cookie(saved):
    print_prompt_box(0, "MONEYTASK COOKIE",
                     "Dan Cookie moneytask.top (F12 > Application > Cookies > copy, hoac header Cookie), Enter = dung da luu",
                     MT_TASKS_URL)
    if saved:
        print_slot_info(0, "Da co cookie luu (%d ky tu). Enter = dung lai, dan moi = ghi de.", len(saved))
    sys.stdout.write(f"  {ColorCyan2}{Bold}>> Dan Cookie (Enter = bo qua): {Reset}")
    sys.stdout.flush()
    text, ok = read_line_eof()
    if not ok:
        return ""
    text = (text or "").strip().strip('"').strip("'")
    if not text:
        return saved
    if "token=" not in text:
        print_slot_warning(0, "Cookie dan vao thieu token=... co the het han, van thu.")
    # KHONG luu o day - chi luu sau khi cookie chay duoc (thay task list)
    return text


_MT_LIST_JS = r"""(() => {
  // Chi liet ke NUT THAT: div[role=button] chua canvas + nam TRONG viewport.
  // LOAI honeypot/decoy: [data-honeypot] [data-decoy] [data-decoy-role] [data-hpx*]
  // [data-autoclick] [data-auto-clicker] aria-hidden=true display:none off-screen.
  // (Nut that khong co chu - la canvas - nen do text se vo trung moi.)
  const out = [];
  const seen = new Set();
  const hasBadAttr = (el) => {
    try {
      const names = el.getAttributeNames ? el.getAttributeNames() : [];
      for (const a of names) {
        const al = (a + '').toLowerCase();
        if (al === 'data-honeypot' || al === 'data-decoy' || al === 'data-decoy-role' ||
            al === 'data-autoclick' || al === 'data-auto-clicker' || al.indexOf('data-hpx') === 0) return true;
      }
    } catch (e) {}
    return false;
  };
  const isHidden = (el) => {
    try {
      const cs = window.getComputedStyle(el);
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse')) return true;
    } catch (e) {}
    try { if (el.getAttribute && el.getAttribute('aria-hidden') === 'true') return true; } catch (e) {}
    return false;
  };
  const inViewport = (el) => {
    try {
      const r = el.getBoundingClientRect();
      if (!r || r.width <= 0 || r.height <= 0) return false;
      const vw = window.innerWidth || 1920, vh = window.innerHeight || 1080;
      return r.bottom > 0 && r.right > 0 && r.left < vw && r.top < vh && r.left >= -2 && r.top >= -2;
    } catch (e) { return false; }
  };
  const cands = Array.from(document.querySelectorAll('div[role="button"], button, a[role="button"], input[type="button"], input[type="submit"]'));
  for (const b of cands) {
    if (hasBadAttr(b) || isHidden(b)) continue;
    if (!inViewport(b)) continue;
    const hasCanvas = !!(b.querySelector && b.querySelector('canvas'));
    let t = ((b.getAttribute && b.getAttribute('aria-label')) || b.innerText || b.textContent || b.value || '').trim().replace(/\s+/g, ' ');
    let name = '';
    const alm = t.match(/^(thuc hien nhiem vu|bam de thuc hien|th\u1ef1c hi\u1ec7n nhi\u1ec7m v\u1ee5|b\u1ea5m \u0111\u1ec3 th\u1ef1c hi\u1ec7n)\s+(.+)$/i);
    if (alm && alm[2]) name = alm[2].trim();
    if (!hasCanvas) {
      if (!/nh\u1eadn|nhan|accept|l\u00e0m nhi\u1ec7m v\u1ee5|lam nhiem vu|th\u1ef1c hi\u1ec7n|thuc hien/i.test(t)) continue;
    }
    if (!name) {
      const card = (b.closest && b.closest('[class*="card"],[class*="task"],[class*="job"],[class*="item"],li,tr,[role="row"]')) || b.parentElement;
      if (card) {
        const heads = Array.from(card.querySelectorAll('h1,h2,h3,h4,h5,h6,[class*="title"],[class*="name"]'));
        for (const h of heads) {
          const ht = ((h.innerText || h.textContent || '') + '').trim().replace(/\s+/g, ' ');
          if (ht && ht.length > 1 && ht.length < 120 && ht.toLowerCase() !== t.toLowerCase()) { name = ht.slice(0, 90); break; }
        }
        if (!name) {
          const lines = ((card.innerText || card.textContent || '') + '').split('\n').map(s => s.trim()).filter(s => s && s !== t && s.length > 1 && s.length < 120);
          if (lines.length) name = lines[0].slice(0, 90);
        }
      }
    }
    if (!name) name = t.slice(0, 90);
    if (!name) continue;
    const key = name.slice(0, 40);
    if (seen.has(key)) continue;
    seen.add(key);
    try { b.dataset.mtIdx = String(out.length); } catch (e) {}
    out.push({text: (hasCanvas ? 'Bam thuc hien' : t.slice(0, 40)), name: name.slice(0, 90), visible: true});
  }
  return JSON.stringify(out);
})();"""


_MT_DISMISS_JS = r"""([pt]) => {
  // Diem [x,y] giua nut that dang bi che:
  // - Trung nut that -> null.
  // - Modal THAT (div.fixed/[role=dialog]/*modal*/*overlay*/*backdrop*/*popup*,
  //   hoac rect phu gan full viewport) -> tag nut tat that -> 'close', khong co -> 'esc'.
  // - Phan tu thuong (sticky header...) che -> 'recenter' (scroll nut ra giua man hinh).
  //   CAM tag svg lung tung (vd nut theme-toggle trong header).
  const x = pt[0], y = pt[1];
  let el = null;
  try { el = document.elementFromPoint(x, y); } catch (e) { el = null; }
  const out = {action: null, info: '', bx: 0, by: 0};
  const done = () => JSON.stringify(out);
  if (!el) return done();
  try {
    if ((el.hasAttribute && el.hasAttribute('data-mt-idx')) ||
        (el.closest && el.closest('[data-mt-idx]'))) return done();
  } catch (e) {}
  let ov = null;
  try {
    ov = el.closest && el.closest('div.fixed, [role="dialog"], [class*="modal"], [class*="overlay"], [class*="backdrop"], [class*="popup"]');
  } catch (e) { ov = null; }
  let fullCover = false;
  try {
    const er = el.getBoundingClientRect();
    const vw = window.innerWidth || 1920, vh = window.innerHeight || 1080;
    fullCover = er && er.width >= vw * 0.7 && er.height >= vh * 0.4;
  } catch (e) {}
  if (!ov && !fullCover) { out.action = 'recenter'; return done(); }
  const scope = ov || el;
  try { out.info = ((scope.className || '') + '|' + (scope.getAttribute('role') || '')).slice(0, 120); } catch (e) {}
  // Diem backdrop: ria trai overlay (vung dem p-4, ngoai dialog giua) de click tat modal.
  try {
    const r = scope.getBoundingClientRect();
    out.bx = Math.max(4, r.left + 8);
    out.by = Math.max(4, r.top + Math.min(r.height / 2, 160));
  } catch (e) {}
  const btns = [];
  try {
    for (const c of Array.from(scope.querySelectorAll('button, [role="button"], a'))) {
      if (c.hasAttribute && (c.hasAttribute('data-honeypot') || c.hasAttribute('data-decoy') ||
          c.hasAttribute('data-decoy-role') || c.getAttribute('aria-hidden') === 'true')) continue;
      btns.push(c);
    }
  } catch (e) {}
  // Modal quang cao tai hien: tick "Khong hien thi lai" TRUOC khi Dong de diet vinh vien.
  const NOSHOW_RE = /không hiển thị lại|khong hien thi lai|không hiện|khong hien|don't show|do not show|2 ngày|2 ngay/i;
  const tagNoshow = () => {
    try {
      const boxes = Array.from(scope.querySelectorAll('input[type="checkbox"]'));
      for (const bx of boxes) {
        let lab = '';
        try {
          const lb = bx.closest ? bx.closest('label') : null;
          lab = ((lb && (lb.innerText || lb.textContent)) || bx.getAttribute('aria-label') || '') + '';
        } catch (e) {}
        if (lab && NOSHOW_RE.test(lab)) {
          try { bx.dataset.mtCheck = '1'; } catch (e) {}
          out.check = true;
          return true;
        }
      }
      // checkbox tran (khong label ro): chi 1 checkbox duy nhat trong modal thong bao
      if (boxes.length === 1) {
        try { boxes[0].dataset.mtCheck = '1'; } catch (e) {}
        out.check = true;
        return true;
      }
    } catch (e) {}
    return false;
  };
  const CLOSE_RE = /đóng|dong|close|hủy|huy|cancel|bỏ qua|bo qua|đồng ý|dong y|^x$|×|thử lại|thu lai|để sau|de sau|tắt|tat/i;
  for (const c of btns) {
    let t = '';
    try { t = ((c.innerText || c.textContent || c.getAttribute('aria-label') || '') + '').trim(); } catch (e) {}
    if (t && CLOSE_RE.test(t)) {
      try { c.dataset.mtClose = '1'; } catch (e) {}
      tagNoshow();
      out.action = 'close'; out.info += ' -> nut "' + t.slice(0, 30) + '"' + (out.check ? ' + tick khong-hien-lai' : ''); return done();
    }
  }
  // Nut X chi icon (svg): CHI khi scope la modal that, tranh tag nut theme header.
  if (ov) {
    for (const c of btns) {
      let t = '';
      try { t = ((c.innerText || c.textContent || '') + '').trim(); } catch (e) {}
      if (!t && c.querySelector && c.querySelector('svg,path')) {
        try { c.dataset.mtClose = '1'; } catch (e) {}
        out.action = 'close'; out.info += ' -> nut X icon'; return done();
      }
    }
  }
  out.action = 'esc';
  return done();
}"""


def _mt_scroll_center(page, loc):
    """Scroll nut ra GIUA viewport (tranh sticky header de len nut sau scroll)."""
    try:
        loc.evaluate("(el) => { try { el.scrollIntoView({block: 'center', inline: 'center'}); } catch (e) {} }")
        return True
    except Exception:
        pass
    try:
        loc.scroll_into_view_if_needed(timeout=5000)
        return True
    except Exception:
        return False


def _mt_trusted_click(page, loc, timeout=15000):
    """Re chuot Bezier (nguoi) + click trusted cua Playwright (isTrusted=true)."""
    loc.wait_for(state="visible", timeout=10000)
    _mt_scroll_center(page, loc)
    try:
        bb = loc.bounding_box(timeout=5000)
    except Exception:
        bb = None
    if bb:
        _mt_human_move(page, bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
    loc.click(timeout=timeout)


def _mt_dismiss_overlay(page, loc):
    """Neu co gi che nut that: modal -> nut tat that (trusted) / ESC / click backdrop (trusted);
    header/thuong -> recenter. Tra (handled, detail) de log."""
    try:
        bb = loc.bounding_box(timeout=3000)
    except Exception:
        return False, "no bbox"
    if not bb:
        return False, "no bbox"
    cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    try:
        raw = page.evaluate(_MT_DISMISS_JS, [cx, cy]) or '{"action": null}'
        res = json.loads(raw) or {}
        act = res.get("action")
    except Exception as e:
        return False, f"evaluate loi: {e}"[:100]
    info = str(res.get("info", ""))[:120]
    if act == "close":
        if res.get("check"):
            try:
                _mt_trusted_click(page, page.locator("[data-mt-check='1']"), timeout=8000)
                info += " [da tick khong-hien-lai]"
            except Exception as e:
                info += f" [tick loi {e}"[:60] + "]"
        try:
            _mt_trusted_click(page, page.locator("[data-mt-close='1']"), timeout=8000)
            return True, f"close {info}"
        except Exception as e:
            return True, f"close loi {e}"[:100]
    if act == "esc":
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        try:
            bx, by = float(res.get("bx") or 0), float(res.get("by") or 0)
        except Exception:
            bx, by = 0, 0
        if bx > 0 and by > 0:
            try:
                _mt_human_move(page, bx, by)
                page.mouse.click(bx, by)
                return True, f"esc + backdrop ({int(bx)},{int(by)}) {info}"
            except Exception:
                pass
        return True, f"esc {info}"
    if act == "recenter":
        _mt_scroll_center(page, loc)
        return True, "recenter"
    return False, "trung nut that/khong overlay"


# ============================================================================
# MT AUTO LOOP (cookie 1 lan -> tu mt -> tu chon 1; blacklist 5x/xoay proxy;
# id chi so-so; demo -> goi lai link gan nhat; finish xong tu mt tiep)
# ============================================================================
RE_STRICT_TASK_KEY = re.compile(r"^\d+-\d+$")
RE_STRICT_TOTREVIEW = re.compile(r"^totreview-.+")

_octo_history = []
_octo_history_lock = threading.Lock()
_blacklist_attempts = {}
_blacklist_attempts_lock = threading.Lock()


def is_strict_task_key(s):
    s = (s or "").strip()
    if not s:
        return False
    return bool(RE_STRICT_TASK_KEY.match(s) or RE_STRICT_TOTREVIEW.match(s))


def remember_octo_link(url):
    u = (url or "").strip()
    if not u:
        return
    lu = u.lower()
    if not any(k in lu for k in ("octolink.", "trafficvip.", "up2link", "uptolink", "linkhuongdan")):
        return
    with _octo_history_lock:
        if not _octo_history or _octo_history[-1] != u:
            _octo_history.append(u)
        del _octo_history[:-10]


def recall_last_octo():
    with _octo_history_lock:
        return _octo_history[-1] if _octo_history else ""


def _blacklist_should_retry(key):
    with _blacklist_attempts_lock:
        n = _blacklist_attempts.get(key, 0) + 1
        _blacklist_attempts[key] = n
        if n <= 5:
            return True, n
        return False, n


def _blacklist_reset(key):
    with _blacklist_attempts_lock:
        _blacklist_attempts.pop(key, None)


def mt_auto_enabled():
    try:
        with open(resolve_path('settings.json'), 'r', encoding='utf-8') as f:
            st = json.load(f)
        v = st.get('mt_auto', True)
        if isinstance(v, str):
            return v.strip().lower() not in ("0", "false", "no", "off")
        return bool(v)
    except Exception:
        return True


def mt_set_auto(on):
    try:
        p = resolve_path('settings.json')
        try:
            with open(p, 'r', encoding='utf-8') as f:
                st = json.load(f)
        except Exception:
            st = {}
        st['mt_auto'] = bool(on)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(st, f, indent=4)
    except Exception:
        pass


_RETRYABLE_MARKS = ["mã hóa demo", "Session không hợp lệ", "proxy fail-fast",
                    "Thử lại", "làm mới mã hóa", "Hết hạn", "hết thời gian chờ bypass"]
_DEMO_MARKS = ["mã hóa demo", "Session không hợp lệ", "hết thời gian chờ bypass"]


def is_retryable_err(e):
    return any(x in (e or "") for x in _RETRYABLE_MARKS)


def is_demo_err(e):
    return any(x in (e or "") for x in _DEMO_MARKS)


# Loi tang proxy chet (server chua tung phan hoi) -> duoc xoay IP.
# Loi server da tra ve (job not found, wait, ...) -> GIU NGUYEN IP keo mat job.
_PROXY_LEVEL_MARKS = ["proxy", "tunnel", "ERR_PROXY", "ERR_TUNNEL", "connection refused",
                      "econnrefused", "socks", "407", "proxy auth", "Failed to establish",
                      "NS_ERROR_PROXY", "net::ERR_"]


def is_proxy_level_err(e):
    el = (e or "").lower()
    return any(x.lower() in el for x in _PROXY_LEVEL_MARKS)


# Session chet (server tra demo/khong hop le) -> job cu chet roi nen DUOC xoay IP
# + mo cong lai tu dau. Timeout thong thuong (het han continue...) thi VAN GIU IP.
_SESSION_DEAD_MARKS = ["mã hóa demo", "Session không hợp lệ"]


def is_session_dead_err(e):
    return any(x in (e or "") for x in _SESSION_DEAD_MARKS)


_MT_CF_MARKERS = ("cf-challenge", "turnstile", "just a moment", "verify you are human",
                   "challenge-platform", "checking your browser", "attention required")


_MT_CF_CLICK_JS = r"""(() => {
  // Tim widget Turnstile/CF challenge de click THAT (isTrusted=true) nhu tay.
  // Tag nutOI wrapper bang data-mt-turnstile. Khong thay -> {found:false}.
  const out = {found: false};
  const inVp = (el) => {
    try {
      const r = el.getBoundingClientRect();
      if (!r || r.width <= 0 || r.height <= 0) return false;
      const vw = window.innerWidth || 1920, vh = window.innerHeight || 1080;
      return r.bottom > 0 && r.right > 0 && r.left < vw && r.top < vh;
    } catch (e) { return false; }
  };
  try {
    const sels = ['#turnstile-wrapper', '[id*="turnstile"]',
      'iframe[src*="challenges.cloudflare.com"]', 'iframe[src*="turnstile"]',
      '.cf-turnstile', '.challenge-container', '#cf-challenge',
      '[data-sitekey]', '.turnstile-container', '.captcha-container',
      'div[class*="turnstile"]', 'div[class*="challenge"]',
      'input[type="checkbox"][id*="cf"]'];
    for (const s of sels) {
      const els = Array.from(document.querySelectorAll(s));
      for (const el of els) {
        let box = el;
        try {
          if (el.tagName === 'IFRAME' && el.parentElement) box = el.parentElement;
          if (box.tagName === 'DIV' && box.parentElement && box.parentElement.id &&
              box.parentElement.id.indexOf('turnstile') >= 0) box = box.parentElement;
        } catch (e) {}
        if (!inVp(box)) continue;
        try { box.dataset.mtTurnstile = '1'; } catch (e) {}
        out.found = true;
        return JSON.stringify(out);
      }
    }
  } catch (e) {}
  return JSON.stringify(out);
})();"""


def _mt_auto_pick(tasks):
    """Auto mode: chon task Uptolink (4 steps) theo ten; khong thay thi chon 0."""
    try:
        for i, t in enumerate(tasks or []):
            n = str((t or {}).get("name", "")) + " " + str((t or {}).get("text", ""))
            if "uptolink" in n.lower():
                return i
    except Exception:
        pass
    return 0


def moneytask_auto_fetch_octo(auto=None):
    """Tu dong lay url octolink nhiem vu tu MoneyTask. Tra ve shortenedUrl hoac ''."""
    cookie_str = _mt_load_cookie()
    if cookie_str:
        exp = _mt_jwt_exp(cookie_str)
        if exp and exp < time.time():
            try:
                exp_s = time.strftime("%H:%M %d/%m", time.localtime(exp))
            except Exception:
                exp_s = str(exp)
            print_slot_warning(0, f"Cookie luu da het han tu {exp_s} -> can dan moi (file cu giu nguyen).")
            cookie_str = ""
        else:
            print_slot_info(0, f"Dung cookie MoneyTask da luu ({len(cookie_str)} ky tu). Go 'mtc' o prompt de doi cookie.")
    if not cookie_str:
        cookie_str = _mt_prompt_cookie("")
        if not cookie_str:
            print_slot_warning(0, "Chua co cookie MoneyTask -> bo qua.")
            return ""
        _mt_cache_cookie(cookie_str)
    cookies = _mt_parse_cookie(cookie_str)
    if not cookies:
        print_slot_warning(0, "Cookie khong parse duoc (can dang a=b; c=d). Dan lai (file cu giu nguyen).")
        cookie_str = _mt_prompt_cookie(cookie_str)
        cookies = _mt_parse_cookie(cookie_str)
        if not cookies:
            return ""
        _mt_cache_cookie(cookie_str)

    print_slot_info(0, "Mo MoneyTask nhu trinh duyet that (UA Chrome/152 + cookie that, page tu handshake pubcrypto)...")
    pw = None
    browser = None
    ctx = None
    try:
        pw = sync_playwright().start()
        # Direct (khong proxy) de tranh IP datacenter bi flag - giong bypass_list moneytask
        # Profile persistent mt_profile/ giu cf_clearance sau khi giai tay 1 lan (--view)
        ctx = _mt_launch_ctx(pw)
        try:
            ctx.add_init_script(MT_STEALTH_JS)
        except Exception:
            pass
        try:
            ctx.add_cookies(cookies)
        except Exception as e:
            print_slot_warning(0, f"Set cookie loi: {e}")
        page = ctx.new_page()

        captured = {"tasks": [], "accept": []}

        def _on_resp(resp):
            try:
                u = resp.url or ""
            except Exception:
                return
            try:
                if "/api/tasks/accept" in u:
                    captured["accept"].append(resp.text())
                elif u.rstrip("/").endswith("/api/tasks") or "/api/tasks?" in u:
                    captured["tasks"].append(resp.text())
            except Exception:
                pass

        def _open_tasks():
            pg = ctx.new_page()
            pg.on("response", _on_resp)
            try:
                pg.goto(MT_TASKS_URL, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(4000)
            except Exception as e:
                print_slot_warning(0, f"Mo trang MoneyTask loi: {e}")
            return pg

        def _manual_solve(cur_page):
            """CF chan cung: mo Chrome THAT cho user giai tay, Enter -> dong lai,
            mo headless tiep (chung profile nen clearance duoc giu). Tra page moi/None."""
            nonlocal ctx
            if VIEW_MODE:
                print_slot_warning(0, "Chrome that dang mo (--view): giai Cloudflare tay trong do roi Enter...")
            else:
                print_slot_warning(0, "Mo Chrome THAT: giai Cloudflare tay trong do...")
                for _c in (cur_page, ctx):
                    try:
                        _c.close()
                    except Exception:
                        pass
                try:
                    ctx = _mt_launch_ctx(pw, headed=True)
                    ctx.add_init_script(MT_STEALTH_JS)
                    ctx.add_cookies(cookies)
                except Exception as e:
                    print_slot_warning(0, f"Mo Chrome that loi: {e}")
                    return None
                cur_page = ctx.new_page()
                try:
                    cur_page.goto(MT_TASKS_URL, wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
            sys.stdout.write(f"  {ColorCyan2}{Bold}>> Giai Cloudflare xong bam Enter de tiep tuc: {Reset}")
            sys.stdout.flush()
            read_line_eof()
            if not VIEW_MODE:
                for _c in (cur_page, ctx):
                    try:
                        _c.close()
                    except Exception:
                        pass
                try:
                    ctx = _mt_launch_ctx(pw)
                    ctx.add_init_script(MT_STEALTH_JS)
                    ctx.add_cookies(cookies)
                except Exception as e:
                    print_slot_warning(0, f"Mo lai headless loi: {e}")
                    return None
            return _open_tasks()

        page = _open_tasks()

        # Het han cookie -> ve trang login
        try:
            cur = page.url or ""
            body_txt = page.evaluate("document.body ? document.body.innerText.slice(0,500) : ''") or ""
        except Exception:
            cur, body_txt = "", ""
        if "dang-nhap" in cur or "login" in cur or "Đăng nhập" in body_txt:
            print_slot_warning(0, "Cookie het han (trang doi ve login). Dan cookie moi (file cu giu nguyen).")
            cookie_str = _mt_prompt_cookie("")
            if not cookie_str:
                return ""
            _mt_cache_cookie(cookie_str)
            try:
                ctx.add_cookies(_mt_parse_cookie(cookie_str))
                page.goto(MT_TASKS_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print_slot_warning(0, f"Mo lai loi: {e}")
                return ""

        # Chan doan: page dung o dau (CF challenge? login la? trang trang?) - chi log
        try:
            _d_url = page.url or ""
            _d_title = ""
            try:
                _d_title = page.title() or ""
            except Exception:
                pass
            _d_body = page.evaluate("document.body ? document.body.innerText.slice(0,300) : ''") or ""
            _d_html = page.evaluate("document.documentElement ? document.documentElement.outerHTML.slice(0,3000) : ''") or ""
            _d_hits = [m for m in _MT_CF_MARKERS if m in (_d_html + " " + _d_body).lower()]
            print_slot_info(0, "[DIAG] url=" + _d_url[:100] + " | title=" + _d_title[:80] + " | body=" + str(len(_d_body)) + " chars | api_tasks=" + str(len(captured["tasks"])))
            if _d_hits:
                print_slot_warning(0, "[DIAG] Cloudflare markers: " + ", ".join(_d_hits) + " -> doi + tick that...")
                _cf_clicks = 0
                for _ in range(45):
                    page.wait_for_timeout(1000)
                    try:
                        _rh = page.evaluate("document.documentElement ? document.documentElement.outerHTML.slice(0,3000) : ''") or ""
                    except Exception:
                        break
                    if not any(m in _rh.lower() for m in _MT_CF_MARKERS):
                        print_slot_success(0, "[DIAG] Cloudflare tu mo, tiep tuc.")
                        break
                    # Tick that vao widget Turnstile (toi da 3 lan, cach nhau) nhu tay
                    if _cf_clicks < 3 and _ % 8 == 4:
                        try:
                            _rc = page.evaluate(_MT_CF_CLICK_JS) or "{}"
                            if (json.loads(_rc) or {}).get("found"):
                                _mt_trusted_click(page, page.locator("[data-mt-turnstile='1']"), timeout=8000)
                                _cf_clicks += 1
                                print_slot_info(0, f"[DIAG] Da tick Turnstile lan {_cf_clicks} (cho tu mo)...")
                        except Exception:
                            pass
                else:
                    print_slot_warning(0, "CF van chan -> mo Chrome that giai tay...")
                    _np = _manual_solve(page)
                    if _np is None:
                        print_slot_warning(0, "Khong mo duoc Chrome that de giai tay.")
                        return ""
                    page = _np
                    print_slot_success(0, "Da giai tay xong, tiep tuc lay task...")
            if _d_body:
                print_slot_info(0, "[DIAG] body: " + _d_body[:200])
        except Exception as _de:
            print_slot_warning(0, "DIAG loi: " + str(_de)[:120])

        # Don modal thong bao ("Khong hien thi lai trong 2 ngay") ngay sau load de khoi che nut
        try:
            vw = page.evaluate("({w: window.innerWidth || 1920, h: window.innerHeight || 1080})") or {}
            raw0 = page.evaluate(_MT_DISMISS_JS, [int(vw.get("w", 1920) / 2), int(vw.get("h", 1080) / 2)]) or "{}"
            res0 = json.loads(raw0) or {}
            if res0.get("action") == "close":
                if res0.get("check"):
                    try:
                        _mt_trusted_click(page, page.locator("[data-mt-check='1']"), timeout=6000)
                    except Exception:
                        pass
                try:
                    _mt_trusted_click(page, page.locator("[data-mt-close='1']"), timeout=6000)
                except Exception:
                    pass
                print_slot_info(0, "Da tat modal thong bao dau trang.")
                page.wait_for_timeout(600)
            elif res0.get("action") == "esc":
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
        except Exception:
            pass

        # Doi list task hien ra (page tu GET /api/tasks + giai ma pubcrypto.cjk)
        tasks = []
        for _ in range(30):
            try:
                raw = page.evaluate(_MT_LIST_JS) or "[]"
                tasks = json.loads(raw)
            except Exception:
                tasks = []
            if tasks:
                break
            page.wait_for_timeout(1000)
        # Neu DOM khong co nhung /api/tasks tra JSON plain thi parse
        if not tasks:
            for body in captured["tasks"]:
                try:
                    j = json.loads(body)
                except Exception:
                    continue
                arr = None
                if isinstance(j, list):
                    arr = j
                elif isinstance(j, dict):
                    for k in ("data", "tasks", "list", "items"):
                        if isinstance(j.get(k), list):
                            arr = j[k]
                            break
                if arr:
                    for it in arr:
                        if isinstance(it, dict):
                            tasks.append({
                                "text": str(it.get("name") or it.get("title") or it.get("id") or "?")[:60],
                                "name": str(it.get("website_url") or it.get("guild_link") or "")[:90],
                            })
                    break
        if not tasks:
            print_slot_warning(0, "Khong thay nut Nhan nhiem vu nao (co the het task hoac bi chan).")
            return ""

        # Cookie chay duoc (thay task) -> moi luu, lan sau khoi dan lai
        try:
            _mt_save_cookie(cookie_str)
            print_slot_success(0, f"Da luu cookie ({len(cookie_str)} ky tu) vao {MT_COOKIE_FILE}.")
        except Exception:
            pass

        print_slot_success(0, f"Thay {len(tasks)} nhiem vu MoneyTask:")
        for i, t in enumerate(tasks[:20], 1):
            vis = "" if t.get("visible", True) else " (an)"
            print_slot_info(0, f"  [{i}] {t.get('text','?')}{vis} | {t.get('name','')[:60]}")
        if auto is None:
            auto = mt_auto_enabled()
        if auto:
            idx = _mt_auto_pick(tasks)
            print_slot_info(0, f"Tu chon [{idx+1}] {tasks[idx].get('text','')} (auto) -> bam Nhan nhiem vu...")
        else:
            sys.stdout.write(f"  {ColorCyan2}{Bold}>> Chon nhiem vu [1-{min(len(tasks),20)}] (Enter = 1): {Reset}")
            sys.stdout.flush()
            choice_txt, ok = read_line_eof()
            try:
                idx = int((choice_txt or "1").strip()) - 1
            except Exception:
                idx = 0
            idx = max(0, min(idx, min(len(tasks), 20) - 1))
            print_slot_info(0, f"Chon [{idx+1}] {tasks[idx].get('text','')} -> bam Nhan nhiem vu...")

        # Click trusted qua Playwright (khong dung JS click de tranh isTrusted=false)
        # Nut MoneyTask ghi "Thuc Hien" (khong chi "Nhan") -> match rong
        # Click TRUSTED vao nut THAT da tag data-mt-idx (khong do text de tranh moi).
        # CAM JS .click(): isTrusted=false -> an flag programmatic_clicks (dump anti-cheat B2).
        # Modal overlay che nut -> tat modal that / ESC (van trusted) roi click lai.
        clicked = False
        last_err = ""
        try:
            loc = page.locator("[data-mt-idx='%d']" % idx)
            dismissed = 0
            for _ in range(5):
                try:
                    if dismissed >= 2:
                        # Modal cu hien theo chuot: dung focus + Enter that (trusted,
                        # khong re chuot) de bam nut ma khong kich modal.
                        loc.wait_for(state="visible", timeout=8000)
                        _mt_scroll_center(page, loc)
                        loc.focus(timeout=5000)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(1000)
                    else:
                        _mt_trusted_click(page, loc, timeout=8000)
                    clicked = True
                    break
                except Exception as e:
                    last_err = str(e)
                    # Moi loi click deu thu dismiss; LOG MOI KET QUA (ke ca that bai)
                    if dismissed < 3:
                        try:
                            ok, detail = _mt_dismiss_overlay(page, loc)
                        except Exception as de:
                            ok, detail = False, f"dismiss crash: {de}"[:120]
                        dismissed += 1
                        print_slot_info(0, f"Dismiss lan {dismissed} [{'OK' if ok else 'FAIL'}: {detail}], thu lai nut [{idx+1}]...")
                        page.wait_for_timeout(800)
                        continue
                    break
        except Exception as e:
            last_err = str(e)
        if not clicked:
            try:
                shot = os.path.join(LOG_DIR, f"mt_blocked_{time.strftime('%H%M%S')}.png")
                page.screenshot(path=shot)
                print_slot_warning(0, f"Da chup man hinh modal che nut: {shot} (gui file nay de xem)")
            except Exception:
                pass
            print_slot_warning(0, f"Khong click duoc nut that [{idx+1}] (khong JS click de giu bypass): {last_err[:2000]}")
            print_slot_warning(0, "Khong bam duoc nut Nhan nhiem vu.")
            return ""

        # Doi POST /api/tasks/accept JSON {shortenedUrl, taskUrl, waitSeconds, endTime}
        accept_json = None
        for _ in range(30):
            while captured["accept"]:
                body = captured["accept"].pop(0)
                try:
                    j = json.loads(body)
                except Exception:
                    continue
                cand = j.get("data") if isinstance(j.get("data"), dict) else j
                if isinstance(cand, dict) and (cand.get("shortenedUrl") or cand.get("taskUrl")):
                    accept_json = cand
                    break
            if accept_json:
                break
            page.wait_for_timeout(1000)
        if not accept_json:
            print_slot_warning(0, "Khong bat duoc POST /api/tasks/accept (qua 30s).")
            return ""
        short_url = (accept_json.get("shortenedUrl") or accept_json.get("taskUrl") or "").strip()
        wait_s = accept_json.get("waitSeconds", "")
        end_t = accept_json.get("endTime", "")
        if short_url:
            try:
                global _mt_last_end_time
                _mt_last_end_time = int(end_t or 0)
            except Exception:
                pass
            remember_octo_link(short_url)
            print_slot_success(0, f"MoneyTask tra link octo: {short_url} (cho {wait_s}s, endTime={end_t})")
            write_log_file(f"[{timestamp_now()}] MT accept -> {short_url} wait={wait_s} end={end_t}")
            return short_url
        print_slot_warning(0, f"Accept khong co shortenedUrl: {str(accept_json)[:200]}")
        return ""
    except Exception as e:
        print_slot_warning(0, f"MoneyTask auto fetch loi: {e}")
        return ""
    finally:
        try:
            if ctx:
                ctx.close()
        except Exception:
            pass
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass


# ============================================================================
# MONEYTASK FINISH CLAIM (Link Goc moneytask.top/finish?attempt=... -> mo an + bam Xac nhan)
# Dung dung cookie moneytask_cookie.txt da dan (giong mt auto fetch), Direct (khong proxy)
# de tranh IP datacenter bi flag. Khong bam Link Goc tren octolink, chi claim o day.
# ============================================================================

def is_moneytask_finish_claim_url(u):
    try:
        p = urlparse(u or "")
        return (p.hostname or "").lower().endswith("moneytask.top") and "/finish" in (p.path or "")
    except Exception:
        return False


def parse_claim_result(body_text):
    t = (body_text or "").lower()
    if ("nhận thưởng thành công" in t or "đã nhận thưởng" in t
            or "claim thành công" in t or "nhận thưởng thành công!" in t):
        return "success"
    if "chờ duyệt" in t or "cho duyet" in t:
        return "pending"
    return "unknown"


# Claim browser TUYET DOI Direct: --proxy-server=direct:// ep cung Chromium
# khong di qua proxy (ke ca env HTTP_PROXY), giu IP nha nhu badge IP:xx VN
MT_CLAIM_CHROME_ARGS = [
    "--no-sandbox", "--disable-dev-shm-usage", "--mute-audio",
    "--disable-blink-features=AutomationControlled",
    "--proxy-server=direct://",
]

# Bypass anti-cheat CHI cho moneytask (theo dump Anti moneytask 6 tang):
# - T3 ow(): webdriver instance-only (KHONG cham Navigator.prototype -> qua webdriver_spoofed),
#   chrome stub, khong hook fetch/XHR/querySelector (qua fn_override), khong tao global GM_*
# - T4 Lu(): chuot trusted qua CDP + Bezier (xem _mt_human_move), click 1-2 cai (qua uniform_clicks)
# - T6: doi qua endTime + jitter truoc khi claim (qua CALLBACK_TOO_FAST +60)
# - T1/T2/T5: khong can - khong mo DevTools, fingerprint that nhat quan, crypto nho page tu xu ly
MT_STEALTH_JS = """(() => {
  try { Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true}); } catch (e) {}
  try { if (!window.chrome) window.chrome = { runtime: {} }; } catch (e) {}
  try { Object.defineProperty(navigator, 'languages', {get: () => ['vi-VN', 'vi', 'en-US', 'en'], configurable: true}); } catch (e) {}
})();"""

# endTime cua accept gan nhat (de claim doi qua moc, tranh CALLBACK_TOO_FAST)
_mt_last_end_time = 0


def mt_claim_delay(end_time, now_s):
    """So giay can doi truoc khi bam Xac nhan: het endTime + jitter 5-15s. Tra >=5."""
    try:
        wait = max(0, float(end_time or 0) - float(now_s))
    except Exception:
        wait = 0
    return wait + 5 + random.uniform(0, 10)


def _mt_human_move(page, x, y, steps=24):
    """Re chuot trusted (CDP) theo duong cong co jitter + pause, de Lu() thay hanh vi nguoi."""
    try:
        box_vp = page.viewport_size or {"width": 1920, "height": 1080}
        sx, sy = box_vp["width"] * 0.3, box_vp["height"] * 0.3
        cx, cy = (sx + x) / 2 + random.uniform(-60, 60), (sy + y) / 2 + random.uniform(-60, 60)
        for i in range(steps + 1):
            t = i / steps
            px = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * cx + t * t * x + random.uniform(-1.5, 1.5)
            py = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * cy + t * t * y + random.uniform(-1.5, 1.5)
            page.mouse.move(px, py)
            time.sleep(random.uniform(0.008, 0.03))
            if i in (int(steps * 0.45), int(steps * 0.75)):
                time.sleep(random.uniform(0.22, 0.35))
    except Exception:
        pass

_MT_CLAIM_FIND_JS = r"""(() => {
  // Tim nut Xac nhan THAT tren trang finish: div[role=button] chua canvas +
  // aria-label ~ xac nhan, TRONG viewport, khong honeypot/decoy/aria-hidden.
  // (button[type=submit] trong suot + text trong canvas -> do text vo trung moi.)
  // Tra {found, disabled, session409}. Tag nut that = data-mt-confirm.
  const out = {found: false, disabled: true, session409: false};
  try {
    const bt = (document.body ? document.body.innerText : '') || '';
    if (/\(409\)|không xác thực được phiên|khong xac thuc duoc phien/i.test(bt)) out.session409 = true;
  } catch (e) {}
  const bad = (el) => {
    try {
      const ns = el.getAttributeNames ? el.getAttributeNames() : [];
      for (const a of ns) {
        const al = (a + '').toLowerCase();
        if (al === 'data-honeypot' || al === 'data-decoy' || al === 'data-decoy-role' ||
            al === 'data-autoclick' || al === 'data-auto-clicker' || al.indexOf('data-hpx') === 0) return true;
      }
      if (el.getAttribute && el.getAttribute('aria-hidden') === 'true') return true;
    } catch (e) {}
    return false;
  };
  const inVp = (el) => {
    try {
      const r = el.getBoundingClientRect();
      if (!r || r.width <= 0 || r.height <= 0) return false;
      const vw = window.innerWidth || 1920, vh = window.innerHeight || 1080;
      return r.bottom > 0 && r.right > 0 && r.left < vw && r.top < vh && r.left >= -2 && r.top >= -2;
    } catch (e) { return false; }
  };
  try {
    const cands = Array.from(document.querySelectorAll('div[role="button"]'));
    for (const b of cands) {
      if (bad(b)) continue;
      if (!inVp(b)) continue;
      if (!b.querySelector || !b.querySelector('canvas')) continue;
      let lab = '';
      try { lab = (b.getAttribute('aria-label') || '') + ''; } catch (e) {}
      if (!/xác nhận|xac nhan|confirm|hoàn thành|hoan thanh/i.test(lab)) continue;
      out.found = true;
      try { out.disabled = (b.getAttribute('aria-disabled') === 'true'); } catch (e) { out.disabled = true; }
      try { b.dataset.mtConfirm = '1'; } catch (e) {}
      break;
    }
  } catch (e) {}
  return JSON.stringify(out);
})();""";


_MT_CLAIM_JS_HAS_FORM = r"""(() => {
  try {
    const btns = Array.from(document.querySelectorAll('button[type="submit"], button'));
    for (const b of btns) {
      const t = ((b.innerText || b.textContent || '') + '').trim().toLowerCase();
      if (t.includes('xác nhận') || t.includes('xac nhan')) return 'yes';
    }
    return 'no';
  } catch (e) { return 'no'; }
})();"""


def moneytask_auto_claim(finish_url, slot_id=0):
    """Mo trang moneytask.top/finish?attempt=... bang cookie da luu, bam Xac nhan. Tra True neu claim xong."""
    cookie_str = _mt_load_cookie()
    if not cookie_str:
        print_slot_warning(slot_id, "Chua co cookie MoneyTask -> gõ 'mtc' roi dan cookie truoc khi claim.")
        return False
    cookies = _mt_parse_cookie(cookie_str)
    if not cookies:
        print_slot_warning(slot_id, "Cookie MoneyTask khong parse duoc. Dan lai.")
        return False

    print_slot_info(slot_id, f"🎯 [MT-CLAIM] Mở ẩn {finish_url[:70]}... bằng cookie đã lưu (Direct, không proxy)...")
    pw = None
    browser = None
    ctx = None
    try:
        pw = sync_playwright().start()
        # KHONG truyen proxy=... -> Playwright direct; them --proxy-server=direct:// de chac chan
        # Chung profile persistent mt_profile/ voi mt fetch (giu cf_clearance)
        ctx = _mt_launch_ctx(pw, extra_args=MT_CLAIM_CHROME_ARGS)
        try:
            ctx.add_init_script(MT_STEALTH_JS)
        except Exception:
            pass
        try:
            ctx.add_cookies(cookies)
        except Exception as e:
            print_slot_warning(slot_id, f"Set cookie claim loi: {e}")
        page = ctx.new_page()
        try:
            page.goto(finish_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
        except Exception as e:
            print_slot_warning(slot_id, f"Mo trang finish loi: {e}")
            return False

        try:
            cur = page.url or ""
            txt = page.evaluate("document.body ? document.body.innerText.slice(0,300) : ''") or ""
        except Exception:
            cur, txt = "", ""
        if "dang-nhap" in cur or "login" in cur or "Đăng nhập" in txt:
            print_slot_warning(slot_id, "Cookie het han (finish doi ve login). Go 'mt' dan lai cookie moi (file cu giu nguyen).")
            return False

        # Doi qua endTime (neu co tu accept) roi moi bam -> tranh CALLBACK_TOO_FAST +60
        try:
            endt = globals().get("_mt_last_end_time", 0) or 0
        except Exception:
            endt = 0
        if endt:
            dw = mt_claim_delay(endt, time.time())
            if dw > 1:
                print_slot_info(slot_id, f"⏳ [MT-CLAIM] Doi qua endTime ({int(dw)}s) roi moi bam Xac nhan...")
                time.sleep(dw)

        # Doi phien finish song (nut that enable, khong 409) roi click trusted.
        # Nut that la canvas (khong chu) -> tim bang _MT_CLAIM_FIND_JS, KHONG do text.
        # CAM JS .click() (isTrusted=false -> flag programmatic_clicks).
        ready = False
        saw409 = False
        for _ in range(30):
            try:
                raw = page.evaluate(_MT_CLAIM_FIND_JS) or "{}"
                st = json.loads(raw)
            except Exception:
                st = {}
            if st.get("session409"):
                saw409 = True
            if st.get("found") and not st.get("disabled"):
                ready = True
                break
            page.wait_for_timeout(1000)
        if saw409 and not ready:
            print_slot_warning(slot_id, "Phien attempt het han (409). Can nhan task moi tu 'mt' (attempt cu khong dung duoc).")
            return False
        if not ready:
            print_slot_warning(slot_id, "Khong thay nut Xac nhan that (nut disabled hoac trang loi).")
            return False
        clicked = False
        try:
            _mt_trusted_click(page, page.locator("[data-mt-confirm='1']"), timeout=15000)
            clicked = True
        except Exception as e:
            print_slot_warning(slot_id, f"Khong bam duoc nut Xac nhan: {str(e)[:300]}")
            return False
        if not clicked:
            return False
        print_slot_info(slot_id, "Đã bấm Xác nhận, chờ kết quả claim...")

        deadline = time.time() + 25
        while time.time() < deadline:
            try:
                body = page.evaluate("document.body ? document.body.innerText.slice(0,2000) : ''") or ""
            except Exception:
                body = ""
            st = parse_claim_result(body)
            if st == "success":
                print_slot_success(slot_id, "🎉 [MT-CLAIM] Claim thành công!")
                write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] MT claim success {finish_url[:80]}")
                return True
            if st == "pending":
                print_slot_success(slot_id, "⏳ [MT-CLAIM] Nhiệm vụ Chờ duyệt.")
                write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] MT claim pending {finish_url[:80]}")
                return True
            page.wait_for_timeout(1000)
        print_slot_warning(slot_id, "Claim xong nhung chua thay thong bao thanh cong (qua 25s).")
        write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] MT claim unknown {finish_url[:80]}")
        return False
    except Exception as e:
        print_slot_warning(slot_id, f"MoneyTask auto claim loi: {e}")
        return False
    finally:
        try:
            if ctx:
                ctx.close()
        except Exception:
            pass
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass


# ============================================================================
# URL HELPERS (port tu job_runner.go)
# ============================================================================

RE_SANITIZE_URL = re.compile(r"https?://[a-zA-Z0-9_.~:/?#\[\]@!$&*+,;=-]+")
RE_TRIM_TAIL = re.compile(r"[^a-zA-Z0-9_.~:/?#\[\]@!$&*+,;=-]+$")
RE_ALIAS_TOKEN = re.compile(r"^[a-zA-Z0-9_-]{4,}$")
RE_TASK_KEY_PATH = re.compile(r"/(\d+-\d+)(?:/|$)")
RE_TASK_KEY_LOOSE = re.compile(r"(?:id|task|taskId|/)(\d+-\d+)")
RE_TASK_KEY_DIRECT = re.compile(r"^\d+-\d+$")


def sanitize_input_url(raw):
    raw = (raw or "").strip()
    m = RE_SANITIZE_URL.search(raw)
    if m:
        return RE_TRIM_TAIL.sub("", m.group(0))
    return ""


def extract_task_key(input_str):
    try:
        u = urlparse(input_str)
        qs = parse_qs(u.query)
        for qk in ("id", "task", "taskId"):
            if qs.get(qk):
                return qs[qk][0]
        if u.path:
            m = RE_TASK_KEY_PATH.search(u.path)
            if m:
                if "totreview.com" in (u.netloc or "").lower():
                    return "totreview-" + m.group(1)
                return m.group(1)
            if "totreview.com" in (u.netloc or "").lower():
                parts = [p for p in u.path.split("/") if p]
                if parts:
                    last = parts[-1]
                    for suf in (".html", ".htm"):
                        if last.endswith(suf):
                            last = last[:-len(suf)]
                    if last:
                        return "totreview-" + last
    except Exception:
        pass
    m = RE_TASK_KEY_LOOSE.search(input_str or "")
    if m:
        return m.group(1)
    if RE_TASK_KEY_DIRECT.match((input_str or "").strip()):
        return input_str.strip()
    return ""


def extract_alias_from_input(raw):
    raw = (raw or "").strip()
    try:
        u = urlparse(raw)
        qs = parse_qs(u.query)
        for qk in ("alias", "task", "taskId", "id"):
            if qs.get(qk):
                return qs[qk][0]

        host = (u.netloc or "").lower()
        is_gate = ("octolink" in host) or ("trafficvip" in host) or ("up2link" in host)
        parts = [p for p in (u.path or "").split("/") if p]
        if is_gate and parts:
            for p in reversed(parts):
                if p and ("device" not in p) and ("check" not in p) and ("statics" not in p) and ("fp" not in p):
                    return p
    except Exception:
        pass

    k = extract_task_key(raw)
    if k:
        return k

    if not raw.startswith("http://") and not raw.startswith("https://"):
        m = RE_ALIAS_TOKEN.search(raw)
        if m:
            return m.group(0)
    return ""


# ============================================================================
# GATE RESOLVE (port tu ResolveGateURL - mo cong Octolink/TrafficVIP /check/device)
# ============================================================================

def resolve_gate_url(raw_input, proxy_url="", slot_id=0):
    try:
        u = urlparse(raw_input)
    except Exception:
        return {"resolved_url": raw_input, "cookie_str": ""}

    host = (u.netloc or "").lower()
    if not (("octolink.vip" in host) or ("trafficvip.vip" in host) or ("trafficvip.net" in host)):
        return {"resolved_url": raw_input, "cookie_str": ""}

    parts = [p for p in (u.path or "").split("/") if p]
    if not parts:
        return {"resolved_url": raw_input, "cookie_str": ""}

    alias = parts[-1]
    for suf in (".html", ".htm"):
        if alias.endswith(suf):
            alias = alias[:-len(suf)]

    if not alias or any(x in alias for x in ("device", "check", "statics", "finish")) or "." in alias:
        return {"resolved_url": raw_input, "cookie_str": ""}

    scheme = u.scheme or "https"

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    sess = requests.Session()
    sess.verify = False
    sess.proxies = proxies or {}

    try:
        r1 = sess.get(raw_input, timeout=15, headers={
            "User-Agent": ua_for_slot(slot_id),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        try:
            r1.close()
        except Exception:
            pass

        post_url = f"{scheme}://{u.netloc}/check/device"
        r2 = sess.post(post_url, data={"alias": alias, "dv": ""}, timeout=15, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"{scheme}://{u.netloc}",
            "Referer": raw_input,
            "User-Agent": ua_for_slot(slot_id),
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })
        result = r2.json()
        if result.get("ok") and result.get("url"):
            cookie_pairs = []
            for c in sess.cookies:
                cookie_pairs.append(f"{c.name}={c.value}")
            return {"resolved_url": result["url"], "cookie_str": "; ".join(cookie_pairs)}
    except Exception:
        pass
    return {"resolved_url": raw_input, "cookie_str": ""}


# ============================================================================
# PLATFORM DETECTION (port tu platform.go)
# ============================================================================

PLATFORM_REGISTRY = [
    {"id": "moneytask", "display": "MoneyTask (moneytask.top)",
     "hosts": ["moneytask.top", "moneytask"], "scripts": ["lấy-link-mnt", "moneytask", "mnt"]},
    {"id": "yeutask", "display": "YeuTask (yeutask.com)",
     "hosts": ["yeutask.com", "yeutask"], "scripts": ["lấy link-yeutask", "yeutask"]},
    {"id": "kiemkhoai", "display": "KiemKhoai (kiemkhoai.com)",
     "hosts": ["kiemkhoai.com", "kiemkhoai"], "scripts": ["lấy link-kiemkhoai", "kiemkhoai"]},
]


def platform_detect(req_platform="", req_origin="", req_referer="", input_url="", dest_url=""):
    if req_platform:
        p_lower = req_platform.strip().lower()
        for info in PLATFORM_REGISTRY:
            if info["id"] == p_lower:
                return info["id"]
            for alias in info["scripts"]:
                if alias in p_lower:
                    return info["id"]

    check_header = (req_origin + " " + req_referer).lower()
    for info in PLATFORM_REGISTRY:
        for host in info["hosts"]:
            if host in check_header:
                return info["id"]

    for src in (dest_url, input_url):
        if src:
            check = src.lower()
            for info in PLATFORM_REGISTRY:
                for host in info["hosts"]:
                    if host in check:
                        return info["id"]
    return "unknown"


def platform_display_name(p):
    for info in PLATFORM_REGISTRY:
        if info["id"] == p:
            return info["display"]
    if not p or p == "unknown":
        return "Chưa rõ (Generic)"
    return p


# ============================================================================
# PLAYWRIGHT BROWSER ENGINE (port tu browser/ engine.go + solver.go + interceptor.go)
# ============================================================================

TRANSIENT_NAV_HOSTS = [
    "octolink.", "trafficvip.", "up2link", "uptolink", "linkhuongdan",
    "huongdan", "getcode", "shortearn", "google.", "facebook.", "youtube.",
    "zalo.me", "cloudflare", "gstatic", "moneytask.top", "yeutask.com",
    "example.com", "minuc.vn",
]

FAIL_FAST_PATTERNS = [
    "err_proxy", "err_tunnel", "err_socks", "err_connection_refused",
    "err_name_not_resolved", "err_connection_timed_out",
]

VERBOSE_ENGINE_PREFIXES = [
    "Cookie synced:", "Bridge binary body", "mkHd keys:", "mkHd sig:",
    "body type:", "_0xjj:", "contJ: step:", "REDIRECT_TO_OCTO_SUCCESS:",
]


def is_verbose_engine_log(msg):
    if any(msg.startswith(p) for p in VERBOSE_ENGINE_PREFIXES):
        return True
    if "Mã hóa đã làm mới:" in msg:
        return True
    return False


def is_transient_nav_host(url_str):
    lower = (url_str or "").lower()
    return any(d in lower for d in TRANSIENT_NAV_HOSTS)


def is_money_task_finish_url(u):
    return ("moneytask.top" in u) and ("finish" in u)


def is_yeu_task_url(u):
    return "yeutask." in u.lower()


def same_host(a, b):
    try:
        ha = urlparse(a).hostname or ""
        hb = urlparse(b).hostname or ""
        return ha != "" and ha.lower() == hb.lower()
    except Exception:
        return False


def extract_host(url_str):
    try:
        return (urlparse(url_str).hostname or "").lower()
    except Exception:
        return ""


def build_proxy_bypass_list(platform_name):
    if platform_name == "moneytask":
        return "moneytask.top,*.moneytask.top"
    if platform_name == "yeutask":
        return "yeutask.com,*.yeutask.com,yeutask.net,*.yeutask.net"
    if platform_name == "kiemkhoai":
        return "kiemkhoai.com,*.kiemkhoai.com"
    return ""


def build_chrome_args(proxy_url, bypass_list="", headless=True):
    args = [
        "--headless=new" if headless else "--headless=false",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--allow-running-insecure-content",
        "--blink-settings=imagesEnabled=false",
        "--mute-audio",
        "--disable-background-networking",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure",
        "--window-size=1920,1080",
        "--ignore-certificate-errors",
    ]
    if not headless:
        args.append("--start-maximized")
    if proxy_url:
        args.append(f"--proxy-server={proxy_url}")
        bypass_parts = ["localhost", "127.0.0.1"]
        for extra in (bypass_list or "").split(","):
            extra = extra.strip()
            if extra:
                bypass_parts.append(extra)
        args.append("--proxy-bypass-list=" + ";".join(bypass_parts))
    return args


class SolverResult:
    def __init__(self, data, is_passcode):
        self.data = data
        self.is_passcode = is_passcode


class SolveContext:
    """Hop nhat cac hang doi ket qua giua cac CDP event handler va polling loop."""

    def __init__(self, slot_id, start_url):
        self.slot_id = slot_id
        self.start_url = start_url
        self.results = queue.Queue()
        self.fail_fast = queue.Queue()
        self.nav = queue.Queue()
        self.wait_req = queue.Queue()


def parse_wait_response(url_str, body_text):
    """Doc (wait, step) tu response /check/job & /check/continue cua server.
    Server tra: {status, wait: 53, step: "1", message...}. Tra None neu khong co."""
    if not body_text:
        return None
    lower = (url_str or "").lower()
    if ("/check/job" not in lower) and ("/check/continue" not in lower):
        return None
    try:
        data = json.loads(body_text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    try:
        wait = int(float(data.get("wait") or data.get("time") or 0))
    except Exception:
        wait = 0
    step = str(data.get("step") or "").strip() or None
    if wait > 0 and wait <= 600:
        return wait, step
    return None


def setup_cdp_interceptor(sc, page, context_obj):
    """Port tu SetupCDPInterceptor: fail-fast, frame nav, console, response body."""

    def on_request_failed(req):
        try:
            failure = (req.failure or "").lower()
            if req.resource_type == "document" and any(p in failure for p in FAIL_FAST_PATTERNS):
                try:
                    sc.fail_fast.put_nowait(f"Mạng Proxy gặp sự cố ({req.failure})")
                except Exception:
                    pass
        except Exception:
            pass

    def on_framenavigated(frame):
        try:
            if frame.parent_frame is not None:
                return
            final_url = frame.url or ""
            if final_url.startswith("http") and not same_host(final_url, sc.start_url) \
                    and not is_transient_nav_host(final_url) and ("/finish/" not in final_url):
                try:
                    sc.results.put_nowait(SolverResult(final_url, False))
                except Exception:
                    pass
        except Exception:
            pass

    def on_console(msg):
        try:
            val = msg.text or ""
            if "[OCTO_COOKIE] " in val:
                cookie_str = val.split("[OCTO_COOKIE] ", 1)[1].strip().strip('"')
                try:
                    cookie_str = json.loads(val.split("[OCTO_COOKIE] ", 1)[1].strip())
                except Exception:
                    pass
                for part in str(cookie_str).split(";"):
                    part = part.strip()
                    if not part or "=" not in part:
                        continue
                    c_name, c_val = part.split("=", 1)
                    c_name, c_val = c_name.strip(), c_val.strip()
                    if c_name and c_val:
                        try:
                            context_obj.add_cookies([{
                                "name": c_name, "value": c_val, "url": "https://octolink.vip"
                            }])
                        except Exception:
                            pass
                return

            if "[OCTO_PANEL]" in val:
                clean = val.split("[OCTO_PANEL]", 1)[1].strip()
                try:
                    clean = json.loads(clean)
                except Exception:
                    pass
                clean = str(clean).strip()
                parts = clean.split(" | ", 1)
                if len(parts) == 2:
                    log_type, log_msg = parts[0], parts[1]
                    write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] [{log_type}] {log_msg}")
                    # loc bo log rac "Cụt Tay X KG [Pure Engine]" theo yeu cau - van ghi file, khong in ra man hinh
                    if "Cụt Tay" in log_msg or "Pure Engine" in log_msg or "[Pure Engine]" in log_msg:
                        # van xu ly redirect/wait ben duoi nhung khong in
                        pass
                    elif (not is_verbose_engine_log(log_msg)) or is_dev_mode():
                        if log_type == "success":
                            print_slot_success(sc.slot_id, log_msg)
                        elif log_type == "warn":
                            print_slot_warning(sc.slot_id, log_msg)
                        elif log_type == "error":
                            print_slot_warning(sc.slot_id, f"❌ {log_msg}")
                        else:
                            print_slot_info(sc.slot_id, f"⚡ {log_msg}")

                    if log_msg.startswith("REDIRECT_TO_OCTO_SUCCESS: "):
                        dest_url = log_msg.replace("REDIRECT_TO_OCTO_SUCCESS: ", "").strip()
                        if dest_url:
                            if is_transient_nav_host(dest_url) or ("/finish/" in dest_url):
                                # lay link redirect roi di tiep toi finish nhu ban 5.3/5.5
                                try:
                                    base = getattr(sc, "target_domain", "") or ""
                                    if base and dest_url and "/finish/" in dest_url:
                                        from urllib.parse import quote as _q
                                        redirect_url = base.rstrip("/") + "/?redirect_to_octo=" + _q(dest_url, safe="")
                                        print_slot_success(sc.slot_id, f"REDIRECT_TO_OCTO: {redirect_url}")
                                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] REDIRECT {redirect_url} (finish: {dest_url})")
                                        sc.nav.put_nowait(redirect_url)
                                    else:
                                        print_slot_success(sc.slot_id, f"REDIRECT_TO_OCTO: {dest_url}")
                                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] REDIRECT {dest_url}")
                                        sc.nav.put_nowait(dest_url)
                                except Exception:
                                    try:
                                        sc.nav.put_nowait(dest_url)
                                    except Exception:
                                        pass
                            else:
                                try:
                                    sc.results.put_nowait(SolverResult(dest_url, False))
                                except Exception:
                                    pass
                    # bat wait tu log "Bắt đầu chặng X (chờ Ns)." de dem dung cho moi chang
                    if "Bắt đầu chặng" in log_msg and "chờ" in log_msg:
                        try:
                            m = re.search(r"Bắt đầu chặng\s+(\S+).*?\(chờ\s+(\d+)\s*s", log_msg)
                            if m:
                                step = m.group(1).strip(" .)")
                                wait = int(m.group(2))
                                if 0 < wait <= 600:
                                    sc.wait_req.put_nowait((wait, step))
                        except Exception:
                            pass
                    if ("Session không hợp lệ" in log_msg) or ("Domain nhiệm vụ đã đổi" in log_msg):
                        try:
                            sc.fail_fast.put_nowait(log_msg)
                        except Exception:
                            pass
        except Exception:
            pass

    def on_response(resp):
        try:
            url_str = resp.url or ""
            if resp.status == 407:
                try:
                    sc.fail_fast.put_nowait("Proxy yêu cầu xác thực (HTTP 407)")
                except Exception:
                    pass
                return
            # Gom Set-Cookie nhu Chodenocto 5.5: moi check/* tra AppSession/ref/dvid/csrf -> dong bo vao context that
            try:
                if "octolink.vip" in url_str or "trafficvip.vip" in url_str:
                    hdrs = {}
                    try:
                        hdrs = resp.headers or {}
                    except Exception:
                        hdrs = {}
                    set_cookies = []
                    for hk, hv in hdrs.items():
                        if hk.lower() == "set-cookie":
                            if isinstance(hv, list):
                                set_cookies.extend(hv)
                            else:
                                # Playwright gom nhieu Set-Cookie thanh 1 string noi bang \n
                                set_cookies.extend([x.strip() for x in str(hv).split("\n") if x.strip()])
                    for sc_hdr in set_cookies:
                        # Tach cookie dau tien truoc ;
                        first = sc_hdr.split(";")[0].strip()
                        if "=" not in first:
                            continue
                        cn, cv = first.split("=", 1)
                        cn, cv = cn.strip(), cv.strip()
                        if not cn or not cv:
                            continue
                        if cn.lower() in ("expires", "max-age", "path", "domain", "samesite", "secure", "httponly", "partitioned"):
                            continue
                        if cn.lower() == "csrftoken":
                            continue
                        try:
                            context_obj.add_cookies([{"name": cn, "value": cv, "url": "https://octolink.vip"}])
                        except Exception:
                            pass
                    # Dam bao from_google luon co nhu ban 5.5
                    try:
                        context_obj.add_cookies([{"name": "from_google", "value": "true", "url": "https://octolink.vip"}])
                    except Exception:
                        pass
            except Exception:
                pass
            if ("octolink.vip" not in url_str) and ("trafficvip.vip" not in url_str) and ("/check/" not in url_str):
                return
            try:
                body = resp.text()
            except Exception:
                return
            if not body:
                return

            # Finish page HTML: trich Link Goc truc tiep tu response POST (khi POST finish tra ve HTML) - phai giai captcha xong moi lay, cho phep moneytask/minuc/yeutask/caytien
            if "/finish/" in url_str.lower():
                is_post = False
                try:
                    rm = ""
                    try:
                        rm = (resp.request.method or "").upper()
                    except Exception:
                        try:
                            rm = (resp.request().method or "").upper()
                        except Exception:
                            rm = ""
                    if rm == "POST":
                        is_post = True
                    elif rm == "":
                        is_post = True
                    else:
                        is_post = False
                except Exception:
                    is_post = True
                if is_post:
                    try:
                        found = False
                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST recv len={len(body)} hasLinkGoc={'Link G' in body}")
                        def is_transient_finish(u):
                            l = u.lower()
                            return any(d in l for d in ["octolink", "trafficvip", "up2link", "uptolink", "linkhuongdan", "/check/", "example.com"])
                        m = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>[^<]*?Link[^<]*?</a>', body, re.I)
                        if m:
                            link = m.group(1).strip()
                            if link and link.startswith("http") and not is_transient_finish(link):
                                try:
                                    sc.results.put_nowait(SolverResult(link, False))
                                    write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST LinkGoc a-tag: {link}")
                                    found = True
                                except Exception:
                                    pass
                        if not found:
                            m2 = re.search(r'<form[^>]*id=["\']go-link["\'][^>]*>[\s\S]*?<input[^>]+value=["\'](https?://[^"\']+)["\']', body, re.I)
                            if m2:
                                link2 = m2.group(1).strip()
                                if link2 and link2.startswith("http") and not is_transient_finish(link2):
                                    try:
                                        sc.results.put_nowait(SolverResult(link2, False))
                                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST go-link: {link2}")
                                        found = True
                                    except Exception:
                                        pass
                        if not found:
                            for m3 in re.finditer(r'href=["\'](https?://[^"\']+)["\']', body, re.I):
                                link3 = m3.group(1).strip()
                                if link3 and link3.startswith("http") and not is_transient_finish(link3) and "/finish/" not in link3:
                                    lower3 = link3.lower()
                                    if any(d in lower3 for d in ["octolink", "trafficvip", "google.", "facebook.", "youtube."]):
                                        continue
                                    try:
                                        sc.results.put_nowait(SolverResult(link3, False))
                                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST fallback href: {link3}")
                                        found = True
                                        break
                                    except Exception:
                                        pass
                        if not found:
                            write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST no LinkGoc, body snippet: {body[:400].replace(chr(10),' ')[:300]}")
                    except Exception as e:
                        write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH POST parse err: {e}")
                else:
                    write_log_file(f"[{timestamp_now()}] [#{sc.slot_id:02d}] FINISH GET ignored len={len(body)}")

            # /check/job & /check/continue: server bao wait + step -> Python dem nguoc dung so do
            wait_info = parse_wait_response(url_str, body)
            if wait_info is not None:
                try:
                    sc.wait_req.put_nowait(wait_info)
                except Exception:
                    pass

            try:
                parsed = json.loads(body)
            except Exception:
                return
            if not isinstance(parsed, dict):
                return

            def check_map(m):
                if not isinstance(m, dict):
                    return None
                for k in ("code", "passcode", "passCode", "key"):
                    v = m.get(k)
                    if isinstance(v, str) and 4 <= len(v) <= 50 and not v.lower().startswith("http"):
                        return SolverResult(v, True)
                for k in ("url", "destination", "redirect", "link", "target"):
                    v = m.get(k)
                    if isinstance(v, str) and v.startswith("http") and ("google.com" not in v) \
                            and ("octolink.vip" not in v) and not is_transient_nav_host(v):
                        return SolverResult(v, False)
                return None

            r = check_map(parsed)
            if r is None:
                r = check_map(parsed.get("data"))
            if r is not None:
                try:
                    sc.results.put_nowait(r)
                except Exception:
                    pass
        except Exception:
            pass

    page.on("requestfailed", on_request_failed)
    page.on("framenavigated", on_framenavigated)
    page.on("console", on_console)
    page.on("response", on_response)


def native_cdp_click(cdp, x, y):
    """Port tu actions.go NativeCDPClick: click chuot that isTrusted=true qua CDP."""
    jx = x + (random.random() * 4.0 - 2.0)
    jy = y + (random.random() * 4.0 - 2.0)
    cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": jx, "y": jy})
    time.sleep((60 + random.randint(0, 59)) / 1000.0)
    cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": jx, "y": jy, "button": "left", "clickCount": 1})
    time.sleep((80 + random.randint(0, 69)) / 1000.0)
    cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": jx, "y": jy, "button": "left", "clickCount": 1})


def native_cdp_hold(cdp, x, y, duration_s):
    """Port tu actions.go NativeCDPHold: nhan giu chuot that cho Hold Captcha."""
    jx = x + (random.random() * 2.0 - 1.0)
    jy = y + (random.random() * 2.0 - 1.0)
    steps = max(1, int(duration_s / 0.2))
    cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": jx, "y": jy})
    time.sleep(0.04)
    cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": jx, "y": jy, "button": "left", "clickCount": 1})
    cx, cy = jx, jy
    for _ in range(steps):
        cx += (random.random() * 1.6 - 0.8)
        cy += (random.random() * 1.6 - 0.8)
        time.sleep(0.2)
        cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": cx, "y": cy, "button": "left"})
    time.sleep(0.08)
    cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": cx, "y": cy, "button": "left", "clickCount": 1})
    time.sleep(0.4)


def _add_cookie_kv(context_obj, cookie_str, domain):
    if not cookie_str:
        return
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and v:
            cookies.append({"name": k, "value": v, "domain": domain, "path": "/"})
    if cookies:
        try:
            context_obj.add_cookies(cookies)
        except Exception:
            pass


# JS doc so giay cho doi con lai tren trang (anti-bot timer) -> de Python dem nguoc dung so do
WAIT_EXTRACT_JS = r"""
(() => {
  try {
    const sels = ['#timer', '.timer', '#countdown', '.countdown', '.wait', '#wait',
                  '[class*="countdown"]', '[class*="timer"]', '[id*="countdown"]', '[id*="timer"]'];
    for (const s of sels) {
      const el = document.querySelector(s);
      if (el && el.offsetParent !== null) {
        const m = (el.innerText || el.textContent || '').match(/(\d{1,3})/);
        if (m) return parseInt(m[1], 10);
      }
    }
    const txt = document.body ? (document.body.innerText || '') : '';
    let m = txt.match(/(?:vui l[òo]ng [đd]ợi|please wait|[đd]ợi|ch[ờo])[^0-9]{0,25}(\d{1,3})/i);
    if (!m) m = txt.match(/\b(\d{1,3})\s*(?:gi[âa]y|s|sec|seconds)\b/i);
    if (m) {
      const n = parseInt(m[1], 10);
      if (n > 0 && n <= 300) return n;
    }
    return 0;
  } catch (e) { return 0; }
})();
"""


def solve_url(target_url, target_domain="", slot_id=0, proxy_url="", gate_cookies="", platform_name="", client_cookies="", headless=True):
    """Port tu SolveURL: mo Chrome (headless mac dinh, headful de xem), inject engine, intercept CDP, poll ket qua."""
    if not ENGINE_JS:
        return "", False, "Không tìm thấy thư mục scripts/ (engine.js) cạnh HTCT.py!"

    bypass_list = build_proxy_bypass_list(platform_name)

    sc = SolveContext(slot_id, target_url)
    sc.target_domain = target_domain
    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        launch_kwargs = {
            "headless": bool(headless),
            "args": build_chrome_args(proxy_url, bypass_list, headless=bool(headless)),
        }
        if proxy_url:
            pw_proxy = {"server": proxy_url}
            if bypass_list:
                bypass_parts = ["localhost", "127.0.0.1"] + [x.strip() for x in bypass_list.split(",") if x.strip()]
                pw_proxy["bypass"] = ";".join(bypass_parts)
            launch_kwargs["proxy"] = pw_proxy
        browser = pw.chromium.launch(**launch_kwargs)
        ctx_kwargs = {
            "user_agent": ua_for_slot(slot_id),
            "viewport": None if not headless else {"width": 1920, "height": 1080},
            "ignore_https_errors": True,
            "java_script_enabled": True,
        }
        context_obj = browser.new_context(**ctx_kwargs)
        page = context_obj.new_page()
        setup_cdp_interceptor(sc, page, context_obj)

        preset_script = ""
        if target_domain:
            preset_script += f"window.__OCTO_TARGET_DOMAIN__ = \"{target_domain}\";\n"
        if gate_cookies:
            preset_script += f"window.__OCTO_GATE_COOKIES__ = \"{gate_cookies}\";\n"
        injection = STEALTH_JS + "\n" + preset_script + "\n" + ENGINE_JS + "\n" + GIAI_CAP_JS + "\n" + HOOK_JS

        if gate_cookies:
            _add_cookie_kv(context_obj, gate_cookies, ".octolink.vip")
        if client_cookies:
            domain = ".yeutask.com" if platform_name == "yeutask" else ".moneytask.top"
            _add_cookie_kv(context_obj, client_cookies, domain)
        # from_google nhu Chodenocto 5.5 document-start de qua Go without Earn
        try:
            context_obj.add_cookies([
                {"name": "from_google", "value": "true", "url": "https://octolink.vip"},
                {"name": "from_google", "value": "true", "url": "https://trafficvip.vip"},
            ])
        except Exception:
            pass

        try:
            context_obj.add_init_script(injection)
        except Exception:
            pass

        try:
            page.goto(target_url, wait_until="commit", timeout=60000)
            page.wait_for_timeout(2000)
        except Exception as e:
            return "", False, f"không thể mở trang trong Chrome: {e}"

        print_slot_info(slot_id, f"🌐 Đã mở trình duyệt tới link: {target_url}")

        deadline = time.time() + 500
        next_poll = 0.0
        wait_total = 0
        wait_end = 0.0
        wait_active = False
        finish_idle_ticks = 0

        while time.time() < deadline:
            # 1. Fail-Fast
            try:
                fail_reason = sc.fail_fast.get_nowait()
                clear_countdown_line()
                wait_active = False
                print_slot_warning(slot_id, f"⚠️ Fail-Fast: {fail_reason} -> Dừng sớm để xoay Proxy!")
                return "", False, f"proxy fail-fast: {fail_reason}"
            except queue.Empty:
                pass

            # 2. Nav tu engine (REDIRECT_TO_OCTO_SUCCESS) - di qua redirect_to_octo nhu Chodenocto 5.5
            try:
                nav_url = sc.nav.get_nowait()
                clear_countdown_line()
                wait_active = False
                # neu la redirect_to_octo -> tach finish url va di voi referer nhu ban goc, roi kich hoat giai captcha lay Link Goc (khong bam)
                if "redirect_to_octo=" in nav_url:
                    try:
                        from urllib.parse import unquote as _uq
                        base = getattr(sc, "target_domain", "") or ""
                        qpart = nav_url.split("redirect_to_octo=", 1)[1].split("&")[0]
                        finish_url = _uq(qpart)
                        if finish_url.startswith("http"):
                            print_slot_info(slot_id, f"➡️ Đi qua redirect_to_octo -> {finish_url[:80]}...")
                            try:
                                page.goto(finish_url, wait_until="commit", timeout=60000, referer=base if base else None)
                            except Exception:
                                pass
                            print_slot_info(slot_id, f"Đã tới trang finish, kích hoạt giải captcha để lấy Link Gốc trong nút (không bấm)...")
                        else:
                            try:
                                page.goto(nav_url, wait_until="commit", timeout=60000)
                            except Exception:
                                pass
                    except Exception:
                        try:
                            page.goto(nav_url, wait_until="commit", timeout=60000)
                        except Exception:
                            pass
                else:
                    try:
                        page.goto(nav_url, wait_until="commit", timeout=60000)
                    except Exception:
                        pass
                    if "/finish/" in nav_url:
                        print_slot_info(slot_id, f"Đã tới trang finish, kích hoạt giải captcha để lấy Link Gốc trong nút (không bấm)...")
            except queue.Empty:
                pass

            # 3. Ket qua tu interceptor
            try:
                r = sc.results.get_nowait()
                clear_countdown_line()
                wait_active = False
                if r.is_passcode:
                    print_slot_success(slot_id, f"🎉 Thu được mã Passcode từ tầng mạng CDP: {r.data}")
                else:
                    print_slot_success(slot_id, f"🎉 Link gốc (từ tầng mạng CDP): {r.data}")
                return r.data, r.is_passcode, None
            except queue.Empty:
                pass

            # 4. Polling moi 1s (ticker)
            if time.time() >= next_poll:
                next_poll = time.time() + 1.0

                try:
                    current_url = page.url or ""
                except Exception:
                    current_url = ""

                # 4c. Da sang link goc (tab tu di chuyen sang host dich thu)
                if current_url.startswith("http") and not same_host(current_url, target_url) \
                        and not is_transient_nav_host(current_url) \
                        and not is_money_task_finish_url(current_url) \
                        and not is_yeu_task_url(current_url):
                    clear_countdown_line()
                    wait_active = False
                    print_slot_success(slot_id, f"🎉 Link gốc: {current_url}")
                    return current_url, False, None

                # 4d. Dem nguoc theo wait server tra tu /check/job & /check/continue (tung chang)
                try:
                    wait_now = int(page.evaluate(WAIT_EXTRACT_JS) or 0)
                except Exception:
                    wait_now = 0

                drained = False
                while True:
                    try:
                        w, wstep = sc.wait_req.get_nowait()
                    except queue.Empty:
                        break
                    drained = True
                    # Chang moi hoac server bao them thoi gian -> reset phien dem + gia han deadline de khong timeout giua chung
                    cur_step = getattr(sc, "wait_step", None)
                    if (not wait_active) or (wstep and wstep != cur_step) or w > (wait_end - time.time()):
                        wait_total = w
                        wait_end = time.time() + w
                        deadline = max(deadline, wait_end + 30)
                        wait_active = True
                        sc.wait_step = wstep
                        if wstep:
                            print_slot_info(slot_id, f"⏳ [CHẶNG {wstep}] Server báo chờ {w}s -> bắt đầu đếm ngược")
                    elif w > 0:
                        wait_total = max(wait_total, w)
                        wait_end = time.time() + w
                        deadline = max(deadline, wait_end + 30)

                if drained and wait_active:
                    next_poll = time.time() + 1.0

                if wait_active:
                    remaining = max(0, int(round(wait_end - time.time())))
                    if remaining > 0:
                        label = "WAIT"
                        step_lbl = getattr(sc, "wait_step", None)
                        if step_lbl:
                            label = f"CHẶNG {step_lbl}"
                        print_countdown_progress(slot_id, remaining, max(wait_total, remaining), label)
                    else:
                        clear_countdown_line()
                        wait_active = False
                        sc.last_dom_wait = -1
                elif wait_now > 0 and wait_now != getattr(sc, "last_dom_wait", -1):
                    # Fallback: doc timer tren trang khi server khong tra wait
                    sc.last_dom_wait = wait_now
                    wait_total = wait_now
                    wait_end = time.time() + wait_now
                    deadline = max(deadline, wait_end + 30)
                    wait_active = True
                else:
                    clear_countdown_line()

# 5. solver_check.js
            try:
                raw_json = page.evaluate(SOLVER_CHECK_JS) or ""
            except Exception:
                raw_json = ""
            res = None
            if raw_json:
                try:
                    res = json.loads(raw_json)
                except Exception:
                    res = None
                if res:
                    rtype = res.get("type", "")
                    rdata = res.get("data", "")
                    if rtype == "code":
                        clear_countdown_line()
                        wait_active = False
                        print_slot_success(slot_id, f"🎉 Đã nhận mã Passcode: {rdata}")
                        return rdata, True, None
                    if rtype == "url":
                        clear_countdown_line()
                        wait_active = False
                        print_slot_success(slot_id, f"🎉 Link gốc: {rdata}")
                        return rdata, False, None
                    if rtype == "hold_captcha":
                            clear_countdown_line()
                            wait_active = False
                            print_slot_success(slot_id, f"🎯 {res.get('text', '')}")
                            time.sleep(2.5)
                    elif rtype == "navigate":
                        clear_countdown_line()
                        wait_active = False
                        print_slot_info(slot_id, "🚀 Đang chuyển tiếp bước cuối qua Link Gốc...")
                        try:
                            page.goto(rdata, wait_until="commit", timeout=60000)
                        except Exception:
                            pass
                        time.sleep(1.5)
                    elif rtype == "idle":
                        # Tiep tuc polling cho den khi co Link Goc hoac het gio
                        pass
                # Kiem tra 404 sau khi giai captcha - ghi HTML ra txt nhu yeu cau
                try:
                    is_404 = page.evaluate("""() => {
                        const t = (document.title || '').toLowerCase();
                        const b = document.body ? document.body.innerText.toLowerCase() : '';
                        return t.includes('404') || (b.includes('404') && (b.includes('không tìm thấy') || b.includes('not found')));
                    }""")
                    if is_404:
                        print_slot_warning(slot_id, "⚠️ Trang sau khi giải captcha báo 404 - ghi HTML ra file txt")
                        try:
                            full_html = page.content()
                        except Exception:
                            try:
                                full_html = page.evaluate("document.documentElement ? document.documentElement.outerHTML : ''") or ""
                            except Exception:
                                full_html = ""
                        if full_html:
                            try:
                                txt_path = os.path.join(LOG_DIR, f"finish_404_{slot_id}_{int(time.time())}.txt")
                                with open(txt_path, "w", encoding="utf-8") as f:
                                    f.write(f"URL: {page.url}\n")
                                    f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                                    f.write(f"Slot: {slot_id}\n")
                                    f.write("="*80 + "\n")
                                    f.write(full_html)
                                print_slot_info(slot_id, f"📄 Đã ghi HTML trang 404 ra {txt_path} ({len(full_html)} bytes)")
                                write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] 404 HTML saved to {txt_path} len={len(full_html)}")
                            except Exception as e:
                                write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] 404 save err: {e}")
                        # Dung vong lap hien tai de tranh treo 240s, bao loi ro
                        # return "", False, f"trang finish tra ve 404 sau khi giai captcha: {page.url}"
                except Exception:
                    pass

                # Debug finish idle - khi o trang finish ma van idle (khong thay Link Goc)
                try:
                    cur_dbg = page.url or ""
                except Exception:
                    cur_dbg = ""
                if "/finish/" in cur_dbg:
                    is_idle = (not res) or (res.get("type") == "idle")
                    if is_idle:
                        finish_idle_ticks += 1
                        if finish_idle_ticks % 5 == 0:
                            try:
                                # Lay ca outerHTML va body innerHTML de dam bao bat duoc Link Goc
                                html_snip = page.evaluate("""() => {
                                    const b = document.body ? document.body.innerHTML.slice(0,2000) : '';
                                    const h = document.documentElement ? document.documentElement.outerHTML.slice(0,2000) : '';
                                    return (b.length > 100 ? b : h).slice(0,800);
                                }""") or ""
                                html_snip = html_snip.replace("\n", " ").replace("\r", " ")[:500]
                                has_link = "Link G" in html_snip or "link goc" in html_snip.lower() or "yeutask.com" in html_snip.lower()
                                print_slot_info(slot_id, f"🔍 [FINISH] idle {finish_idle_ticks}s | has LinkGoc? {has_link} | URL: {cur_dbg[:70]}")
                                if html_snip:
                                    write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] FINISH HTML: {html_snip[:700]}")
                                if finish_idle_ticks % 15 == 0:
                                    try:
                                        full = page.content()
                                        # Neu page.content chi co head, lay them body
                                        if len(full) < 500:
                                            try:
                                                body_html = page.evaluate("document.body ? document.body.innerHTML : ''") or ""
                                                full += "\n<!-- BODY_INNER -->\n" + body_html[:3000]
                                            except Exception:
                                                pass
                                        tp = os.path.join(LOG_DIR, f"finish_idle_{slot_id}_{int(time.time())}.txt")
                                        with open(tp, "w", encoding="utf-8") as f:
                                            f.write(f"URL: {cur_dbg}\nIdle: {finish_idle_ticks}s\nhasHold={page.evaluate('!!(window.HOLD_CAPTCHA_CID && document.getElementById(\"hold_captcha_response\"))')}\n")
                                            f.write(full)
                                        write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] FINISH IDLE HTML saved {tp} len={len(full)} hasHold={page.evaluate('!!(window.HOLD_CAPTCHA_CID && document.getElementById(\"hold_captcha_response\"))')}")
                                    except Exception as e:
                                        write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] FINISH IDLE save err: {e}")
                            except Exception:
                                pass
                    else:
                        finish_idle_ticks = 0
                else:
                    finish_idle_ticks = 0

            time.sleep(0.1)

        return "", False, "hết thời gian chờ bypass trong Chrome (500s)"

    except Exception as e:
        return "", False, f"Lỗi trình duyệt: {e}"
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass


# ============================================================================
# JOB RUNNER (port tu job_runner.go)
# ============================================================================

proxy_failure_reporter = None


def report_proxy_failure(proxy_url):
    if proxy_url and proxy_failure_reporter is not None:
        proxy_failure_reporter(proxy_url)


def is_valid_partner_domain(raw_url):
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        return False
    system_domains = [
        "octolink.vip", "trafficvip.vip", "linkhuongdan", "google.com",
        "facebook.com", "youtube.com", "zalo.me", "cloudflare.com",
        "minuc.vn", "moneytask.top", "yeutask.com",
    ]
    lower = raw_url.lower()
    return not any(d in lower for d in system_domains)


def saved_domain_for(task_key):
    dom, _ = get_campaign_domain(task_key)
    return dom


class JobRunner:
    def __init__(self, license_key=""):
        self.license_key = license_key

    def run_with_slot(self, raw_input, slot_id=0, is_multi_slot=False, proxy_url="", platform_name="", client_cookies=""):
        global ACTIVE_MONEYTASK_JOBS
        start_time = time.time()
        raw_input = sanitize_input_url(raw_input)
        if not raw_input:
            print_diagnostic_box(slot_id, "INIT", "ERR_EMPTY_URL",
                                 "Đường dẫn URL đầu vào trống hoặc không hợp lệ",
                                 "Kiểm tra lại định dạng link nhiệm vụ")
            return "", False, "đường dẫn nhiệm vụ không được để trống"

        print_slot_info(slot_id, f"Bắt đầu xử lý link: {raw_input}")
        orig_input = raw_input
        remember_octo_link(raw_input)

        # 0. Cong Octolink: TRINH DUYET tu qua (khong resolve bang requests nua).
        # TrafficVIP giu resolve cu (engine khong cover cong trafficvip).
        gate_cookies = ""
        if ("octolink.vip" in raw_input):
            print_slot_info(slot_id, "Trình duyệt tự qua cổng Octolink (không resolve trước)...")
        if ("trafficvip" in raw_input) and ("octolink.vip" not in raw_input):
            gate_info = resolve_gate_url(raw_input, proxy_url, slot_id)
            if gate_info["resolved_url"] and gate_info["resolved_url"] != raw_input:
                print_slot_success(slot_id, f"🔓 Đã tự động mở cổng thiết bị Octolink: {raw_input} -> {gate_info['resolved_url']}")
                if gate_info["cookie_str"]:
                    if is_dev_mode():
                        print_slot_info(slot_id, f"🍪 Đã đồng bộ Cookie phiên Octolink Gate: {gate_info['cookie_str']}")
                    else:
                        print_slot_info(slot_id, "🍪 Đã đồng bộ phiên Cookie Octolink Gate thành công.")
                    write_log_file(f"[{timestamp_now()}] [#{slot_id:02d}] Gate Cookies: {gate_info['cookie_str']}")
                    gate_cookies = gate_info["cookie_str"]
                raw_input = gate_info["resolved_url"]

        # 1. Alias / taskKey (id chi nhan so-so, alias sai nhu wFIU7pa/hblQD57 thi bo)
        alias = extract_alias_from_input(raw_input)
        task_key = extract_task_key(raw_input) or ""
        if task_key and not is_strict_task_key(task_key):
            task_key = ""
        if not task_key and alias and is_strict_task_key(alias):
            task_key = alias
        # 1b. Noi alias octo -> camp id qua GitHub redirects (vd XtQr -> 140-2)
        # roi tra domain tu file local nhu thuong
        if not task_key and alias:
            _camp = _alias_to_camp_id(alias)
            if _camp:
                task_key = _camp
                print_slot_info(slot_id, f"🔗 Alias [{alias}] -> camp [{task_key}] (GitHub redirects)")

        # 2. Blacklist (dinh blacklist thi lay lai link octo vua dan lam lai 5 lan, het thi xoay proxy)
        blacklisted, black_token = is_campaign_blacklisted(task_key, raw_input)
        if blacklisted:
            retry, attempt = _blacklist_should_retry(orig_input)
            if retry:
                print_slot_warning(slot_id, f"⛔ Camp [{task_key}] blacklist, thử lại {attempt}/5 với link vừa dán...")
                time.sleep(1)
                return self.run_with_slot(orig_input, slot_id, is_multi_slot, proxy_url, platform_name, client_cookies)
            _blacklist_reset(orig_input)
            try:
                report_proxy_failure(proxy_url)
            except Exception:
                pass
            rotate_slot_key(slot_id)
            force_slot_rotate(slot_id)
            print_slot_warning(slot_id, f"⛔ Nhiệm vụ [{task_key}] khớp mã camp lỗi [{black_token}] trong {BlacklistCampsFileName} -> Tự động bỏ qua + xoay IP mới cho link tiếp theo!")
            return "", False, f"camp [{task_key}] nằm trong danh sách đen ({black_token})"

        # 2.1 Skip cooldown
        if task_key and is_campaign_temporarily_skipped(task_key):
            print_slot_warning(slot_id, f"⛔ Nhiệm vụ [{task_key}] đang trong danh sách tạm bỏ qua ({int(GLOBAL_SKIP_COOLDOWN / 60)} phút) -> Tự động bỏ qua ngay!")
            return "", False, f"camp [{task_key}] đang trong thời gian tạm bỏ qua"

        # 3. Tra cuu domain dich
        target_domain = ""
        if task_key:
            dom, ok = get_campaign_domain(task_key)
            if ok and dom:
                target_domain = dom
                print_slot_success(slot_id, f"🎯 Đã tra cứu domain chiến dịch: [{task_key}] -> {target_domain}")
        # 3b. Chua co domain ma co alias octo -> tra thang qua guild_link MoneyTask
        if not target_domain and alias:
            domA = _domain_from_moneytask_alias(alias)
            if domA:
                target_domain = domA
                print_slot_success(slot_id, f"🎯 Alias [{alias}] -> domain MoneyTask: {target_domain}")

        # 3.1 Tu dong phat hien redirect (nhap vao chrome ra url khac) -> cap nhat
        if target_domain:
            try:
                r = requests.head(target_domain, allow_redirects=True, timeout=6, verify=False, headers={"User-Agent": DEFAULT_UA, "Accept": "text/html"})
                # neu HEAD bi chan (405), thu GET nhe
                if r.status_code in (405, 403):
                    r = requests.get(target_domain, allow_redirects=True, timeout=6, verify=False, headers={"User-Agent": DEFAULT_UA}, stream=True)
                    r.close()
                final_host = (urlparse(r.url).hostname or "").lower()
                orig_host = (urlparse(target_domain).hostname or "").lower()
                if final_host and orig_host and final_host != orig_host:
                    new_dom = f"{urlparse(r.url).scheme}://{final_host}"
                    print_slot_warning(slot_id, f"⚠️ Domain [{target_domain}] khi load thực tế redirect -> [{new_dom}] (Chrome thấy khác). Tự động cập nhật file!")
                    save_campaign_domain(task_key, new_dom)
                    target_domain = new_dom
            except Exception:
                pass

        # 4. Khong co domain -> chi hoi neu la camp id thuc (vd 168-2), khong hoi cho alias octolink nhu wFIU7pa
        if not target_domain and task_key:
            is_real_camp = bool(re.match(r'^\d+-\d+$', task_key) or task_key.startswith('totreview-'))
            if not is_real_camp and re.match(r'^[A-Za-z0-9]{5,}$', task_key) and not re.search(r'\d+-\d+', raw_input):
                print_slot_info(slot_id, f"Alias Octolink [{task_key}] chua co camp id, cho mo cong lay linkhuongdan roi moi hoi domain...")
            else:
                print_slot_warning(slot_id, f"Chưa tìm thấy web đích cho camp [{task_key}] trên MoneyTask & GitHub. Bạn có muốn nhập thủ công?")
                new_domain, ok = prompt_manual_domain(slot_id, task_key, "", raw_input)
                if ok and new_domain:
                    save_campaign_domain(task_key, new_domain)
                    target_domain = new_domain
                    print_slot_success(slot_id, f"Đã lưu domain [{new_domain}] cho camp [{task_key}]!")
                else:
                    return "", False, f"đã bỏ qua campaign [{task_key}] do chưa có tên miền web đích"

        # 5. Solve - MoneyTask: tam dung goi them link khi dang o chang 1 cho den khi co Link Goc
        start_url = raw_input
        if VIEW_MODE:
            print_slot_info(slot_id, f"🖥️ [VIEW MODE] Mở Chrome thật để theo dõi quá trình giải: {start_url}")
        else:
            print_slot_info(slot_id, f"🚀 Mở trình duyệt ngầm xử lý link nhiệm vụ: {start_url}")
        is_moneytask_pause = (platform_name == "moneytask")
        if is_moneytask_pause:
            with MONEYTASK_PAUSE_LOCK:
                ACTIVE_MONEYTASK_JOBS += 1
            print_slot_info(slot_id, "⏸️ [MoneyTask] Bắt đầu chặng 1 -> Tạm dừng gọi thêm link Octo cho đến khi có Link Gốc...")
        try:
            res, is_code, err = solve_url(start_url, target_domain, slot_id, proxy_url, gate_cookies, platform_name, client_cookies, headless=not VIEW_MODE)

            if err:
                if "proxy" in err:
                    report_proxy_failure(proxy_url)
                record_task_failure()
                return "", False, f"không thể hoàn thành nhiệm vụ: {err}"

            if (not is_code) and task_key and res and res != saved_domain_for(task_key) and is_valid_partner_domain(res):
                try:
                    host = extract_host(res)
                    if host:
                        save_campaign_domain(task_key, f"https://{host}")
                        print_slot_info(slot_id, f"💾 Đã tự lưu domain mới [https://{host}] cho camp [{task_key}]")
                except Exception:
                    pass

            # 5.1 Link Goc la trang moneytask.top/finish?attempt=... -> mo an + bam Xac nhan claim
            if (not is_code) and res and is_moneytask_finish_claim_url(res):
                try:
                    claimed = moneytask_auto_claim(res, slot_id)
                    if claimed:
                        print_slot_success(slot_id, "✅ [MT-CLAIM] Xong claim MoneyTask.")
                    else:
                        print_slot_warning(slot_id, "Claim MoneyTask chua xong (xem log tren), Link Goc van giu.")
                except Exception as e:
                    print_slot_warning(slot_id, f"Claim MoneyTask loi: {e}")

            elapsed_s = time.time() - start_time
            elapsed = time.strftime("%Mm%Ss", time.gmtime(elapsed_s))
            print_slot_result_box(slot_id, res, is_code, elapsed)
            record_task_success(is_code, elapsed_s)
            _blacklist_reset(orig_input)
            return res, is_code, None
        finally:
            if is_moneytask_pause:
                with MONEYTASK_PAUSE_LOCK:
                    ACTIVE_MONEYTASK_JOBS = max(0, ACTIVE_MONEYTASK_JOBS - 1)
                print_slot_success(slot_id, "▶️ [MoneyTask] Đã có Link Gốc / kết thúc -> Tiếp tục gọi link Octo mới...")


# ============================================================================
# LOCAL BRIDGE SERVER (port tu http_server.go)
# ============================================================================

class BridgeState:
    def __init__(self, runner, port, max_concurrency, proxy_mgr, target_tasks=0):
        self.runner = runner
        self.port = port or "8080"
        self.max_concurrency = max(1, max_concurrency)
        self.proxy_mgr = proxy_mgr
        self.target_tasks = target_tasks
        self.tg_mu = threading.Lock()
        self.tg_inbox = []
        self.tg_outbox = {}
        self.completed_tasks = 0
        self.slots = [False] * self.max_concurrency
        self.active_count = 0
        self.mu = threading.Lock()

    def acquire_slot(self):
        with self.mu:
            for i in range(self.max_concurrency):
                if not self.slots[i]:
                    self.slots[i] = True
                    self.active_count += 1
                    return i + 1
            return 0

    def release_slot(self, slot_id):
        with self.mu:
            idx = slot_id - 1
            if 0 <= idx < self.max_concurrency:
                self.slots[idx] = False
                self.active_count -= 1


BRIDGE_STATE = None


# ============================================================================
# TELEGRAM RELAY (phone -> tool -> phone): inbox link + outbox Link Goc
# tg_relay.py POST link vao, main loop lay ra xu ly, xong day ket qua ve.
# ============================================================================
def tg_push_inbox(chat_id, url):
    try:
        s = BRIDGE_STATE
        u = (url or "").strip()
        if not (u.lower().startswith("http://") or u.lower().startswith("https://")):
            return False
        if s is None:
            return False
        with s.tg_mu:
            s.tg_inbox.append((int(chat_id), u))
        return True
    except Exception:
        return False


def tg_pop_inbox():
    try:
        s = BRIDGE_STATE
        if s is None:
            return None
        with s.tg_mu:
            if s.tg_inbox:
                return s.tg_inbox.pop(0)
        return None
    except Exception:
        return None


def tg_push_result(chat_id, ok, link="", err=""):
    try:
        s = BRIDGE_STATE
        if s is None:
            return
        with s.tg_mu:
            s.tg_outbox.setdefault(int(chat_id), []).append(
                {"ok": bool(ok), "link": link or "", "err": (err or "")[:300]})
    except Exception:
        pass


def tg_pop_result(chat_id):
    try:
        s = BRIDGE_STATE
        if s is None:
            return None
        with s.tg_mu:
            q = s.tg_outbox.get(int(chat_id)) or []
            if q:
                return q.pop(0)
        return None
    except Exception:
        return None


def read_console_or_tg():
    """Cho console HOAC link Telegram: tra (text, ok, chat_id|None)."""
    while True:
        try:
            s = _stdin_queue.get_nowait()
        except queue.Empty:
            s = None
        if s is not None:
            if s == EOF_TOKEN:
                return "", False, None
            return s.strip(), True, None
        if _stdin_eof:
            return "", False, None
        tg = tg_pop_inbox()
        if tg:
            cid, url = tg
            print_slot_info(0, f"📩 Link tu Telegram: {url[:70]}...")
            return url, True, cid
        time.sleep(0.5)
MONEYTASK_PAUSE_LOCK = threading.Lock()
ACTIVE_MONEYTASK_JOBS = 0
ACTIVE_KEY_XOAY_VIP = ""
ACTIVE_PROVIDER_VIP = ""
FORCE_DIRECT = False  # chon "3" o prompt proxy = tat het proxy (key + file), di thang Direct


def get_file_proxy(mgr, slot=1):
    if FORCE_DIRECT:
        return ""
    try:
        return mgr.get_next_proxy(slot) if mgr is not None else ""
    except Exception:
        return ""


def respond_json(handler, status_code, data):
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except Exception:
        pass


class BridgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "HTCT/7.3"

    def log_message(self, fmt, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            try:
                self.connection.close()
            except Exception:
                pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            try:
                self.connection.close()
            except Exception:
                pass

    # ---- localhost-only (chan DNS rebinding), CORS do respond_json tu them ----
    def _guard(self):
        host = self.headers.get("Host", "")
        if ":" in host and "]" not in host:
            host = host.rsplit(":", 1)[0]
        host = host.lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            self.send_error(403, "forbidden")
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        if path == "/api/status":
            self.handle_status()
        elif path == "/api/tg_result":
            self.handle_tg_result()
        else:
            self.send_error(404)

    def do_POST(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        if path == "/api/solve":
            self.handle_solve()
        elif path == "/api/proxy":
            self.handle_forward(relay_mode=False)
        elif path == "/api/relay":
            self.handle_forward(relay_mode=True)
        elif path == "/api/tg_submit":
            self.handle_tg_submit()
        else:
            self.send_error(404)

    # ---- Telegram relay ----
    def handle_tg_submit(self):
        req = self._read_json()
        if req is None:
            self.send_error(400)
            return
        try:
            cid = int(req.get("chat_id", 0) or 0)
        except Exception:
            cid = 0
        url_str = str(req.get("url", "") or "")
        if cid <= 0 or not tg_push_inbox(cid, url_str):
            self.send_error(400, "bad chat_id/url")
            return
        respond_json(self, 200, {"ok": True})

    def handle_tg_result(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            cid = int((qs.get("chat_id") or ["0"])[0] or 0)
        except Exception:
            cid = 0
        if cid <= 0:
            self.send_error(400, "bad chat_id")
            return
        r = tg_pop_result(cid)
        if r is None:
            respond_json(self, 200, {"ok": True, "empty": True})
        else:
            respond_json(self, 200, {"ok": True, "empty": False, "result": r})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except Exception:
            length = 0
        length = min(length, maxBridgeBodyBytes)
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            return None

    # ---- /api/solve ----
    def handle_solve(self):
        global BRIDGE_STATE
        s = BRIDGE_STATE
        if s is None:
            self.send_error(500)
            return

        if self.command != "POST":
            self.send_error(405)
            return

        # 0. Target tasks check
        with s.mu:
            if s.target_tasks > 0 and s.completed_tasks >= s.target_tasks:
                done, target = s.completed_tasks, s.target_tasks
                print_warning(f"⛔ ĐÃ ĐẠT MỤC TIÊU [{done}/{target}] NHIỆM VỤ! Tự động dừng nhận thêm nhiệm vụ để bảo vệ tài khoản.")
                respond_json(self, 200, {
                    "status": "stopped",
                    "message": f"Đã đạt mục tiêu {done}/{target} nhiệm vụ! Tool đã dừng an toàn.",
                    "readyForNext": False,
                    "timestamp": int(time.time()),
                })
                return

        # 1. Slot
        slot_id = s.acquire_slot()
        if slot_id == 0:
            print_warning(f"Từ chối request: Đã sử dụng hết {s.max_concurrency}/{s.max_concurrency} luồng xử lý song song!")
            respond_json(self, 429, {
                "status": "busy",
                "message": "Tất cả các luồng xử lý đang bận. Vui lòng chờ luồng hoàn tất!",
                "readyForNext": False,
                "timestamp": int(time.time()),
            })
            return

        try:
            req = self._read_json() or {}
            task_url = sanitize_input_url(str(req.get("url", "")))
            if not task_url:
                respond_json(self, 400, {
                    "status": "error", "slotId": slot_id,
                    "message": "URL nhiệm vụ không hợp lệ",
                    "readyForNext": True, "timestamp": int(time.time()),
                })
                return

            print_slot_info(slot_id, f"📥 [NHẬN TỪ TRÌNH DUYỆT] {task_url}")

            # 2. Platform detection
            client_origin = self.headers.get("Origin", "") or str(req.get("origin", "") or "")
            client_referer = self.headers.get("Referer", "")
            plat_name = platform_detect(str(req.get("platform", "") or ""), client_origin, client_referer, task_url, "")
            if plat_name != "unknown":
                print_slot_info(slot_id, f"🏷️ [NỀN TẢNG NHIỆM VỤ] {platform_display_name(plat_name)} (Tự động nhận diện)")

            # 3. Proxy - uu tien key RIENG cua slot (le -> key 1, chan -> key 2)
            proxy_url = get_proxy_with_api_fallback(slot_id)
            if not proxy_url and s.proxy_mgr is not None:
                proxy_url = get_file_proxy(s.proxy_mgr, slot_id)

            # 4. Run - demo/session thi goi lai link gan nhat toi 5 lan, loi khac 3 lan
            result, is_passcode, err = None, False, None
            for attempt in range(5):
                result, is_passcode, err = s.runner.run_with_slot(
                    task_url, slot_id, s.max_concurrency > 1, proxy_url,
                    plat_name, str(req.get("cookies", "") or ""),
                )
                if not err:
                    break
                if ("bỏ qua" in err) or ("danh sách đen" in err):
                    print_slot_warning(slot_id, f"Nhiệm vụ được bỏ qua: {err}")
                    break
                retryable = is_retryable_err(err)
                is_demo = is_demo_err(err)
                max_att = 5 if is_demo else 3
                if retryable and attempt < max_att - 1:
                    if is_demo:
                        rec = recall_last_octo()
                        if rec:
                            task_url = rec
                            print_slot_warning(slot_id, f"🔄 Demo/session/timeout -> dùng lại link octo gần nhất (lần {attempt+1}/{max_att})...")
                    print_slot_warning(slot_id, f"🔄 Lỗi retryable ({err[:60]}...) -> Thử lại {attempt+1}/{max_att} (giữ IP) cho {task_url[:40]}...")
                    if proxy_url and (is_proxy_level_err(err) or is_session_dead_err(err)) and s.proxy_mgr:
                        try:
                            s.proxy_mgr.mark_proxy_failed(proxy_url)
                        except Exception:
                            pass
                        # Xoay khi proxy chet HOAC session chet (job cu chet roi);
                        # loi server khac thi GIU IP keo mat job
                        rotate_slot_key(slot_id)
                        force_slot_rotate(slot_id)
                        proxy_url = get_proxy_with_api_fallback(slot_id) or ""
                        if not proxy_url:
                            proxy_url = get_file_proxy(s.proxy_mgr, slot_id)
                    time.sleep(2)
                    continue
                else:
                    break

            if err:
                if ("bỏ qua" in err) or ("danh sách đen" in err):
                    print_slot_warning(slot_id, f"Nhiệm vụ được bỏ qua: {err}")
                else:
                    print_slot_error(slot_id, f"Xử lý thất bại: {err}")
                respond_json(self, 500, {
                    "status": "error", "slotId": slot_id, "platform": plat_name,
                    "message": err, "readyForNext": True, "timestamp": int(time.time()),
                })
                return

            print_slot_success(slot_id, "📤 Đã giải xong! Gửi tín hiệu hoàn tất (OCTO_TASK_FINISHED_OK) về Trình duyệt.")

            # 4.1 Progress
            with s.mu:
                s.completed_tasks += 1
                current_done = s.completed_tasks
                target = s.target_tasks

            if target > 0:
                percent = current_done / target * 100
                print_slot_success(slot_id, f"📊 [TIẾN ĐỘ] Đã hoàn thành: {current_done}/{target} nhiệm vụ ({percent:.1f}%)")
                if current_done >= target:
                    print()
                    print_success("═════════════════════════════════════════════════════════════════════")
                    print_success(f"🎉 CHÚC MỪNG: ĐÃ ĐẠT ĐỦ MỤC TIÊU [{current_done} / {target}] NHIỆM VỤ ĐÃ ĐẶT RA!")
                    print_success("🛡️ Hệ thống tự động dừng nhận thêm nhiệm vụ để bảo vệ an toàn tài khoản.")
                    print_success("═════════════════════════════════════════════════════════════════════")
            else:
                print_slot_success(slot_id, f"📊 [TIẾN ĐỘ] Đã hoàn thành: {current_done} nhiệm vụ (Chế độ chạy liên tục)")

            # 5. Response
            resp = {
                "status": "success", "slotId": slot_id, "platform": plat_name,
                "isPasscode": is_passcode, "readyForNext": True,
                "signalCode": "OCTO_TASK_FINISHED_OK", "timestamp": int(time.time()),
            }
            if is_passcode:
                resp["code"] = result
            else:
                resp["url"] = result
                if plat_name == "moneytask" or ("moneytask.top/finish" in result):
                    resp["completed"] = True
                    resp["message"] = "Đã tự động vượt Anti-Cheat và bấm Xác nhận hoàn thành MoneyTask!"
                if plat_name == "yeutask" or ("yeutask" in result):
                    resp["completed"] = True
                    resp["message"] = "Đã tự động xác thực Cloudflare và hoàn thành nhiệm vụ YeuTask!"
            respond_json(self, 200, resp)
        finally:
            s.release_slot(slot_id)

    # ---- /api/status ----
    def handle_status(self):
        global BRIDGE_STATE
        s = BRIDGE_STATE
        if s is None:
            self.send_error(500)
            return
        with s.mu:
            active = s.active_count
            max_slots = s.max_concurrency
            completed = s.completed_tasks
            target = s.target_tasks
        free = max_slots - active
        is_stopped = target > 0 and completed >= target
        with MONEYTASK_PAUSE_LOCK:
            paused = ACTIVE_MONEYTASK_JOBS > 0
        respond_json(self, 200, {
            "status": "stopped" if is_stopped else "running",
            "service": "Hỗ Trợ Cụt Tay Bridge",
            "version": "v7.3",
            "maxSlots": max_slots,
            "activeSlots": active,
            "freeSlots": free,
            "isBusy": free == 0,
            "completedTasks": completed,
            "targetTasks": target,
            "isTargetReached": is_stopped,
            "pauseMoneytask": paused,
            "timestamp": int(time.time()),
        })

    # ---- /api/proxy + /api/relay ----
    def handle_forward(self, relay_mode=False):
        req = self._read_json()
        if req is None:
            self.send_error(400)
            return
        url_str = str(req.get("url", "") or "")
        if not url_str.lower().startswith("http://") and not url_str.lower().startswith("https://"):
            self.send_error(400, "only http/https URLs allowed")
            return
        method = str(req.get("method", "") or "GET").upper()
        headers = req.get("headers") or {}
        data = str(req.get("data", "") or "")
        is_base64 = bool(req.get("is_base64", False))

        body_bytes = b""
        if data:
            if is_base64:
                try:
                    body_bytes = base64.b64decode(data)
                except Exception:
                    body_bytes = data.encode("utf-8", "ignore")
            else:
                body_bytes = data.encode("utf-8", "ignore")

        out_headers = {}
        slot_for_log = 0
        fake_ip = ""
        if relay_mode:
            fake_ip = str(req.get("fake_ip", "") or "")
            try:
                slot_for_log = int(req.get("slot_id", 0) or 0)
            except Exception:
                slot_for_log = 0

        for k, v in headers.items():
            lk = k.lower()
            if lk == "content-length":
                continue
            if lk == "cookie":
                out_headers["Cookie"] = str(v).replace("\r", "").replace("\n", " ").strip()
                continue
            out_headers[k] = v
        if not out_headers.get("User-Agent"):
            out_headers["User-Agent"] = DEFAULT_UA

        if relay_mode and fake_ip:
            out_headers["X-Forwarded-For"] = fake_ip
            out_headers["X-Real-IP"] = fake_ip
            out_headers["CF-Connecting-IP"] = fake_ip
            print_slot_info(slot_for_log, f"🎭 [Relay] Fake IP={fake_ip} -> {url_str}")

        proxies = None
        # Relay cung uu tien key RIENG cua slot - chi log 1 lan moi khi doi proxy
        relay_proxy = get_proxy_with_api_fallback(slot_for_log)
        if relay_proxy:
            proxies = {"http": relay_proxy, "https": relay_proxy}
            # Chi log 1 lan moi khi proxy doi, tranh spam moi request
            if not hasattr(self, '_last_relay_proxy') or getattr(self, '_last_relay_proxy', '') != relay_proxy:
                print_slot_info(slot_for_log, f"🔀 [Relay] Route qua API Key proxy: {safe_proxy_string(relay_proxy)}")
                self._last_relay_proxy = relay_proxy
        elif relay_mode and BRIDGE_STATE is not None and BRIDGE_STATE.proxy_mgr is not None:
            slot_id = slot_for_log if slot_for_log > 0 else 1
            proxy_str = get_file_proxy(BRIDGE_STATE.proxy_mgr, slot_id)
            if proxy_str:
                proxies = {"http": proxy_str, "https": proxy_str}
                if not hasattr(self, '_last_relay_proxy') or getattr(self, '_last_relay_proxy', '') != proxy_str:
                    print_slot_info(slot_for_log, f"🔀 [Relay] Route qua proxy: {safe_proxy_string(proxy_str)}")
                    self._last_relay_proxy = proxy_str

        # Dung _OCTO_SESSION rieng cho octolink de tranh chung pool voi Kiot gay 10053, them delay chong rate limit
        try:
            # Chong rate limit octolink: nghi nhe neu vua goi xong
            if "octolink.vip" in url_str:
                try:
                    last_octo = getattr(self, '_last_octo_ts', 0)
                    now = time.time()
                    if now - last_octo < 0.8:
                        time.sleep(0.8 - (now - last_octo))
                    self._last_octo_ts = time.time()
                except Exception:
                    pass
            sess = _OCTO_SESSION if "octolink.vip" in url_str or "trafficvip" in url_str else requests
            resp = sess.request(method, url_str, headers=out_headers, data=body_bytes,
                                timeout=60, proxies=proxies, verify=False, allow_redirects=False)
        except Exception as e:
            print_slot_warning(slot_for_log, f"{'[Relay] ' if relay_mode else 'Proxy bridge '}forward error to {url_str}: {e}")
            self.send_error(502, str(e))
            return

        resp_headers = {}
        for k, v in resp.headers.items():
            lk = k.lower()
            if lk == "set-cookie":
                existing = resp_headers.get("set-cookie")
                resp_headers["set-cookie"] = (existing + "\nset-cookie: " + v) if existing else v
            else:
                resp_headers[k] = v

        body = resp.content[:maxBridgeBodyBytes]
        respond_json(self, 200, {
            "status": resp.status_code,
            "statusText": f"{resp.status_code} {resp.reason}",
            "responseText": body.decode("utf-8", "ignore"),
            "responseBase64": base64.b64encode(body).decode("ascii"),
            "responseHeaders": resp_headers,
        })


class QuietBridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def handle_error(self, request, client_address):
        ex = sys.exc_info()[1]
        if isinstance(ex, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError)):
            try:
                request.close()
            except Exception:
                pass
            return
        super().handle_error(request, client_address)


def start_bridge_server(runner, port, max_concurrency, proxy_mgr, target_tasks):
    global BRIDGE_STATE
    BRIDGE_STATE = BridgeState(runner, port, max_concurrency, proxy_mgr, target_tasks)
    try:
        httpd = QuietBridgeServer(("127.0.0.1", int(port)), BridgeHandler)
        httpd.daemon_threads = True
    except OSError as e:
        return None, e
    t = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    t.start()
    return httpd, None


# ============================================================================
# MAIN FLOW (port tu main.go - bo license theo yeu cau)
# ============================================================================

_exit_requested = threading.Event()


def handle_exit_signal():
    def _on_sigint(signum, frame):
        print()
        print_warning("Nhận tín hiệu dừng (Ctrl+C) — Đang dọn dẹp hệ thống...")
        print_session_summary()
        os._exit(0)

    import signal
    try:
        signal.signal(signal.SIGINT, _on_sigint)
        signal.signal(signal.SIGTERM, _on_sigint)
    except Exception:
        pass


def prompt_target_tasks():
    print_target_tasks_prompt_box()
    sys.stdout.write(f"  {ColorCyan2}{Bold}>> Bạn muốn làm bao nhiêu nhiệm vụ thì dừng? (Nhập số / Enter = Chạy / N = Tắt): {Reset}")
    sys.stdout.flush()

    raw, ok = read_line_eof()
    if not ok:
        print_info("Đầu vào kết thúc. Thoát ứng dụng.")
        os._exit(0)

    val = raw.strip()
    lower = val.lower()

    if lower in ("n", "no", "exit", "quit", "q"):
        print()
        print_warning(f"Bạn đã nhập '{val}' — Đang tắt ứng dụng. Hẹn gặp lại!")
        os._exit(0)

    try:
        n = int(val)
        if n > 0:
            print_success(f"Đã thiết lập mục tiêu: Chạy đúng {n} nhiệm vụ rồi tự động dừng an toàn!")
            return n
    except ValueError:
        pass

    print_success("Chế độ: Chạy KHÔNG GIỚI HẠN (Tự động cày liên tục xuyên suốt)!")
    return 0


def main():
    global VIEW_MODE
    parser = argparse.ArgumentParser(description="HTCT Engine v7.3 - Python Port")
    parser.add_argument("--url", default="", help="Đường dẫn nhiệm vụ cần vượt")
    parser.add_argument("--threads", type=int, default=0, help="Số luồng chạy song song (1-10)")
    parser.add_argument("--dev", action="store_true", help="Chế độ lập trình viên (hiển thị đầy đủ log debug)")
    parser.add_argument("--view", action="store_true", help="Mở Chrome THẬT (headful) để xem trực tiếp quá trình giải captcha & lấy Link Gốc")
    args = parser.parse_args()

    VIEW_MODE = bool(args.view)
    init_logger(args.dev)

    banner_ver = VERSION + (" [DEV]" if args.dev else "")
    print_prime_banner(banner_ver)
    handle_exit_signal()

    # 1. Cau hinh luong / xoay proxy
    threads, rotate_tasks = interactive_setup(args.threads)

    # 2. Muc tieu so nhiem vu
    target_tasks = prompt_target_tasks()

    # 3. Proxy manager (file)
    proxy_mgr = ProxyManager(rotate_tasks)
    proxy_count = proxy_mgr.get_proxy_count()
    global proxy_failure_reporter
    proxy_failure_reporter = proxy_mgr.mark_proxy_failed

    # 3.1 Proxy API Key - 2 slot doc lap (key 1 / key 2)
    _k, _pr = prompt_proxy_key_selection()
    # Luu de vong lap dung
    global ACTIVE_KEY_XOAY_VIP, ACTIVE_PROVIDER_VIP
    ACTIVE_KEY_XOAY_VIP = _k
    ACTIVE_PROVIDER_VIP = _pr
    # Luong >= 2: hoi not key slot con lai (moi luong 1 key + 1 UA rieng)
    if threads >= 2:
        _sl2, _ac2 = load_proxy_slots()
        _other = 2 if _ac2 == 1 else 1
        if not _sl2[_other]["key"]:
            print_info(f"Luồng 2 cần key RIÊNG (tránh trùng IP/UA với luồng 1). Dán key cho slot {_other} (Enter = dùng chung Direct/file):")
            try:
                _nk = read_line_eof(f"  Key slot {_other}: ").strip()
            except Exception:
                _nk = ""
            if _nk:
                _npr = detect_proxy_provider_vip(_nk)
                _sl2[_other] = {"key": _nk, "provider": _npr}
                save_proxy_slots(_sl2, _ac2)
                _t = get_rotating_key_proxy_vip(_nk, provider=_npr, rotate=False)
                print_success(f"  -> Slot {_other}: {_npr or '?'} OK ({safe_proxy_string(_t or '')}), luồng {_other} dùng UA Chrome riêng + key riêng.")

    # 4. Dashboard
    dash_ver = VERSION + (" [DEV]" if args.dev else "")
    print_dashboard({
        "threads": threads,
        "proxy_count": proxy_count,
        "rotate_tasks": rotate_tasks,
        "target_tasks": target_tasks,
        "completed_tasks": 0,
        "bridge_port": BridgePort,
    })

    if args.dev:
        print_info(f"Chế độ: BẢN DEV (Đầy đủ log debug & Ghi file: logs/hkt_debug.log)")
    else:
        print_info(f"Chế độ: BẢN THƯỜNG (Tự động lưu log chi tiết vào: logs/hkt_debug.log)")

    # 5. Job Runner
    runner = JobRunner()

    # 6. Bridge server
    httpd, listen_err = start_bridge_server(runner, BridgePort, threads, proxy_mgr, target_tasks)
    if listen_err is not None:
        print_error(f"Không thể mở cổng Bridge {BridgePort}: {listen_err}")
        print_warning(f"Hãy đóng ứng dụng đang chiếm cổng (netstat -ano | findstr :{BridgePort}) rồi khởi động lại tool!")
        try:
            input()
        except Exception:
            pass
        return
    print_success(f"Bridge Server đang lắng nghe tại http://127.0.0.1:{BridgePort}")

    # 7. Co --url: chay 1 nhiem vu roi vao che do lang nghe
    if args.url:
        task_url = sanitize_input_url(args.url)
        if not task_url:
            print_warning(f"URL truyền vào không hợp lệ: {args.url}")
        else:
            proxy_url = get_proxy_with_api_fallback(1) or get_file_proxy(proxy_mgr, 1)
            _, _, run_err = runner.run_with_slot(task_url, 1, False, proxy_url)
            if run_err:
                if ("bỏ qua" in run_err) or ("danh sách đen" in run_err):
                    print_warning(f"Nhiệm vụ được bỏ qua: {run_err}")
                else:
                    print_error(f"Xử lý link thất bại: {run_err}")

    # 8. Blacklist summary
    print_blacklist_summary()

    # 9. Che do lang nghe + nhap thu cong
    print()
    print_ready_listening(BridgePort)

    pending_auto = ""
    while True:
        print()
        sys.stdout.write(f"  {ColorT2}{Bold}>> Dán link nhiệm vụ {Reset}{ColorDarkGray}(gõ 'mt' lấy link MoneyTask, 'auto' bật/tắt tự động, 'exit' thoát): {Reset}")
        sys.stdout.flush()

        tg_chat = None
        if pending_auto:
            task_input = pending_auto
            pending_auto = ""
            print_slot_info(0, f"Tự động tiếp tục với: {task_input[:70]}...")
        else:
            raw_input, ok, tg_chat = read_console_or_tg()
            if not ok:
                print_session_summary()
                print_info("Đầu vào đã kết thúc — Hẹn gặp lại!")
                return
            task_input = raw_input.strip()
        if not task_input:
            continue
        if task_input.lower() in ("exit", "quit"):
            print_session_summary()
            print_info("Đã thoát chương trình. Hẹn gặp lại!")
            return
        if task_input.lower() in ("auto", "auto on", "auto off"):
            low = task_input.lower()
            if "off" in low:
                mt_set_auto(False)
                print_info("Auto MT: OFF (mt hoi cookie/chon tay).")
            elif "on" in low:
                mt_set_auto(True)
                print_info("Auto MT: ON (tu mt -> tu cookie -> tu chon 1 -> tu tiep).")
            else:
                mt_set_auto(not mt_auto_enabled())
                print_info(f"Auto MT: {'ON' if mt_auto_enabled() else 'OFF'}.")
            continue
        if task_input.lower() in ("pkey", "key", "proxykey"):
            _k, _pr = prompt_proxy_key_selection()
            ACTIVE_KEY_XOAY_VIP = _k
            ACTIVE_PROVIDER_VIP = _pr
            continue
        if task_input.lower() in ("mtc", "cookie", "mt-cookie"):
            _mt_save_cookie("")
            with _mt_cookie_lock:
                _mt_cookie_cache["loaded"] = False
            print_slot_info(0, "Da xoa cookie MoneyTask da luu. Lan 'mt' toi se hoi dan lai.")
            continue
        if task_input.lower() in ("mt", "moneytask", "money task", "money-task"):
            fetched = moneytask_auto_fetch_octo()
            if not fetched:
                continue
            task_input = fetched

        if re.fullmatch(r"\d{1,3}", task_input):
            print_warning("Số vừa gõ không phải link (chọn số ở prompt 'Chon nhiem vu' của lệnh mt). Gõ 'mt' để lấy task mới hoặc dán link octolink.")
            continue
        clean_input = sanitize_input_url(task_input)
        if not clean_input:
            print_warning("Đường dẫn không hợp lệ. Vui lòng nhập link bắt đầu bằng http:// hoặc https://")
            continue

        # Tu dong thu lai tu dau voi chinh link octo do khi gap loi retryable.
        # KHOA IP theo link: giu nguyen proxy suot cac attempt (server gan job theo IP);
        # chi xoay khi loi tang proxy chet. demo/session thi goi lai link gan nhat + toi 5 lan;
        # loi khac 3 lan; blacklist xu ly trong run_with_slot
        run_err = None
        res_url = ""
        proxy_url = get_proxy_with_api_fallback(1) or get_file_proxy(proxy_mgr, 1)
        for attempt in range(5):
            res_url, _, run_err = runner.run_with_slot(clean_input, 1, False, proxy_url)
            if not run_err:
                break
            if ("bỏ qua" in run_err) or ("danh sách đen" in run_err):
                print_warning(f"Nhiệm vụ được bỏ qua: {run_err}")
                break
            retryable = is_retryable_err(run_err)
            is_demo = is_demo_err(run_err)
            max_att = 5 if is_demo else 3
            if retryable and attempt < max_att - 1:
                if is_demo:
                    rec = recall_last_octo()
                    if rec:
                        clean_input = rec
                        print_warning(f"🔄 Demo/session/timeout -> dùng lại link octo gần nhất: {rec[:60]}... (lần {attempt+1}/{max_att})")
                    else:
                        print_warning(f"🔄 Lỗi retryable ({run_err[:60]}...) -> Thử lại {attempt+1}/{max_att}...")
                else:
                    print_warning(f"🔄 Lỗi retryable ({run_err[:60]}...) -> Thử lại {attempt+1}/{max_att} (giữ IP) cho link {clean_input[:40]}...")
                if proxy_url and (is_proxy_level_err(run_err) or is_session_dead_err(run_err)):
                    try:
                        proxy_mgr.mark_proxy_failed(proxy_url)
                    except Exception:
                        pass
                    rotate_slot_key(1)
                    force_slot_rotate(1)
                    proxy_url = get_proxy_with_api_fallback(1) or get_file_proxy(proxy_mgr, 1)
                time.sleep(2)
                continue
            else:
                print_error(f"Quá trình thất bại: {run_err}")
                break

        # Tra Link Goc ve Telegram (neu link tu phone)
        if tg_chat is not None:
            if not run_err and res_url:
                tg_push_result(tg_chat, True, link=res_url)
                print_slot_info(0, f"📤 Da gui Link Goc ve Telegram.")
            else:
                tg_push_result(tg_chat, False, err=run_err or "that bai")
                print_slot_warning(0, f"📤 Da bao loi ve Telegram: {(run_err or 'that bai')[:80]}")
            tg_chat = None

        # Auto tiep: thanh cong (octolink/moneytask) HOAC that bai het luot -> tu mt lay link moi
        if mt_auto_enabled():
            nxt = ""
            try:
                if not run_err and res_url and (("octolink.vip" in res_url) or ("moneytask.top" in res_url)):
                    print_slot_info(0, "Xong 1 link, tự động lấy link tiếp theo từ MoneyTask...")
                    nxt = moneytask_auto_fetch_octo(auto=True)
                elif run_err:
                    print_slot_info(0, "Thất bại hết lượt, tự động lấy link mới từ MoneyTask để tiếp tục...")
                    nxt = moneytask_auto_fetch_octo(auto=True)
            except Exception:
                nxt = ""
            if nxt:
                remember_octo_link(nxt)
                pending_auto = nxt
                continue


if __name__ == "__main__":
    main()
