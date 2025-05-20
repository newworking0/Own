import logging
import time
import random
from datetime import datetime
import braintree
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
OWNER_ID = 8179218740  # Apna Telegram user id daalo yahan

# BrainTree Gateway setup - apni keys yahan daalo
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=braintree.Environment.Sandbox,  # ya braintree.Environment.Production
        merchant_id="q3hwsdcgv5vdxphb",
        public_key="8c64vknj8d38nznb",
        private_key="271bf4fb8d331458a307eb3c276b9a26"
    )
)

# Access control dictionary {user_id: expiry_timestamp}
access_users = {}

# --------- ACCESS CONTROL --------
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

# --------- BrainTree CARD CHECK FUNCTION --------
def braintree_check_card(cc, mm, yy, cvv):
    try:
        # Create payment method nonce by tokenizing card
        result = gateway.payment_method.create({
            "customer_id": "fake_customer_id_for_testing",  # optional, use if needed
            "payment_method_nonce": "fake-valid-nonce"  # We'll create nonce below
        })

        # Instead, we do a simple transaction sale with card info directly (sandbox allows)
        result = gateway.transaction.sale({
            "amount": "1.00",
            "credit_card": {
                "number": cc,
                "expiration_month": mm,
                "expiration_year": yy,
                "cvv": cvv,
            },
            "options": {
                "submit_for_settlement": False
            }
        })

        if result.is_success:
            return "Approved ✅", "Transaction authorized"
        else:
            message = "; ".join([e.message for e in result.errors.deep_errors]) if result.errors.deep_errors else result.message
            return "Declined ❌", message
    except Exception as e:
        return "Declined ❌", str(e)

# --------- /chk COMMAND --------
@restricted
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /chk <cc|mm|yy|cvv>")
        return
    card = context.args[0]
    try:
        cc, mm, yy, cvv = card.split("|")
    except:
        await update.message.reply_text("❌ Invalid card format. Use cc|mm|yy|cvv")
        return

    start = time.time()
    status, resp = braintree_check_card(cc, mm, yy, cvv)
    end = time.time()
    bin_info = get_bin_info(cc[:6])

    msg = (
        f"CC: {card}\n"
        f"Status: {status}\n"
        f"Response: {resp}\n"
        f"Gateway: BrainTree\n"
        f"Info: {bin_info}\n"
        f"Time: {round(end-start, 2)}s\n"
        f"Checked by: @{update.effective_user.username or update.effective_user.id}"
    )
    await update.message.reply_text(msg)

# --------- /mass COMMAND --------
@restricted
async def mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /mass <10 cards> (each card in cc|mm|yy|cvv format separated by space or new line)")
        return
    raw_input = " ".join(context.args)
    cards = raw_input.strip().splitlines() if "\n" in raw_input else raw_input.strip().split()
    if len(cards) != 10:
        await update.message.reply_text("❌ Please provide exactly 10 cards.")
        return

    await update.message.reply_text("Checking 10 cards, please wait...")

    results = ["↯ BrainTree Auth\n"]
    start = time.time()
    for card in cards:
        try:
            cc, mm, yy, cvv = card.strip().split("|")
            status, resp = braintree_check_card(cc, mm, yy, cvv)
            results.append(
                f"Card↯ {card}\nStatus - {status}\nResult - {resp}\n"
            )
        except:
            results.append(f"❌ Invalid format: {card}\n")
    end = time.time()

    results.append(f"\nChecked by: @{update.effective_user.username or update.effective_user.id}\nTime taken: {round(end - start, 2)} seconds")

    await update.message.reply_text("\n".join(results))

# ===== Main =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("mass", mass))

    print("Bot started...")
    app.run_polling()
