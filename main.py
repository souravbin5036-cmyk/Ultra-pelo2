import hashlib
import json
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from queue import Queue
import threading
import os

API_URL = "https://api.shreewinapi.com/api/webapi/Register"
INVITE_CODE = "65232742363"

# Telegram Configurations
BOT_TOKEN = "8810691058:AAEzwc6Cu__7vTI6p95h8kKCOmQBt0verEU"
ADMIN_ID = 8401097557

# Runtime Control Variables
max_workers = 30
is_running = False
total_attempts = 0
success_count = 0
fail_count = 0

proxy_queue = Queue()
lock = threading.Lock()
bot_thread = None
worker_executor = None

def load_saved_proxies():
    # Agar railway par proxies.txt nahi hai, toh default fallback ya empty list use karegi
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    return []

def random_username():
    first_digit = random.choice(["6", "7", "8", "9"])
    remaining_digits = "".join(random.choices(string.digits, k=9))
    return "91" + first_digit + remaining_digits

def random_password():
    return "".join(random.choices(string.ascii_letters + string.digits, k=10)) + "S"

def generate_random_hex():
    return "".join(random.choices("0123456789abcdef", k=32))

def generate_signature(payload_dict):
    ignored_keys = {"signature", "track", "xosoBettingData", "timestamp"}
    filtered = {}
    for k in sorted(payload_dict.keys()):
        v = payload_dict[k]
        if v is not None and v != "" and k not in ignored_keys:
            filtered[k] = v
    raw_json = json.dumps(filtered, separators=(",", ":"), ensure_ascii=False)
    return hashlib.md5(raw_json.encode("utf-8")).hexdigest().upper()

def get_proxy():
    if proxy_queue.empty():
        return None
    try:
        return proxy_queue.get_nowait()
    except:
        return None

def return_proxy(proxy):
    if proxy:
        proxy_queue.put(proxy)

def register(index):
    global success_count, fail_count, total_attempts
    if not is_running:
        return None

    username = random_username()
    password = random_password()
    now_ts = int(time.time())
    rand_str = generate_random_hex()

    payload = {
        "username": username,
        "smsvcode": "",
        "registerType": "mobile",
        "pwd": password,
        "invitecode": INVITE_CODE,
        "packId": "",
        "domainurl": "www.shreewin16.com",
        "phonetype": 1,
        "captchaId": "",
        "track": "",
        "deviceId": generate_random_hex(),
        "pixelId": "",
        "fbcId": "",
        "fbc": "",
        "fbp": "",
        "adId": "",
        "language": 0,
        "random": rand_str,
    }

    payload["signature"] = generate_signature(payload)
    payload["timestamp"] = now_ts

    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Linux; Android 16; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]),
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.shreewin16.com",
        "Referer": "https://www.shreewin16.com/",
        "Accept": "application/json, text/plain, */*",
    }

    proxy = get_proxy()
    proxies = None
    if proxy:
        if not proxy.startswith("http"):
            proxy = f"http://{proxy}"
        proxies = {"http": proxy, "https": proxy}

    try:
        session = requests.Session()
        session.headers.update(headers)
        r = session.post(API_URL, json=payload, proxies=proxies, timeout=8)
        if proxy:
            return_proxy(proxy)
            
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text}

        code = data.get("code")
        with lock:
            total_attempts += 1
            if r.status_code == 200 and code == 0:
                success_count += 1
                with open("shreewin.txt", "a", encoding="utf-8") as f:
                    f.write(f"{username}:{password}\n")
                    f.flush()
                return True
            else:
                fail_count += 1
                return False
    except requests.RequestException:
        if proxy:
            return_proxy(proxy)
        with lock:
            total_attempts += 1
            fail_count += 1
        return False

def worker_loop():
    global is_running
    counter = 1
    proxy_pool = load_saved_proxies()
    for p in proxy_pool:
        proxy_queue.put(p)

    while is_running:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(register, counter + i) for i in range(max_workers)]
            for future in as_completed(futures):
                if not is_running:
                    break
            counter += max_workers
        time.sleep(0.1)

# Telegram Bot Handler using requests (No external python-telegram-bot dependency needed)
def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except:
        pass

def telegram_listener():
    global is_running, max_workers, success_count, fail_count, total_attempts
    offset = 0
    print("[+] Telegram bot listener started.")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35).json()
            if res.get("ok"):
                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat_id = message.get("from", {}).get("id")
                    text = message.get("text", "")

                    if chat_id != ADMIN_ID:
                        send_telegram_message(chat_id, "⚠️ Unauthorized access!")
                        continue

                    if text == "/start":
                        send_telegram_message(chat_id, "🤖 *ShreeWin Bot Active!*\n\nCommands:\n/run - Start generating accounts\n/stop - Stop process\n/status - Check live stats\n/speed <num> - Change threads (e.g. /speed 50)\n/getfile - Download shreewin.txt")
                    elif text == "/run":
                        if not is_running:
                            is_running = True
                            threading.Thread(target=worker_loop, daemon=True).start()
                            send_telegram_message(chat_id, "🚀 Account generation started successfully!")
                        else:
                            send_telegram_message(chat_id, "⚠️ Already running!")
                    elif text == "/stop":
                        is_running = False
                        send_telegram_message(chat_id, "🛑 Stopping account generation...")
                    elif text == "/status":
                        rate = (success_count / (total_attempts if total_attempts > 0 else 1)) * 100
                        status_text = f"📊 *Live Status*\n\nStatus: {'🟢 Running' if is_running else '🔴 Stopped'}\nThreads: {max_workers}\nTotal Attempts: {total_attempts}\nSuccess: {success_count}\nFailed: {fail_count}\nSuccess Rate: {rate:.1f}%"
                        send_telegram_message(chat_id, status_text)
                    elif text.startswith("/speed"):
                        try:
                            new_speed = int(text.split()[1])
                            max_workers = new_speed
                            send_telegram_message(chat_id, f"⚡ Speed (Workers) updated to: {max_workers}")
                        except:
                            send_telegram_message(chat_id, "❌ Usage: /speed 30")
                    elif text == "/getfile":
                        if os.path.exists("shreewin.txt") and os.path.getsize("shreewin.txt") > 0:
                            try:
                                doc_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                                with open("shreewin.txt", "rb") as doc:
                                    requests.post(doc_url, data={"chat_id": chat_id}, files={"document": doc}, timeout=15)
                            except Exception as e:
                                send_telegram_message(chat_id, f"❌ Error sending file: {e}")
                        else:
                            send_telegram_message(chat_id, "⚠️ shreewin.txt is empty or does not exist.")
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    # Background me telegram listener start karo
    threading.Thread(target=telegram_listener, daemon=True).start()
    print("[*] Bot is running and waiting for commands on Telegram...")
    # Keep alive for Railway deployment
    while True:
        time.sleep(100)
