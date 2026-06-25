from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading

app = Ursina()

# ================= CONNECT TO SERVER =================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5000))   # change IP if server is remote

# ================= MAP =================
road = Entity(model="cube", texture="white_cube", color=color.gray,
              scale=(18, 0.5, 3), position=(0, 0, 3), collider="box")

level1 = Entity(model="cube", texture="white_cube", color=color.gray,
                scale=(18, 0.5, 3), position=(0, 0, 15), collider="box")

bridge1 = Entity(model="cube", texture="white_cube", color=color.gray,
                 scale=(3, 0.5, 9), position=(0, 0, 9),
                 collider=None, enabled=False)

ground_red = Entity(model="cube", texture="white_cube", color=color.red,
                    scale=(4, 0.5, 3), position=(-7, 0, 0), collider="box")

ground_blue = Entity(model="cube", texture="white_cube", color=color.blue,
                     scale=(4, 0.5, 3), position=(7, 0, 0), collider="box")

Entity(model="cube", color=color.brown, scale=(1, 1, 1),
       position=(-7, 0.5, 3), collider="box")
red_button = Entity(model="cube", color=color.red, scale=(1.3, 0.2, 1.3),
                    position=(-7, 1.1, 3), collider="box")

Entity(model="cube", color=color.brown, scale=(1, 1, 1),
       position=(7, 0.5, 3), collider="box")
blue_button = Entity(model="cube", color=color.blue, scale=(1.3, 0.2, 1.3),
                     position=(7, 1.1, 3), collider="box")

# ================= VARIABLES =================
editor_cam = EditorCamera()
player = None
spawn_point = None
player_team = None
pos_text = None

red_pressed = False
blue_pressed = False
bridge_active = False

# ================= SERVER LISTENER =================
def listen():
    global red_pressed, blue_pressed, bridge_active
    while True:
        try:
            data = client.recv(1024).decode().strip()
            if not data:
                continue
            msg = json.loads(data)

            # Update bridge state from server
            if "bridge_active" in msg:
                bridge_active = msg["bridge_active"]
                if bridge_active:
                    bridge1.enabled = True
                    bridge1.collider = "box"
                else:
                    bridge1.enabled = False
                    bridge1.collider = None

            # Update button colors from server
            if "red_pressed" in msg:
                red_pressed = msg["red_pressed"]
                red_button.color = color.lime if red_pressed else color.red
            if "blue_pressed" in msg:
                blue_pressed = msg["blue_pressed"]
                blue_button.color = color.cyan if blue_pressed else color.blue

        except Exception as e:
            print("Error:", e)

threading.Thread(target=listen, daemon=True).start()

# ================= GAME START =================
def start_game(choice):
    global player, spawn_point, player_team, pos_text
    player_team = choice

    # Remove menu UI
    for e in scene.entities.copy():
        if isinstance(e, Button) or isinstance(e, Text) or e.name == "menu_bg":
            destroy(e)

    # Team setup
    if choice == "red":
        spawn_point = ground_red.position + Vec3(0, 2, 0)
        body_color = color.red
    else:
        spawn_point = ground_blue.position + Vec3(0, 2, 0)
        body_color = color.blue

    # Tell server which team we chose
    client.sendall(json.dumps({"team": choice}).encode())

    player = FirstPersonController(position=spawn_point)

    Entity(parent=player, model="cube", color=body_color,
           scale=(0.6, 1.2, 0.6), y=0.5)

    pos_text = Text(text="Pos: 0,0,0", x=-0.85, y=0.45,
                    scale=1.5, color=color.yellow)

# ================= UPDATE =================
def update():
    global red_pressed, blue_pressed

    if not player:
        return

    # Position HUD
    if pos_text:
        pos_text.text = f"Pos: {round(player.x,2)}, {round(player.y,2)}, {round(player.z,2)}"

    # Respawn if fallen
    if player.y < -10:
        player.position = spawn_point

    # Send position to server
    pos = {"x": player.x, "y": player.y, "z": player.z}
    client.sendall(json.dumps({"pos": pos}).encode())

    # Red player activates only red button
    if player_team == "red":
        if abs(player.x - red_button.x) < 1 and abs(player.z - red_button.z) < 1 and abs(player.y - red_button.y) < 2:
            if not red_pressed:
                red_pressed = True
                client.sendall(json.dumps({"button": True}).encode())

    # Blue player activates only blue button
    if player_team == "blue":
        if abs(player.x - blue_button.x) < 1 and abs(player.z - blue_button.z) < 1 and abs(player.y - blue_button.y) < 2:
            if not blue_pressed:
                blue_pressed = True
                client.sendall(json.dumps({"button": True}).encode())

# ================= MENU =================
menu_bg = Entity(model="quad", scale=(20, 10), color=color.black, z=1, name="menu_bg")

title = Text("Choose Your Home", origin=(0, 0), y=.3, scale=3, color=color.azure)

Button(text="Red Home", color=color.red, scale=(.3, .1), position=(0, .05, 0),
       text_color=color.white, on_click=lambda: start_game("red"))

Button(text="Blue Home", color=color.blue, scale=(.3, .1), position=(0, -.15, 0),
       text_color=color.white, on_click=lambda: start_game("blue"))

Button(text="Quit", color=color.gray, scale=(.2, .08), position=(0, -.35, 0),
       text_color=color.white, on_click=application.quit)

app.run()
