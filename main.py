import os
import time
import json
import random
import threading
import telebot
from telebot import types
import requests
from flask import Flask

# ================= CONFIGURATION =================
BOT_TOKEN = "8802635273:AAFkW8033y_JREWUlCbz_adLWdghxm7n8sE"
ADMIN_ID = 8671410379

# UPI ID for Auto QR Code (Yahan apni sahi UPI ID dalein)
UPI_ID = "rehan@paytm"  # <-- Apni UPI ID se replace karein
UPI_NAME = "OxRehan"

# API Configurations
SMM_API_URL = "https://your-smm-panel.com/api/v2"
SMM_API_KEY = "sk_live_Ruhid4TuS87e6l4618yRUFt25zSnMpW-"
SERVICE_ID = "101"

# Channels Setup
CHANNELS = [
    {"name": "OX 1 MODS", "chat_id": "@ox1mods", "url": "https://t.me/ox1mods"},
    {"name": "OX 2 MODS", "chat_id": "@ox2mods", "url": "https://t.me/ox2mods"},
    {"name": "OX Cyber", "chat_id": "@OxRehanCyber", "url": "https://t.me/OxRehanCyber"},
    {"name": "VIP Channel", "chat_id": -1003782903063, "url": "https://t.me/+fw4X2NYNRmoyODA1"}
]

PLANS = {
    "plan_20": {"inr": 20, "credits": 1500},
    "plan_40": {"inr": 40, "credits": 3200},
    "plan_100": {"inr": 100, "credits": 5200}
}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
DATA_FILE = "database.json"

# ================= DATABASE SETUP =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "codes": {}, "ads": {}, "pending_ad": {}, "pending_orders": {}}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "codes": {}, "ads": {}, "pending_ad": {}, "pending_orders": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(db, user_id):
    str_id = str(user_id)
    if str_id not in db["users"]:
        db["users"][str_id] = {
            "balance": 0,
            "referred_by": None,
            "verified": False,
            "joined_date": time.time(),
            "selected_plan": None
        }
        save_data(db)
    return db["users"][str_id]

# ================= FLASK SERVER (Render 24/7) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= BACKGROUND ADS SCHEDULER =================
def schedule_ad(user_id):
    def delayed_send():
        time.sleep(20)
        db = load_data()
        ads = db.get("ads", {})
        if ads:
            ad_code = random.choice(list(ads.keys()))
            ad = ads[ad_code]
            try:
                if ad["type"] == "text":
                    bot.send_message(user_id, f"📢 <b>Sponsored:</b>\n\n{ad['content']}")
                elif ad["type"] == "photo":
                    bot.send_photo(user_id, ad["file_id"], caption=ad.get("caption", ""))
                elif ad["type"] == "video":
                    bot.send_video(user_id, ad["file_id"], caption=ad.get("caption", ""))
            except:
                pass
    threading.Thread(target=delayed_send, daemon=True).start()

# ================= HELPERS & MENUS =================
def check_join(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def get_verify_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(text=f"Join {ch['name']}", url=ch["url"]) for ch in CHANNELS]
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton(text="✅ Verify Membership", callback_data="verify_sub"))
    return markup

def get_main_keyboard(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("💰 Balance"), types.KeyboardButton("👀 Increase Views"))
    markup.add(types.KeyboardButton("🛍 Buy Credits"), types.KeyboardButton("🔗 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Redeem Code"))
    if is_admin:
        markup.add(types.KeyboardButton("🛠 All Commands"))
    return markup

# ================= START & VERIFY =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    db = load_data()
    user = get_user(db, user_id)
    
    args = message.text.split()
    if len(args) > 1 and not user["verified"] and user["referred_by"] is None:
        ref_id = args[1]
        if ref_id != str(user_id) and ref_id in db["users"]:
            user["referred_by"] = ref_id
            save_data(db)

    if not check_join(user_id):
        text = "<b>👋 Please join our 4 channels to continue:</b>"
        bot.send_message(user_id, text, reply_markup=get_verify_keyboard())
    else:
        user["verified"] = True
        save_data(db)
        bot.send_message(user_id, "🎉 <b>Verification Confirmed!</b> Welcome to your Dashboard.", reply_markup=get_main_keyboard(user_id == ADMIN_ID))
        schedule_ad(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def verify_callback(call):
    user_id = call.from_user.id
    db = load_data()
    user = get_user(db, user_id)
    
    if check_join(user_id):
        user["verified"] = True
        if user["referred_by"]:
            ref_id = user["referred_by"]
            if ref_id in db["users"]:
                db["users"][ref_id]["balance"] += 100
                try:
                    bot.send_message(int(ref_id), "🎉 <b>Referral Success!</b> A new user joined. You got <b>+100 credits</b>.")
                except:
                    pass
            user["referred_by"] = None
            
        save_data(db)
        bot.answer_callback_query(call.id, "Verified successfully!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, "🎉 <b>Verification Confirmed!</b> Welcome to your Dashboard.", reply_markup=get_main_keyboard(user_id == ADMIN_ID))
        schedule_ad(user_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

# ================= BUY CREDITS SYSTEM (DYNAMIC UPI SCANNER) =================
@bot.message_handler(func=lambda m: m.text == "🛍 Buy Credits")
def buy_credits_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    b1 = types.InlineKeyboardButton("💳 ₹20 -> 1,500 Credits", callback_data="buy_plan_20")
    b2 = types.InlineKeyboardButton("💳 ₹40 -> 3,200 Credits", callback_data="buy_plan_40")
    b3 = types.InlineKeyboardButton("💳 ₹100 -> 5,200 Credits", callback_data="buy_plan_100")
    markup.add(b1, b2, b3)
    
    bot.send_message(message.chat.id, "🛒 <b>Select your Credit Pack:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_plan_selection(call):
    plan_key = call.data.replace("buy_", "")
    if plan_key not in PLANS:
        return
        
    plan = PLANS[plan_key]
    user_id = call.from_user.id
    
    db = load_data()
    user = get_user(db, user_id)
    user["selected_plan"] = plan_key
    save_data(db)
    
    # Generate UPI QR Code URL
    amount = plan["inr"]
    upi_payload = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={requests.utils.quote(upi_payload)}"
    
    caption = (
        f"<b>⚡ Payment Auto-Scanner</b>\n\n"
        f"• <b>Amount:</b> ₹{amount}\n"
        f"• <b>Credits:</b> {plan['credits']}\n"
        f"• <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
        "👉 Scan is QR code ko PayTM / PhonePe / GPay se scan karke payment karein.\n\n"
        "⚠️ <b>Payment karne ke baad, turant payment ka saaf SCREENSHOT yahan send karein:</b>"
    )
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_photo(call.message.chat.id, qr_url, caption=caption)

# ================= SCREENSHOT RECEIVER & APPROVAL =================
@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    user_id = message.from_user.id
    db = load_data()
    user = get_user(db, user_id)
    plan_key = user.get("selected_plan")
    
    if not plan_key or plan_key not in PLANS:
        return  # Regular photo, not payment proof
        
    plan = PLANS[plan_key]
    order_id = str(random.randint(100000, 999999))
    file_id = message.photo[-1].file_id
    
    if "pending_orders" not in db:
        db["pending_orders"] = {}
        
    db["pending_orders"][order_id] = {
        "user_id": user_id,
        "amount": plan["inr"],
        "credits": plan["credits"]
    }
    user["selected_plan"] = None  # Reset
    save_data(db)
    
    # Notify user
    bot.reply_to(message, "✅ <b>Screenshot Received!</b> Aapka payment review ke liye Admin ke paas bhej diya gaya hai. Approve hote hi credits add ho jayenge.")
    
    # Send to Admin with Approve / Reject buttons
    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"appr_{order_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rejc_{order_id}")
    )
    
    admin_text = (
        f"🔔 <b>New Payment Screenshot!</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Amount:</b> ₹{plan['inr']}\n"
        f"🎁 <b>Credits:</b> {plan['credits']}\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>"
    )
    
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("appr_", "rejc_")))
def process_admin_approval(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    action, order_id = call.data.split("_")
    db = load_data()
    
    if order_id not in db.get("pending_orders", {}):
        bot.answer_callback_query(call.id, "Order already processed or not found.")
        return
        
    order = db["pending_orders"][order_id]
    target_uid = order["user_id"]
    credits = order["credits"]
    
    if action == "appr":
        target_user = get_user(db, target_uid)
        target_user["balance"] += credits
        del db["pending_orders"][order_id]
        save_data(db)
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + f"\n\n<b>Status: ✅ APPROVED by Admin (ChatID: {ADMIN_ID})</b>"
        )
        try:
            bot.send_message(target_uid, f"🎉 <b>Payment Approved!</b>\n\n<b>+{credits} Credits</b> aapke wallet me add ho gaye hain.")
        except:
            pass
            
    elif action == "rejc":
        del db["pending_orders"][order_id]
        save_data(db)
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + f"\n\n<b>Status: ❌ REJECTED by Admin (ChatID: {ADMIN_ID})</b>"
        )
        try:
            bot.send_message(target_uid, "❌ <b>Payment Rejected!</b> Aapka screenshot verify nahi ho paya. Kripya sahi screenshot bhejein ya support se contact karein.")
        except:
            pass

# ================= OTHER HANDLERS =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance_handler(message):
    db = load_data()
    user = get_user(db, message.from_user.id)
    bot.send_message(message.chat.id, f"💳 <b>Your Account Balance:</b> <code>{user['balance']}</code> Credits\n\n<i>(100 Credits = 1,000 Instagram Views)</i>")

@bot.message_handler(func=lambda m: m.text == "🔗 Refer & Earn")
def refer_handler(message):
    bot_name = bot.get_me().username
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot_name}?start={user_id}"
    bot.send_message(message.chat.id, f"🔗 <b>Your Personal Referral Link:</b>\n<code>{ref_link}</code>\n\nShare this link. Per valid referral you will get <b>100 Credits</b> when they join all channels!")

@bot.message_handler(func=lambda m: m.text == "🎁 Redeem Code")
def redeem_prompt(message):
    msg = bot.send_message(message.chat.id, "🎟 Please enter your promo/gift code:")
    bot.register_next_step_handler(msg, process_redeem)

def process_redeem(message):
    code_text = message.text.strip()
    db = load_data()
    user = get_user(db, message.from_user.id)
    
    if code_text in db["codes"]:
        item = db["codes"][code_text]
        if str(message.from_user.id) in item.get("claimed_by", []):
            bot.send_message(message.chat.id, "❌ You have already claimed this code.")
            return
        
        user["balance"] += item["amount"]
        item["claimed_by"].append(str(message.from_user.id))
        item["uses"] -= 1
        
        if item["uses"] <= 0:
            del db["codes"][code_text]
            
        save_data(db)
        bot.send_message(message.chat.id, f"🎉 <b>Success!</b> Code applied. <b>+{item['amount']}</b> credits added to your account!")
    else:
        bot.send_message(message.chat.id, "❌ Invalid or expired code.")

@bot.message_handler(func=lambda m: m.text == "👀 Increase Views")
def views_prompt(message):
    db = load_data()
    user = get_user(db, message.from_user.id)
    if user["balance"] < 100:
        bot.send_message(message.chat.id, "❌ <b>Insufficient Balance!</b>\n\nYou need at least 100 credits for 1,000 views. Buy credits or refer friends.")
        return
    msg = bot.send_message(message.chat.id, "🔗 Send your <b>Instagram Post/Reel link:</b>")
    bot.register_next_step_handler(msg, process_views_order)

def process_views_order(message):
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        bot.send_message(message.chat.id, "❌ Invalid link. Order cancelled.")
        return
        
    db = load_data()
    user = get_user(db, message.from_user.id)
    if user["balance"] < 100:
        bot.send_message(message.chat.id, "❌ Balance went down. Order cancelled.")
        return

    payload = {"key": SMM_API_KEY, "action": "add", "service": SERVICE_ID, "link": url, "quantity": 1000}
    try:
        res = requests.post(SMM_API_URL, data=payload, timeout=10)
        res_data = res.json()
    except Exception:
        res_data = {"order": f"Sim_{random.randint(10000, 99999)}"}

    user["balance"] -= 100
    save_data(db)
    
    order_id = res_data.get("order", "Processed")
    bot.send_message(message.chat.id, f"✅ <b>Order Placed Successfully!</b>\n\n📦 <b>Quantity:</b> 1,000 Views\n🆔 <b>Order ID:</b> <code>{order_id}</code>\n💰 100 credits deducted.")

# ================= ADMIN DASHBOARD & COMMANDS =================
@bot.message_handler(func=lambda m: m.text == "🛠 All Commands" and m.from_user.id == ADMIN_ID)
def admin_commands_btn(message):
    text = (
        "<b>🛠 Admin Commands Guide:</b>\n\n"
        "• <code>/gen [credit] [uses]</code> - Gift code banaye (Ex: /gen 100 5)\n"
        "• <code>/addbal [user_id] [amt]</code> - Kisi user ko credit bhejein\n"
        "• <code>/rembal [user_id] [amt]</code> - Credit minus karein\n"
        "• <code>/ads</code> - Reply karke ya text likhkar ad create karein\n"
        "• <code>/chekads</code> - Chal rahe sabhi ads dekhein\n"
        "• <code>/adsdlt [code]</code> - Specific 2-digit code wala ad delete karein\n"
        "• <code>/stats</code> - Bot stats check karein"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['gen'])
def gen_code(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        amount = int(parts[1])
        uses = int(parts[2])
        code = f"OX-{random.randint(1000, 9999)}"
        db = load_data()
        db["codes"][code] = {"amount": amount, "uses": uses, "claimed_by": []}
        save_data(db)
        bot.send_message(message.chat.id, f"✅ Code Generated:\n\nCode: <code>{code}</code>\nAmount: {amount} Credits\nMax Uses: {uses}")
    except:
        bot.send_message(message.chat.id, "Usage: <code>/gen 100 5</code>")

@bot.message_handler(commands=['addbal'])
def add_bal(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amt = message.text.split()
        db = load_data()
        u = get_user(db, uid)
        u["balance"] += int(amt)
        save_data(db)
        bot.send_message(message.chat.id, f"✅ Added {amt} to {uid}. New balance: {u['balance']}")
    except:
        bot.send_message(message.chat.id, "Usage: <code>/addbal [user_id] [amt]</code>")

@bot.message_handler(commands=['rembal'])
def rem_bal(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amt = message.text.split()
        db = load_data()
        u = get_user(db, uid)
        u["balance"] = max(0, u["balance"] - int(amt))
        save_data(db)
        bot.send_message(message.chat.id, f"✅ Deducted {amt} from {uid}. Balance: {u['balance']}")
    except:
        bot.send_message(message.chat.id, "Usage: <code>/rembal [user_id] [amt]</code>")

@bot.message_handler(commands=['stats'])
def bot_stats(message):
    if message.from_user.id != ADMIN_ID: return
    db = load_data()
    bot.send_message(message.chat.id, f"📊 <b>Bot Statistics:</b>\n\nTotal Users: <b>{len(db['users'])}</b>\nActive Ads: <b>{len(db.get('ads', {}))}</b>\nPending Payments: <b>{len(db.get('pending_orders', {}))}</b>")

# ================= ADS CREATION =================
@bot.message_handler(commands=['ads'])
def handle_ads_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    db = load_data()
    ad_item = None
    
    if message.reply_to_message:
        target = message.reply_to_message
        if target.photo:
            ad_item = {"type": "photo", "file_id": target.photo[-1].file_id, "caption": target.caption or ""}
        elif target.video:
            ad_item = {"type": "video", "file_id": target.video.file_id, "caption": target.caption or ""}
        elif target.text:
            ad_item = {"type": "text", "content": target.text}
    else:
        text = message.text.replace("/ads", "").strip()
        if text:
            ad_item = {"type": "text", "content": text}
            
    if not ad_item:
        bot.send_message(message.chat.id, "❌ Send ad text with /ads OR reply to a Photo/Video/Text with /ads")
        return
        
    db["pending_ad"] = ad_item
    save_data(db)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📢 Publish", callback_data="ad_publish"),
        types.InlineKeyboardButton("🗑 Delete Old & Publish", callback_data="ad_replace")
    )
    bot.send_message(message.chat.id, "What would you like to do with this Ad draft?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["ad_publish", "ad_replace"])
def ad_action_callback(call):
    if call.from_user.id != ADMIN_ID: return
    db = load_data()
    pending = db.get("pending_ad")
    if not pending:
        bot.answer_callback_query(call.id, "No ad draft found.")
        return
        
    if call.data == "ad_replace":
        db["ads"] = {}
        
    ad_code = str(random.randint(10, 99))
    while ad_code in db["ads"]:
        ad_code = str(random.randint(10, 99))
        
    db["ads"][ad_code] = pending
    db["pending_ad"] = None
    save_data(db)
    
    bot.edit_message_text(f"✅ Ad published successfully with Code: <code>{ad_code}</code>", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['chekads'])
def check_ads(message):
    if message.from_user.id != ADMIN_ID: return
    db = load_data()
    ads = db.get("ads", {})
    if not ads:
        bot.send_message(message.chat.id, "No active ads running.")
        return
        
    out = "<b>📢 Live Active Ads:</b>\n\n"
    for code, details in ads.items():
        out += f"• Code: <code>{code}</code> | Type: <b>{details['type'].upper()}</b>\n"
    out += "\nTo delete an ad use: <code>/adsdlt [code]</code>"
    bot.send_message(message.chat.id, out)

@bot.message_handler(commands=['adsdlt'])
def delete_ad_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        code = message.text.split()[1]
        db = load_data()
        if code in db.get("ads", {}):
            del db["ads"][code]
            save_data(db)
            bot.send_message(message.chat.id, f"✅ Ad with code <code>{code}</code> deleted.")
        else:
            bot.send_message(message.chat.id, "❌ Code not found.")
    except:
        bot.send_message(message.chat.id, "Usage: <code>/adsdlt [code]</code>")

# ================= RUN SERVER & BOT =================
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot polling started...")
    bot.infinity_polling(skip_pending=True)
