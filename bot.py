import logging
import time
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === CONFIGURATION ===
BOT_TOKEN = "7928470785:AAHMz54GOWoI-NsbD2zyj0Av_VbnqX7fYzI8179218740"
OWNER_ID = 8179218740  # Apka Telegram user id

# Brainthree API credentials
MERCHANT_ID = "q3hwsdcgv5vdxphb"
PUBLIC_KEY = "8c64vknj8d38nznb"
PRIVATE_KEY = "271bf4fb8d331458a307eb3c276b9a26"

# Access control dictionary {user_id: expiry_timestamp}
access_users = {}

def is_owner(user_id):
    return user_id == OWNER_ID

def is_allowed(user_id):
    now = time.time()
    expired = [uid for uid, exp in access_users.items() if exp < now]
    for uid in expired:
        del access_users[uid]
    return is_owner(user_id) or user_id in access_users

def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_allowed(user_id):
            await update.message.reply_text("❌ You don't have access. Contact owner.")
            return
        return await func(update, context)
    return wrapper

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 Welcome to Brainthree CC Checker Bot 🔥\n\n"
        "Commands:\n"
        "/add <user_id> <days> - Add user access (Owner only)\n"
        "/remove <user_id> - Remove user access (Owner only)\n"
        "/chk <cc|mm|yy|cvv> - Check a single card\n"
        "/mass <10 cards> - Check 10 cards at once (cards separated by space or newline)\n\n"
        "Format: cc|mm|yy|cvv\n"
        "Contact owner for access if you don't have it."
    )
    await update.message.reply_text(text)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only owner can use this command.")
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /add <user_id> <days>")
        return
    try:
        uid = int(args[0])
        days = int(args[1])
        expire_time = time.time() + days * 86400
        access_users[uid] = expire_time
        expire_date = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(f"✅ User {uid} added for {days} days. Expires on {expire_date}.")
    except:
        await update.message.reply_text("❌ Invalid user_id or days.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only owner can use this command.")
        return
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /remove <user_id>")
        return
    try:
        uid = int(args[0])
        if uid in access_users:
            del access_users[uid]
            await update.message.reply_text(f"✅ User {uid} removed from access list.")
        else:
            await update.message.reply_text("❌ User not found in access list.")
    except:
        await update.message.reply_text("❌ Invalid user_id.")

def brainthree_check_card(cc, mm, yy, cvv):
    url = "https://api.brainthree.com/v1/card-check"
    headers = {
        "Merchant-ID": MERCHANT_ID,
        "Public-Key": PUBLIC_KEY,
        "Private-Key": PRIVATE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "card_number": cc,
        "exp_month": mm,
        "exp_year": yy,
        "cvv": cvv
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        data = res.json()
        if data.get("status") == "approved":
            return "Approved ✅", data.get("message", "Success"), data.get("card_type", None)
        else:
            return "Declined ❌", data.get("message", "Declined"), None
    except Exception as e:
        return "Declined ❌", str(e), None

@restricted
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /chk <cc|mm|yy|cvv>")
        return

    progress_msg = await update.message.reply_text("Checking... Please wait.")

    card = context.args[0]
    try:
        cc, mm, yy, cvv = card.split("|")
    except:
        await progress_msg.edit_text("❌ Invalid card format. Use cc|mm|yy|cvv")
        return

    start = time.time()
    status, resp, card_type = brainthree_check_card(cc, mm, yy, cvv)
    end = time.time()
    bin_info = get_bin_info(cc[:6])

    msg = (
        f"CC: {card}\n"
        f"Status: {status}\n"
        f"Response: {resp}\n"
        f"Gateway: Brainthree\n"
        f"Info: {bin_info}\n"
        f"Time: {round(end-start, 2)}s\n"
        f"Checked by: @{update.effective_user.username or update.effective_user.id}"
    )
    await progress_msg.edit_text(msg)

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

    results = ["↯ Brainthree Auth\n"]
    start = time.time()
    for card in cards:
        try:
            cc, mm, yy, cvv = card.strip().split("|")
            status, resp, card_type = brainthree_check_card(cc, mm, yy, cvv)
            results.append(
                f"Card↯ {card}\nStatus - {status}\nResult - ⤿ {resp} ⤾\n"
            )
        except:
            results.append(f"❌ Invalid format: {card}\n")
    end = time.time()

    results.append(f"\nChecked by: @{update.effective_user.username or update.effective_user.id}\nTime taken: {round(end - start, 2)} seconds")

    await progress_msg.edit_text("\n".join(results))


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("mass", mass))

    print("Bot started...")
    app.run_polling()
