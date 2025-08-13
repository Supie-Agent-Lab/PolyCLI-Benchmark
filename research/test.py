#!/usr/bin/env python3
from polycli import OpenSourceAgent
from polycli.orchestration import session, serve_session
from polycli.builtin_patterns import notify, tell, get_status


def main():
    # Three agents with IDs so you can see them in the UI
    Confucius = OpenSourceAgent(id="Confucius")
    Nietzsche = OpenSourceAgent(id="Nietzsche")

    with session() as s:
        # Start the monitor (http://127.0.0.1:8765)
        server, _ = serve_session(s, port=8765)
        print("Monitor running at http://127.0.0.1:8765")
        print("Try Stop/Resume and Inject from the UI while this sequence runs...\n")

        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")
        tell(Confucius, Nietzsche, "Tell him about your opinion.")
        tell(Nietzsche, Confucius, "Tell him about your opinion.")

if __name__ == "__main__":
    main()

