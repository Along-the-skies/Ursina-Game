import socket
import json
import threading

# Track waiting players
teams = {"red": [], "blue": []}

# Shared game state
state = {
    "red_pressed": False,
    "blue_pressed": False,
    "bridge_active": False,
    "players": {"red": {"x": 0, "y": 0, "z": 0},
                "blue": {"x": 0, "y": 0, "z": 0}}
}

connections = []
lock = threading.Lock()

# Broadcast state to all active players in a match
def send_all():
    data = json.dumps(state).encode()
    with lock:
        for c in connections:
            try:
                c.sendall(data + b"\n")
            except:
                pass

# Handle each player
def handle(conn):
    try:
        # First message must be team choice
        msg = conn.recv(1024).decode().strip()
        if not msg:
            return
        data = json.loads(msg)
        choice = data.get("team")
        if choice not in ["red", "blue"]:
            conn.sendall(b"invalid_team\n")
            return

        # Add to team list
        teams[choice].append(conn)
        print(f"Player chose {choice}")

        # Matchmaking
        if teams["red"] and teams["blue"]:
            r = teams["red"].pop(0)
            b = teams["blue"].pop(0)
            connections.clear()
            connections.extend([r, b])
            r.sendall(b"match_start\n")
            b.sendall(b"match_start\n")
            print("Match started: Red + Blue")
        else:
            conn.sendall(b"waiting\n")
            print("Waiting for mate...")

        # Keep listening for updates
        while True:
            msg = conn.recv(1024)
            if not msg:
                break
            try:
                data = json.loads(msg.decode().strip())
            except:
                continue

            # Update state
            if "pos" in data:
                state["players"][choice] = data["pos"]
            if "button" in data:
                if choice == "red":
                    state["red_pressed"] = data["button"]
                elif choice == "blue":
                    state["blue_pressed"] = data["button"]

            # Bridge logic
            state["bridge_active"] = state["red_pressed"] and state["blue_pressed"]

            send_all()

    finally:
        conn.close()
        print("Player disconnected")

# ================= MAIN SERVER =================
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5000))
    server.listen()
    print("Server listening on port 5000")

    while True:
        conn, addr = server.accept()
        print("Player connected from", addr)
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
