import logging
import time
import random
from datetime import datetime
import stripe
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === SETUP ===
BOT_TOKEN = "7928470785:AAHMz54GOWoI-NsbD2zyj0Av_VbnqX7fYzI"
OWNER_ID = 8179218740  # Apna telegram user id daalo yahan

# Stripe secret key - apni key yahan daalo
stripe.api_key = "sk_test_51RQinfIOi20W3Z306gPLrw998n2Isxh3OgRqCl59MlNDZU9jQ3l4gKmHj7fOWoNSZjnLktvj650ISUYIf4C1Qfcb000uvGoYwE"

# Access control dictionary {user_id: expiry_timestamp}
access_users = {}

# --------- ACCESS CONTROL --------
def is_owner(user_id):
    return user_id == OWNER_ID

def is_allowed(user_id):
    now = time.time()
    # Clean expired users
    expired = [uid for uid, exp in access_users.items() if exp < now]
    for uid in expired:
        del access_users[uid]
    if is_owner(user_id):
        return True
    return user_id in access_users

# Decorator to restrict commands
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_allowed(user_id):
            await update.message.reply_text("❌ You don't have access to use this command. Contact owner.")
            return
        return await func(update, context)
    return wrapper

# --------- BIN INFO FUNCTION --------
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

# --------- /start COMMAND --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 Welcome to the CC Checker Bot 🔥\n\n"
        "Available commands:\n"
        "/add <user_id> <days> - Add user access (Owner only)\n"
        "/remove <user_id> - Remove user access (Owner only)\n"
        "/gen <bin> <amount> - Generate cards\n"
        "/chk <cc|mm|yy|cvv> - Check a single card\n"
        "/mass <10 cards> - Check 10 cards at once (each card separated by space or newline)\n\n"
        "Format for cards: cc|mm|yy|cvv\n\n"
        "Contact owner for access if you don't have it."
    )
    await update.message.reply_text(text)

# --------- /add COMMAND --------
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
        await update.message.reply_text(f"✅ User {uid} added for {days} days. Access expires on {expire_date}.")
    except:
        await update.message.reply_text("❌ Invalid user_id or days.")

# --------- /remove COMMAND --------
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

# --------- /gen COMMAND --------
@restricted
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /gen <bin> <amount>")
        return
    bin_num = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Invalid amount number.")
        return
    cards = []
    for _ in range(amount):
        cc = bin_num + "".join(str(random.randint(0,9)) for _ in range(16 - len(bin_num)))
        mm = f"{random.randint(1,12):02d}"
        yy = str(random.randint(23,30))
        cvv = f"{random.randint(100,999)}"
        cards.append(f"{cc}|{mm}|20{yy}|{cvv}")
    await update.message.reply_text(f"𝐂𝐂 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲\n\n𝐁𝐢𝐧 - {bin_num}\n𝐀𝐦𝐨𝐮𝐧𝐭 - {amount}\n\n" + "\n".join(cards) + f"\n\n𝗜𝗻𝗳𝗼 - {get_bin_info(bin_num)}\n\n𝐓𝐢𝐦𝐞: {round(random.uniform(1,3), 2)} seconds\n\n𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲: @{update.effective_user.username or update.effective_user.id}")

# --------- STRIPE CARD CHECK FUNCTION --------
def stripe_check_card(cc, mm, yy, cvv):
    try:
        token = stripe.Token.create(
            card={
                "number": cc,
                "exp_month": int(mm),
                "exp_year": int(yy),
                "cvc": cvv,
            }
        )
        charge = stripe.Charge.create(
            amount=100,  # 1 USD
            currency="usd",
            source=token.id,
            description="Test Charge"
        )
        return "Approved ✅", "Approved", charge.payment_method_details.type
    except stripe.error.CardError as e:
        body = e.json_body
        err = body.get("error", {})
        msg = err.get("message", "Declined")
        return "Declined ❌", msg, None
    except Exception as e:
        return "Declined ❌", str(e), None

# --------- /chk COMMAND --------
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
    status, resp, card_type = stripe_check_card(cc, mm, yy, cvv)
    end = time.time()
    bin_info = get_bin_info(cc[:6])

    msg = (
        f"CC: {card}\n"
        f"Status: {status}\n"
        f"Response: {resp}\n"
        f"Gateway: Stripe\n"
        f"Info: {bin_info}\n"
        f"Time: {round(end-start, 2)}s\n"
        f"Checked by: @{update.effective_user.username or update.effective_user.id}"
    )
    await progress_msg.edit_text(msg)

# --------- /mass COMMAND --------
@restricted
async def mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /mass <10 cards> (each card in cc|mm|yy|cvv format separated by space or new line)")
        return
    
    progress_msg = await update.message.reply_text("Checking 10 cards, please wait...")
    
    raw_input = " ".join(context.args)
    cards = raw_input.strip().splitlines() if "\n" in raw_input else raw_input.strip().split()
    if len(cards) != 10:
        await progress_msg.edit_text("❌ Please provide exactly 10 cards.")
        return

    results = ["↯ Stripe Auth\n"]
    start = time.time()
    for card in cards:
        try:
            cc, mm, yy, cvv = card.strip().split("|")
            status, resp, card_type = stripe_check_card(cc, mm, yy, cvv)
            results.append(
                f"Card↯ {card}\nStatus - {status}\nResult - ⤿ {resp} ⤾\n"
            )
        except:
            results.append(f"❌ Invalid format: {card}\n")
    end = time.time()

    results.append(f"\nChecked by: @{update.effective_user.username or update.effective_user.id}\nTime taken: {round(end - start, 2)} seconds")

    await progress_msg.edit_text("\n".join(results))

# ===== Main =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("gen", gen))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("mass", mass))

    print("Bot started...")
    app.run_polling()
