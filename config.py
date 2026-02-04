import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    OWNER_ID = int(os.getenv('OWNER_ID', '8588773170'))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    PORT = int(os.getenv('PORT', '8443'))
    NEWS_CHANNEL = os.getenv('NEWS_CHANNEL', '')  # e.g., '@ancient_world_news'
    DATABASE_PATH = 'game_data.db'
    
    # Game constants
    RESOURCES = ['gold', 'iron', 'stone', 'food']
    COUNTRIES = [
        'Persia', 'Rome', 'Egypt', 'Greece', 'China', 'Babylon',
        'Assyria', 'Carthage', 'India', 'Macedonia', 'Scythia', 'Celtic'
    ]
    COUNTRY_BONUSES = {
        'Persia': {'cavalry_speed': 1.3},
        'Rome': {'defense': 1.4},
        'Egypt': {'archer_damage': 1.25, 'food_production': 1.2},
        'China': {'wall_strength': 1.5},
        'Greece': {'phalanx_defense': 1.35},
        'Carthage': {'naval_strength': 1.4},
    }