import os
import json
import asyncio
import websockets

teams = {"red": [], "blue": []}

state = {
    "red_pressed": False,
    "blue_pressed": False,
    "bridge_active": False,
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

            state["bridge_active"] = (
                state["red_pressed"] and
                state["blue_pressed"]
            )

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