import random
import json
from typing import Dict, List, Tuple
from config import Config
from database import Database

class Advisor:
    @staticmethod
    def analyze_threats(country: str, db: Database) -> List[str]:
        resources = db.get_resources(country)
        army = db.get_army(country)
        threats = []
        
        # Low food warning
        if resources['food'] < 300:
            threats.append("⚠️ Critical food shortage! Prioritize farm upgrades or trade.")
        
        # Weak defenses
        if army['infantry'] < 50 and army['infantry_lvl'] < 2:
            threats.append("🛡️ Your infantry is undertrained. Upgrade barracks immediately.")
        
        # Resource imbalance
        total_resources = sum(resources[r] for r in Config.RESOURCES)
        if resources['gold'] > 2000 and total_resources - resources['gold'] < 1200:
            threats.append("💰 Resource imbalance detected. Convert gold to needed resources via trade.")
        
        return threats
    
    @staticmethod
    def suggest_strategy(country: str, db: Database) -> str:
        bonuses = Config.COUNTRY_BONUSES.get(country, {})
        army = db.get_army(country)
        resources = db.get_resources(country)
        
        if 'cavalry_speed' in bonuses and army['cavalry'] > 80:
            return "🎯 Persia's strength is mobility. Use cavalry raids on distant weak territories."
        elif 'defense' in bonuses and army['infantry_lvl'] >= 3:
            return "🏰 Rome excels in defense. Fortify borders and let enemies exhaust themselves attacking."
        elif 'archer_damage' in bonuses:
            return "🏹 Egypt dominates ranged combat. Keep enemies at distance with archer formations."
        elif resources['food'] > 1500:
            return "🌾 Strong food surplus! Expand army size or trade for strategic resources."
        
        return "⚖️ Balanced strategy recommended: Upgrade core units and secure nearby resource nodes."

class AIEngine:
    def __init__(self, db: Database):
        self.db = db
    
    def execute_ai_turn(self):
        """Run strategic AI decisions for all AI-controlled countries"""
        ai_countries = self.db.get_ai_countries()
        for country in ai_countries:
            self._ai_decision_cycle(country)
    
    def _ai_decision_cycle(self, country: str):
        resources = self.db.get_resources(country)
        army = self.db.get_army(country)
        
        # Decision weights based on state
        actions = []
        
        # 1. If rich in resources, upgrade army
        total_resources = sum(resources[r] for r in Config.RESOURCES)
        if total_resources > 3000:
            actions.append(('upgrade', 0.4))
        
        # 2. If army strong relative to neighbors, attack weakest
        army_power = army['infantry'] * 1.0 + army['cavalry'] * 1.5 + army['archers'] * 1.2
        if army_power > 200:
            actions.append(('attack', 0.35))
        
        # 3. If weak, seek alliance
        if army_power < 100:
            actions.append(('alliance', 0.25))
        
        if not actions:
            return
        
        # Weighted random choice
        total_weight = sum(w for _, w in actions)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        chosen = actions[0][0]
        
        for action, weight in actions:
            cumulative += weight
            if rand < cumulative:
                chosen = action
                break
        
        # Execute chosen action
        if chosen == 'upgrade':
            self._ai_upgrade_army(country)
        elif chosen == 'attack':
            self._ai_attack(country)
        elif chosen == 'alliance':
            self._ai_seek_alliance(country)
    
    def _ai_upgrade_army(self, country: str):
        resources = self.db.get_resources(country)
        army = self.db.get_army(country)
        
        # Choose cheapest viable upgrade
        affordable = []
        if resources['gold'] >= 200 and resources['iron'] >= 150:
            affordable.append('infantry')
        if resources['gold'] >= 250 and resources['food'] >= 200:
            affordable.append('cavalry')
        
        if not affordable:
            return
        
        unit = random.choice(affordable)
        cost = {'gold': -200, 'iron': -150} if unit == 'infantry' else {'gold': -250, 'food': -200}
        
        # Apply resource costs
        new_resources = {k: resources[k] + v for k, v in cost.items()}
        self.db.update_resources(country, new_resources)
        
        # Upgrade army - CORRECTED SQL WITH PROPER BRACE BALANCING
        self.db.conn.execute(
            f"UPDATE army SET {unit} = {unit} + 30, {unit}_lvl = {unit}_lvl + 1 WHERE country = ?",
            (country,)
        )
        self.db.conn.commit()
        self.db.log_event('AI_UPGRADE', f"{country} upgraded {unit} units", [country])
    
    def _ai_attack(self, country: str):
        human_players = self.db.get_human_players()
        if not human_players:
            return
        
        # Find weakest human player by army strength
        weakest = min(
            human_players,
            key=lambda x: sum(self.db.get_army(x[1]).get(u, 0) for u in ['infantry', 'cavalry', 'archers'])
        )
        target_country = weakest[1]
        
        # Simulate battle (simplified probability-based outcome)
        attacker_army = self.db.get_army(country)
        defender_army = self.db.get_army(target_country)
        
        attacker_strength = (
            attacker_army['infantry'] * 1.0 + 
            attacker_army['cavalry'] * 1.8 + 
            attacker_army['archers'] * 1.3
        )
        defender_strength = (
            defender_army['infantry'] * 1.2 + 
            defender_army['archers'] * 1.4 + 
            defender_army['cavalry'] * 1.0
        )
        
        # Base win probability on strength ratio
        win_prob = min(0.9, max(0.1, attacker_strength / (attacker_strength + defender_strength)))
        outcome = "victory" if random.random() < win_prob else "defeat"
        
        self.db.log_event(
            'BATTLE',
            f"⚔️ AI {country} attacked {target_country} - {outcome.upper()}",
            [country, target_country]
        )
        
        # Post to news channel
        if Config.NEWS_CHANNEL:
            try:
                from telegram.ext import Application
                # This would be handled by the main bot instance in practice
                pass
            except:
                pass
    
    def _ai_seek_alliance(self, country: str):
        # Simplified: propose alliance to strongest neighbor
        pass
