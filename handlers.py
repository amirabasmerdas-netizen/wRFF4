from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
from database import Database
from game_engine import Advisor, AIEngine
import logging
import re

db = Database()
ai_engine = AIEngine(db)
logger = logging.getLogger(__name__)

# --- Owner Verification Decorator ---
def owner_only(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not db.is_owner(user_id):
            await update.message.reply_text("⛔ Access denied. Owner only.")
            return
        return await handler(update, context)
    return wrapper

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_player_country(user_id)
    
    if db.is_owner(user_id):
        keyboard = [
            [InlineKeyboardButton("👑 Owner Dashboard", callback_data='owner_menu')],
        ]
        if country:
            keyboard.append([InlineKeyboardButton("📊 My Country", callback_data='my_country')])
        keyboard.append([InlineKeyboardButton("💡 Advisor", callback_data='advisor')])
    elif country:
        keyboard = [
            [InlineKeyboardButton("🏰 My Country", callback_data='my_country')],
            [InlineKeyboardButton("⚔️ Military", callback_data='military')],
            [InlineKeyboardButton("🌾 Resources", callback_data='resources')],
            [InlineKeyboardButton("💡 Advisor", callback_data='advisor')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='start')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("ℹ️ Game Info", callback_data='game_info')]]
    
    text = f"🌍 *Ancient World Wars - Season {'ACTIVE' if db.is_season_active() else 'INACTIVE'}*\n"
    if country:
        text += f"You rule *{country}*! Command your empire wisely."
    else:
        text += "You are not assigned to a country yet."
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
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
        [InlineKeyboardButton("📢 Broadcast", callback_data='owner_broadcast_prompt')],
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
        for country in free_countries[:12]
    ] + [[InlineKeyboardButton("🔙 Cancel", callback_data='owner_menu')]]
    
    await query.edit_message_text(
        "➕ *SELECT COUNTRY TO ASSIGN*\nChoose a free country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- Country Selection Handler ---
@owner_only
async def owner_select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    country = query.data.replace('owner_select_', '')
    context.user_data['assign_country'] = country
    
    await query.edit_message_text(
        f"✏️ Enter Telegram ID for *{country}*:\n\n"
        "(Reply with numeric ID only - e.g., 123456789)",
        parse_mode='Markdown'
    )

# --- Handle Telegram ID Input (CRITICAL: Was Missing!) ---
@owner_only
async def handle_telegram_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'assign_country' not in context.user_data:
        return  # Not in assignment flow
    
    country = context.user_data['assign_country']
    text = update.message.text.strip()
    
    # Validate numeric ID
    if not re.match(r'^\d+$', text):
        await update.message.reply_text("❌ Invalid ID. Please enter a numeric Telegram ID only.")
        return
    
    telegram_id = int(text)
    
    # Assign country
    if db.add_player(telegram_id, country):
        await update.message.reply_text(
            f"✅ Successfully assigned *{country}* to player ID `{telegram_id}`",
            parse_mode='Markdown'
        )
        # Clear state
        context.user_data.pop('assign_country', None)
    else:
        await update.message.reply_text(
            f"❌ Failed to assign {country}. It may no longer be available."
        )

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
                text=f"⚔️ *SEASON STARTED*\n\nYou rule *{country}*! Command your armies wisely.\nUse /start to access your war room.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to notify player {telegram_id}: {e}")
    
    # Channel announcement
    if Config.NEWS_CHANNEL:
        try:
            player_list = '\n'.join(f"• {country}" for _, country in players) or "No players yet"
            await context.bot.send_message(
                chat_id=Config.NEWS_CHANNEL,
                text=f"🌍 *ANCIENT WORLD WARS - SEASON STARTED*\n\nHuman rulers:\n{player_list}\n\nMay the strongest empire prevail!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Channel broadcast failed: {e}")
    
    await query.edit_message_text("✅ Season started successfully!")

# --- Broadcast Flow ---
@owner_only
async def owner_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 Enter your broadcast message (supports Markdown):\n\n"
        "Reply to this message with your announcement."
    )
    context.user_data['awaiting_broadcast'] = True

@owner_only
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_broadcast'):
        return
    
    message = update.message.text
    
    # Send to all players
    players = db.get_human_players()
    success_count = 0
    for telegram_id, _ in players:
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"📣 *OFFICIAL BROADCAST*\n\n{message}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"Broadcast failed to {telegram_id}: {e}")
    
    # Send to news channel
    if Config.NEWS_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=Config.NEWS_CHANNEL,
                text=f"📣 *OFFICIAL BROADCAST*\n\n{message}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Channel broadcast failed: {e}")
    
    await update.message.reply_text(
        f"✅ Broadcast sent to {success_count}/{len(players)} players and news channel."
    )
    context.user_data['awaiting_broadcast'] = False

# --- Register Handlers ---
def register_handlers(application):
    # Command handlers
    application.add_handler(CommandHandler('start', start))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(owner_menu, pattern='^owner_menu$'))
    application.add_handler(CallbackQueryHandler(owner_add_player, pattern='^owner_add_player$'))
    application.add_handler(CallbackQueryHandler(owner_select_country, pattern='^owner_select_'))
    application.add_handler(CallbackQueryHandler(advisor_handler, pattern='^advisor$'))
    application.add_handler(CallbackQueryHandler(start_season, pattern='^owner_start_season$'))
    application.add_handler(CallbackQueryHandler(owner_broadcast_prompt, pattern='^owner_broadcast_prompt$'))
    
    # Message handlers (MUST be after callback handlers)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.User(user_id=Config.OWNER_ID),
        handle_telegram_id_input
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.User(user_id=Config.OWNER_ID),
        handle_broadcast_message
    ))
