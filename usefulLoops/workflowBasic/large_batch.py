import polycli
from polycli.orchestration import batch, session, pattern, serve_session

@pattern
def singleprintrun():
    agent = polycli.PolyAgent()
    print(agent.run("hello", tracked=True, cli="qwen-code"))

@pattern
def printrun():
    with batch():
        singleprintrun()
        singleprintrun()
    return "done"

with session(max_workers=100) as s:
    _, _ = serve_session(s)
    with batch():
        for _ in range(50):
            printrun()
    with batch():
        for _ in range(50):
            printrun()

input()
