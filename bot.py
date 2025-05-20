import logging
import time
import random
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === CONFIG ===
BOT_TOKEN = "7928470785:AAHMz54GOWoI-NsbD2zyj0Av_VbnqX7fYzI"
OWNER_ID = 8179218740  # Tumhara owner telegram id

# BrainThree API credentials (jo tumne diye the)
MERCHANT_ID = "q3hwsdcgv5vdxphb"
PUBLIC_KEY = "8c64vknj8d38nznb"
PRIVATE_KEY = "271bf4fb8d331458a307eb3c276b9a26"

# Access control dict {user_id: expiry_timestamp}
access_users = {}

# Access control helpers
def is_owner(user_id):
    return user_id == OWNER_ID

def is_allowed(user_id):
    now = time.time()
    expired = [uid for uid, exp in access_users.items() if exp < now]
    for uid in expired:
        del access_users[uid]
    if is_owner(user_id):
        return True
    return user_id in access_users

# Restriction decorator
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_allowed(user_id):
            await update.message.reply_text("❌ You don't have access. Contact owner.")
            return
        return await func(update, context)
    return wrapper

# BIN info fetch
def get_bin_info(bin_num):
    try:
        r = requests.get(f"https://lookup.binlist.net/{bin_num}")
        if r.status_code == 200:
            data = r.json()
            brand = data.get("brand", "Unknown")
            card_type = data.get("type", "Unknown").capitalize()
            prepaid = "Prepaid" if data.get("prepaid") else "Not Prepaid"
            bank = data.get("bank", {}).get("name", "Unknown Bank")
            country = data.get("country", {}).get("name", "Unknown Country")
            emoji = data.get("country", {}).get("emoji", "")
            return f"{brand} - {card_type} - {prepaid}\nBank - {bank}\nCountry - {country} {emoji}"
        else:
            return "BIN info not found."
    except:
        return "Error fetching BIN info."

# BrainThree API card check
def brainthree_check_card(cc, mm, yy, cvv):
    url = "https://api.brainthree.com/card/check"
    headers = {
        "merchant": MERCHANT_ID,
        "public": PUBLIC_KEY,
        "private": PRIVATE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "cc": cc,
        "mm": mm,
        "yy": yy,
        "cvv": cvv
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        data = res.json()
        status = data.get("status", "error").capitalize()
        message = data.get("message", "No message")
        return status, message
    except Exception as e:
        return "Error", str(e)

# -------- COMMANDS --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Welcome to CC Checker Bot 🔥\n\n"
        "Commands:\n"
        "/add <user_id> <days> - Add access (Owner only)\n"
        "/remove <user_id> - Remove access (Owner only)\n"
        "/gen <bin> <amount> - Generate cards\n"
        "/chk <cc|mm|yy|cvv> - Check single card\n"
        "/mass <10 cards> - Check 10 cards\n\n"
        "Format cards as cc|mm|yy|cvv\n"
        "Contact owner if no access."
    )

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only owner can add users.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add <user_id> <days>")
        return
    try:
        uid = int(context.args[0])
        days = int(context.args[1])
        expire = time.time() + days * 86400
        access_users[uid] = expire
        expire_date = datetime.fromtimestamp(expire).strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(f"✅ Added user {uid} for {days} days (expires {expire_date}).")
    except:
        await update.message.reply_text("❌ Invalid user_id or days.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only owner can remove users.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove <user_id>")
        return
    try:
        uid = int(context.args[0])
        if uid in access_users:
            del access_users[uid]
            await update.message.reply_text(f"✅ Removed user {uid}.")
        else:
            await update.message.reply_text("❌ User not found.")
    except:
        await update.message.reply_text("❌ Invalid user_id.")

@restricted
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /gen <bin> <amount>")
        return
    bin_num = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Invalid amount.")
        return

    cards = []
    for _ in range(amount):
        cc = bin_num + "".join(str(random.randint(0,9)) for _ in range(16 - len(bin_num)))
        mm = f"{random.randint(1,12):02d}"
        yy = str(random.randint(23,30))
        cvv = f"{random.randint(100,999)}"
        cards.append(f"{cc}|{mm}|20{yy}|{cvv}")

    await update.message.reply_text(
        f"𝐂𝐂 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲\n\n"
        f"𝐁𝐢𝐧 - {bin_num}\n𝐀𝐦𝐨𝐮𝐧𝐭 - {amount}\n\n" +
        "\n".join(cards) +
        f"\n\n𝗜𝗻𝗳𝗼 - {get_bin_info(bin_num)}\n\n"
        f"𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲: @{update.effective_user.username or update.effective_user.id}"
    )

@restricted
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /chk <cc|mm|yy|cvv>")
        return

    progress_msg = await update.message.reply_text("Checking card, please wait...")

    card = context.args[0]
    try:
        cc, mm, yy, cvv = card.split("|")
    except:
        await progress_msg.edit_text("❌ Invalid card format. Use cc|mm|yy|cvv")
        return

    status, msg = brainthree_check_card(cc, mm, yy, cvv)

    bin_info = get_bin_info(cc[:6])
    response = (
        f"Card: {card}\n"
        f"Status: {status}\n"
        f"Message: {msg}\n"
        f"Info: {bin_info}\n"
        f"Checked by: @{update.effective_user.username or update.effective_user.id}"
    )

    await progress_msg.edit_text(response)

@restricted
async def mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /mass <10 cards> (each card in cc|mm|yy|cvv format separated by space or newline)")
        return

    progress_msg = await update.message.reply_text("Checking 10 cards, please wait...")

    raw_input = " ".join(context.args)
    cards = raw_input.strip().splitlines() if "\n" in raw_input else raw_input.strip().split()
    if len(cards) != 10:
        await progress_msg.edit_text("❌ Please provide exactly 10 cards.")
        return

    results = ["↯ BrainThree Card Check ↯\n"]
    for card in cards:
        try:
            cc, mm, yy, cvv = card.strip().split("|")
            status, msg = brainthree_check_card(cc, mm, yy, cvv)
            results.append(f"Card: {card}\nStatus: {status}\nMessage: {msg}\n")
        except:
            results.append(f"❌ Invalid format: {card}\n")

    results.append(f"Checked by: @{update.effective_user.username or update.effective_user.id}")

    await progress_msg.edit_text("\n".join(results))


# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("gen", gen))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("mass", mass))

    print("Bot started...")
    app.run_polling()
