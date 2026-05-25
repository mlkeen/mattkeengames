import json
import random
import secrets
import re
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
)

ntp_bp = Blueprint(
    "ntp",
    __name__,
    template_folder="templates",
)

BASE_DIR = Path(__file__).resolve().parent
GAME_STATE_DIR = BASE_DIR / "instance" / "ntp_games"
GAME_STATE_DIR.mkdir(parents=True, exist_ok=True)


PLAYER_COLORS = ["green", "orange", "purple"]

COLOR_CARD_BACKS = {
    "green": "games/new-troll-party/cards/green/NTP_back_green.png",
    "orange": "games/new-troll-party/cards/orange/NTP_back_orange.png",
    "purple": "games/new-troll-party/cards/purple/NTP_back_purple.png",
}

CARD_FOLDER = (
    BASE_DIR /
    "static" /
    "games" /
    "new-troll-party" /
    "cards"
)

def make_color_deck(color):

    deck = []

    color_dir = CARD_FOLDER / color

    image_files = sorted(color_dir.glob("*.png"))

    for image_path in image_files:

        filename = image_path.stem.lower()

        if "back" in filename:
            continue

        card = {
            "id": filename,
            "color": color,
            "image": (
                f"games/new-troll-party/cards/"
                f"{color}/{image_path.name}"
            ),
            "back": COLOR_CARD_BACKS[color],
            "type": "number",
            "value": None,
            "goat_effect": parse_goat_effect(filename),
            "endgame_action": None,
        }

        number_match = re.search(r"_(\d{1,2})", filename)

        if number_match:
            card["value"] = int(number_match.group(1))

        if "endgame" in filename:
            card["type"] = "endgame"

            action_name = filename.replace(
                f"ntp_{color}_endgame_",
                ""
            )

            # Strip goat tag from action name
            action_name = re.sub(r"_goat-?\d+", "", action_name)

            card["endgame_action"] = action_name

        deck.append(card)

    random.shuffle(deck)

    return deck



def game_path(code):
    return GAME_STATE_DIR / f"{code}.json"


def load_game(code):
    path = game_path(code)

    if not path.exists():
        return None

    return json.loads(path.read_text())


def save_game(game):
    path = game_path(game["code"])
    path.write_text(json.dumps(game, indent=2))


@ntp_bp.route("/new-troll-party")
def ntp_index():
    return render_template("ntp/index.html")


@ntp_bp.route("/new-troll-party/create", methods=["POST"])
def ntp_create():
    code = secrets.token_hex(3).upper()

    game = {
        "code": code,
        "status": "waiting",
        "round": 1,
        "phase": "waiting",
        "players": [],
        "plays": [],
        "deck": make_deck(),
        "log": ["Game created."],
    }

    save_game(game)

    return redirect(url_for("ntp.ntp_join", code=code))


@ntp_bp.route("/new-troll-party/join/<code>", methods=["GET", "POST"])
def ntp_join(code):
    game = load_game(code)

    if not game:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "Anonymous Troll")[:24]

        player_id = secrets.token_hex(8)

        player = {
            "id": player_id,
            "name": name,
            "hand": [],
            "score": 0,
            "goats": 0,
            "won": [],
        }

        game["players"].append(player)

        session["ntp_player_id"] = player_id
        session["ntp_game_code"] = code

        if len(game["players"]) >= 3:
            game["status"] = "active"
            game["phase"] = "placing"

            for _ in range(5):
                for p in game["players"]:
                    if game["deck"]:
                        p["hand"].append(game["deck"].pop())

            game["log"].append("The trolls gather around the tables.")

        save_game(game)

        return redirect(url_for("ntp.ntp_table", code=code))

    return render_template("ntp/join.html", game=game)


@ntp_bp.route("/new-troll-party/game/<code>")
def ntp_table(code):
    game = load_game(code)

    if not game:
        abort(404)

    player_id = session.get("ntp_player_id")

    player = next(
        (p for p in game["players"] if p["id"] == player_id),
        None,
    )

    return render_template(
        "ntp/table.html",
        game=game,
        player=player,
        card_back=CARD_BACK,
    )


@ntp_bp.route("/new-troll-party/play/<code>", methods=["POST"])
def ntp_play(code):
    game = load_game(code)

    if not game:
        abort(404)

    player_id = session.get("ntp_player_id")

    player = next(
        (p for p in game["players"] if p["id"] == player_id),
        None,
    )

    if not player:
        return redirect(url_for("ntp.ntp_join", code=code))

    card_id = request.form.get("card_id")

    card = next((c for c in player["hand"] if c["id"] == card_id), None)

    if not card:
        return redirect(url_for("ntp.ntp_table", code=code))

    existing = next(
        (p for p in game["plays"] if p["player_id"] == player_id),
        None,
    )

    if existing:
        return redirect(url_for("ntp.ntp_table", code=code))

    player["hand"] = [c for c in player["hand"] if c["id"] != card_id]

    game["plays"].append({
        "player_id": player_id,
        "player_name": player["name"],
        "card": card,
    })

    if len(game["plays"]) >= 3:
        reveal(game)

    save_game(game)

    return redirect(url_for("ntp.ntp_table", code=code))



def reveal(game):
    plays = game["plays"]

    winner = sorted(
        plays,
        key=lambda p: p["card"]["value"],
        reverse=True,
    )[0]

    winning_player = next(
        p for p in game["players"]
        if p["id"] == winner["player_id"]
    )

    total_goats = sum(p["card"].get("goat_effect", 0) for p in plays)

    winning_player["score"] += 1
    winning_player["goats"] += total_goats

    game["log"].append(
        f'{winner["player_name"]} wins the scuffle with '
        f'{winner["card"]["value"]}. '
        f'Collected goats: {total_goats}.'
    )

    game["plays"] = []

    remaining_cards = sum(len(p["hand"]) for p in game["players"])

    if remaining_cards <= 0:
        game["phase"] = "complete"

        game["log"].append("The party is over. Several goats are missing.")