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
        if resources['gold'] > 2000 and min(resources[r] for r in Config.RESOURCES if r != 'gold') < 400:
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
        # Simple strategic logic - expandable in V3
        resources = self.db.get_resources(country)
        army = self.db.get_army(country)
        
        # Decision weights
        actions = []
        
        # 1. If rich in resources, upgrade army
        if sum(resources[r] for r in Config.RESOURCES) > 3000:
            actions.append(('upgrade', 0.4))
        
        # 2. If army strong relative to neighbors, attack weakest
        if army['infantry'] + army['cavalry'] > 150:
            actions.append(('attack', 0.35))
        
        # 3. If weak, seek alliance
        if army['infantry'] < 60:
            actions.append(('alliance', 0.25))
        
        if not actions:
            return
        
        # Weighted random choice
        total = sum(w for _, w in actions)
        rand = random.uniform(0, total)
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
        
        if affordable:
            unit = random.choice(affordable)
            cost = {'gold': -200, 'iron': -150} if unit == 'infantry' else {'gold': -250, 'food': -200}
            self.db.update_resources(country, cost)
            self.db.conn.execute(
                f"UPDATE army SET {unit}={unit}+30, {unit}_lvl={unit}_lvl}+1 WHERE country=?",
                (country,)
            )
            self.db.conn.commit()
            self.db.log_event('AI_UPGRADE', f"{country} upgraded {unit} units", [country])
    
    def _ai_attack(self, country: str):
        # Simplified: attack weakest neighbor
        human_players = self.db.get_human_players()
        if not human_players:
            return
        
        target_country = min(
            human_players,
            key=lambda x: sum(self.db.get_army(x[1]).get(u, 0) for u in ['infantry', 'cavalry', 'archers'])
        )[1]
        
        # Simulate battle (simplified)
        attacker_str = sum(self.db.get_army(country).get(u, 0) * 1.2 for u in ['infantry', 'cavalry'])
        defender_str = sum(self.db.get_army(target_country).get(u, 0) * 1.0 for u in ['infantry', 'archers'])
        
        if attacker_str > defender_str * 0.8:  # 80% threshold to attempt attack
            outcome = "victory" if random.random() < 0.6 else "defeat"
            self.db.log_event(
                'BATTLE',
                f"AI {country} attacked {target_country} - {outcome.upper()}",
                [country, target_country]
            )