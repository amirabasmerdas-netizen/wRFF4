import os
import logging
from flask import Flask, request
from telegram.ext import Application, CommandHandler
from config import Config
from database import Database
from handlers import register_handlers, start
from game_engine import AIEngine
from apscheduler.schedulers.background import BackgroundScheduler

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Flask app for webhook
app = Flask(__name__)

# Initialize bot
application = Application.builder().token(Config.BOT_TOKEN).build()
register_handlers(application)

# Initialize game systems
db = Database()
ai_engine = AIEngine(db)

# AI scheduler (runs every 6 hours)
scheduler = BackgroundScheduler()
scheduler.add_job(ai_engine.execute_ai_turn, 'interval', hours=6)
scheduler.start()

@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(request.get_json())
    return 'OK'

@app.route('/health')
def health():
    return {'status': 'ok', 'season_active': db.is_season_active()}

def setup_webhook():
    webhook_url = f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
    application.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

if __name__ == '__main__':
    # Start bot polling during development
    if os.getenv('ENVIRONMENT') == 'development':
        application.run_polling()
    else:
        # Production: webhook mode
        setup_webhook()
        port = int(os.environ.get('PORT', 8443))
        app.run(host='0.0.0.0', port=port, threaded=True)
