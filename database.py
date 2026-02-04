import sqlite3
from config import Config
from typing import Dict, List, Tuple
import json

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        cursor = self.conn.cursor()
        
        # Players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                country TEXT,
                is_owner BOOLEAN DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Countries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                name TEXT PRIMARY KEY,
                controller_type TEXT CHECK(controller_type IN ('HUMAN', 'AI')),
                controller_id INTEGER,  -- telegram_id for HUMAN, NULL for AI
                capital TEXT,
                territory_size INTEGER DEFAULT 100,
                morale INTEGER DEFAULT 70,
                last_ai_action TIMESTAMP
            )
        ''')
        
        # Resources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                country TEXT PRIMARY KEY,
                gold INTEGER DEFAULT 1000,
                iron INTEGER DEFAULT 800,
                stone INTEGER DEFAULT 900,
                food INTEGER DEFAULT 1200,
                gold_mine_lvl INTEGER DEFAULT 1,
                iron_mine_lvl INTEGER DEFAULT 1,
                stone_quarry_lvl INTEGER DEFAULT 1,
                farm_lvl INTEGER DEFAULT 1,
                FOREIGN KEY(country) REFERENCES countries(name)
            )
        ''')
        
        # Army table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS army (
                country TEXT PRIMARY KEY,
                infantry INTEGER DEFAULT 100,
                cavalry INTEGER DEFAULT 50,
                archers INTEGER DEFAULT 40,
                siege INTEGER DEFAULT 10,
                infantry_lvl INTEGER DEFAULT 1,
                cavalry_lvl INTEGER DEFAULT 1,
                archers_lvl INTEGER DEFAULT 1,
                siege_lvl INTEGER DEFAULT 1,
                FOREIGN KEY(country) REFERENCES countries(name)
            )
        ''')
        
        # Alliances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_a TEXT,
                country_b TEXT,
                treaty_type TEXT CHECK(treaty_type IN ('ALLIANCE', 'NON_AGGRESSION', 'TRADE')),
                formed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(country_a) REFERENCES countries(name),
                FOREIGN KEY(country_b) REFERENCES countries(name)
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER DEFAULT 1,
                event_type TEXT,
                description TEXT,
                involved_countries TEXT,  -- JSON array
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Season state
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Initialize default countries if empty
        if not cursor.execute("SELECT 1 FROM countries LIMIT 1").fetchone():
            for country in Config.COUNTRIES:
                cursor.execute(
                    "INSERT INTO countries (name, controller_type) VALUES (?, 'AI')",
                    (country,)
                )
                cursor.execute(
                    "INSERT INTO resources (country) VALUES (?)",
                    (country,)
                )
                cursor.execute(
                    "INSERT INTO army (country) VALUES (?)",
                    (country,)
                )
        
        # Ensure owner exists
        cursor.execute(
            "INSERT OR IGNORE INTO players (telegram_id, is_owner) VALUES (?, 1)",
            (Config.OWNER_ID,)
        )
        
        self.conn.commit()
    
    # --- Player operations ---
    def add_player(self, telegram_id: int, country: str) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE countries SET controller_type='HUMAN', controller_id=? WHERE name=? AND controller_type='AI'",
                (telegram_id, country)
            )
            if cursor.rowcount == 0:
                return False
            
            cursor.execute(
                "INSERT OR REPLACE INTO players (telegram_id, country) VALUES (?, ?)",
                (telegram_id, country)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_player_country(self, telegram_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT country FROM players WHERE telegram_id=?",
            (telegram_id,)
        ).fetchone()
        return row['country'] if row else None
    
    def is_owner(self, telegram_id: int) -> bool:
        row = self.conn.execute(
            "SELECT is_owner FROM players WHERE telegram_id=?",
            (telegram_id,)
        ).fetchone()
        return bool(row and row['is_owner'])
    
    def get_free_countries(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT name FROM countries WHERE controller_type='AI'"
        ).fetchall()
        return [r['name'] for r in rows]
    
    # --- Resource/Army operations ---
    def get_resources(self, country: str) -> Dict:
        row = self.conn.execute("SELECT * FROM resources WHERE country=?", (country,)).fetchone()
        return dict(row) if row else {}
    
    def update_resources(self, country: str, updates: Dict):
        set_clause = ', '.join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [country]
        self.conn.execute(
            f"UPDATE resources SET {set_clause} WHERE country=?",
            values
        )
        self.conn.commit()
    
    def get_army(self, country: str) -> Dict:
        row = self.conn.execute("SELECT * FROM army WHERE country=?", (country,)).fetchone()
        return dict(row) if row else {}
    
    # --- AI & Game State ---
    def get_ai_countries(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT name FROM countries WHERE controller_type='AI'"
        ).fetchall()
        return [r['name'] for r in rows]
    
    def get_human_players(self) -> List[Tuple[int, str]]:
        rows = self.conn.execute(
            "SELECT telegram_id, country FROM players WHERE telegram_id != ?",
            (Config.OWNER_ID,)
        ).fetchall()
        return [(r['telegram_id'], r['country']) for r in rows]
    
    def log_event(self, event_type: str, description: str, countries: List[str]):
        self.conn.execute(
            "INSERT INTO events (event_type, description, involved_countries) VALUES (?, ?, ?)",
            (event_type, description, json.dumps(countries))
        )
        self.conn.commit()
    
    def set_season_active(self, active: bool):
        self.conn.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('season_active', ?)",
            ('1' if active else '0',)
        )
        self.conn.commit()
    
    def is_season_active(self) -> bool:
        row = self.conn.execute(
            "SELECT value FROM game_state WHERE key='season_active'"
        ).fetchone()
        return bool(row and row['value'] == '1')
    
    def close(self):
        self.conn.close()