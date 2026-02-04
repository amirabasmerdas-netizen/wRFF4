from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import Config
from database import Database
from game_engine import Advisor, AIEngine
import logging

db = Database()
ai_engine = AIEngine(db)
logger = logging.getLogger(__name__)

# --- Owner Verification ---
def owner_only(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not db.is_owner(user_id):
            await update.message.reply_text("⛔ Access denied. Owner only.")
            return
        return await handler(update, context)
    return wrapper

# --- Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_player_country(user_id)
    
    if db.is_owner(user_id):
        keyboard = [
            [InlineKeyboardButton("👑 Owner Dashboard", callback_data='owner_menu')],
            [InlineKeyboardButton("📊 My Country", callback_data='my_country')] if country else [],
            [InlineKeyboardButton("💡 Advisor", callback_data='advisor')]
        ]
    elif country:
        keyboard = [
            [InlineKeyboardButton("🏰 My Country", callback_data='my_country')],
            [InlineKeyboardButton("⚔️ Military", callback_data='military')],
            [InlineKeyboardButton("🌾 Resources", callback_data='resources')],
            [InlineKeyboardButton("🤝 Diplomacy", callback_data='diplomacy')],
            [InlineKeyboardButton("💡 Advisor", callback_data='advisor')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("ℹ️ Game Info", callback_data='game_info')]]
    
    await update.message.reply_text(
        f"🌍 *Ancient World Wars - Season {'ACTIVE' if db.is_season_active() else 'INACTIVE'}*\n"
        f"Welcome, {update.effective_user.first_name}!",
        reply_markup=InlineKeyboardMarkup([btn for btn in keyboard if btn]),
        parse_mode='Markdown'
    )

# --- Owner Menu ---
@owner_only
async def owner_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Player", callback_data='owner_add_player')],
        [InlineKeyboardButton("🔄 Start Season", callback_data='owner_start_season')],
        [InlineKeyboardButton("🛑 End Season", callback_data='owner_end_season')],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data='owner_broadcast')],
        [InlineKeyboardButton("🔙 Back", callback_data='start')]
    ]
    
    await query.edit_message_text(
        "👑 *OWNER DASHBOARD*\nSelect an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- Add Player Flow ---
@owner_only
async def owner_add_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    free_countries = db.get_free_countries()
    if not free_countries:
        await query.edit_message_text("❌ No free countries available!")
        return
    
    keyboard = [
        [InlineKeyboardButton(country, callback_data=f'owner_select_{country}')]
        for country in free_countries[:12]  # Limit to 12 for Telegram constraints
    ] + [[InlineKeyboardButton("🔙 Cancel", callback_data='owner_menu')]]
    
    await query.edit_message_text(
        "➕ *SELECT COUNTRY TO ASSIGN*\nChoose a free country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Store selected country in context for next step
async def owner_select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    country = query.data.replace('owner_select_', '')
    context.user_data['assign_country'] = country
    
    await query.edit_message_text(
        f"✏️ Enter Telegram ID for *{country}*:\n\n"
        "(Reply with numeric ID only)",
        parse_mode='Markdown'
    )
    # Set state to wait for message input (handled in message handler)

# --- Broadcast System ---
async def broadcast_to_players(context: ContextTypes.DEFAULT_TYPE, message: str):
    players = db.get_human_players()
    for telegram_id, _ in players:
        try:
            await context.bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.warning(f"Failed to send to {telegram_id}: {e}")
    
    # Also post to news channel
    if Config.NEWS_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=Config.NEWS_CHANNEL,
                text=f"📣 *OFFICIAL BROADCAST*\n\n{message}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Channel broadcast failed: {e}")

# --- Advisor Handler ---
async def advisor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    country = db.get_player_country(user_id)
    
    if not country:
        await query.edit_message_text("❌ You don't control a country yet.")
        return
    
    threats = Advisor.analyze_threats(country, db)
    strategy = Advisor.suggest_strategy(country, db)
    
    text = f"🧠 *STRATEGIC ADVISOR - {country}*\n\n"
    if threats:
        text += "⚠️ *THREAT ASSESSMENT*\n" + "\n".join(threats) + "\n\n"
    text += f"💡 *RECOMMENDATION*\n{strategy}"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data='my_country')
        ]]),
        parse_mode='Markdown'
    )

# --- Season Start ---
@owner_only
async def start_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.set_season_active(True)
    
    # Notify all players
    players = db.get_human_players()
    for telegram_id, country in players:
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"⚔️ *SEASON STARTED*\n\nYou rule {country}! Command your armies wisely.\nUse /start to access your war room.",
                parse_mode='Markdown'
            )
        except:
            pass
    
    # Channel announcement
    if Config.NEWS_CHANNEL:
        player_list = '\n'.join(f"• {country}" for _, country in players)
        await context.bot.send_message(
            chat_id=Config.NEWS_CHANNEL,
            text=f"🌍 *ANCIENT WORLD WARS - SEASON STARTED*\n\nHuman rulers:\n{player_list}\n\nMay the strongest empire prevail!",
            parse_mode='Markdown'
        )
    
    await query.edit_message_text("✅ Season started successfully!")

# Register handlers
def register_handlers(application):
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(owner_menu, pattern='^owner_menu$'))
    application.add_handler(CallbackQueryHandler(owner_add_player, pattern='^owner_add_player$'))
    application.add_handler(CallbackQueryHandler(owner_select_country, pattern='^owner_select_'))
    application.add_handler(CallbackQueryHandler(advisor_handler, pattern='^advisor$'))
    application.add_handler(CallbackQueryHandler(start_season, pattern='^owner_start_season$'))
    # Add more handlers as needed...