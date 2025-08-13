from polycli import OpenSourceAgent
from polycli.orchestration import session, serve_session, batch
from polycli.builtin_patterns import notify, tell

batman = OpenSourceAgent(system_prompt="You are Batman.")
wolfman = OpenSourceAgent(system_prompt="You are Wolfman.")
dm = OpenSourceAgent(system_prompt="You are the dungeon master.")

with session() as s:
    notify(dm, "You are the dungeon master. You act as the environment to determine the action results of batman and wolfman.")
    notify(batman, "You are in a duel. You goal is to defeat Wolfman.")
    notify(wolfman, "You are in a duel. You goal is to defeat Batman.")
    batman_life = 100
    wolfman_life = 100
    while batman_life > 0 and wolfman_life > 0:
        tell(batman, dm, "Your next action against Wolfman.")
        result = dm.run("Your description of the outcome of batman's action. And remaining life points.")
        notify(batman, result.content)
        notify(wolfman, result.content)
        tell(wolfman, dm, "Your next action against Batman.")
        result = dm.run("Your description of the outcome of wolfman's action. And remaining life points.")
        notify(batman, result.content)
        notify(wolfman, result.content)



