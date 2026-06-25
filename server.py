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
    buffer = ""
    try:
        # First message must be team choice
        msg = conn.recv(1024).decode().strip()

        if not msg:
            return

        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            print("Bad first message:", repr(msg))
            return

        choice = data.get("team")

        if choice not in ["red", "blue"]:
            conn.sendall(b"invalid_team\n")
            return

        teams[choice].append(conn)
        print(f"Player chose {choice}")

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

        while True:
            chunk = conn.recv(1024).decode()
            if not chunk:
                break

            buffer += chunk

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)

                if not line.strip():
                    continue

                try:
                    data = json.loads(line.strip())
                except json.JSONDecodeError:
                    print("Bad JSON:", repr(line))
                    continue

                if "pos" in data:
                    state["players"][choice] = data["pos"]

                if "button" in data:
                    if choice == "red":
                        state["red_pressed"] = data["button"]
                    else:
                        state["blue_pressed"] = data["button"]

                state["bridge_active"] = (
                    state["red_pressed"] and state["blue_pressed"]
                )

                send_all()

    finally:
        with lock:
            if conn in connections:
                connections.remove(conn)

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
