#!/usr/bin/env python3
import os
import sys
import time
import random
import json
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from datetime import datetime, timedelta

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
    DIM = '\033[2m'

class GameState(Enum):
    MENU = "menu"
    EXPLORING = "exploring"
    DIALOGUE = "dialogue"
    INVESTIGATING = "investigating"
    PUZZLE = "puzzle"
    TERMINAL = "terminal"
    ENDING = "ending"

class Player:
    def __init__(self, name: str = "Commander"):
        self.name = name
        self.location = "cryobay"
        self.inventory = {
            "Security Keycard - Level 1": 1,
            "Personal Datapad": 1,
            "Emergency Rations": 3,
            "Flashlight": 1
        }
        self.evidence = {}
        self.relationships = {}
        self.knowledge = set()
        self.actions_taken = []
        self.current_objective = "Investigate the distress signal"
        self.sanity = 100
        self.health = 100
        self.oxygen = 100
        self.time_elapsed = 0
        self.access_level = 1
        self.skills = {
            "hacking": 1,
            "engineering": 1,
            "medicine": 1,
            "investigation": 1,
            "combat": 1
        }
        self.flags = {}

class Location:
    def __init__(self, id: str, name: str, description: str, 
                 connections: Dict[str, str], 
                 items: List[str] = None,
                 npcs: List[str] = None,
                 terminals: List[str] = None,
                 requires_access: int = 0,
                 requires_item: str = None,
                 oxygen_drain: int = 0):
        self.id = id
        self.name = name
        self.description = description
        self.connections = connections
        self.items = items or []
        self.npcs = npcs or []
        self.terminals = terminals or []
        self.requires_access = requires_access
        self.requires_item = requires_item
        self.oxygen_drain = oxygen_drain
        self.investigated = False
        self.events = []

class NPC:
    def __init__(self, id: str, name: str, role: str, 
                 location: str, alive: bool = True,
                 suspicious: int = 0):
        self.id = id
        self.name = name
        self.role = role
        self.location = location
        self.alive = alive
        self.suspicious = suspicious
        self.talked_topics = set()
        self.trust = 50
        self.knows = []
        self.inventory = {}

class EchoesOfEuropa:
    def __init__(self):
        self.player = None
        self.state = GameState.MENU
        self.locations = {}
        self.npcs = {}
        self.items = {}
        self.evidence_pieces = {}
        self.terminals = {}
        self.current_act = 1
        self.killer = None
        self.ending = None
        self.save_file = "echoes_save.json"
        self.init_game_data()
        
    def init_game_data(self):
        self.init_locations()
        self.init_npcs()
        self.init_items()
        self.init_evidence()
        self.init_terminals()
        self.select_killer()
    
    def init_locations(self):
        self.locations = {
            "cryobay": Location(
                "cryobay",
                "Cryogenic Bay",
                "Rows of cryogenic pods line the walls, most still occupied by sleeping crew members. "
                "Your pod stands open, frost still clinging to its edges. Emergency lights cast eerie "
                "shadows across the room. A terminal blinks urgently nearby.",
                {"north": "corridor_a", "east": "medbay"},
                items=["Cryopod Manifest", "Emergency Stimulant"],
                terminals=["cryo_terminal"],
                oxygen_drain=0
            ),
            "corridor_a": Location(
                "corridor_a",
                "Corridor A - Main Deck",
                "The main corridor stretches before you, its metallic walls reflecting the dim emergency "
                "lighting. Scratch marks run along one wall, and there's a dark stain on the floor that "
                "looks disturbingly like dried blood.",
                {"south": "cryobay", "north": "bridge", "east": "mess_hall", "west": "quarters_deck"},
                items=["Broken Communicator"],
                oxygen_drain=0
            ),
            "bridge": Location(
                "bridge",
                "Command Bridge",
                "The nerve center of the station. Multiple screens flicker with error messages and "
                "warning signals. The captain's chair sits empty, and the main viewscreen shows Europa's "
                "icy surface below. Several consoles are damaged, sparking occasionally.",
                {"south": "corridor_a", "east": "captain_quarters"},
                npcs=["lt_chen", "navigator_jones"],
                terminals=["bridge_main", "nav_console"],
                requires_access=2,
                oxygen_drain=0
            ),
            "captain_quarters": Location(
                "captain_quarters",
                "Captain's Quarters",
                "A spacious cabin with personal effects scattered about. The bed is unmade, and papers "
                "are strewn across the desk. A personal terminal sits powered down, and there's a locked "
                "safe in the wall.",
                {"west": "bridge"},
                items=["Captain's Log", "Level 3 Keycard"],
                terminals=["captain_terminal"],
                requires_access=3,
                oxygen_drain=0
            ),
            "medbay": Location(
                "medbay",
                "Medical Bay",
                "Sterile white walls are splattered with blood. Medical equipment is scattered about, "
                "and several bio-beds show signs of recent use. A quarantine field flickers around one "
                "section of the room.",
                {"west": "cryobay", "north": "mess_hall", "east": "lab"},
                npcs=["dr_vasquez"],
                items=["Medical Scanner", "Sedative", "Blood Sample A"],
                terminals=["med_terminal"],
                oxygen_drain=0
            ),
            "lab": Location(
                "lab",
                "Research Laboratory",
                "A state-of-the-art research facility filled with mysterious equipment. Specimen containers "
                "line one wall, some broken, their contents missing. A strange, pulsing organic mass is "
                "contained behind reinforced glass.",
                {"west": "medbay", "north": "specimen_storage"},
                npcs=["dr_petrov"],
                items=["Research Notes", "Alien Sample", "Lab Keycard"],
                terminals=["research_terminal"],
                requires_access=2,
                oxygen_drain=0
            ),
            "specimen_storage": Location(
                "specimen_storage",
                "Specimen Storage",
                "A cold, dark room filled with preservation tanks. Most are empty or broken, but one "
                "contains something that shouldn't exist - a creature that seems to shift and change "
                "as you watch it. The temperature here is well below freezing.",
                {"south": "lab"},
                items=["Classified Document", "Cryo-gun"],
                terminals=["containment_terminal"],
                requires_access=3,
                oxygen_drain=5
            ),
            "mess_hall": Location(
                "mess_hall",
                "Mess Hall",
                "The communal dining area is in disarray. Tables are overturned, and food is scattered "
                "across the floor. The kitchen area shows signs of a struggle, with knives missing from "
                "their blocks.",
                {"west": "corridor_a", "south": "medbay", "east": "rec_room"},
                npcs=["chef_rodriguez"],
                items=["Kitchen Knife", "Crew Roster"],
                oxygen_drain=0
            ),
            "rec_room": Location(
                "rec_room",
                "Recreation Room",
                "What should be a place of relaxation is now unsettling. The holographic projector "
                "flickers with corrupted images, and someone has written 'THEY'RE AMONG US' on the wall "
                "in what appears to be blood.",
                {"west": "mess_hall", "north": "observatory"},
                items=["Playing Cards", "Personal Journal"],
                terminals=["entertainment_console"],
                oxygen_drain=0
            ),
            "observatory": Location(
                "observatory",
                "Observation Deck",
                "A large dome provides a spectacular view of Europa and Jupiter beyond. The sight would "
                "be breathtaking if not for the body floating outside, pressed against the glass, frozen "
                "in a silent scream.",
                {"south": "rec_room"},
                npcs=["scientist_wong"],
                items=["Telescope Data", "Victim's Badge"],
                oxygen_drain=0
            ),
            "quarters_deck": Location(
                "quarters_deck",
                "Crew Quarters Deck",
                "A hallway lined with personal quarters. Several doors are sealed, others stand ominously "
                "open. You can hear something moving in the ventilation system above.",
                {"east": "corridor_a", "north": "room_201", "south": "room_104", "west": "room_305"},
                oxygen_drain=0
            ),
            "room_201": Location(
                "room_201",
                "Room 201 - Chen's Quarters",
                "A tidy room with military precision. Everything is in its place, except for a hidden "
                "compartment behind the dresser that's been hastily closed.",
                {"south": "quarters_deck"},
                items=["Military Orders", "Hidden Weapon"],
                oxygen_drain=0
            ),
            "room_104": Location(
                "room_104",
                "Room 104 - Vasquez's Quarters",
                "Medical texts and personal items fill this space. There's a strange smell in the air, "
                "and several vials of unknown substances are hidden in a drawer.",
                {"north": "quarters_deck"},
                items=["Medical Research", "Suspicious Vial"],
                oxygen_drain=0
            ),
            "room_305": Location(
                "room_305",
                "Room 305 - Empty Quarter",
                "This room appears unoccupied, but someone has been here recently. Fresh scratches "
                "mark the walls, and there's a makeshift bed in the corner.",
                {"east": "quarters_deck"},
                items=["Torn Fabric", "Strange Drawing"],
                oxygen_drain=0
            ),
            "engineering": Location(
                "engineering",
                "Engineering Bay",
                "The heart of the station's power systems. Massive reactors hum with energy, but several "
                "systems show critical failures. Coolant leaks create puddles of glowing liquid on the floor.",
                {"north": "corridor_b", "west": "reactor_core"},
                npcs=["engineer_kowalski"],
                items=["Repair Kit", "System Diagnostic", "Level 2 Keycard"],
                terminals=["engineering_terminal"],
                requires_access=1,
                oxygen_drain=0
            ),
            "reactor_core": Location(
                "reactor_core",
                "Reactor Core",
                "The station's main power source. Radiation levels are dangerously high, and the "
                "containment field is failing. You'll need protective gear to stay here long.",
                {"east": "engineering"},
                items=["Reactor Codes", "Radiation Badge"],
                terminals=["reactor_terminal"],
                requires_access=3,
                requires_item="Radiation Suit",
                oxygen_drain=10
            ),
            "corridor_b": Location(
                "corridor_b",
                "Corridor B - Lower Deck",
                "A darker, less maintained corridor. Pipes run along the ceiling, occasionally venting "
                "steam. Something has torn through the ventilation grates here.",
                {"south": "engineering", "north": "cargo_bay", "east": "maintenance"},
                oxygen_drain=2
            ),
            "cargo_bay": Location(
                "cargo_bay",
                "Cargo Bay",
                "Massive storage containers fill this cavernous space. Some are open, their contents "
                "spilled across the floor. In one corner, you notice a makeshift barricade and signs "
                "of a last stand.",
                {"south": "corridor_b", "west": "airlock"},
                npcs=["cargo_tech_miller"],
                items=["Cargo Manifest", "Crowbar", "Emergency Beacon"],
                oxygen_drain=0
            ),
            "airlock": Location(
                "airlock",
                "Airlock Chamber",
                "The exit to space. The outer door shows signs of forced entry from the outside. "
                "Spacesuits hang on the walls, but several are missing or damaged.",
                {"east": "cargo_bay"},
                items=["Damaged Spacesuit", "EVA Log"],
                terminals=["airlock_terminal"],
                requires_access=2,
                oxygen_drain=0
            ),
            "maintenance": Location(
                "maintenance",
                "Maintenance Tunnels",
                "Cramped service tunnels that run throughout the station. Perfect for moving unseen. "
                "You find traces of someone - or something - living here.",
                {"west": "corridor_b", "up": "corridor_a", "down": "sublevel"},
                items=["Maintenance Access Card", "Bloodstained Tool"],
                oxygen_drain=3
            ),
            "sublevel": Location(
                "sublevel",
                "Sublevel - Restricted Area",
                "A hidden level not on any official map. Here you find evidence of secret experiments "
                "and communications equipment connected to unknown recipients.",
                {"up": "maintenance"},
                items=["Conspiracy Evidence", "Alien Artifact", "Truth Serum"],
                terminals=["secret_terminal"],
                requires_access=4,
                oxygen_drain=5
            ),
            "hydroponics": Location(
                "hydroponics",
                "Hydroponics Bay",
                "The station's food production facility. Plants grow in orderly rows, but some have "
                "mutated into unrecognizable forms. The air is thick with pollen and an unknown substance.",
                {"south": "corridor_a"},
                npcs=["botanist_green"],
                items=["Mutated Plant Sample", "Growth Hormones"],
                terminals=["hydro_terminal"],
                oxygen_drain=0
            ),
            "comms_center": Location(
                "comms_center",
                "Communications Center",
                "Banks of communication equipment fill the room. Most are offline, but one terminal "
                "shows an active connection to Earth - with the last message sent just hours ago.",
                {"west": "bridge"},
                items=["Communication Log", "Encrypted Message"],
                terminals=["comms_terminal"],
                requires_access=2,
                oxygen_drain=0
            )
        }
    
    def init_npcs(self):
        self.npcs = {
            "lt_chen": NPC("lt_chen", "Lieutenant Sarah Chen", "Security Chief", "bridge", True, 30),
            "dr_vasquez": NPC("dr_vasquez", "Dr. Maria Vasquez", "Chief Medical Officer", "medbay", True, 40),
            "dr_petrov": NPC("dr_petrov", "Dr. Alexei Petrov", "Lead Researcher", "lab", True, 60),
            "navigator_jones": NPC("navigator_jones", "Navigator Tom Jones", "Navigation Officer", "bridge", True, 20),
            "engineer_kowalski": NPC("engineer_kowalski", "Chief Kowalski", "Chief Engineer", "engineering", True, 35),
            "chef_rodriguez": NPC("chef_rodriguez", "Chef Rodriguez", "Head Chef", "mess_hall", True, 15),
            "scientist_wong": NPC("scientist_wong", "Dr. Lisa Wong", "Xenobiologist", "observatory", True, 45),
            "cargo_tech_miller": NPC("cargo_tech_miller", "Jake Miller", "Cargo Technician", "cargo_bay", True, 25),
            "botanist_green": NPC("botanist_green", "Emma Green", "Botanist", "hydroponics", True, 50),
            "captain_reeves": NPC("captain_reeves", "Captain Reeves", "Station Commander", "unknown", False, 0)
        }
        
        for npc in self.npcs.values():
            npc.knows = self.generate_npc_knowledge(npc.id)
    
    def generate_npc_knowledge(self, npc_id: str) -> List[str]:
        knowledge_pool = {
            "lt_chen": [
                "security_breach",
                "missing_weapons",
                "captain_argument",
                "locked_sections"
            ],
            "dr_vasquez": [
                "crew_medical_records",
                "strange_symptoms",
                "quarantine_breach",
                "missing_medicines"
            ],
            "dr_petrov": [
                "alien_discovery",
                "experiment_failure",
                "corporate_pressure",
                "specimen_escape"
            ],
            "navigator_jones": [
                "course_deviation",
                "hidden_signals",
                "nav_sabotage",
                "escape_pods"
            ],
            "engineer_kowalski": [
                "system_failures",
                "sabotage_evidence",
                "maintenance_access",
                "power_fluctuations"
            ],
            "chef_rodriguez": [
                "crew_tensions",
                "food_poisoning",
                "missing_supplies",
                "late_night_visitors"
            ],
            "scientist_wong": [
                "europa_anomaly",
                "alien_signals",
                "research_coverup",
                "observatory_incident"
            ],
            "cargo_tech_miller": [
                "smuggled_cargo",
                "unauthorized_shipments",
                "cargo_manifests",
                "hidden_compartments"
            ],
            "botanist_green": [
                "plant_mutations",
                "contamination_source",
                "hydroponic_sabotage",
                "growth_experiments"
            ]
        }
        return knowledge_pool.get(npc_id, [])
    
    def init_items(self):
        self.items = {
            "Security Keycard - Level 1": {"type": "key", "description": "Basic security access card"},
            "Level 2 Keycard": {"type": "key", "description": "Advanced security clearance"},
            "Level 3 Keycard": {"type": "key", "description": "Command level clearance"},
            "Personal Datapad": {"type": "tool", "description": "Your personal data device"},
            "Emergency Rations": {"type": "consumable", "description": "Sealed food packets"},
            "Flashlight": {"type": "tool", "description": "High-powered LED flashlight"},
            "Medical Scanner": {"type": "tool", "description": "Portable medical diagnostic device"},
            "Sedative": {"type": "consumable", "description": "Fast-acting tranquilizer"},
            "Blood Sample A": {"type": "evidence", "description": "Unidentified blood sample"},
            "Captain's Log": {"type": "evidence", "description": "The captain's personal recordings"},
            "Research Notes": {"type": "evidence", "description": "Dr. Petrov's research findings"},
            "Alien Sample": {"type": "evidence", "description": "Organic material of unknown origin"},
            "Lab Keycard": {"type": "key", "description": "Access to restricted lab areas"},
            "Classified Document": {"type": "evidence", "description": "Top secret corporate orders"},
            "Cryo-gun": {"type": "weapon", "description": "Experimental freezing weapon"},
            "Kitchen Knife": {"type": "weapon", "description": "Sharp culinary blade"},
            "Crew Roster": {"type": "evidence", "description": "Complete crew manifest"},
            "Playing Cards": {"type": "misc", "description": "A deck of cards with notes written on them"},
            "Personal Journal": {"type": "evidence", "description": "Someone's private thoughts"},
            "Telescope Data": {"type": "evidence", "description": "Astronomical observations of Europa"},
            "Victim's Badge": {"type": "evidence", "description": "ID badge from the body outside"},
            "Military Orders": {"type": "evidence", "description": "Classified military directives"},
            "Hidden Weapon": {"type": "weapon", "description": "Concealed military-grade pistol"},
            "Medical Research": {"type": "evidence", "description": "Experimental treatment notes"},
            "Suspicious Vial": {"type": "evidence", "description": "Unknown chemical compound"},
            "Torn Fabric": {"type": "evidence", "description": "Piece of unusual material"},
            "Strange Drawing": {"type": "evidence", "description": "Cryptic symbols and diagrams"},
            "Repair Kit": {"type": "tool", "description": "Engineering repair tools"},
            "System Diagnostic": {"type": "evidence", "description": "Station system analysis"},
            "Reactor Codes": {"type": "key", "description": "Emergency reactor shutdown codes"},
            "Radiation Badge": {"type": "tool", "description": "Radiation exposure monitor"},
            "Radiation Suit": {"type": "equipment", "description": "Protective anti-radiation gear"},
            "Cargo Manifest": {"type": "evidence", "description": "Shipping records with discrepancies"},
            "Crowbar": {"type": "tool", "description": "Heavy metal prying tool"},
            "Emergency Beacon": {"type": "tool", "description": "Distress signal transmitter"},
            "Damaged Spacesuit": {"type": "evidence", "description": "EVA suit with suspicious damage"},
            "EVA Log": {"type": "evidence", "description": "External activity records"},
            "Maintenance Access Card": {"type": "key", "description": "Universal maintenance access"},
            "Bloodstained Tool": {"type": "evidence", "description": "Wrench covered in dried blood"},
            "Conspiracy Evidence": {"type": "evidence", "description": "Proof of a cover-up"},
            "Alien Artifact": {"type": "evidence", "description": "Object of non-human origin"},
            "Truth Serum": {"type": "consumable", "description": "Pharmaceutical interrogation aid"},
            "Mutated Plant Sample": {"type": "evidence", "description": "Genetically altered flora"},
            "Growth Hormones": {"type": "evidence", "description": "Experimental growth accelerants"},
            "Communication Log": {"type": "evidence", "description": "Record of all station transmissions"},
            "Encrypted Message": {"type": "evidence", "description": "Coded transmission to Earth"},
            "Broken Communicator": {"type": "evidence", "description": "Sabotaged communication device"},
            "Cryopod Manifest": {"type": "evidence", "description": "List of crew in cryosleep"},
            "Emergency Stimulant": {"type": "consumable", "description": "Adrenaline auto-injector"}
        }
    
    def init_evidence(self):
        self.evidence_pieces = {
            "security_breach": {
                "name": "Security System Breach",
                "description": "Someone disabled the security systems 3 hours before the incident",
                "importance": "high",
                "suspects": ["lt_chen", "engineer_kowalski"]
            },
            "alien_infection": {
                "name": "Alien Pathogen",
                "description": "Crew members showing signs of alien infection",
                "importance": "critical",
                "suspects": ["dr_petrov", "dr_vasquez", "botanist_green"]
            },
            "corporate_conspiracy": {
                "name": "Corporate Cover-up",
                "description": "The company knew about the dangers and sent the crew anyway",
                "importance": "high",
                "suspects": ["captain_reeves", "dr_petrov"]
            },
            "sabotage": {
                "name": "Deliberate Sabotage",
                "description": "Multiple systems were intentionally damaged",
                "importance": "high",
                "suspects": ["engineer_kowalski", "cargo_tech_miller"]
            },
            "impostor": {
                "name": "Impostor Among Crew",
                "description": "One crew member is not who they claim to be",
                "importance": "critical",
                "suspects": ["navigator_jones", "chef_rodriguez"]
            }
        }
    
    def init_terminals(self):
        self.terminals = {
            "cryo_terminal": {
                "name": "Cryogenic Control Terminal",
                "locked": False,
                "files": [
                    {"name": "wake_protocol.txt", "content": "Emergency wake protocol initiated at 04:23. Cause: Unknown distress signal detected."},
                    {"name": "pod_status.log", "content": "Pods 1-15: Occupied. Pod 16: Malfunction - occupant deceased. Pod 17: Empty - occupant missing."},
                    {"name": "crew_vitals.dat", "content": "Anomalous readings in 3 crew members. Recommend immediate medical examination."}
                ]
            },
            "bridge_main": {
                "name": "Bridge Main Console",
                "locked": True,
                "password": "europa2185",
                "files": [
                    {"name": "captain_log_final.txt", "content": "They're among us. I don't know who to trust anymore. Initiating lockdown."},
                    {"name": "distress_signal.wav", "content": "[AUDIO] Help... something... escaped... do not... trust..."},
                    {"name": "nav_override.exe", "content": "Navigation overridden by corporate directive. New destination: Classified Research Site."}
                ]
            },
            "med_terminal": {
                "name": "Medical Database",
                "locked": False,
                "files": [
                    {"name": "patient_records.db", "content": "Multiple crew showing symptoms: paranoia, aggression, cellular mutation."},
                    {"name": "quarantine_log.txt", "content": "Quarantine breached at 03:45. Subject escaped. Current location unknown."},
                    {"name": "treatment_notes.doc", "content": "Standard treatments ineffective. Organism appears to be adapting to our medicine."}
                ]
            },
            "research_terminal": {
                "name": "Research Terminal",
                "locked": True,
                "password": "specimen",
                "files": [
                    {"name": "project_pandora.pdf", "content": "Specimen shows remarkable adaptability. Can mimic human DNA perfectly."},
                    {"name": "test_results.csv", "content": "Subject integration: 78% complete. Host consciousness: suppressed."},
                    {"name": "emergency_protocol.txt", "content": "If containment fails, initiate station self-destruct. Authorization: Alpha-7-7."}
                ]
            },
            "engineering_terminal": {
                "name": "Engineering Control",
                "locked": False,
                "files": [
                    {"name": "system_status.log", "content": "Life support: 67%. Reactor: Critical. Communications: Offline."},
                    {"name": "sabotage_report.txt", "content": "Deliberate damage to cooling systems. Reactor will go critical in 12 hours."},
                    {"name": "maintenance_schedule.xls", "content": "Unauthorized access to restricted areas by: [REDACTED]"}
                ]
            },
            "secret_terminal": {
                "name": "Black Site Terminal",
                "locked": True,
                "password": "pandora",
                "files": [
                    {"name": "directive_omega.enc", "content": "Retrieve specimen at all costs. Crew expendable. Clean-up team en route."},
                    {"name": "experiment_log.txt", "content": "Day 47: Full integration achieved. Subject believes it is human."},
                    {"name": "truth.txt", "content": "We were never meant to survive. We're the experiment."}
                ]
            }
        }
    
    def select_killer(self):
        suspects = ["lt_chen", "dr_vasquez", "dr_petrov", "navigator_jones", 
                   "engineer_kowalski", "scientist_wong", "cargo_tech_miller"]
        self.killer = random.choice(suspects)
        self.npcs[self.killer].suspicious = 80
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, text: str):
        print(f"\n{Colors.CYAN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.CYAN}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.ENDC}\n")
    
    def type_text(self, text: str, delay: float = 0.03):
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()
    
    def show_status(self):
        print(f"{Colors.DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        status = f"Location: {self.locations[self.player.location].name} | "
        status += f"Health: {self.player.health}% | "
        status += f"O₂: {self.player.oxygen}% | "
        status += f"Sanity: {self.player.sanity}% | "
        status += f"Time: {self.player.time_elapsed:02d}:00"
        print(f"{Colors.BOLD}{status}{Colors.ENDC}")
        print(f"{Colors.WARNING}Objective: {self.player.current_objective}{Colors.ENDC}")
        print(f"{Colors.DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    
    def main_menu(self):
        self.clear_screen()
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("""
        ███████╗ ██████╗██╗  ██╗ ██████╗ ███████╗███████╗     ██████╗ ███████╗
        ██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝██╔════╝    ██╔═══██╗██╔════╝
        █████╗  ██║     ███████║██║   ██║█████╗  ███████╗    ██║   ██║█████╗  
        ██╔══╝  ██║     ██╔══██║██║   ██║██╔══╝  ╚════██║    ██║   ██║██╔══╝  
        ███████╗╚██████╗██║  ██║╚██████╔╝███████╗███████║    ╚██████╔╝██║     
        ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝     ╚═════╝ ╚═╝     
                                                                                
        ███████╗██╗   ██╗██████╗  ██████╗ ██████╗  █████╗                     
        ██╔════╝██║   ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗                    
        █████╗  ██║   ██║██████╔╝██║   ██║██████╔╝███████║                    
        ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔═══╝ ██╔══██║                    
        ███████╗╚██████╔╝██║  ██║╚██████╔╝██║     ██║  ██║                    
        ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝                    
        """)
        print(f"{Colors.ENDC}")
        print(f"{Colors.WARNING}A Space Station Mystery{Colors.ENDC}\n")
        
        print("1. New Game")
        print("2. Load Game")
        print("3. About")
        print("4. Quit")
        
        choice = input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}")
        
        if choice == "1":
            self.new_game()
        elif choice == "2":
            self.load_game()
        elif choice == "3":
            self.show_about()
        elif choice == "4":
            print(f"{Colors.GREEN}Thank you for playing!{Colors.ENDC}")
            sys.exit(0)
        else:
            self.main_menu()
    
    def show_about(self):
        self.clear_screen()
        self.print_header("ABOUT")
        print(f"{Colors.CYAN}Europa Station, 2185.{Colors.ENDC}")
        print(f"{Colors.CYAN}You wake from cryosleep to find the station in chaos.{Colors.ENDC}")
        print(f"{Colors.CYAN}The captain is dead. The crew is terrified.{Colors.ENDC}")
        print(f"{Colors.CYAN}Something has escaped from the research lab.{Colors.ENDC}")
        print(f"{Colors.CYAN}And someone among you is not who they claim to be.{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Can you uncover the truth before it's too late?{Colors.ENDC}")
        print(f"\n{Colors.DIM}A text-based mystery adventure game{Colors.ENDC}")
        print(f"{Colors.DIM}Featuring multiple endings based on your choices{Colors.ENDC}")
        input(f"\n{Colors.CYAN}Press Enter to return to menu...{Colors.ENDC}")
        self.main_menu()
    
    def new_game(self):
        self.clear_screen()
        self.print_header("INITIALIZATION")
        
        name = input(f"{Colors.CYAN}Enter your name, Commander: {Colors.ENDC}")
        if not name:
            name = "Commander"
        
        self.player = Player(name)
        
        self.clear_screen()
        print(f"{Colors.CYAN}")
        self.type_text("Date: March 15, 2185")
        self.type_text("Location: Europa Station, Orbit around Jupiter's Moon")
        self.type_text("Mission Duration: Day 127")
        print(f"{Colors.ENDC}")
        
        time.sleep(1)
        
        print(f"\n{Colors.WARNING}")
        self.type_text("EMERGENCY WAKE PROTOCOL INITIATED")
        self.type_text("CRITICAL SYSTEM FAILURE DETECTED")
        self.type_text("DISTRESS SIGNAL RECEIVED")
        print(f"{Colors.ENDC}")
        
        time.sleep(1)
        
        print(f"\n{Colors.CYAN}")
        self.type_text(f"You are {name}, second-in-command of Europa Station.")
        self.type_text("The hiss of your cryopod opening pulls you from a dreamless sleep.")
        self.type_text("Emergency lights bathe everything in red.")
        self.type_text("Something has gone terribly wrong.")
        self.type_text("\nThe captain is missing. You're in command now.")
        print(f"{Colors.ENDC}")
        
        input(f"\n{Colors.WARNING}Press Enter to begin your investigation...{Colors.ENDC}")
        
        self.state = GameState.EXPLORING
        self.game_loop()
    
    def game_loop(self):
        while True:
            if self.state == GameState.EXPLORING:
                self.explore()
            elif self.state == GameState.DIALOGUE:
                self.dialogue()
            elif self.state == GameState.INVESTIGATING:
                self.investigate()
            elif self.state == GameState.TERMINAL:
                self.use_terminal()
            elif self.state == GameState.ENDING:
                self.show_ending()
                break
            
            self.update_status()
            self.check_endings()
    
    def explore(self):
        self.clear_screen()
        location = self.locations[self.player.location]
        
        self.show_status()
        self.print_header(location.name.upper())
        
        if not location.investigated:
            self.type_text(location.description)
            location.investigated = True
        else:
            print(location.description)
        
        self.show_location_contents(location)
        self.show_actions()
        
        choice = input(f"\n{Colors.CYAN}What do you do? {Colors.ENDC}").lower()
        self.process_action(choice)
    
    def show_location_contents(self, location):
        if location.npcs:
            alive_npcs = [self.npcs[npc_id].name for npc_id in location.npcs if self.npcs[npc_id].alive]
            if alive_npcs:
                print(f"\n{Colors.GREEN}People here: {', '.join(alive_npcs)}{Colors.ENDC}")
        
        if location.items:
            print(f"{Colors.WARNING}Items visible: {', '.join(location.items)}{Colors.ENDC}")
        
        if location.terminals:
            print(f"{Colors.BLUE}Terminals: {', '.join([self.terminals[t]['name'] for t in location.terminals])}{Colors.ENDC}")
    
    def show_actions(self):
        print(f"\n{Colors.BOLD}Actions:{Colors.ENDC}")
        print("1. Move to another area")
        print("2. Investigate area")
        print("3. Check inventory")
        print("4. Review evidence")
        
        location = self.locations[self.player.location]
        if location.npcs:
            print("5. Talk to someone")
        if location.terminals:
            print("6. Use terminal")
        if location.items:
            print("7. Take item")
        
        print("8. Save game")
        print("9. Return to menu")
    
    def process_action(self, choice):
        if choice in ["1", "move"]:
            self.move()
        elif choice in ["2", "investigate"]:
            self.investigate_area()
        elif choice in ["3", "inventory"]:
            self.show_inventory()
        elif choice in ["4", "evidence"]:
            self.show_evidence()
        elif choice in ["5", "talk"] and self.locations[self.player.location].npcs:
            self.talk()
        elif choice in ["6", "terminal"] and self.locations[self.player.location].terminals:
            self.access_terminal()
        elif choice in ["7", "take"] and self.locations[self.player.location].items:
            self.take_item()
        elif choice in ["8", "save"]:
            self.save_game()
        elif choice in ["9", "menu"]:
            self.main_menu()
    
    def move(self):
        location = self.locations[self.player.location]
        
        print(f"\n{Colors.BOLD}Available exits:{Colors.ENDC}")
        exits = []
        for direction, dest_id in location.connections.items():
            dest = self.locations[dest_id]
            status = ""
            if dest.requires_access > self.player.access_level:
                status = f" {Colors.FAIL}[LOCKED - Level {dest.requires_access} Required]{Colors.ENDC}"
            elif dest.requires_item and dest.requires_item not in self.player.inventory:
                status = f" {Colors.FAIL}[Requires {dest.requires_item}]{Colors.ENDC}"
            exits.append((direction, dest_id, dest.name, status))
            print(f"{len(exits)}. {direction.capitalize()} to {dest.name}{status}")
        
        print(f"{len(exits) + 1}. Cancel")
        
        choice = input(f"\n{Colors.CYAN}Choose direction: {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(exits):
                direction, dest_id, dest_name, status = exits[idx]
                dest = self.locations[dest_id]
                
                if dest.requires_access > self.player.access_level:
                    print(f"{Colors.FAIL}You need Level {dest.requires_access} access to enter.{Colors.ENDC}")
                    input("Press Enter to continue...")
                elif dest.requires_item and dest.requires_item not in self.player.inventory:
                    print(f"{Colors.FAIL}You need {dest.requires_item} to enter safely.{Colors.ENDC}")
                    input("Press Enter to continue...")
                else:
                    self.player.location = dest_id
                    self.player.time_elapsed += 1
                    if dest.oxygen_drain > 0:
                        self.player.oxygen -= dest.oxygen_drain
                        print(f"{Colors.WARNING}Warning: Oxygen decreasing in this area!{Colors.ENDC}")
                        time.sleep(1)
        except (ValueError, IndexError):
            pass
    
    def investigate_area(self):
        self.clear_screen()
        location = self.locations[self.player.location]
        self.print_header(f"INVESTIGATING: {location.name}")
        
        discoveries = []
        
        if random.random() < 0.7:
            if location.id == "bridge" and "bridge_clue" not in self.player.knowledge:
                discoveries.append("You find scratches on the captain's chair - signs of a struggle.")
                self.player.knowledge.add("bridge_clue")
                self.player.evidence["Captain's Struggle"] = "Evidence of violence on the bridge"
            elif location.id == "medbay" and "medical_clue" not in self.player.knowledge:
                discoveries.append("Blood samples don't match any crew member's DNA.")
                self.player.knowledge.add("medical_clue")
                self.player.evidence["Unknown DNA"] = "Non-human genetic material found"
            elif location.id == "lab" and "lab_clue" not in self.player.knowledge:
                discoveries.append("The containment breach was deliberate - someone released it.")
                self.player.knowledge.add("lab_clue")
                self.player.evidence["Sabotage"] = "Intentional release of specimen"
        
        if discoveries:
            for discovery in discoveries:
                self.type_text(f"{Colors.GREEN}{discovery}{Colors.ENDC}")
        else:
            print(f"{Colors.CYAN}You search carefully but find nothing new.{Colors.ENDC}")
        
        self.player.skills["investigation"] += 0.1
        input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
    
    def talk(self):
        location = self.locations[self.player.location]
        npcs_here = [self.npcs[npc_id] for npc_id in location.npcs if self.npcs[npc_id].alive]
        
        if not npcs_here:
            print(f"{Colors.FAIL}No one alive here to talk to.{Colors.ENDC}")
            input("Press Enter to continue...")
            return
        
        print(f"\n{Colors.BOLD}Who do you want to talk to?{Colors.ENDC}")
        for i, npc in enumerate(npcs_here, 1):
            trust_indicator = ""
            if npc.trust > 70:
                trust_indicator = f" {Colors.GREEN}[Trusts you]{Colors.ENDC}"
            elif npc.trust < 30:
                trust_indicator = f" {Colors.FAIL}[Suspicious]{Colors.ENDC}"
            print(f"{i}. {npc.name} - {npc.role}{trust_indicator}")
        
        print(f"{len(npcs_here) + 1}. Cancel")
        
        choice = input(f"\n{Colors.CYAN}Choose person: {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(npcs_here):
                self.dialogue_with_npc(npcs_here[idx])
        except (ValueError, IndexError):
            pass
    
    def dialogue_with_npc(self, npc):
        self.clear_screen()
        self.print_header(f"TALKING TO: {npc.name}")
        
        dialogue_options = self.generate_dialogue_options(npc)
        
        print(f"{Colors.CYAN}{npc.name}: ", end="")
        greeting = self.get_npc_greeting(npc)
        self.type_text(greeting)
        print(f"{Colors.ENDC}")
        
        while True:
            print(f"\n{Colors.BOLD}What do you want to discuss?{Colors.ENDC}")
            for i, (topic, _) in enumerate(dialogue_options.items(), 1):
                if topic not in npc.talked_topics:
                    print(f"{i}. {topic}")
                else:
                    print(f"{i}. {Colors.DIM}{topic} [Already discussed]{Colors.ENDC}")
            
            print(f"{len(dialogue_options) + 1}. [End conversation]")
            
            choice = input(f"\n{Colors.CYAN}Choose topic: {Colors.ENDC}")
            
            try:
                idx = int(choice) - 1
                if idx == len(dialogue_options):
                    break
                elif 0 <= idx < len(dialogue_options):
                    topic = list(dialogue_options.keys())[idx]
                    response = dialogue_options[topic]
                    
                    print(f"\n{Colors.WARNING}You: {topic}{Colors.ENDC}")
                    print(f"{Colors.CYAN}{npc.name}: ", end="")
                    self.type_text(response)
                    print(f"{Colors.ENDC}")
                    
                    npc.talked_topics.add(topic)
                    self.process_dialogue_consequences(npc, topic)
            except (ValueError, IndexError):
                pass
    
    def generate_dialogue_options(self, npc):
        options = {
            "What happened here?": self.get_npc_response(npc, "general"),
            "Where were you when the alarm went off?": self.get_npc_response(npc, "alibi"),
            "Have you noticed anything suspicious?": self.get_npc_response(npc, "suspicious"),
            "What do you know about the research?": self.get_npc_response(npc, "research")
        }
        
        if npc.trust > 60:
            options["Can I trust you?"] = self.get_npc_response(npc, "trust")
        
        if "alien_infection" in self.player.evidence:
            options["Are you feeling alright?"] = self.get_npc_response(npc, "health")
        
        return options
    
    def get_npc_greeting(self, npc):
        greetings = {
            "lt_chen": "Commander. Good to see you're awake. We have a situation.",
            "dr_vasquez": "Thank God you're here. People are sick, and I don't know what's causing it.",
            "dr_petrov": "Ah, Commander. I... I can explain everything. Please, you must listen.",
            "navigator_jones": "Sir! The navigation systems are compromised. We're off course.",
            "engineer_kowalski": "Commander! The reactor's going critical. We need to act fast.",
            "chef_rodriguez": "Commander... something's wrong with the food supplies. And the crew.",
            "scientist_wong": "Commander, I've detected something impossible from Europa's surface.",
            "cargo_tech_miller": "Boss! There's stuff in the cargo that ain't on the manifest.",
            "botanist_green": "Commander, the plants... they're changing. Evolving."
        }
        return greetings.get(npc.id, "Hello, Commander.")
    
    def get_npc_response(self, npc, topic):
        if npc.id == self.killer and topic == "alibi":
            return "I was... in my quarters. Sleeping. No one can verify that, unfortunately."
        
        responses = {
            "lt_chen": {
                "general": "Security breach at 0400. Multiple systems compromised. The captain... he's dead.",
                "alibi": "I was on patrol in Corridor B. Security footage can confirm it.",
                "suspicious": "Dr. Petrov has been acting strange. And those experiments...",
                "research": "Classified above my pay grade, but I know it involves something from Europa.",
                "trust": "I've served with you for two years. You know my record.",
                "health": "I'm fine. Just tired. We all are."
            },
            "dr_petrov": {
                "general": "It escaped. God help us, it escaped and now it's among us.",
                "alibi": "In the lab, trying to contain the specimen. Check the logs.",
                "suspicious": "Everyone's suspicious! That's what it wants - to turn us against each other.",
                "research": "We found it in the ice. An organism unlike anything on Earth. It can... adapt.",
                "trust": "I know how this looks, but I tried to stop this. The company wouldn't listen.",
                "health": "The organism... it doesn't just kill. It replaces. Anyone could be infected."
            }
        }
        
        return responses.get(npc.id, {}).get(topic, "I... I don't know what to say about that.")
    
    def process_dialogue_consequences(self, npc, topic):
        if topic == "Can I trust you?":
            if npc.id == self.killer:
                npc.trust -= 10
            else:
                npc.trust += 5
        
        if topic == "Are you feeling alright?" and npc.id == self.killer:
            npc.suspicious += 10
            self.player.sanity -= 5
    
    def access_terminal(self):
        location = self.locations[self.player.location]
        
        print(f"\n{Colors.BOLD}Available terminals:{Colors.ENDC}")
        for i, terminal_id in enumerate(location.terminals, 1):
            terminal = self.terminals[terminal_id]
            status = " [LOCKED]" if terminal.get("locked") else ""
            print(f"{i}. {terminal['name']}{status}")
        
        print(f"{len(location.terminals) + 1}. Cancel")
        
        choice = input(f"\n{Colors.CYAN}Choose terminal: {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(location.terminals):
                terminal_id = location.terminals[idx]
                self.use_specific_terminal(terminal_id)
        except (ValueError, IndexError):
            pass
    
    def use_specific_terminal(self, terminal_id):
        terminal = self.terminals[terminal_id]
        
        self.clear_screen()
        self.print_header(terminal['name'])
        
        if terminal.get("locked"):
            password = input(f"{Colors.WARNING}Enter password: {Colors.ENDC}")
            if password.lower() == terminal.get("password", "").lower():
                print(f"{Colors.GREEN}Access granted.{Colors.ENDC}")
                terminal["locked"] = False
                self.player.skills["hacking"] += 0.5
            else:
                print(f"{Colors.FAIL}Access denied.{Colors.ENDC}")
                input("Press Enter to continue...")
                return
        
        print(f"\n{Colors.BOLD}Files available:{Colors.ENDC}")
        for i, file in enumerate(terminal.get("files", []), 1):
            print(f"{i}. {file['name']}")
        
        print(f"{len(terminal.get('files', [])) + 1}. Exit terminal")
        
        choice = input(f"\n{Colors.CYAN}Select file: {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(terminal.get("files", [])):
                file = terminal["files"][idx]
                print(f"\n{Colors.GREEN}Opening {file['name']}...{Colors.ENDC}\n")
                self.type_text(file['content'])
                
                evidence_name = f"Terminal File: {file['name']}"
                self.player.evidence[evidence_name] = file['content']
                
                input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")
                self.use_specific_terminal(terminal_id)
        except (ValueError, IndexError):
            pass
    
    def take_item(self):
        location = self.locations[self.player.location]
        
        print(f"\n{Colors.BOLD}Items here:{Colors.ENDC}")
        for i, item in enumerate(location.items, 1):
            desc = self.items[item]["description"]
            print(f"{i}. {item} - {desc}")
        
        print(f"{len(location.items) + 1}. Cancel")
        
        choice = input(f"\n{Colors.CYAN}Take which item? {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(location.items):
                item = location.items[idx]
                self.player.inventory[item] = self.player.inventory.get(item, 0) + 1
                location.items.remove(item)
                
                print(f"{Colors.GREEN}You take the {item}.{Colors.ENDC}")
                
                if "Level" in item and "Keycard" in item:
                    level = int(item.split("Level ")[1].split(" ")[0])
                    if level > self.player.access_level:
                        self.player.access_level = level
                        print(f"{Colors.GREEN}Access level increased to {level}!{Colors.ENDC}")
                
                if item == "Radiation Suit":
                    print(f"{Colors.GREEN}You can now enter high-radiation areas safely.{Colors.ENDC}")
                
                input("Press Enter to continue...")
        except (ValueError, IndexError):
            pass
    
    def show_inventory(self):
        self.clear_screen()
        self.print_header("INVENTORY")
        
        if not self.player.inventory:
            print(f"{Colors.CYAN}Your inventory is empty.{Colors.ENDC}")
        else:
            categories = {
                "key": "Access Cards",
                "weapon": "Weapons",
                "tool": "Tools",
                "evidence": "Evidence Items",
                "consumable": "Consumables",
                "equipment": "Equipment",
                "misc": "Miscellaneous"
            }
            
            for cat_type, cat_name in categories.items():
                cat_items = [(item, count) for item, count in self.player.inventory.items() 
                            if self.items[item]["type"] == cat_type]
                
                if cat_items:
                    print(f"\n{Colors.BOLD}{cat_name}:{Colors.ENDC}")
                    for item, count in cat_items:
                        desc = self.items[item]["description"]
                        count_str = f" x{count}" if count > 1 else ""
                        print(f"  • {item}{count_str} - {desc}")
        
        print(f"\n{Colors.CYAN}Access Level: {self.player.access_level}{Colors.ENDC}")
        print(f"{Colors.WARNING}Skills: ", end="")
        for skill, level in self.player.skills.items():
            print(f"{skill.capitalize()}: {level:.1f} ", end="")
        print(f"{Colors.ENDC}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
    
    def show_evidence(self):
        self.clear_screen()
        self.print_header("EVIDENCE COLLECTED")
        
        if not self.player.evidence:
            print(f"{Colors.CYAN}No evidence collected yet.{Colors.ENDC}")
        else:
            for name, description in self.player.evidence.items():
                print(f"\n{Colors.BOLD}{name}:{Colors.ENDC}")
                print(f"  {description}")
        
        if self.player.knowledge:
            print(f"\n{Colors.BOLD}Discoveries:{Colors.ENDC}")
            for knowledge in self.player.knowledge:
                print(f"  • {knowledge.replace('_', ' ').title()}")
        
        suspects = self.analyze_suspects()
        if suspects:
            print(f"\n{Colors.WARNING}Prime Suspects:{Colors.ENDC}")
            for suspect, suspicion in suspects[:3]:
                print(f"  • {suspect}: {suspicion}% suspicious")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
    
    def analyze_suspects(self):
        suspects = []
        for npc in self.npcs.values():
            if npc.alive:
                suspicion = npc.suspicious
                if npc.id == self.killer:
                    suspicion += 20
                if npc.trust < 30:
                    suspicion += 10
                if len(npc.talked_topics) == 0:
                    suspicion += 5
                suspects.append((npc.name, min(suspicion, 100)))
        
        return sorted(suspects, key=lambda x: x[1], reverse=True)
    
    def update_status(self):
        self.player.oxygen = min(100, self.player.oxygen + 1)
        
        if self.player.oxygen <= 0:
            self.state = GameState.ENDING
            self.ending = "suffocation"
        
        if self.player.health <= 0:
            self.state = GameState.ENDING
            self.ending = "death"
        
        if self.player.sanity <= 0:
            self.state = GameState.ENDING
            self.ending = "madness"
        
        if self.player.time_elapsed >= 24:
            self.state = GameState.ENDING
            self.ending = "timeout"
    
    def check_endings(self):
        if len(self.player.evidence) >= 10 and self.killer in [npc.id for npc in self.npcs.values()]:
            if input(f"\n{Colors.WARNING}Do you want to make an accusation? (y/n): {Colors.ENDC}").lower() == 'y':
                self.make_accusation()
        
        if "Truth Serum" in self.player.inventory and self.killer in [npc.id for npc in self.npcs.values()]:
            if input(f"\n{Colors.WARNING}Use Truth Serum on someone? (y/n): {Colors.ENDC}").lower() == 'y':
                self.use_truth_serum()
    
    def make_accusation(self):
        self.clear_screen()
        self.print_header("MAKE YOUR ACCUSATION")
        
        alive_npcs = [npc for npc in self.npcs.values() if npc.alive]
        
        print(f"{Colors.WARNING}Who is the impostor?{Colors.ENDC}\n")
        for i, npc in enumerate(alive_npcs, 1):
            print(f"{i}. {npc.name} - {npc.role}")
        
        choice = input(f"\n{Colors.CYAN}Choose the impostor (number): {Colors.ENDC}")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(alive_npcs):
                accused = alive_npcs[idx]
                if accused.id == self.killer:
                    self.ending = "victory"
                else:
                    self.ending = "wrong_accusation"
                self.state = GameState.ENDING
        except (ValueError, IndexError):
            pass
    
    def use_truth_serum(self):
        print("\n[Truth Serum feature - would reveal the killer]")
        self.ending = "truth_serum"
        self.state = GameState.ENDING
    
    def show_ending(self):
        self.clear_screen()
        
        endings = {
            "victory": {
                "title": "VICTORY",
                "text": f"You correctly identified {self.npcs[self.killer].name} as the impostor. "
                       "The creature is contained, and the remaining crew is saved. "
                       "Europa Station will survive another day.",
                "color": Colors.GREEN
            },
            "wrong_accusation": {
                "title": "FAILURE",
                "text": "You accused the wrong person. The real impostor remains hidden, "
                       "and one by one, the crew disappears. Europa Station goes dark.",
                "color": Colors.FAIL
            },
            "suffocation": {
                "title": "ASPHYXIATION",
                "text": "Your oxygen runs out. As darkness closes in, you realize "
                       "the truth will die with you. The station is doomed.",
                "color": Colors.FAIL
            },
            "death": {
                "title": "DEATH",
                "text": "Your injuries prove fatal. The investigation ends with your "
                       "last breath. The mystery of Europa Station remains unsolved.",
                "color": Colors.FAIL
            },
            "madness": {
                "title": "MADNESS",
                "text": "The paranoia becomes too much. You can no longer tell friend "
                       "from foe, human from alien. In your madness, you doom them all.",
                "color": Colors.WARNING
            },
            "timeout": {
                "title": "TIME'S UP",
                "text": "The reactor goes critical. Europa Station is consumed in nuclear "
                       "fire. The truth burns with it.",
                "color": Colors.FAIL
            },
            "truth_serum": {
                "title": "THE TRUTH",
                "text": f"The serum works. {self.npcs[self.killer].name} confesses to being "
                       "the host organism. But is it too late to stop the spread?",
                "color": Colors.CYAN
            }
        }
        
        ending = endings.get(self.ending, endings["timeout"])
        
        print(f"{ending['color']}{Colors.BOLD}")
        print("="*70)
        print(ending['title'].center(70))
        print("="*70)
        print(f"{Colors.ENDC}")
        
        print(f"\n{ending['color']}")
        self.type_text(ending['text'])
        print(f"{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Final Statistics:{Colors.ENDC}")
        print(f"Time Survived: {self.player.time_elapsed} hours")
        print(f"Evidence Collected: {len(self.player.evidence)}")
        print(f"Areas Explored: {sum(1 for loc in self.locations.values() if loc.investigated)}")
        print(f"The Impostor Was: {self.npcs[self.killer].name}")
        
        if input(f"\n{Colors.CYAN}Play again? (y/n): {Colors.ENDC}").lower() == 'y':
            self.__init__()
            self.main_menu()
        else:
            print(f"{Colors.GREEN}Thank you for playing Echoes of Europa!{Colors.ENDC}")
            sys.exit(0)
    
    def save_game(self):
        save_data = {
            "player": {
                "name": self.player.name,
                "location": self.player.location,
                "inventory": self.player.inventory,
                "evidence": self.player.evidence,
                "knowledge": list(self.player.knowledge),
                "actions_taken": self.player.actions_taken,
                "current_objective": self.player.current_objective,
                "sanity": self.player.sanity,
                "health": self.player.health,
                "oxygen": self.player.oxygen,
                "time_elapsed": self.player.time_elapsed,
                "access_level": self.player.access_level,
                "skills": self.player.skills,
                "flags": self.player.flags
            },
            "game": {
                "current_act": self.current_act,
                "killer": self.killer,
                "locations_investigated": {loc_id: loc.investigated for loc_id, loc in self.locations.items()},
                "npc_states": {
                    npc_id: {
                        "alive": npc.alive,
                        "location": npc.location,
                        "suspicious": npc.suspicious,
                        "trust": npc.trust,
                        "talked_topics": list(npc.talked_topics)
                    } for npc_id, npc in self.npcs.items()
                }
            }
        }
        
        with open(self.save_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"{Colors.GREEN}Game saved successfully!{Colors.ENDC}")
        input("Press Enter to continue...")
    
    def load_game(self):
        if not os.path.exists(self.save_file):
            print(f"{Colors.FAIL}No save file found!{Colors.ENDC}")
            input("Press Enter to return...")
            self.main_menu()
            return
        
        try:
            with open(self.save_file, 'r') as f:
                save_data = json.load(f)
            
            self.player = Player()
            for key, value in save_data["player"].items():
                if key == "knowledge":
                    setattr(self.player, key, set(value))
                else:
                    setattr(self.player, key, value)
            
            self.current_act = save_data["game"]["current_act"]
            self.killer = save_data["game"]["killer"]
            
            for loc_id, investigated in save_data["game"]["locations_investigated"].items():
                if loc_id in self.locations:
                    self.locations[loc_id].investigated = investigated
            
            for npc_id, npc_state in save_data["game"]["npc_states"].items():
                if npc_id in self.npcs:
                    npc = self.npcs[npc_id]
                    npc.alive = npc_state["alive"]
                    npc.location = npc_state["location"]
                    npc.suspicious = npc_state["suspicious"]
                    npc.trust = npc_state["trust"]
                    npc.talked_topics = set(npc_state["talked_topics"])
            
            print(f"{Colors.GREEN}Game loaded successfully!{Colors.ENDC}")
            self.state = GameState.EXPLORING
            self.game_loop()
        
        except Exception as e:
            print(f"{Colors.FAIL}Error loading save: {e}{Colors.ENDC}")
            input("Press Enter to return...")
            self.main_menu()

def main():
    game = EchoesOfEuropa()
    game.main_menu()

if __name__ == "__main__":
    main()