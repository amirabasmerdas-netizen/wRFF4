import os
import logging
from flask import Flask, request
from telegram.ext import Application, CommandHandler
from config import Config
from database import Database
from handlers import register_handlers, start
from game_engine import AIEngine
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for webhook
app = Flask(__name__)

# Initialize bot
application = Application.builder().token(Config.BOT_TOKEN).build()
register_handlers(application)

# Initialize game systems
db = Database()
ai_engine = AIEngine(db)
ai_lock = Lock()  # Thread safety for SQLite

# AI scheduler (runs every 6 hours)
scheduler = BackgroundScheduler()
scheduler.add_job(
    lambda: ai_engine.execute_ai_turn() if ai_lock.acquire(blocking=False) else None,
    'interval',
    hours=6
)
scheduler.start()

@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        application.update_queue.put(request.get_json())
        return 'OK'
    return 'Invalid content type', 400

@app.route('/health')
def health():
    return {
        'status': 'ok',
        'season_active': db.is_season_active(),
        'players': len(db.get_human_players())
    }

def setup_webhook():
    webhook_url = f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
    try:
        application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook set successfully to {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8443))
    
    if os.getenv('ENVIRONMENT') == 'development':
        logger.info("🚀 Starting in DEVELOPMENT mode (polling)...")
        application.run_polling()
    else:
        logger.info("🚀 Starting in PRODUCTION mode (webhook)...")
        setup_webhook()
        app.run(host='0.0.0.0', port=port)
