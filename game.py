from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import json
import threading
import asyncio
import websockets

app = Ursina()

# ================= WS STATE =================
ws = None
loop = asyncio.new_event_loop()

# ================= CONNECT =================
async def ws_connect():
    global ws
    ws = await websockets.connect("wss://ursina-game.onrender.com")  # change for server
    print("Connected")

async def ws_send(data):
    try:
        if ws:
            await ws.send(json.dumps(data))
    except:
        pass


def send(data):
    asyncio.run_coroutine_threadsafe(ws_send(data), loop)

# ================= SERVER LISTENER =================
async def ws_listen():
    global red_pressed, blue_pressed, bridge_active

    async for msg in ws:
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            print("Ignored non-JSON message:", msg)
            continue

        msg_type = data.get("type")
        if msg_type == "waiting":
            print("Waiting for match...")
            continue
        elif msg_type == "match_start":
            print("Match started")
            continue

        if "bridge_active" in data:
            bridge_active = data["bridge_active"]
            bridge1.enabled = bridge_active
            bridge1.collider = "box" if bridge_active else None

        if "red_pressed" in data:
            red_pressed = data["red_pressed"]
            red_button.color = color.lime if red_pressed else color.red

        if "blue_pressed" in data:
            blue_pressed = data["blue_pressed"]
            blue_button.color = color.cyan if blue_pressed else color.blue


def start_listener():
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ws_connect())
        loop.create_task(ws_listen())
        loop.run_forever()
    except Exception as e:
        print("WS listener stopped:", e)

# optional: add reconnect logic here for production use


threading.Thread(target=start_listener, daemon=True).start()

# ================= MAP =================
road = Entity(model="cube", color=color.gray, scale=(18, 0.5, 3), position=(0, 0, 3), collider="box")
level1 = Entity(model="cube", color=color.gray, scale=(18, 0.5, 3), position=(0, 0, 15), collider="box")

bridge1 = Entity(model="cube", color=color.gray, scale=(3, 0.5, 9), position=(0, 0, 9), enabled=False)

ground_red = Entity(model="cube", color=color.red, scale=(4, 0.5, 3), position=(-7, 0, 0), collider="box")
ground_blue = Entity(model="cube", color=color.blue, scale=(4, 0.5, 3), position=(7, 0, 0), collider="box")

red_button = Entity(model="cube", color=color.red, scale=(1.3, 0.2, 1.3), position=(-7, 1.1, 3), collider="box")
blue_button = Entity(model="cube", color=color.blue, scale=(1.3, 0.2, 1.3), position=(7, 1.1, 3), collider="box")

# ================= GAME STATE =================
player = None
spawn_point = None
player_team = None
pos_text = None

red_pressed = False
blue_pressed = False
bridge_active = False

# ================= START GAME =================
def start_game(choice):
    global player, spawn_point, player_team, pos_text

    player_team = choice

    for e in scene.entities.copy():
        if isinstance(e, Button) or isinstance(e, Text) or e.name == "menu_bg":
            destroy(e)

    if choice == "red":
        spawn_point = ground_red.position + Vec3(0, 2, 0)
        body_color = color.red
    else:
        spawn_point = ground_blue.position + Vec3(0, 2, 0)
        body_color = color.blue

    send({"team": choice})

    player = FirstPersonController(position=spawn_point)

    Entity(parent=player, model="cube", color=body_color, scale=(0.6, 1.2, 0.6), y=0.5)

    pos_text = Text("", x=-0.85, y=0.45, scale=1.5, color=color.yellow)


# ================= UPDATE LOOP =================
def update():
    if not player:
        return

    pos_text.text = f"{round(player.x,2)}, {round(player.y,2)}, {round(player.z,2)}"

    if player.y < -10:
        player.position = spawn_point

    # send position (throttled by frame, OK for small game)
    send({"pos": {"x": player.x, "y": player.y, "z": player.z}})

    # button logic
    if player_team == "red":
        on_button = distance(player.position, red_button.position) < 1.5
        send({"button": on_button})
    elif player_team == "blue":
        on_button = distance(player.position, blue_button.position) < 1.5
        send({"button": on_button})


# ================= MENU =================
menu_bg = Entity(model="quad", scale=(20, 10), color=color.black, z=1, name="menu_bg")

Text("Choose Your Home", y=.3, scale=3, color=color.azure)

Button("Red Home", color=color.red, scale=(.3, .1), position=(0, .05, 0),
       on_click=lambda: start_game("red"))

Button("Blue Home", color=color.blue, scale=(.3, .1), position=(0, -.15, 0),
       on_click=lambda: start_game("blue"))

Button("Quit", color=color.gray, scale=(.2, .08), position=(0, -.35, 0),
       on_click=application.quit)

app.run()