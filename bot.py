import os
import random
import statistics
import asyncio
from datetime import datetime
from collections import deque
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]

# ─── STORAGE ─────────────────────────────

db_data = deque(maxlen=200)

performance = {"wins": 0, "losses": 0, "total": 0}
last_signal = None

user_bankroll = {}

# ─── DATA GENERATOR ──────────────────────

def fake():
    if random.random() < 0.04:
        return 1.0
    return round(1 + random.random()*5, 2)

for _ in range(50):
    db_data.append(fake())

# ─── ENGINE ─────────────────────────────

def analyze():
    global last_signal

    data = list(db_data)
    last20 = data[-20:]
    last5 = data[-5:]

    avg = statistics.mean(last20)
    vol = statistics.stdev(last20) if len(last20) > 2 else 0

    # streak
    streak = 0
    for v in reversed(data):
        if v < 2:
            streak += 1
        else:
            break

    # market
    if avg < 1.6:
        mode = "💤 DEAD"
    elif avg < 2.2:
        mode = "⚖️ NORMAL"
    else:
        mode = "🔥 HOT"

    # confidence
    confidence = 50
    if streak >= 4:
        confidence += 15
    if vol < 1.2:
        confidence += 10
    if last5.count(1.0) >= 2:
        confidence -= 20

    confidence = max(10, min(95, confidence))

    # signal
    if confidence >= 75:
        signal = "🚀 SNIPER"
        cashout = round(random.uniform(2.2, 3.5), 2)
    elif confidence >= 55:
        signal = "🎯 SAFE"
        cashout = round(random.uniform(1.5, 2.2), 2)
    else:
        signal = "❌ SKIP"
        cashout = 1.0

    last_signal = {"cashout": cashout, "signal": signal}

    return {
        "mode": mode,
        "confidence": confidence,
        "cashout": cashout,
        "signal": signal,
        "streak": streak
    }

# ─── PERFORMANCE TRACKING ───────────────

def update_performance(result):
    global performance, last_signal

    if not last_signal or last_signal["signal"] == "❌ SKIP":
        return

    performance["total"] += 1

    if result >= last_signal["cashout"]:
        performance["wins"] += 1
    else:
        performance["losses"] += 1

# ─── COMMANDS ───────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_bankroll[update.effective_user.id] = 1000
    await update.message.reply_text(
        "✈️ AVIATOR ULTIMATE BOT\n\n"
        "/signal\n/autosignal 15\n/addcrash 2.5\n/stats"
    )

async def signal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = analyze()

    acc = (performance["wins"] / performance["total"] * 100) if performance["total"] else 0

    msg = (
        f"{data['mode']}\n{data['signal']}\n\n"
        f"🎯 {data['cashout']}x\n"
        f"📊 Confidence: {data['confidence']}%\n"
        f"📉 Streak: {data['streak']}\n\n"
        f"📈 Accuracy: {acc:.1f}%"
    )

    await update.message.reply_text(msg)

async def add_crash(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(ctx.args[0])
        db_data.append(val)
        update_performance(val)
        await update.message.reply_text(f"Added {val}x")
    except:
        await update.message.reply_text("Use: /addcrash 2.5")

async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if performance["total"] == 0:
        await update.message.reply_text("No data yet")
        return

    acc = (performance["wins"] / performance["total"]) * 100

    await update.message.reply_text(
        f"📊 Accuracy: {acc:.1f}%\n"
        f"Wins: {performance['wins']}\n"
        f"Losses: {performance['losses']}"
    )

active = {}

async def autosignal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    active[uid] = True

    await update.message.reply_text("Auto ON")

    while active.get(uid, False):
        await asyncio.sleep(15)
        db_data.append(fake())
        data = analyze()

        await ctx.bot.send_message(
            chat_id=uid,
            text=f"{data['signal']} | {data['cashout']}x | {data['confidence']}%"
        )

async def stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    active[update.effective_user.id] = False
    await update.message.reply_text("Stopped")

# ─── MAIN ───────────────────────────────

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("addcrash", add_crash))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("autosignal", autosignal))
    app.add_handler(CommandHandler("stop", stop))

    app.run_polling()

if __name__ == "__main__":
    main()
