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
    global red_pressed, blue_pressed, bridge_active, level, door_open, exit_open, goal_open

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

        if "level" in data:
            level = data["level"]
            if status_text is not None:
                if level == 1:
                    status_text.text = "Level 1: Build the bridge"
                elif level == 2:
                    status_text.text = "Level 2: Open the door"
                elif level == 3:
                    status_text.text = "Level 3: Open the exit"
                elif level >= 4:
                    status_text.text = "Level cleared!"

        if "bridge_active" in data:
            bridge_active = data["bridge_active"]
            bridge1.enabled = bridge_active
            bridge1.collider = "box" if bridge_active else None

        if "door_open" in data and door:
            door_open = data["door_open"]
            door.enabled = (level >= 2 and not door_open)
            door.collider = "box" if (level >= 2 and not door_open) else None

        if "exit_open" in data and exit_gate:
            exit_open = data["exit_open"]
            exit_gate.enabled = (level >= 3 and not exit_open)
            exit_gate.collider = "box" if (level >= 3 and not exit_open) else None

        if "goal_open" in data and goal_gate:
            goal_open = data["goal_open"]
            goal_gate.enabled = (level >= 4 and not goal_open)
            goal_gate.collider = "box" if (level >= 4 and not goal_open) else None

        if "red_pressed" in data:
            red_pressed = data["red_pressed"]
            red_button.color = color.lime if red_pressed else color.red

        if "blue_pressed" in data:
            blue_pressed = data["blue_pressed"]
            blue_button.color = color.cyan if blue_pressed else color.blue

        if "players" in data and remote_player:
            remote_data = data["players"].get(remote_team)
            if remote_data:
                remote_player.position = Vec3(remote_data["x"], remote_data["y"], remote_data["z"])

        if "level" in data and level_text:
            level_text.text = f"Level {level}"


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
level2 = Entity(model="cube", color=color.gray, scale=(18, 0.5, 3), position=(0, 0, 22), collider="box")
level3 = Entity(model="cube", color=color.gray, scale=(18, 0.5, 3), position=(0, 0, 28), collider="box")

bridge1 = Entity(model="cube", color=color.gray, scale=(3, 0.5, 9), position=(0, 0, 9), enabled=False)

door = Entity(model="cube", color=color.orange, scale=(6, 3.5, 0.4), position=(0, 2, 19.5), collider="box", enabled=False)
exit_gate = Entity(model="cube", color=color.green, scale=(6, 3.5, 0.4), position=(0, 2, 25.5), collider="box", enabled=False)
goal_gate = Entity(model="cube", color=color.gold, scale=(6, 3.5, 0.4), position=(0, 2, 33.5), collider="box", enabled=False)

ground_red = Entity(model="cube", color=color.red, scale=(4, 0.5, 3), position=(-7, 0, 0), collider="box")
ground_blue = Entity(model="cube", color=color.blue, scale=(4, 0.5, 3), position=(7, 0, 0), collider="box")

red_button = Entity(model="cube", color=color.red, scale=(1.3, 0.2, 1.3), position=(-7, 1.1, 3), collider="box")
blue_button = Entity(model="cube", color=color.blue, scale=(1.3, 0.2, 1.3), position=(7, 1.1, 3), collider="box")

# ================= GAME STATE =================
player = None
spawn_point = None
player_team = None
remote_team = None
remote_player = None
pos_text = None
level_text = None
status_text = None

red_pressed = False
blue_pressed = False
bridge_active = False
level = 1
door_open = False
exit_open = False
goal_open = False

# ================= START GAME =================
def start_game(choice):
    global player, spawn_point, player_team, remote_team, remote_player, pos_text, level_text, status_text

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

    camera.parent = player
    camera.position = Vec3(0, 2, -10)
    camera.rotation_x = 10
    camera.rotation_y = 0
    camera.rotation_z = 0

    remote_team = "blue" if choice == "red" else "red"
    remote_player = Entity(model="cube", color=color.azure if remote_team == "blue" else color.pink,
                           scale=(0.8, 1.3, 0.8), position=(0, -10, 0))

    pos_text = Text("", x=-0.85, y=0.45, scale=1.5, color=color.yellow)
    level_text = Text("Level 1", x=-0.85, y=0.35, scale=1.2, color=color.white)
    status_text = Text("Waiting for match...", x=-0.85, y=0.25, scale=1.1, color=color.yellow)


# ================= UPDATE LOOP =================
def update():
    if not player:
        return

    pos_text.text = f"{round(player.x,2)}, {round(player.y,2)}, {round(player.z,2)}"

    if player.y < -10:
        player.position = spawn_point

    camera.look_at(player.position + Vec3(0, 1, 0))

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