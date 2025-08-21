
#!/usr/bin/env python3
"""
Interactive chat via monitoring web UI.
The session pauses after each bot response, waiting for user input via web injection.
"""

from polycli import PolyAgent
from polycli.orchestration import session, serve_session


def main():
    agent = PolyAgent(id="ChatBot")
    
    with session() as s:
        # Start monitoring
        server, _ = serve_session(s, port=8768)
        print("Monitor at: http://localhost:8768")
        print("Use the web UI to inject messages and resume\n")
        
        # Summon the agent so it appears immediately in the UI
        s.summon_agents(agent)
        
        # Initial pause for first user message
        s.request_pause()
        
        # Chat loop
        while True:
            agent.run("Continue.", cli="claude-code", tracked=True)
            agent.save_state("1.jsonl")
            s.request_pause()

if __name__ == "__main__":
    main()
