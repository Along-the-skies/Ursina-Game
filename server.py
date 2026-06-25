import os
import json
import asyncio
import websockets

teams = {"red": [], "blue": []}

state = {
    "level": 1,
    "red_pressed": False,
    "blue_pressed": False,
    "bridge_active": False,
    "door_open": False,
    "exit_open": False,
    "goal_open": False,
    "players": {
        "red": {"x": 0, "y": 0, "z": 0},
        "blue": {"x": 0, "y": 0, "z": 0}
    }
}

connections = set()


def cleanup_connection(ws):
    connections.discard(ws)
    for team in teams.values():
        if ws in team:
            team.remove(ws)


def inside_zone(pos, center, radius=3):
    return (
        abs(pos["x"] - center[0]) <= radius and
        abs(pos["y"] - center[1]) <= 2 and
        abs(pos["z"] - center[2]) <= radius
    )


async def send_all():
    if not connections:
        return

    data = json.dumps(state)

    dead = set()
    for ws in connections:
        try:
            await ws.send(data)
        except:
            dead.add(ws)

    for ws in dead:
        cleanup_connection(ws)


async def handle(ws):
    choice = None

    try:
        first = await ws.recv()

        try:
            data = json.loads(first)
        except json.JSONDecodeError:
            return

        choice = data.get("team")

        if choice not in ["red", "blue"]:
            await ws.send(json.dumps({"type": "invalid_team"}))
            return

        teams[choice].append(ws)
        print(f"Player chose {choice}")

        connections.add(ws)
        await ws.send(json.dumps(state))

        if teams["red"] and teams["blue"]:
            r = teams["red"].pop(0)
            b = teams["blue"].pop(0)

            await r.send(json.dumps({"type": "match_start"}))
            await b.send(json.dumps({"type": "match_start"}))

            print("Match started")
        else:
            await ws.send(json.dumps({"type": "waiting"}))

        async for msg in ws:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            if "pos" in data:
                state["players"][choice] = data["pos"]

            if "button" in data:
                if choice == "red":
                    state["red_pressed"] = data["button"]
                else:
                    state["blue_pressed"] = data["button"]

            if state["level"] == 1:
                state["bridge_active"] = (
                    state["red_pressed"] and
                    state["blue_pressed"]
                )
                if state["bridge_active"] and all(
                    inside_zone(state["players"][team], (0, 0, 15), radius=5)
                    for team in ["red", "blue"]
                ):
                    state["level"] = 2
                    state["red_pressed"] = False
                    state["blue_pressed"] = False
                    state["bridge_active"] = False
                    state["door_open"] = False
                    state["exit_open"] = False
                    state["goal_open"] = False

            elif state["level"] == 2:
                state["door_open"] = (
                    state["red_pressed"] and
                    state["blue_pressed"]
                )
                if state["door_open"] and all(
                    inside_zone(state["players"][team], (0, 0, 22), radius=4)
                    for team in ["red", "blue"]
                ):
                    state["level"] = 3
                    state["red_pressed"] = False
                    state["blue_pressed"] = False
                    state["door_open"] = False
                    state["exit_open"] = False
                    state["goal_open"] = False

            elif state["level"] == 3:
                state["exit_open"] = (
                    state["red_pressed"] and
                    state["blue_pressed"]
                )
                if state["exit_open"] and all(
                    inside_zone(state["players"][team], (0, 0, 28), radius=4)
                    for team in ["red", "blue"]
                ):
                    state["level"] = 4
                    state["red_pressed"] = False
                    state["blue_pressed"] = False
                    state["door_open"] = False
                    state["exit_open"] = False
                    state["goal_open"] = False

            elif state["level"] == 4:
                state["goal_open"] = (
                    state["red_pressed"] and
                    state["blue_pressed"]
                )
                if state["goal_open"] and all(
                    inside_zone(state["players"][team], (0, 0, 34), radius=4)
                    for team in ["red", "blue"]
                ):
                    state["level"] = 5

            await send_all()

    finally:
        cleanup_connection(ws)
        print("Player disconnected")


async def main():
    port = int(os.environ.get("PORT", 10000))

    async with websockets.serve(handle, "0.0.0.0", port):
        print(f"Listening on {port}")
        await asyncio.Future()


asyncio.run(main())