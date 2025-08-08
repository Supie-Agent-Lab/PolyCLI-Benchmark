#!/usr/bin/env python3
import json
import random
import os
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GameState(Enum):
    MENU = "menu"
    EXPLORING = "exploring"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"
    QUEST_LOG = "quest_log"
    SHOP = "shop"
    GAME_OVER = "game_over"

class Player:
    def __init__(self, name: str = "Hero"):
        self.name = name
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.max_hp = 100
        self.hp = 100
        self.max_mp = 30
        self.mp = 30
        self.attack = 15
        self.defense = 10
        self.magic = 12
        self.speed = 10
        self.gold = 50
        self.inventory = {
            "Health Potion": 3,
            "Mana Potion": 2
        }
        self.equipment = {
            "weapon": "Rusty Sword",
            "armor": "Leather Vest",
            "accessory": None
        }
        self.skills = ["Slash", "Heal"]
        self.location = "village_square"
        self.quests_completed = []
        self.active_quests = []
        self.flags = {}
    
    def level_up(self):
        self.level += 1
        self.max_hp += 20
        self.hp = self.max_hp
        self.max_mp += 10
        self.mp = self.max_mp
        self.attack += 5
        self.defense += 3
        self.magic += 4
        self.speed += 2
        self.exp_to_next = self.level * 100
        
        if self.level == 3:
            self.skills.append("Fire Bolt")
        elif self.level == 5:
            self.skills.append("Power Strike")
        elif self.level == 7:
            self.skills.append("Lightning")
        elif self.level == 10:
            self.skills.append("Divine Shield")
        
        return f"{Colors.GREEN}Level Up! You are now level {self.level}!{Colors.ENDC}"
    
    def gain_exp(self, amount: int):
        self.exp += amount
        messages = [f"{Colors.CYAN}Gained {amount} EXP!{Colors.ENDC}"]
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            messages.append(self.level_up())
        return messages
    
    def take_damage(self, damage: int):
        actual_damage = max(1, damage - self.defense // 2)
        self.hp -= actual_damage
        self.hp = max(0, self.hp)
        return actual_damage
    
    def heal(self, amount: int):
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp
    
    def restore_mp(self, amount: int):
        old_mp = self.mp
        self.mp = min(self.max_mp, self.mp + amount)
        return self.mp - old_mp
    
    def add_item(self, item: str, quantity: int = 1):
        if item in self.inventory:
            self.inventory[item] += quantity
        else:
            self.inventory[item] = quantity
    
    def remove_item(self, item: str, quantity: int = 1):
        if item in self.inventory:
            self.inventory[item] -= quantity
            if self.inventory[item] <= 0:
                del self.inventory[item]
                return True
        return False
    
    def has_item(self, item: str, quantity: int = 1) -> bool:
        return item in self.inventory and self.inventory[item] >= quantity
    
    def equip_item(self, item: str, slot: str):
        if self.equipment[slot]:
            self.add_item(self.equipment[slot])
        self.equipment[slot] = item
        self.remove_item(item)

class Enemy:
    def __init__(self, name: str, hp: int, attack: int, defense: int, exp: int, gold: int, drops: Dict[str, float] = None):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.exp = exp
        self.gold = gold
        self.drops = drops or {}
    
    def take_damage(self, damage: int):
        actual_damage = max(1, damage - self.defense // 2)
        self.hp -= actual_damage
        self.hp = max(0, self.hp)
        return actual_damage
    
    def is_alive(self) -> bool:
        return self.hp > 0

class Quest:
    def __init__(self, id: str, name: str, description: str, objectives: Dict, rewards: Dict):
        self.id = id
        self.name = name
        self.description = description
        self.objectives = objectives
        self.rewards = rewards
        self.progress = {}
        for obj in objectives:
            self.progress[obj] = 0
    
    def update_progress(self, objective: str, amount: int = 1):
        if objective in self.progress:
            self.progress[objective] += amount
    
    def is_complete(self) -> bool:
        for obj, target in self.objectives.items():
            if self.progress.get(obj, 0) < target:
                return False
        return True

class Location:
    def __init__(self, name: str, description: str, connections: Dict[str, str], npcs: List[str] = None, 
                 enemies: List[str] = None, items: List[str] = None, shops: List[str] = None):
        self.name = name
        self.description = description
        self.connections = connections
        self.npcs = npcs or []
        self.enemies = enemies or []
        self.items = items or []
        self.shops = shops or []

class Game:
    def __init__(self):
        self.player = None
        self.state = GameState.MENU
        self.current_enemy = None
        self.current_npc = None
        self.dialogue_index = 0
        self.locations = self.init_locations()
        self.npcs = self.init_npcs()
        self.enemy_templates = self.init_enemies()
        self.items = self.init_items()
        self.quests = self.init_quests()
        self.shops = self.init_shops()
        self.save_file = "shadow_realm_save.json"
    
    def init_locations(self) -> Dict[str, Location]:
        return {
            "village_square": Location(
                "Village Square",
                "The heart of Lumenhaven village. The fountain in the center sparkles with clear water. "
                "Villagers go about their daily business, though many seem worried about something.",
                {"north": "market", "east": "inn", "south": "village_gate", "west": "elder_house"},
                npcs=["village_elder", "guard_captain"],
                items=["Gold Coin"]
            ),
            "market": Location(
                "Market District",
                "Colorful stalls line the streets, selling everything from fresh produce to magical trinkets. "
                "The air is filled with the sounds of merchants hawking their wares.",
                {"south": "village_square", "east": "blacksmith"},
                npcs=["merchant"],
                shops=["general_store"]
            ),
            "blacksmith": Location(
                "Blacksmith's Forge",
                "The rhythmic sound of hammer on anvil fills the air. Weapons and armor of all kinds "
                "line the walls, and the heat from the forge is almost overwhelming.",
                {"west": "market"},
                npcs=["blacksmith"],
                shops=["weapon_shop"]
            ),
            "inn": Location(
                "The Weary Traveler Inn",
                "A cozy establishment with the smell of hearty stew wafting from the kitchen. "
                "Adventurers and locals alike gather here to share stories and rest.",
                {"west": "village_square", "up": "inn_room"},
                npcs=["innkeeper", "mysterious_stranger"]
            ),
            "inn_room": Location(
                "Inn Room",
                "A simple but comfortable room with a bed, desk, and window overlooking the village square. "
                "You can rest here to recover your health and mana.",
                {"down": "inn"}
            ),
            "elder_house": Location(
                "Elder's House",
                "A modest home filled with ancient books and mystical artifacts. The elder's wisdom "
                "is sought by many in times of trouble.",
                {"east": "village_square"},
                npcs=["village_elder"]
            ),
            "village_gate": Location(
                "Village Gate",
                "The southern entrance to Lumenhaven. Guards stand watch, alert for any signs of danger "
                "from the wilderness beyond.",
                {"north": "village_square", "south": "forest_entrance"},
                npcs=["gate_guard"]
            ),
            "forest_entrance": Location(
                "Dark Forest Entrance",
                "The edge of the mysterious Dark Forest. Twisted trees loom overhead, their branches "
                "blocking out most of the sunlight. Strange sounds echo from within.",
                {"north": "village_gate", "south": "forest_path", "east": "forest_clearing"},
                enemies=["wolf", "goblin"]
            ),
            "forest_path": Location(
                "Forest Path",
                "A winding path through the dark forest. The shadows seem to move on their own, "
                "and you can't shake the feeling that you're being watched.",
                {"north": "forest_entrance", "south": "deep_forest", "west": "abandoned_camp"},
                enemies=["wolf", "goblin", "bandit"]
            ),
            "forest_clearing": Location(
                "Forest Clearing",
                "A small clearing where sunlight manages to break through the canopy. "
                "Ancient stones form a circle in the center, emanating a faint magical aura.",
                {"west": "forest_entrance", "north": "hidden_grove"},
                enemies=["wolf"],
                items=["Mana Crystal"]
            ),
            "hidden_grove": Location(
                "Hidden Grove",
                "A secret grove protected by ancient magic. A crystal-clear spring bubbles up from the ground, "
                "and the air itself seems to shimmer with power.",
                {"south": "forest_clearing"},
                npcs=["forest_spirit"],
                items=["Elixir of Life"]
            ),
            "abandoned_camp": Location(
                "Abandoned Camp",
                "The remains of what was once a bandit camp. Tattered tents and cold fire pits "
                "tell a story of hasty abandonment. You might find something useful here.",
                {"east": "forest_path"},
                enemies=["bandit"],
                items=["Iron Sword", "Leather Armor"]
            ),
            "deep_forest": Location(
                "Deep Forest",
                "The heart of the Dark Forest. The darkness here is almost tangible, and powerful "
                "creatures lurk in the shadows. This is no place for the unprepared.",
                {"north": "forest_path", "east": "ancient_ruins", "south": "shadow_portal"},
                enemies=["dire_wolf", "orc", "dark_spirit"]
            ),
            "ancient_ruins": Location(
                "Ancient Ruins",
                "Crumbling stone structures covered in mysterious runes. This place predates the village "
                "by centuries, and holds secrets of a forgotten civilization.",
                {"west": "deep_forest", "down": "underground_chamber"},
                enemies=["skeleton", "ghost"],
                items=["Ancient Tome"]
            ),
            "underground_chamber": Location(
                "Underground Chamber",
                "A hidden chamber beneath the ruins. Ancient treasures and powerful artifacts "
                "are said to be hidden here, guarded by deadly traps and monsters.",
                {"up": "ancient_ruins"},
                enemies=["skeleton_warrior", "lich"],
                items=["Legendary Sword", "Dragon Scale Armor"]
            ),
            "shadow_portal": Location(
                "Shadow Portal",
                "A swirling vortex of dark energy. This is the source of the corruption spreading "
                "through the land. The final battle awaits beyond this threshold.",
                {"north": "deep_forest", "enter": "shadow_realm"},
                enemies=["shadow_guardian"]
            ),
            "shadow_realm": Location(
                "Shadow Realm",
                "A twisted mirror of the real world, where darkness reigns supreme. "
                "The Shadow Lord awaits at the heart of this nightmare realm.",
                {"exit": "shadow_portal", "forward": "throne_room"},
                enemies=["shadow_demon", "corrupted_knight"]
            ),
            "throne_room": Location(
                "Shadow Throne Room",
                "The seat of the Shadow Lord's power. Dark energy crackles through the air, "
                "and the very walls seem to pulse with malevolent life.",
                {"back": "shadow_realm"},
                enemies=["shadow_lord"]
            )
        }
    
    def init_npcs(self) -> Dict[str, Dict]:
        return {
            "village_elder": {
                "name": "Elder Aldric",
                "dialogue": [
                    "Welcome, young one. I am Elder Aldric, leader of Lumenhaven.",
                    "Dark times have fallen upon our village. The Shadow Lord has awakened in the depths of the Dark Forest.",
                    "His corruption spreads, turning creatures into monsters and threatening our very existence.",
                    "You must be the hero of the prophecy! Please, venture into the Dark Forest and stop the Shadow Lord!",
                    "Take this blessing. It will protect you on your journey."
                ],
                "quest": "main_quest",
                "reward": {"item": "Blessing of Light", "gold": 100}
            },
            "guard_captain": {
                "name": "Captain Marcus",
                "dialogue": [
                    "Halt! I'm Captain Marcus, head of the village guard.",
                    "The forest has become too dangerous. We've lost three patrols this week alone.",
                    "If you're planning to venture out there, you'll need proper equipment.",
                    "Prove yourself by clearing out some of the wolves near the forest entrance, and I'll reward you."
                ],
                "quest": "wolf_hunt",
                "reward": {"item": "Guard's Shield", "gold": 50}
            },
            "merchant": {
                "name": "Trader Eliza",
                "dialogue": [
                    "Welcome to my humble shop! I'm Eliza, and I have the finest goods in all of Lumenhaven!",
                    "Looking for potions? Weapons? I've got it all!",
                    "Be careful out there. The roads aren't safe anymore."
                ]
            },
            "blacksmith": {
                "name": "Thorin the Smith",
                "dialogue": [
                    "Name's Thorin. I forge the finest weapons and armor in the region.",
                    "That rusty sword won't do you much good against the Shadow Lord's minions.",
                    "Bring me some rare materials from the forest, and I'll forge you something special.",
                    "I'm looking for Shadow Ore. Find me 5 pieces, and I'll make you a blade that can cut through darkness itself."
                ],
                "quest": "shadow_ore_quest",
                "reward": {"item": "Shadowbane Sword", "gold": 200}
            },
            "innkeeper": {
                "name": "Martha",
                "dialogue": [
                    "Welcome to the Weary Traveler! I'm Martha, the innkeeper.",
                    "You look tired. Would you like to rest? It's only 10 gold for the night.",
                    "Resting will fully restore your health and mana."
                ]
            },
            "mysterious_stranger": {
                "name": "Hooded Figure",
                "dialogue": [
                    "...",
                    "You seek the Shadow Lord? Foolish, but brave.",
                    "The path to victory lies not in strength alone, but in wisdom.",
                    "Seek the Forest Spirit in the Hidden Grove. She holds a key to defeating the darkness.",
                    "This map will help you find the grove. Use it wisely."
                ],
                "reward": {"item": "Ancient Map"}
            },
            "gate_guard": {
                "name": "Guard Thomas",
                "dialogue": [
                    "Be careful out there, traveler. The forest isn't what it used to be.",
                    "Strange creatures have been spotted, and even the trees seem hostile.",
                    "If you're not prepared, I suggest visiting the market first."
                ]
            },
            "forest_spirit": {
                "name": "Sylvana",
                "dialogue": [
                    "Greetings, mortal. I am Sylvana, guardian of this sacred grove.",
                    "I sense great purpose in you. The balance of nature has been disrupted by the Shadow Lord.",
                    "To defeat him, you will need the power of light itself.",
                    "Complete my trial, and I shall grant you the Orb of Radiance.",
                    "Cleanse the three corruption nodes in the forest. Only then will you be worthy."
                ],
                "quest": "cleanse_corruption",
                "reward": {"item": "Orb of Radiance", "skill": "Holy Light"}
            }
        }
    
    def init_enemies(self) -> Dict[str, Dict]:
        return {
            "wolf": {"name": "Wild Wolf", "hp": 30, "attack": 8, "defense": 5, "exp": 15, "gold": 10,
                    "drops": {"Wolf Pelt": 0.5, "Sharp Fang": 0.3}},
            "goblin": {"name": "Goblin Scout", "hp": 25, "attack": 10, "defense": 3, "exp": 20, "gold": 15,
                      "drops": {"Goblin Ear": 0.4, "Small Dagger": 0.2}},
            "bandit": {"name": "Bandit", "hp": 45, "attack": 15, "defense": 8, "exp": 35, "gold": 30,
                      "drops": {"Bandit's Blade": 0.3, "Leather Armor": 0.2}},
            "dire_wolf": {"name": "Dire Wolf", "hp": 60, "attack": 18, "defense": 10, "exp": 50, "gold": 25,
                         "drops": {"Dire Wolf Pelt": 0.4, "Alpha Fang": 0.3}},
            "orc": {"name": "Orc Warrior", "hp": 80, "attack": 22, "defense": 15, "exp": 70, "gold": 40,
                   "drops": {"Orc Tusk": 0.5, "Heavy Axe": 0.2, "Shadow Ore": 0.3}},
            "dark_spirit": {"name": "Dark Spirit", "hp": 50, "attack": 25, "defense": 5, "exp": 60, "gold": 35,
                           "drops": {"Spirit Essence": 0.6, "Mana Crystal": 0.4}},
            "skeleton": {"name": "Skeleton", "hp": 40, "attack": 12, "defense": 8, "exp": 30, "gold": 20,
                        "drops": {"Bone": 0.7, "Ancient Coin": 0.3}},
            "ghost": {"name": "Restless Ghost", "hp": 35, "attack": 20, "defense": 2, "exp": 45, "gold": 25,
                     "drops": {"Ectoplasm": 0.5, "Spirit Stone": 0.3}},
            "skeleton_warrior": {"name": "Skeleton Warrior", "hp": 100, "attack": 28, "defense": 20, "exp": 100, "gold": 60,
                                "drops": {"Warrior's Bone": 0.5, "Ancient Sword": 0.3, "Shadow Ore": 0.4}},
            "lich": {"name": "Ancient Lich", "hp": 150, "attack": 35, "defense": 25, "exp": 200, "gold": 100,
                    "drops": {"Lich's Staff": 0.4, "Necromantic Tome": 0.3, "Shadow Ore": 0.6}},
            "shadow_guardian": {"name": "Shadow Guardian", "hp": 200, "attack": 40, "defense": 30, "exp": 300, "gold": 150,
                               "drops": {"Guardian's Core": 0.8, "Shadow Crystal": 0.5}},
            "shadow_demon": {"name": "Shadow Demon", "hp": 120, "attack": 32, "defense": 18, "exp": 150, "gold": 80,
                            "drops": {"Demon Horn": 0.5, "Dark Essence": 0.4}},
            "corrupted_knight": {"name": "Corrupted Knight", "hp": 180, "attack": 38, "defense": 35, "exp": 250, "gold": 120,
                                "drops": {"Corrupted Armor": 0.4, "Cursed Blade": 0.3}},
            "shadow_lord": {"name": "Shadow Lord Malachar", "hp": 500, "attack": 50, "defense": 40, "exp": 1000, "gold": 500,
                           "drops": {"Shadow Crown": 1.0, "Heart of Darkness": 1.0, "Legendary Artifact": 1.0}}
        }
    
    def init_items(self) -> Dict[str, Dict]:
        return {
            "Health Potion": {"type": "consumable", "effect": "heal", "value": 50, "price": 20},
            "Mana Potion": {"type": "consumable", "effect": "mana", "value": 30, "price": 25},
            "Elixir of Life": {"type": "consumable", "effect": "full_heal", "value": 100, "price": 100},
            "Rusty Sword": {"type": "weapon", "attack": 5, "price": 30},
            "Iron Sword": {"type": "weapon", "attack": 10, "price": 80},
            "Bandit's Blade": {"type": "weapon", "attack": 15, "price": 150},
            "Ancient Sword": {"type": "weapon", "attack": 25, "price": 300},
            "Shadowbane Sword": {"type": "weapon", "attack": 35, "price": 500},
            "Legendary Sword": {"type": "weapon", "attack": 50, "price": 1000},
            "Leather Vest": {"type": "armor", "defense": 5, "price": 40},
            "Leather Armor": {"type": "armor", "defense": 10, "price": 100},
            "Guard's Shield": {"type": "armor", "defense": 15, "price": 200},
            "Corrupted Armor": {"type": "armor", "defense": 25, "price": 400},
            "Dragon Scale Armor": {"type": "armor", "defense": 40, "price": 800},
            "Blessing of Light": {"type": "accessory", "effect": "light_resistance", "price": 200},
            "Orb of Radiance": {"type": "accessory", "effect": "damage_boost", "price": 500},
            "Ancient Map": {"type": "key_item", "price": 0},
            "Shadow Ore": {"type": "material", "price": 50},
            "Mana Crystal": {"type": "material", "price": 30}
        }
    
    def init_quests(self) -> Dict[str, Quest]:
        return {
            "main_quest": Quest(
                "main_quest",
                "The Shadow Lord's Threat",
                "Defeat the Shadow Lord Malachar and save Lumenhaven from darkness.",
                {"defeat_shadow_lord": 1},
                {"exp": 500, "gold": 1000, "item": "Hero's Medal"}
            ),
            "wolf_hunt": Quest(
                "wolf_hunt",
                "Wolf Hunt",
                "Captain Marcus wants you to clear out the wolves near the forest entrance.",
                {"kill_wolf": 5},
                {"exp": 100, "gold": 50, "item": "Guard's Shield"}
            ),
            "shadow_ore_quest": Quest(
                "shadow_ore_quest",
                "Forging Shadowbane",
                "Collect 5 Shadow Ore pieces for Thorin to forge the Shadowbane Sword.",
                {"collect_shadow_ore": 5},
                {"exp": 200, "gold": 200, "item": "Shadowbane Sword"}
            ),
            "cleanse_corruption": Quest(
                "cleanse_corruption",
                "Nature's Balance",
                "Cleanse three corruption nodes in the forest to earn Sylvana's blessing.",
                {"cleanse_nodes": 3},
                {"exp": 300, "gold": 150, "item": "Orb of Radiance", "skill": "Holy Light"}
            )
        }
    
    def init_shops(self) -> Dict[str, Dict]:
        return {
            "general_store": {
                "name": "Eliza's General Store",
                "inventory": {
                    "Health Potion": 20,
                    "Mana Potion": 25,
                    "Elixir of Life": 100,
                    "Iron Sword": 80,
                    "Leather Armor": 100
                }
            },
            "weapon_shop": {
                "name": "Thorin's Forge",
                "inventory": {
                    "Iron Sword": 80,
                    "Bandit's Blade": 150,
                    "Leather Armor": 100,
                    "Guard's Shield": 200
                }
            }
        }
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, text: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    def print_status(self):
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.BOLD}{self.player.name} | Lv.{self.player.level} | "
              f"HP: {self.player.hp}/{self.player.max_hp} | "
              f"MP: {self.player.mp}/{self.player.max_mp} | "
              f"Gold: {self.player.gold} | "
              f"EXP: {self.player.exp}/{self.player.exp_to_next}{Colors.ENDC}")
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    
    def main_menu(self):
        self.clear_screen()
        print(f"{Colors.HEADER}{Colors.BOLD}")
        print("""
        ███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗    ██████╗ ███████╗ █████╗ ██╗     ███╗   ███╗
        ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║    ██╔══██╗██╔════╝██╔══██╗██║     ████╗ ████║
        ███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║    ██████╔╝█████╗  ███████║██║     ██╔████╔██║
        ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║    ██╔══██╗██╔══╝  ██╔══██║██║     ██║╚██╔╝██║
        ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝    ██║  ██║███████╗██║  ██║███████╗██║ ╚═╝ ██║
        ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝
        """)
        print(f"{Colors.ENDC}")
        print(f"{Colors.CYAN}A Text-Based RPG Adventure{Colors.ENDC}\n")
        print("1. New Game")
        print("2. Load Game")
        print("3. Quit")
        
        choice = input(f"\n{Colors.WARNING}Enter your choice: {Colors.ENDC}")
        
        if choice == "1":
            self.new_game()
        elif choice == "2":
            self.load_game()
        elif choice == "3":
            print(f"{Colors.GREEN}Thank you for playing!{Colors.ENDC}")
            exit()
        else:
            self.main_menu()
    
    def new_game(self):
        self.clear_screen()
        self.print_header("CHARACTER CREATION")
        name = input(f"{Colors.WARNING}Enter your character's name: {Colors.ENDC}")
        if not name:
            name = "Hero"
        
        self.player = Player(name)
        
        print(f"\n{Colors.GREEN}Welcome, {name}!{Colors.ENDC}")
        print(f"\n{Colors.CYAN}Your journey begins in the village of Lumenhaven...")
        print("The peaceful village has been threatened by the awakening of the Shadow Lord.")
        print("As the chosen hero, you must venture into the Dark Forest and stop him!{Colors.ENDC}")
        
        input(f"\n{Colors.WARNING}Press Enter to begin your adventure...{Colors.ENDC}")
        self.state = GameState.EXPLORING
        self.game_loop()
    
    def save_game(self):
        save_data = {
            "player": {
                "name": self.player.name,
                "level": self.player.level,
                "exp": self.player.exp,
                "exp_to_next": self.player.exp_to_next,
                "hp": self.player.hp,
                "max_hp": self.player.max_hp,
                "mp": self.player.mp,
                "max_mp": self.player.max_mp,
                "attack": self.player.attack,
                "defense": self.player.defense,
                "magic": self.player.magic,
                "speed": self.player.speed,
                "gold": self.player.gold,
                "inventory": self.player.inventory,
                "equipment": self.player.equipment,
                "skills": self.player.skills,
                "location": self.player.location,
                "quests_completed": self.player.quests_completed,
                "active_quests": self.player.active_quests,
                "flags": self.player.flags
            }
        }
        
        with open(self.save_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"{Colors.GREEN}Game saved successfully!{Colors.ENDC}")
    
    def load_game(self):
        if not os.path.exists(self.save_file):
            print(f"{Colors.FAIL}No save file found!{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            self.main_menu()
            return
        
        try:
            with open(self.save_file, 'r') as f:
                save_data = json.load(f)
            
            self.player = Player()
            for key, value in save_data["player"].items():
                setattr(self.player, key, value)
            
            print(f"{Colors.GREEN}Game loaded successfully!{Colors.ENDC}")
            self.state = GameState.EXPLORING
            self.game_loop()
        except Exception as e:
            print(f"{Colors.FAIL}Error loading save file: {e}{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            self.main_menu()
    
    def explore_location(self):
        self.clear_screen()
        location = self.locations[self.player.location]
        
        self.print_status()
        self.print_header(location.name.upper())
        print(f"{Colors.CYAN}{location.description}{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}Available Actions:{Colors.ENDC}")
        print("1. Move to another location")
        print("2. Check inventory")
        print("3. View quest log")
        print("4. Search area")
        
        if location.npcs:
            print("5. Talk to NPCs")
        if location.shops:
            print("6. Visit shop")
        if self.player.location == "inn_room":
            print("7. Rest (Restore HP/MP)")
        
        print("8. Save game")
        print("9. Return to main menu")
        
        choice = input(f"\n{Colors.WARNING}What would you like to do? {Colors.ENDC}")
        
        if choice == "1":
            self.move_location()
        elif choice == "2":
            self.show_inventory()
        elif choice == "3":
            self.show_quest_log()
        elif choice == "4":
            self.search_area()
        elif choice == "5" and location.npcs:
            self.talk_to_npc()
        elif choice == "6" and location.shops:
            self.visit_shop()
        elif choice == "7" and self.player.location == "inn_room":
            self.rest()
        elif choice == "8":
            self.save_game()
            input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
        elif choice == "9":
            self.main_menu()
    
    def move_location(self):
        location = self.locations[self.player.location]
        
        if not location.connections:
            print(f"{Colors.FAIL}There's nowhere to go from here!{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}Available destinations:{Colors.ENDC}")
        directions = list(location.connections.keys())
        for i, direction in enumerate(directions, 1):
            dest_name = self.locations[location.connections[direction]].name
            print(f"{i}. Go {direction} to {dest_name}")
        
        print(f"{len(directions) + 1}. Stay here")
        
        choice = input(f"\n{Colors.WARNING}Choose destination: {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(directions):
                direction = directions[choice_idx]
                self.player.location = location.connections[direction]
                
                new_location = self.locations[self.player.location]
                if new_location.enemies and random.random() < 0.4:
                    enemy_type = random.choice(new_location.enemies)
                    self.start_combat(enemy_type)
        except (ValueError, IndexError):
            pass
    
    def search_area(self):
        location = self.locations[self.player.location]
        
        print(f"\n{Colors.CYAN}Searching the area...{Colors.ENDC}")
        time.sleep(1)
        
        found_something = False
        
        if location.items and random.random() < 0.3:
            item = random.choice(location.items)
            self.player.add_item(item)
            print(f"{Colors.GREEN}You found: {item}!{Colors.ENDC}")
            found_something = True
        
        if location.enemies and random.random() < 0.5:
            enemy_type = random.choice(location.enemies)
            print(f"{Colors.FAIL}You encountered a {self.enemy_templates[enemy_type]['name']}!{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to engage in combat...{Colors.ENDC}")
            self.start_combat(enemy_type)
            return
        
        if not found_something:
            print(f"{Colors.CYAN}You didn't find anything of interest.{Colors.ENDC}")
        
        input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def talk_to_npc(self):
        location = self.locations[self.player.location]
        
        print(f"\n{Colors.BOLD}NPCs in this area:{Colors.ENDC}")
        for i, npc_id in enumerate(location.npcs, 1):
            npc = self.npcs[npc_id]
            print(f"{i}. {npc['name']}")
        
        print(f"{len(location.npcs) + 1}. Back")
        
        choice = input(f"\n{Colors.WARNING}Who would you like to talk to? {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(location.npcs):
                npc_id = location.npcs[choice_idx]
                self.dialogue_with_npc(npc_id)
        except (ValueError, IndexError):
            pass
    
    def dialogue_with_npc(self, npc_id: str):
        npc = self.npcs[npc_id]
        
        self.clear_screen()
        self.print_header(f"Talking to {npc['name']}")
        
        for line in npc['dialogue']:
            print(f"{Colors.CYAN}{npc['name']}: {line}{Colors.ENDC}")
            time.sleep(1)
        
        if 'quest' in npc and npc['quest'] not in self.player.active_quests and npc['quest'] not in self.player.quests_completed:
            quest = self.quests[npc['quest']]
            print(f"\n{Colors.GREEN}New Quest: {quest.name}!{Colors.ENDC}")
            print(f"{Colors.CYAN}{quest.description}{Colors.ENDC}")
            self.player.active_quests.append(npc['quest'])
        
        if 'reward' in npc and f"{npc_id}_rewarded" not in self.player.flags:
            reward = npc['reward']
            if 'item' in reward:
                self.player.add_item(reward['item'])
                print(f"\n{Colors.GREEN}Received: {reward['item']}!{Colors.ENDC}")
            if 'gold' in reward:
                self.player.gold += reward['gold']
                print(f"{Colors.GREEN}Received: {reward['gold']} gold!{Colors.ENDC}")
            if 'skill' in reward:
                if reward['skill'] not in self.player.skills:
                    self.player.skills.append(reward['skill'])
                    print(f"{Colors.GREEN}Learned new skill: {reward['skill']}!{Colors.ENDC}")
            self.player.flags[f"{npc_id}_rewarded"] = True
        
        input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def visit_shop(self):
        location = self.locations[self.player.location]
        shop_id = location.shops[0]
        shop = self.shops[shop_id]
        
        while True:
            self.clear_screen()
            self.print_header(shop['name'])
            print(f"{Colors.GREEN}Your Gold: {self.player.gold}{Colors.ENDC}\n")
            
            print(f"{Colors.BOLD}Items for sale:{Colors.ENDC}")
            items = list(shop['inventory'].items())
            for i, (item, price) in enumerate(items, 1):
                print(f"{i}. {item} - {price} gold")
            
            print(f"\n{len(items) + 1}. Leave shop")
            
            choice = input(f"\n{Colors.WARNING}What would you like to buy? {Colors.ENDC}")
            
            try:
                choice_idx = int(choice) - 1
                if choice_idx == len(items):
                    break
                elif 0 <= choice_idx < len(items):
                    item, price = items[choice_idx]
                    if self.player.gold >= price:
                        self.player.gold -= price
                        self.player.add_item(item)
                        print(f"{Colors.GREEN}You bought {item}!{Colors.ENDC}")
                    else:
                        print(f"{Colors.FAIL}Not enough gold!{Colors.ENDC}")
                    input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
            except (ValueError, IndexError):
                pass
    
    def rest(self):
        print(f"\n{Colors.CYAN}You rest peacefully...{Colors.ENDC}")
        time.sleep(2)
        self.player.hp = self.player.max_hp
        self.player.mp = self.player.max_mp
        print(f"{Colors.GREEN}HP and MP fully restored!{Colors.ENDC}")
        input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def show_inventory(self):
        self.clear_screen()
        self.print_header("INVENTORY")
        
        print(f"{Colors.BOLD}Equipment:{Colors.ENDC}")
        for slot, item in self.player.equipment.items():
            if item:
                print(f"  {slot.capitalize()}: {item}")
            else:
                print(f"  {slot.capitalize()}: None")
        
        print(f"\n{Colors.BOLD}Items:{Colors.ENDC}")
        if self.player.inventory:
            for item, quantity in self.player.inventory.items():
                print(f"  {item} x{quantity}")
        else:
            print("  Empty")
        
        print(f"\n{Colors.BOLD}Skills:{Colors.ENDC}")
        for skill in self.player.skills:
            print(f"  - {skill}")
        
        print("\n1. Use item")
        print("2. Equip item")
        print("3. Back")
        
        choice = input(f"\n{Colors.WARNING}Choose action: {Colors.ENDC}")
        
        if choice == "1":
            self.use_item()
        elif choice == "2":
            self.equip_item()
    
    def use_item(self):
        consumables = {k: v for k, v in self.player.inventory.items() 
                      if k in self.items and self.items[k]["type"] == "consumable"}
        
        if not consumables:
            print(f"{Colors.FAIL}No usable items!{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}Usable items:{Colors.ENDC}")
        items = list(consumables.keys())
        for i, item in enumerate(items, 1):
            print(f"{i}. {item} x{consumables[item]}")
        
        choice = input(f"\n{Colors.WARNING}Which item to use? {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(items):
                item = items[choice_idx]
                item_data = self.items[item]
                
                if item_data["effect"] == "heal":
                    healed = self.player.heal(item_data["value"])
                    print(f"{Colors.GREEN}Restored {healed} HP!{Colors.ENDC}")
                elif item_data["effect"] == "mana":
                    restored = self.player.restore_mp(item_data["value"])
                    print(f"{Colors.GREEN}Restored {restored} MP!{Colors.ENDC}")
                elif item_data["effect"] == "full_heal":
                    self.player.hp = self.player.max_hp
                    self.player.mp = self.player.max_mp
                    print(f"{Colors.GREEN}Fully restored HP and MP!{Colors.ENDC}")
                
                self.player.remove_item(item)
                input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
        except (ValueError, IndexError):
            pass
    
    def equip_item(self):
        equipment = {k: v for k, v in self.player.inventory.items() 
                    if k in self.items and self.items[k]["type"] in ["weapon", "armor", "accessory"]}
        
        if not equipment:
            print(f"{Colors.FAIL}No equipment to equip!{Colors.ENDC}")
            input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}Equipment:{Colors.ENDC}")
        items = list(equipment.keys())
        for i, item in enumerate(items, 1):
            item_type = self.items[item]["type"]
            print(f"{i}. {item} ({item_type})")
        
        choice = input(f"\n{Colors.WARNING}Which item to equip? {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(items):
                item = items[choice_idx]
                item_type = self.items[item]["type"]
                
                slot = item_type if item_type != "accessory" else "accessory"
                self.player.equip_item(item, slot)
                
                if item_type == "weapon":
                    self.player.attack += self.items[item].get("attack", 0)
                elif item_type == "armor":
                    self.player.defense += self.items[item].get("defense", 0)
                
                print(f"{Colors.GREEN}Equipped {item}!{Colors.ENDC}")
                input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
        except (ValueError, IndexError):
            pass
    
    def show_quest_log(self):
        self.clear_screen()
        self.print_header("QUEST LOG")
        
        if not self.player.active_quests:
            print(f"{Colors.CYAN}No active quests.{Colors.ENDC}")
        else:
            print(f"{Colors.BOLD}Active Quests:{Colors.ENDC}")
            for quest_id in self.player.active_quests:
                quest = self.quests[quest_id]
                print(f"\n{Colors.GREEN}{quest.name}{Colors.ENDC}")
                print(f"{Colors.CYAN}{quest.description}{Colors.ENDC}")
                print(f"{Colors.BOLD}Objectives:{Colors.ENDC}")
                for obj, target in quest.objectives.items():
                    progress = quest.progress.get(obj, 0)
                    print(f"  - {obj}: {progress}/{target}")
        
        if self.player.quests_completed:
            print(f"\n{Colors.BOLD}Completed Quests:{Colors.ENDC}")
            for quest_id in self.player.quests_completed:
                quest = self.quests[quest_id]
                print(f"  ✓ {quest.name}")
        
        input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def start_combat(self, enemy_type: str):
        template = self.enemy_templates[enemy_type]
        self.current_enemy = Enemy(
            template["name"],
            template["hp"],
            template["attack"],
            template["defense"],
            template["exp"],
            template["gold"],
            template["drops"]
        )
        self.state = GameState.COMBAT
        self.combat_loop()
    
    def combat_loop(self):
        while self.current_enemy and self.current_enemy.is_alive() and self.player.hp > 0:
            self.clear_screen()
            self.print_header("COMBAT")
            
            print(f"{Colors.FAIL}{self.current_enemy.name} appeared!{Colors.ENDC}\n")
            print(f"{Colors.BOLD}Enemy HP: {self.current_enemy.hp}/{self.current_enemy.max_hp}{Colors.ENDC}")
            print(f"{Colors.BOLD}Your HP: {self.player.hp}/{self.player.max_hp} | MP: {self.player.mp}/{self.player.max_mp}{Colors.ENDC}\n")
            
            print("1. Attack")
            print("2. Skills")
            print("3. Items")
            print("4. Run")
            
            choice = input(f"\n{Colors.WARNING}Choose your action: {Colors.ENDC}")
            
            if choice == "1":
                self.player_attack()
            elif choice == "2":
                self.use_skill()
            elif choice == "3":
                self.use_item_combat()
            elif choice == "4":
                if random.random() < 0.5:
                    print(f"{Colors.GREEN}You managed to escape!{Colors.ENDC}")
                    input(f"{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
                    self.state = GameState.EXPLORING
                    return
                else:
                    print(f"{Colors.FAIL}Couldn't escape!{Colors.ENDC}")
                    time.sleep(1)
            
            if self.current_enemy and self.current_enemy.is_alive():
                self.enemy_attack()
        
        if self.player.hp <= 0:
            self.game_over()
        elif self.current_enemy and not self.current_enemy.is_alive():
            self.victory()
    
    def player_attack(self):
        damage = self.current_enemy.take_damage(self.player.attack + random.randint(-5, 5))
        print(f"{Colors.GREEN}You dealt {damage} damage!{Colors.ENDC}")
        time.sleep(1)
    
    def use_skill(self):
        print(f"\n{Colors.BOLD}Skills:{Colors.ENDC}")
        for i, skill in enumerate(self.player.skills, 1):
            print(f"{i}. {skill}")
        
        choice = input(f"\n{Colors.WARNING}Choose skill: {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(self.player.skills):
                skill = self.player.skills[choice_idx]
                self.use_skill_effect(skill)
        except (ValueError, IndexError):
            pass
    
    def use_skill_effect(self, skill: str):
        if skill == "Slash":
            if self.player.mp >= 5:
                self.player.mp -= 5
                damage = self.current_enemy.take_damage(self.player.attack * 1.5 + random.randint(-3, 3))
                print(f"{Colors.GREEN}Slash dealt {damage} damage!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Heal":
            if self.player.mp >= 10:
                self.player.mp -= 10
                healed = self.player.heal(30)
                print(f"{Colors.GREEN}Healed {healed} HP!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Fire Bolt":
            if self.player.mp >= 15:
                self.player.mp -= 15
                damage = self.current_enemy.take_damage(self.player.magic * 2 + random.randint(-5, 5))
                print(f"{Colors.GREEN}Fire Bolt dealt {damage} damage!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Power Strike":
            if self.player.mp >= 20:
                self.player.mp -= 20
                damage = self.current_enemy.take_damage(self.player.attack * 2 + random.randint(-5, 5))
                print(f"{Colors.GREEN}Power Strike dealt {damage} damage!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Lightning":
            if self.player.mp >= 25:
                self.player.mp -= 25
                damage = self.current_enemy.take_damage(self.player.magic * 3 + random.randint(-7, 7))
                print(f"{Colors.GREEN}Lightning dealt {damage} damage!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Divine Shield":
            if self.player.mp >= 30:
                self.player.mp -= 30
                self.player.defense += 20
                print(f"{Colors.GREEN}Defense increased by 20 for this battle!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        elif skill == "Holy Light":
            if self.player.mp >= 40:
                self.player.mp -= 40
                damage = self.current_enemy.take_damage(self.player.magic * 4 + random.randint(-10, 10))
                healed = self.player.heal(20)
                print(f"{Colors.GREEN}Holy Light dealt {damage} damage and healed {healed} HP!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Not enough MP!{Colors.ENDC}")
        
        time.sleep(1.5)
    
    def use_item_combat(self):
        consumables = {k: v for k, v in self.player.inventory.items() 
                      if k in self.items and self.items[k]["type"] == "consumable"}
        
        if not consumables:
            print(f"{Colors.FAIL}No usable items!{Colors.ENDC}")
            time.sleep(1)
            return
        
        print(f"\n{Colors.BOLD}Items:{Colors.ENDC}")
        items = list(consumables.keys())
        for i, item in enumerate(items, 1):
            print(f"{i}. {item} x{consumables[item]}")
        
        choice = input(f"\n{Colors.WARNING}Which item? {Colors.ENDC}")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(items):
                item = items[choice_idx]
                item_data = self.items[item]
                
                if item_data["effect"] == "heal":
                    healed = self.player.heal(item_data["value"])
                    print(f"{Colors.GREEN}Restored {healed} HP!{Colors.ENDC}")
                elif item_data["effect"] == "mana":
                    restored = self.player.restore_mp(item_data["value"])
                    print(f"{Colors.GREEN}Restored {restored} MP!{Colors.ENDC}")
                
                self.player.remove_item(item)
                time.sleep(1)
        except (ValueError, IndexError):
            pass
    
    def enemy_attack(self):
        damage = self.player.take_damage(self.current_enemy.attack + random.randint(-3, 3))
        print(f"{Colors.FAIL}{self.current_enemy.name} dealt {damage} damage!{Colors.ENDC}")
        time.sleep(1.5)
    
    def victory(self):
        print(f"\n{Colors.GREEN}Victory!{Colors.ENDC}")
        print(f"{Colors.CYAN}Gained {self.current_enemy.exp} EXP!{Colors.ENDC}")
        print(f"{Colors.GREEN}Gained {self.current_enemy.gold} gold!{Colors.ENDC}")
        
        self.player.gold += self.current_enemy.gold
        exp_messages = self.player.gain_exp(self.current_enemy.exp)
        for msg in exp_messages[1:]:
            print(msg)
        
        for item, drop_chance in self.current_enemy.drops.items():
            if random.random() < drop_chance:
                self.player.add_item(item)
                print(f"{Colors.GREEN}Found: {item}!{Colors.ENDC}")
        
        if self.current_enemy.name == "Wild Wolf":
            for quest_id in self.player.active_quests:
                if quest_id == "wolf_hunt":
                    quest = self.quests[quest_id]
                    quest.update_progress("kill_wolf", 1)
                    if quest.is_complete():
                        self.complete_quest(quest_id)
        
        if self.current_enemy.name == "Shadow Lord Malachar":
            for quest_id in self.player.active_quests:
                if quest_id == "main_quest":
                    quest = self.quests[quest_id]
                    quest.update_progress("defeat_shadow_lord", 1)
                    if quest.is_complete():
                        self.complete_quest(quest_id)
                        self.ending_sequence()
        
        self.current_enemy = None
        self.state = GameState.EXPLORING
        input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def complete_quest(self, quest_id: str):
        quest = self.quests[quest_id]
        print(f"\n{Colors.GREEN}Quest Completed: {quest.name}!{Colors.ENDC}")
        
        rewards = quest.rewards
        if "exp" in rewards:
            exp_messages = self.player.gain_exp(rewards["exp"])
            for msg in exp_messages:
                print(msg)
        if "gold" in rewards:
            self.player.gold += rewards["gold"]
            print(f"{Colors.GREEN}Received {rewards['gold']} gold!{Colors.ENDC}")
        if "item" in rewards:
            self.player.add_item(rewards["item"])
            print(f"{Colors.GREEN}Received {rewards['item']}!{Colors.ENDC}")
        if "skill" in rewards:
            if rewards["skill"] not in self.player.skills:
                self.player.skills.append(rewards["skill"])
                print(f"{Colors.GREEN}Learned new skill: {rewards['skill']}!{Colors.ENDC}")
        
        self.player.active_quests.remove(quest_id)
        self.player.quests_completed.append(quest_id)
    
    def game_over(self):
        self.clear_screen()
        print(f"{Colors.FAIL}{Colors.BOLD}")
        print("""
         ██████╗  █████╗ ███╗   ███╗███████╗     ██████╗ ██╗   ██╗███████╗██████╗ 
        ██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔═══██╗██║   ██║██╔════╝██╔══██╗
        ██║  ███╗███████║██╔████╔██║█████╗      ██║   ██║██║   ██║█████╗  ██████╔╝
        ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
        ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║
         ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝     ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝
        """)
        print(f"{Colors.ENDC}")
        print(f"{Colors.CYAN}You have fallen in battle...{Colors.ENDC}")
        print(f"{Colors.CYAN}The Shadow Lord's darkness continues to spread...{Colors.ENDC}")
        
        input(f"\n{Colors.WARNING}Press Enter to return to main menu...{Colors.ENDC}")
        self.__init__()
        self.main_menu()
    
    def ending_sequence(self):
        self.clear_screen()
        print(f"{Colors.GREEN}{Colors.BOLD}")
        print("""
        ██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗██╗
        ██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝██║
        ██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝ ██║
        ╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝  ╚═╝
         ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║   ██╗
          ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝
        """)
        print(f"{Colors.ENDC}")
        
        print(f"{Colors.CYAN}Congratulations, {self.player.name}!{Colors.ENDC}")
        print(f"{Colors.CYAN}You have defeated the Shadow Lord Malachar and saved Lumenhaven!{Colors.ENDC}")
        print(f"{Colors.CYAN}The darkness retreats, and peace returns to the land.{Colors.ENDC}")
        print(f"{Colors.CYAN}Your heroic deeds will be remembered for generations to come!{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Final Statistics:{Colors.ENDC}")
        print(f"Level: {self.player.level}")
        print(f"Quests Completed: {len(self.player.quests_completed)}")
        print(f"Gold Collected: {self.player.gold}")
        
        input(f"\n{Colors.WARNING}Press Enter to return to main menu...{Colors.ENDC}")
        self.__init__()
        self.main_menu()
    
    def game_loop(self):
        while True:
            if self.state == GameState.EXPLORING:
                self.explore_location()
            elif self.state == GameState.COMBAT:
                self.combat_loop()
            elif self.state == GameState.GAME_OVER:
                self.game_over()

def main():
    game = Game()
    game.main_menu()

if __name__ == "__main__":
    main()