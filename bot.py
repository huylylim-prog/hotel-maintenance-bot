import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG (set these as environment variables on Railway) ───────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")           # Your Telegram bot token
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")  # Your Telegram ID
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")    # Google Sheet ID from URL
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")  # Service account JSON as string

# ─── GOOGLE SHEETS SETUP ─────────────────────────────────────────────────────
def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    return sheet.worksheet("🔴 Signalements")

def add_row(data: dict):
    ws = get_sheet()
    now = datetime.now()
    row = [
        now.strftime("%d/%m/%y"),   # Date
        now.strftime("%H:%M"),      # Time
        data.get("staff", ""),      # Staff
        data.get("zone", ""),       # Zone
        data.get("room", "—"),      # Room
        data.get("category", ""),   # Category
        data.get("priority", ""),   # Priority
        data.get("note", ""),       # Description
        "",                         # Photo
        "⏳ Pending",               # Status
        "",                         # Fixed by
        "",                         # Date resolved
    ]
    ws.append_row(row)

# ─── ROOMS DATA ───────────────────────────────────────────────────────────────
ROOMS = {
    "1st Floor": ["R1", "R2", "R3", "R4"],
    "2nd Floor": ["S1", "S2", "S3", "201", "203", "205", "207", "209"],
    "3rd Floor": ["D1","D2","D3","D4","D5","D6","D7","D8","D9","D10","D11","D12","D13","D14","D16"],
    "4th Floor": ["401","402","403","404","405","406","407","408","409","410","411","412","413","414"],
}

ROOM_CATEGORIES = {
    "💡 Lighting / ភ្លើង": "Lighting",
    "❄️ A/C": "A/C",
    "🚿 Plumbing / ទឹក": "Plumbing",
    "📺 TV / WiFi": "TV/WiFi",
    "🚪 Door / Lock": "Door/Lock",
    "🔥 Hot water / ទឹកក្ដៅ": "Hot water",
    "🛏️ Linen / Minibar": "Linen/Minibar",
    "🪟 Tile / Wall": "Tile/Wall",
    "➕ Other / ផ្សេង": "Other",
}

ZONE_CATEGORIES = {
    "💡 Lighting / ភ្លើង": "Lighting",
    "🚿 Plumbing / ទឹក": "Plumbing",
    "❄️ A/C / Equipment": "Equipment",
    "🧹 Hygiene / សំណង": "Hygiene",
    "🔒 Security / សុវត្ថិភាព": "Security",
    "➕ Other / ផ្សេង": "Other",
}

PRIORITIES = {
    "🔴 Urgent": "🔴 Urgent",
    "🟡 Normal": "🟡 Normal",
    "🟢 Low / ទំនេរ": "🟢 Low",
}

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def zone_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Chambre", callback_data="zone_chambre"),
         InlineKeyboardButton("🏊 Pool / អាង", callback_data="zone_pool")],
        [InlineKeyboardButton("🍽️ Resto / Bar", callback_data="zone_resto"),
         InlineKeyboardButton("🏋️ Gym", callback_data="zone_gym")],
        [InlineKeyboardButton("🧖 Sauna / Steam", callback_data="zone_spa"),
         InlineKeyboardButton("👕 Vestiaires", callback_data="zone_locker")],
        [InlineKeyboardButton("🏨 Lobby / Corridor", callback_data="zone_lobby"),
         InlineKeyboardButton("🌿 Garden / Outdoor", callback_data="zone_garden")],
        [InlineKeyboardButton("🅿️ Parking", callback_data="zone_parking"),
         InlineKeyboardButton("⚙️ Technique", callback_data="zone_technique")],
    ])

def floor_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1st Floor (R1–R4)", callback_data="floor_1st Floor")],
        [InlineKeyboardButton("2nd Floor (Suites + 201–209)", callback_data="floor_2nd Floor")],
        [InlineKeyboardButton("3rd Floor (Deluxe D1–D16)", callback_data="floor_3rd Floor")],
        [InlineKeyboardButton("4th Floor (401–414)", callback_data="floor_4th Floor")],
    ])

def room_keyboard(floor):
    rooms = ROOMS.get(floor, [])
    rows = []
    row = []
    for i, r in enumerate(rooms):
        row.append(InlineKeyboardButton(r, callback_data=f"room_{r}"))
        if len(row) == 4 or i == len(rooms) - 1:
            rows.append(row)
            row = []
    return InlineKeyboardMarkup(rows)

def category_keyboard(is_room=True):
    cats = ROOM_CATEGORIES if is_room else ZONE_CATEGORIES
    rows = []
    row = []
    for i, (label, _) in enumerate(cats.items()):
        row.append(InlineKeyboardButton(label, callback_data=f"cat_{label}"))
        if len(row) == 2 or i == len(cats) - 1:
            rows.append(row)
            row = []
    return InlineKeyboardMarkup(rows)

def priority_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p, callback_data=f"prio_{p}")] for p in PRIORITIES.keys()
    ])

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm / បញ្ជាក់", callback_data="confirm"),
         InlineKeyboardButton("✏️ Add note", callback_data="add_note")],
    ])

# ─── USER STATE ───────────────────────────────────────────────────────────────
user_state = {}  # chat_id -> {zone, floor, room, category, priority, note, step}

# ─── HANDLERS ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_chat.id] = {}
    await update.message.reply_text(
        "🏨 *Hotel Ratanakiri — Maintenance*\n"
        "ការថែទាំ / Report an issue\n\n"
        "Select zone / ជ្រើសរើសតំបន់:",
        parse_mode="Markdown",
        reply_markup=zone_keyboard()
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_chat.id] = {}
    await update.message.reply_text(
        "🚨 *Report an issue / រាយការណ៍បញ្ហា*\n\n"
        "Select zone / ជ្រើសរើសតំបន់:",
        parse_mode="Markdown",
        reply_markup=zone_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if chat_id not in user_state:
        user_state[chat_id] = {}

    state = user_state[chat_id]
    staff_name = query.from_user.first_name or "Unknown"

    # ZONE selected
    if data.startswith("zone_"):
        zone_map = {
            "zone_chambre": "Chambre", "zone_pool": "Pool",
            "zone_resto": "Restaurant/Bar", "zone_gym": "Gym",
            "zone_spa": "Sauna/Steam", "zone_locker": "Vestiaires",
            "zone_lobby": "Lobby/Corridor", "zone_garden": "Garden/Outdoor",
            "zone_parking": "Parking", "zone_technique": "Technique",
        }
        zone = zone_map.get(data, data)
        state["zone"] = zone
        state["staff"] = staff_name

        if data == "zone_chambre":
            await query.edit_message_text(
                f"🏠 *Chambre* — Select floor / ជ្រើសជាន់:",
                parse_mode="Markdown",
                reply_markup=floor_keyboard()
            )
        else:
            state["room"] = "—"
            await query.edit_message_text(
                f"*{zone}* — Type of issue / ប្រភេទបញ្ហា:",
                parse_mode="Markdown",
                reply_markup=category_keyboard(is_room=False)
            )

    # FLOOR selected
    elif data.startswith("floor_"):
        floor = data.replace("floor_", "")
        state["floor"] = floor
        await query.edit_message_text(
            f"🏠 *{floor}* — Select room / ជ្រើសបន្ទប់:",
            parse_mode="Markdown",
            reply_markup=room_keyboard(floor)
        )

    # ROOM selected
    elif data.startswith("room_"):
        room = data.replace("room_", "")
        state["room"] = room
        await query.edit_message_text(
            f"🏠 Room *{room}* — Type of issue / ប្រភេទបញ្ហា:",
            parse_mode="Markdown",
            reply_markup=category_keyboard(is_room=True)
        )

    # CATEGORY selected
    elif data.startswith("cat_"):
        cat_label = data.replace("cat_", "")
        cats = ROOM_CATEGORIES if state.get("zone") == "Chambre" else ZONE_CATEGORIES
        state["category"] = cats.get(cat_label, cat_label)
        await query.edit_message_text(
            f"Priority / អាទិភាព:",
            parse_mode="Markdown",
            reply_markup=priority_keyboard()
        )

    # PRIORITY selected
    elif data.startswith("prio_"):
        prio_label = data.replace("prio_", "")
        state["priority"] = PRIORITIES.get(prio_label, prio_label)

        summary = (
            f"📋 *Summary / សង្ខេប*\n\n"
            f"📍 Zone: *{state.get('zone', '—')}*\n"
            f"🚪 Room: *{state.get('room', '—')}*\n"
            f"🔧 Issue: *{state.get('category', '—')}*\n"
            f"⚡ Priority: *{state.get('priority', '—')}*\n"
        )
        await query.edit_message_text(
            summary,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard()
        )

    # ADD NOTE
    elif data == "add_note":
        state["step"] = "waiting_note"
        await query.edit_message_text(
            "✏️ Type your note / សរសេរចំណាំ:\n_(or type 'skip' to confirm without note)_",
            parse_mode="Markdown"
        )

    # CONFIRM
    elif data == "confirm":
        await submit_issue(query, state, chat_id, staff_name)

async def submit_issue(query_or_msg, state, chat_id, staff_name):
    try:
        add_row(state)
        is_urgent = "Urgent" in state.get("priority", "")

        confirm_text = (
            f"✅ *Issue recorded! / បញ្ហាបានទទួល!*\n\n"
            f"📍 {state.get('zone')} — {state.get('room', '')}\n"
            f"🔧 {state.get('category')}\n"
            f"⚡ {state.get('priority')}\n"
            f"{'📝 ' + state.get('note') if state.get('note') else ''}\n\n"
            f"_Recorded in Google Sheets ✓_"
        )

        if hasattr(query_or_msg, 'edit_message_text'):
            await query_or_msg.edit_message_text(confirm_text, parse_mode="Markdown")
        else:
            await query_or_msg.reply_text(confirm_text, parse_mode="Markdown")

        # Alert manager if urgent
        if is_urgent and MANAGER_CHAT_ID:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=MANAGER_CHAT_ID,
                text=(
                    f"🔴 *URGENT ISSUE — {state.get('zone')} {state.get('room', '')}*\n\n"
                    f"🔧 {state.get('category')}\n"
                    f"👤 Reported by: {state.get('staff')}\n"
                    f"🕐 {datetime.now().strftime('%d/%m/%y %H:%M')}\n"
                    f"{'📝 ' + state.get('note') if state.get('note') else ''}"
                ),
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error submitting issue: {e}")
        error_text = "❌ Error saving. Please try again. / មានបញ្ហា សូមព្យាយាម​ម្ដងទៀត។"
        if hasattr(query_or_msg, 'edit_message_text'):
            await query_or_msg.edit_message_text(error_text)
        else:
            await query_or_msg.reply_text(error_text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = user_state.get(chat_id, {})
    text = update.message.text
    staff_name = update.effective_user.first_name or "Unknown"

    if state.get("step") == "waiting_note":
        if text.lower() != "skip":
            state["note"] = text
        state["step"] = None
        await submit_issue(update.message, state, chat_id, staff_name)
    else:
        # Default — show report menu
        user_state[chat_id] = {}
        await update.message.reply_text(
            "🏨 *Hotel Ratanakiri — Maintenance*\n"
            "Tap below to report an issue / ចុចខាងក្រោម:",
            parse_mode="Markdown",
            reply_markup=zone_keyboard()
        )

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
