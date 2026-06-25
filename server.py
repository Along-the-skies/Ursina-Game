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

    connections.difference_update(dead)


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
            await ws.send("invalid_team")
            return

        teams[choice].append(ws)
        print(f"Player chose {choice}")

        connections.add(ws)

        if teams["red"] and teams["blue"]:
            r = teams["red"].pop(0)
            b = teams["blue"].pop(0)

            await r.send("match_start")
            await b.send("match_start")

            print("Match started")
        else:
            await ws.send("waiting")

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
        connections.discard(ws)
        print("Player disconnected")


async def main():
    port = int(os.environ.get("PORT", 10000))

    async with websockets.serve(handle, "0.0.0.0", port):
        print(f"Listening on {port}")
        await asyncio.Future()


asyncio.run(main())