from polycli import OpenSourceAgent
from polycli.orchestration import session, serve_session
from polycli.builtin_patterns import notify, tell
from pydantic import BaseModel, Field

class CombatOutcome(BaseModel):
    """DM's structured response for combat actions"""
    description: str = Field(description="What happened in this turn")
    damage: int = Field(description="Damage dealt (0-30)")
    batman_hp: int = Field(description="Batman's remaining HP")
    wolfman_hp: int = Field(description="Wolfman's remaining HP")

# Create agents
batman = OpenSourceAgent(id="Batman", system_prompt="You are Batman.")
wolfman = OpenSourceAgent(id="Wolfman", system_prompt="You are Wolfman.")
dm = OpenSourceAgent(id="DM", system_prompt="You are the dungeon master.")

with session() as s:
    server, _ = serve_session(s, port=8765)
    print("Monitor at http://localhost:8765")
    
    notify(dm, "You are the dungeon master. You determine the action results of batman and wolfman.")
    notify(batman, "You are in a duel. Your goal is to defeat Wolfman.")
    notify(wolfman, "You are in a duel. Your goal is to defeat Batman.")
    
    batman_hp = 100
    wolfman_hp = 100
    
    while batman_hp > 0 and wolfman_hp > 0:
        # Batman's turn
        tell(batman, dm, "Your next action against Wolfman.")
        result = dm.run(
            f"Describe the outcome of Batman's action. Current HP: Batman {batman_hp}, Wolfman {wolfman_hp}",
            cli="no-tools",
            schema_cls=CombatOutcome
        )
        print(dm.messages)
        
        if result.has_data():
            outcome = result.data
            batman_hp = outcome['batman_hp']
            wolfman_hp = outcome['wolfman_hp']
            notify(batman, outcome['description'])
            notify(wolfman, outcome['description'])
        
        if wolfman_hp <= 0:
            break
            
        # Wolfman's turn
        tell(wolfman, dm, "Your next action against Batman.")
        result = dm.run(
            f"Describe the outcome of Wolfman's action. Current HP: Batman {batman_hp}, Wolfman {wolfman_hp}",
            cli="no-tools",
            schema_cls=CombatOutcome
        )
        
        if result.has_data():
            outcome = result.data
            batman_hp = outcome['batman_hp']
            wolfman_hp = outcome['wolfman_hp']
            notify(batman, outcome['description'])
            notify(wolfman, outcome['description'])
    
    winner = "Batman" if batman_hp > 0 else "Wolfman"
    notify(dm, f"{winner} wins!")
    
    input("Press Enter to stop...")
