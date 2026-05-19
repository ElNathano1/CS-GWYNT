"""
CS-GWYNT Backend Services (Railway branch)

This FastAPI service provides:
- Account management APIs (users, friends, levels, connection state)
- Profile picture processing (upload, convert to WebP/JPEG, thumbnails)
- File management utilities scoped to `UPLOAD_DIR`
- Messaging and invitations
- Realtime multiplayer support via WebSockets:
  - `/ws/lobby`: matchmaking queue by level and invitations
  - `/ws/room/{room_id}`: in-room events (moves, chat, presence)

WebSocket Protocol (JSON):
Outgoing from client:
- `client.hello`: `{ username }`
- `queue.join`: `{ level, username }`
- `queue.leave`: `{}`
- `invite.send`: `{ to }`
- `invite.accept`: `{ invite_id }`
- `invite.decline`: `{ invite_id }`
- `room.join`: `{ room_id }` (handled in room socket)
- `move.play`: `{ x, y }`
- `chat.send`: `{ message }`

Incoming from server:
- `lobby.welcome`: `{ username }`
- `queue.match_found`: `{ room_id, opponent: { username, level } }`
- `invite.received`: `{ invite_id, from }`
- `invite.sent`: `{ invite_id }`
- `invite.declined`: `{ invite_id, to? }`
- `room.joined`: `{ room_id }`
- `room.user_joined`: `{ username }`
- `room.user_left`: `{ username }`
- `move.played`: `{ x, y, from, color }`
- `chat.message`: `{ from, message }`
- `error`: `{ message }`
"""

import os
from random import random
import shutil
import jwt
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import FileResponse
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from database.models import get_session, AchievementsCorrespondancy, User
from database.repository import AccountRepository
from database.card_repository import CardRepository
from database.effect_repository import EffectRepository
from database.achievement_repository import AchievementRepository
from database.card import CardDTO
from database.loot_box import LootBoxDTO
from database.loot_box_repository import LootBoxRepository
from database.effect import EffectDTO, TriggerDTO
from database.achievement import AchievementDTO
from database.account import Account
import asyncio
import json
import uuid

API_NAME = os.environ.get("API_NAME", "CS-GWYNT Backend Services")
API_VERSION = os.environ.get("API_VERSION", "0.1.0")
app = FastAPI(title=API_NAME, version=API_VERSION)

# JWT Secret - use environment variable in production
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRE_HOURS = int(os.environ.get("TOKEN_EXPIRE_HOURS", 24))


def generate_token(username: str) -> str:
    """
    Generate a JWT token for a user.

    Args:
        username: The username to encode in the token

    Returns:
        JWT token string
    """
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> str | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Username if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("username")
    except Exception:
        return None


os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)


def get_repo():
    session = get_session()
    try:
        yield AccountRepository(session)
    finally:
        session.close()


def get_card_repo():
    session = get_session()
    try:
        yield CardRepository(session)
    finally:
        session.close()


def get_effect_repo():
    session = get_session()
    try:
        yield EffectRepository(session)
    finally:
        session.close()


def get_achievement_repo():
    session = get_session()
    try:
        yield AchievementRepository(session)
    finally:
        session.close()


def get_loot_box_repo():
    session = get_session()
    try:
        yield LootBoxRepository(session)
    finally:
        session.close()


# === Schemas Pydantic pour validation ===
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str


class FriendAction(BaseModel):
    friend_username: str


class LevelUpdate(BaseModel):
    new_level: int


class RankUpdate(BaseModel):
    new_rank: int


class GameCreate(BaseModel):
    player1_username: str
    player2_username: str
    timestamp: str
    nbr_rounds_player1: int
    nbr_rounds_player2: int
    replay_data: str = ""


class MessageCreate(BaseModel):
    recipient_username: str
    timestamp: str
    content: str
    type: str  # "chat", "system message", "friend invite", etc.


class TriggerPayload(BaseModel):
    event: str
    activate_on: dict | None = None
    deactivate_on: dict | None = None
    fire_when: dict | None = None
    countdown: int = 0
    repeat_limit: int | None = None
    repeat_interval: int = 0
    initially_active: int = 1


class EffectPayload(BaseModel):
    description: str
    type: str
    target: dict | None = None
    trigger: TriggerPayload | None = None
    value: int | dict | None = None


class CardCreate(BaseModel):
    name: str
    description: str
    rarity: str
    power_table: str
    face_artwork_url: str | None = None
    back_artwork_url: str | None = None
    effect: EffectPayload | None = None


class UserCardAction(BaseModel):
    quantity: int = 1


class AchievementCreate(BaseModel):
    name: str
    description: str
    criteria: str
    illustration: str | None = None


class LootBoxCreate(BaseModel):
    name: str
    description: str
    price: int
    nbr_random_cards: int
    mandatory_cards: list[tuple[int, int]] = Field(default_factory=list)
    random_cards: list[tuple[int, float]] = Field(default_factory=list)


class LootBoxMandatoryCardAction(BaseModel):
    quantity: int = 1


class LootBoxRandomCardAction(BaseModel):
    probability: float


class UserLootBoxAction(BaseModel):
    quantity: int = 1


# === Helper functions for profile pictures ===
def get_profile_pic_dir(profile_picture: str) -> str:
    """Get profile picture directory for a user"""
    upload_dir = os.environ["UPLOAD_DIR"]
    return os.path.join(upload_dir, "profiles", profile_picture)


def ensure_profile_pic_dir(username: str) -> str:
    """Ensure profile picture directory exists"""
    pic_dir = get_profile_pic_dir(username)
    os.makedirs(pic_dir, exist_ok=True)
    return pic_dir


def is_valid_image(file_bytes: bytes) -> bool:
    """Check if file is a valid image"""
    try:
        Image.open(BytesIO(file_bytes))
        return True
    except Exception:
        return False


def process_profile_picture(file_bytes: bytes, username: str) -> tuple[str, str]:
    """
    Process profile picture: convert to WebP and JPEG, create thumbnails.
    Returns (webp_path, jpeg_path)
    """
    pic_dir = ensure_profile_pic_dir(username)

    # Open and validate image
    image = Image.open(BytesIO(file_bytes)).convert("RGB")

    # Resize to 500x500 for full version
    image.thumbnail((500, 500), Image.Resampling.LANCZOS)

    # Save WebP version
    webp_path = os.path.join(pic_dir, "profile.webp")
    image.save(webp_path, "WebP", quality=85, method=6)

    # Save JPEG version (fallback)
    jpeg_path = os.path.join(pic_dir, "profile.jpg")
    image.save(jpeg_path, "JPEG", quality=85)

    # Create thumbnail (150x150)
    thumb = image.copy()
    thumb.thumbnail((150, 150), Image.Resampling.LANCZOS)

    # Save thumbnail WebP
    thumb_webp_path = os.path.join(pic_dir, "profile_thumb.webp")
    thumb.save(thumb_webp_path, "WebP", quality=80, method=6)

    # Save thumbnail JPEG
    thumb_jpeg_path = os.path.join(pic_dir, "profile_thumb.jpg")
    thumb.save(thumb_jpeg_path, "JPEG", quality=80)

    return webp_path, jpeg_path


def _parse_timestamp(timestamp_value: str) -> datetime:
    """Parse a message timestamp string into a datetime."""
    try:
        return datetime.fromisoformat(timestamp_value)
    except ValueError:
        return datetime.strptime(timestamp_value, "%d-%m-%Y %H:%M:%S")


def _trigger_payload_to_dto(payload: TriggerPayload) -> TriggerDTO:
    activate_on = payload.activate_on or {}
    deactivate_on = payload.deactivate_on or {}
    fire_when = payload.fire_when or {}
    return TriggerDTO(
        event=payload.event,
        activate_on_logic=activate_on.get("logic"),
        activate_on_conditions=activate_on.get("conditions"),
        deactivate_on_logic=deactivate_on.get("logic"),
        deactivate_on_conditions=deactivate_on.get("conditions"),
        fire_when_logic=fire_when.get("logic"),
        fire_when_conditions=fire_when.get("conditions"),
        countdown=payload.countdown,
        repeat_limit=payload.repeat_limit,
        repeat_interval=payload.repeat_interval,
        initially_active=payload.initially_active,
    )


def _effect_payload_to_dto(payload: EffectPayload) -> EffectDTO:
    target_payload = payload.target or {}
    target_shape = target_payload.get("shape")
    if target_shape is not None:
        target_payload = {k: v for k, v in target_payload.items() if k != "shape"}

    value_number: int | None = payload.value if isinstance(payload.value, int) else None
    value_data: dict | None = payload.value if isinstance(payload.value, dict) else None

    return EffectDTO(
        description=payload.description,
        type=payload.type,
        target_shape=target_shape,
        target_payload=target_payload or None,
        trigger=(
            _trigger_payload_to_dto(payload.trigger)
            if payload.trigger is not None
            else None
        ),
        value=value_number,
        value_data=value_data,
    )


@app.post("/auth/login")
def login(username: str, password: str, repo: AccountRepository = Depends(get_repo)):
    """
    Login endpoint - verify credentials and return JWT token.

    Args:
        username: User's username
        password: User's password (plaintext)

    Returns:
        JWT token for use in WebSocket connections
    """
    account = repo.get_by_username(username)
    if not account or not account.check_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token(username)
    return {
        "status": "success",
        "username": username,
        "token": token,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,  # seconds
    }


@app.get("/auth/verify")
def verify_auth(token: str):
    """
    Verify if a token is valid.

    Args:
        token: JWT token to verify

    Returns:
        Username if valid
    """
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"status": "success", "username": username}


@app.get("/connected")
def get_connected(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_connected()
    if not accounts:
        raise HTTPException(status_code=404, detail="No connected users found")
    return [
        {
            "username": account.username,
            "display_name": account.display_name,
            "level": account.level,
            "rank": account.rank,
            "friends": account.friends,
            "cards": account.cards,
            "achievements": account.achievements,
            "profile_picture": account.profile_picture,
            "connected": account.is_connected,
            "in_game": account.in_game,
        }
        for account in accounts
    ]


@app.get("/free")
def get_free(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_free()
    if not accounts:
        raise HTTPException(status_code=404, detail="No free users found")
    return [
        {
            "username": account.username,
            "display_name": account.display_name,
            "level": account.level,
            "rank": account.rank,
            "friends": account.friends,
            "cards": account.cards,
            "achievements": account.achievements,
            "profile_picture": account.profile_picture,
            "connected": account.is_connected,
            "in_game": account.in_game,
        }
        for account in accounts
    ]


@app.get("/games/{username}")
def get_games(username: str, repo: AccountRepository = Depends(get_repo)):
    games = repo.get_game_history(username)
    if not games:
        raise HTTPException(status_code=404, detail="No games found for user")
    return [
        {
            "player1": game.player1,
            "player2": game.player2,
            "timestamp": game.timestamp,
            "nbr_rounds_player1": game.nbr_rounds_player1,
            "nbr_rounds_player2": game.nbr_rounds_player2,
            "replay_data": game.replay_data,
        }
        for game in games
    ]


@app.post("/games/")
def add_game(game: GameCreate, repo: AccountRepository = Depends(get_repo)):
    if not repo.get_by_username(game.player1_username):
        raise HTTPException(status_code=404, detail="Player 1 not found")
    if not repo.get_by_username(game.player2_username):
        raise HTTPException(status_code=404, detail="Player 2 not found")

    try:
        parsed_timestamp = _parse_timestamp(game.timestamp)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format. Use ISO 8601 or DD-MM-YYYY.",
        )

    repo.save_game(
        game.player1_username,
        game.player2_username,
        game.nbr_rounds_player1,
        game.nbr_rounds_player2,
        parsed_timestamp,
        game.replay_data,
    )
    return {
        "status": "success",
        "message": (
            f"Game between {game.player1_username} and {game.player2_username} added"
        ),
    }


@app.get("/messages/{username}")
def get_messages(username: str, repo: AccountRepository = Depends(get_repo)):
    messages = repo.get_messages(username)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for user")
    return {
        "sent": [
            {
                "content": msg.content,
                "timestamp": msg.timestamp,
                "type": msg.type,
            }
            for msg in messages["sent"]  # type: ignore
        ],
        "received": [
            {
                "content": msg.content,
                "timestamp": msg.timestamp,
                "type": msg.type,
            }
            for msg in messages["received"]  # type: ignore
        ],
    }


@app.post("/messages/{sender_username}")
def send_message(
    sender_username: str,
    message: MessageCreate,
    repo: AccountRepository = Depends(get_repo),
):
    if not repo.get_by_username(sender_username):
        raise HTTPException(status_code=404, detail="Sender not found")
    if not repo.get_by_username(message.recipient_username):
        raise HTTPException(status_code=404, detail="Recipient not found")

    try:
        parsed_timestamp = _parse_timestamp(message.timestamp)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format. Use ISO 8601 or DD-MM-YYYY HH:MM:SS.",
        )

    repo.post_message(
        sender_username=sender_username,
        recipient_username=message.recipient_username,
        content=message.content,
        type=message.type,
    )
    return {
        "status": "success",
        "message": f"Message sent from {sender_username} to {message.recipient_username}:\n({message.type} ; {parsed_timestamp})\n'{message.content}'",
    }


@app.get("/users/{username}")
def get_user(username: str, repo: AccountRepository = Depends(get_repo)):
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": account.username,
        "display_name": account.display_name,
        "level": account.level,
        "friends": account.friends,
        "profile_picture": account.profile_picture,
        "connected": account.is_connected,
        "in_game": account.in_game,
    }


@app.get("/users")
def get_all_users(repo: AccountRepository = Depends(get_repo)):
    accounts = repo.get_all_users()
    if not accounts:
        raise HTTPException(status_code=404, detail="User not found")
    return [
        {
            "username": account.username,
            "display_name": account.display_name,
            "level": account.level,
            "friends": account.friends,
            "profile_picture": account.profile_picture,
            "connected": account.is_connected,
            "in_game": account.in_game,
        }
        for account in accounts
    ]


@app.post("/users/")
def create_user(user: UserCreate, repo: AccountRepository = Depends(get_repo)):
    if repo.get_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    account = Account(
        username=user.username, password=user.password, display_name=user.display_name
    )
    repo.create(account)
    return {"status": "success", "username": user.username}


@app.post("/users/{username}/change_password")
def change_password(
    username: str,
    old_password: str,
    new_password: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_password(username, old_password, new_password)
    return {
        "status": "success",
        "message": f"{username} changed password",
    }


@app.post("/users/{username}/reset_password")
def reset_password(
    username: str, new_password: str, repo: AccountRepository = Depends(get_repo)
):
    repo.reset_password(username, new_password)
    return {
        "status": "success",
        "message": f"{username} reset password",
    }


@app.post("/users/{username}/change_name")
def change_name(
    username: str,
    new_name: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_display_name(username, new_name)
    return {
        "status": "success",
        "message": f"{username} changed name to {new_name}",
    }


@app.post("/users/{username}/change_profile_picture")
def change_profile_picture(
    username: str,
    new_profile_picture: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.change_profile_picture(username, new_profile_picture)
    return {
        "status": "success",
        "message": f"{username} changed profile picture to {new_profile_picture}",
    }


@app.post("/users/{username}/add_friend")
def add_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.add_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} added to {username}",
    }


@app.post("/users/{username}/accept_friend")
def accept_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.accept_friend_invite(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} and {username} are now friends",
    }


@app.post("/users/{username}/reject_friend")
def reject_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.reject_friend_invite(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} rejected friend invite from {username}",
    }


@app.post("/users/{username}/remove_friend")
def remove_friend(
    username: str, action: FriendAction, repo: AccountRepository = Depends(get_repo)
):
    repo.remove_friend(username, action.friend_username)
    return {
        "status": "success",
        "message": f"{action.friend_username} removed from {username}",
    }


@app.post("/users/{username}/update_level")
def update_level(
    username: str,
    level_update: LevelUpdate,
    repo: AccountRepository = Depends(get_repo),
):
    repo.update_level(username, level_update.new_level)
    return {
        "status": "success",
        "username": username,
        "new_level": level_update.new_level,
    }


@app.post("/users/{username}/update_rank")
def update_rank(
    username: str,
    rank_update: RankUpdate,
    repo: AccountRepository = Depends(get_repo),
):
    repo.update_rank(username, rank_update.new_rank)
    return {
        "status": "success",
        "username": username,
        "new_rank": rank_update.new_rank,
    }


@app.post("/users/{username}/connect")
def connect(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.connect(username)
    return {
        "status": "success",
        "is_connected": 1,
    }


@app.post("/users/{username}/disconnect")
def disconnect(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.disconnect(username)
    return {
        "status": "success",
        "is_connected": 0,
    }


@app.post("/users/{username}/in_game")
def set_in_game(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.set_in_game(username, True)
    return {
        "status": "success",
        "in_game": 1,
    }


@app.post("/users/{username}/not_in_game")
def set_not_in_game(username: str, repo: AccountRepository = Depends(get_repo)):
    repo.set_in_game(username, False)
    return {
        "status": "success",
        "in_game": 0,
    }


@app.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    username: str,
    repo: AccountRepository = Depends(get_repo),
):
    repo.remove_user(username)


@app.get("/leaderboard")
def get_leaderboard(
    limit: int = 10,
    repo: AccountRepository = Depends(get_repo),
):
    users = repo.get_leaderboard(limit=limit)
    return [
        {
            "username": account.username,
            "display_name": account.display_name,
            "rank": account.rank,
            "level": account.level,
            "nbr_games": account.nbr_games,
            "nbr_wins": account.nbr_wins,
        }
        for account in users
    ]


@app.get("/loot-boxes")
def get_loot_boxes(
    search: str | None = None,
    repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    loot_boxes = repo.search(search) if search else repo.get_all()
    return [loot_box.to_dict() for loot_box in loot_boxes]


@app.get("/loot-boxes/{loot_box_id}")
def get_loot_box(
    loot_box_id: int, repo: LootBoxRepository = Depends(get_loot_box_repo)
):
    loot_box = repo.get(loot_box_id)
    if not loot_box:
        raise HTTPException(status_code=404, detail="Loot box not found")
    return loot_box.to_dict()


@app.post("/loot-boxes")
def create_loot_box(
    payload: LootBoxCreate,
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="Price must be >= 0")
    if payload.nbr_random_cards < 0:
        raise HTTPException(status_code=400, detail="nbr_random_cards must be >= 0")

    mandatory_cards: list[tuple[CardDTO, int]] = []
    for card_id, quantity in payload.mandatory_cards:
        if quantity < 1:
            raise HTTPException(
                status_code=400, detail="Mandatory card quantity must be >= 1"
            )
        card = card_repo.get(card_id)
        if not card:
            raise HTTPException(status_code=404, detail=f"Card {card_id} not found")
        mandatory_cards.append((card, quantity))

    random_cards: list[tuple[CardDTO, float]] = []
    for card_id, probability in payload.random_cards:
        if probability < 0:
            raise HTTPException(
                status_code=400, detail="Random card probability must be >= 0"
            )
        card = card_repo.get(card_id)
        if not card:
            raise HTTPException(status_code=404, detail=f"Card {card_id} not found")
        random_cards.append((card, probability))

    created = loot_box_repo.create(
        LootBoxDTO(
            name=payload.name,
            description=payload.description,
            price=payload.price,
            nbr_random_cards=payload.nbr_random_cards,
            mandatory_cards=mandatory_cards,
            random_cards=random_cards,
        )
    )
    return created.to_dict()


@app.delete("/loot-boxes/{loot_box_id}")
def delete_loot_box(
    loot_box_id: int,
    repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    deleted = repo.delete(loot_box_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Loot box not found")
    return {"status": "success", "loot_box_id": loot_box_id}


@app.post("/loot-boxes/{loot_box_id}/mandatory-cards/{card_id}")
def add_loot_box_mandatory_card(
    loot_box_id: int,
    card_id: int,
    action: LootBoxMandatoryCardAction,
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if action.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    success = loot_box_repo.add_mandatory_card(loot_box_id, card_id, action.quantity)
    if not success:
        raise HTTPException(status_code=400, detail="Could not add mandatory card")

    loot_box = loot_box_repo.get(loot_box_id)
    return loot_box.to_dict() if loot_box else {"status": "success"}


@app.delete("/loot-boxes/{loot_box_id}/mandatory-cards/{card_id}")
def remove_loot_box_mandatory_card(
    loot_box_id: int,
    card_id: int,
    quantity: int = 1,
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    success = loot_box_repo.remove_mandatory_card(loot_box_id, card_id, quantity)
    if not success:
        raise HTTPException(
            status_code=404, detail="Mandatory card not found in loot box"
        )

    loot_box = loot_box_repo.get(loot_box_id)
    return loot_box.to_dict() if loot_box else {"status": "success"}


@app.post("/loot-boxes/{loot_box_id}/random-cards/{card_id}")
def add_loot_box_random_card(
    loot_box_id: int,
    card_id: int,
    action: LootBoxRandomCardAction,
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if action.probability < 0:
        raise HTTPException(status_code=400, detail="Probability must be >= 0")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    success = loot_box_repo.add_random_card(loot_box_id, card_id, action.probability)
    if not success:
        raise HTTPException(status_code=400, detail="Could not add random card")

    loot_box = loot_box_repo.get(loot_box_id)
    return loot_box.to_dict() if loot_box else {"status": "success"}


@app.delete("/loot-boxes/{loot_box_id}/random-cards/{card_id}")
def remove_loot_box_random_card(
    loot_box_id: int,
    card_id: int,
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    success = loot_box_repo.remove_random_card(loot_box_id, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Random card not found in loot box")

    loot_box = loot_box_repo.get(loot_box_id)
    return loot_box.to_dict() if loot_box else {"status": "success"}


@app.get("/users/{username}/loot-boxes")
def get_user_loot_boxes(username: str, repo: AccountRepository = Depends(get_repo)):
    if not repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    loot_boxes = repo.get_user_loot_boxes(username)
    return [
        {
            "loot_box": entry["loot_box"].to_dict(),
            "quantity": entry["quantity"],
        }
        for entry in loot_boxes
    ]


@app.post("/users/{username}/loot-boxes/{loot_box_id}")
def add_user_loot_box(
    username: str,
    loot_box_id: int,
    action: UserLootBoxAction,
    account_repo: AccountRepository = Depends(get_repo),
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    if action.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")

    account_repo.add_loot_box(username, loot_box_id, action.quantity)
    return {
        "status": "success",
        "username": username,
        "loot_box_id": loot_box_id,
        "quantity": account_repo.get_loot_box_quantity(username, loot_box_id),
    }


@app.delete("/users/{username}/loot-boxes/{loot_box_id}")
def remove_user_loot_box(
    username: str,
    loot_box_id: int,
    quantity: int = 1,
    account_repo: AccountRepository = Depends(get_repo),
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")

    try:
        account_repo.remove_loot_box(username, loot_box_id, quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "username": username,
        "loot_box_id": loot_box_id,
        "quantity": account_repo.get_loot_box_quantity(username, loot_box_id),
    }


@app.post("/users/{username}/loot-boxes/{loot_box_id}/buy")
def buy_user_loot_box(
    username: str,
    loot_box_id: int,
    action: UserLootBoxAction,
    account_repo: AccountRepository = Depends(get_repo),
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    if action.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")

    success = account_repo.buy_loot_box(username, loot_box_id, action.quantity)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    return {
        "status": "success",
        "username": username,
        "loot_box_id": loot_box_id,
        "quantity": account_repo.get_loot_box_quantity(username, loot_box_id),
    }


@app.post("/users/{username}/loot-boxes/{loot_box_id}/open")
def open_user_loot_box(
    username: str,
    loot_box_id: int,
    account_repo: AccountRepository = Depends(get_repo),
    loot_box_repo: LootBoxRepository = Depends(get_loot_box_repo),
):
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not loot_box_repo.get(loot_box_id):
        raise HTTPException(status_code=404, detail="Loot box not found")

    obtained_cards = account_repo.open_loot_box(username, loot_box_id)
    if not obtained_cards:
        raise HTTPException(
            status_code=400,
            detail="Loot box unavailable or empty for this user",
        )

    return {
        "status": "success",
        "username": username,
        "loot_box_id": loot_box_id,
        "remaining_quantity": account_repo.get_loot_box_quantity(username, loot_box_id),
        "obtained_cards": [card.to_dict() for card in obtained_cards],
    }


@app.get("/cards")
def get_cards(
    rarity: str | None = None,
    search: str | None = None,
    repo: CardRepository = Depends(get_card_repo),
):
    if search:
        cards = repo.search(search)
    elif rarity:
        cards = repo.get_by_rarity(rarity)
    else:
        cards = repo.get_all()
    return [card.to_dict() for card in cards]


@app.post("/cards")
def create_card(
    payload: CardCreate,
    repo: CardRepository = Depends(get_card_repo),
):
    effect_dto = (
        _effect_payload_to_dto(payload.effect) if payload.effect is not None else None
    )
    created = repo.create(
        CardDTO(
            name=payload.name,
            description=payload.description,
            rarity=payload.rarity,
            power_table=payload.power_table,
            face_artwork_url=payload.face_artwork_url,
            back_artwork_url=payload.back_artwork_url,
            effect=effect_dto,
        )
    )
    return created.to_dict()


@app.delete("/cards/{card_id}")
def delete_card(card_id: int, repo: CardRepository = Depends(get_card_repo)):
    deleted = repo.delete(card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "success", "card_id": card_id}


@app.get("/users/{username}/cards")
def get_user_cards(username: str, repo: AccountRepository = Depends(get_repo)):
    if not repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    cards = repo.get_user_cards(username)
    return [
        {
            "card": entry["card"].to_dict(),
            "quantity": entry["quantity"],
        }
        for entry in cards
    ]


@app.post("/users/{username}/cards/{card_id}")
def add_user_card(
    username: str,
    card_id: int,
    action: UserCardAction,
    account_repo: AccountRepository = Depends(get_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if action.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    account_repo.add_card(username, card_id, action.quantity)
    return {
        "status": "success",
        "username": username,
        "card_id": card_id,
        "quantity": account_repo.get_card_quantity(username, card_id),
    }


@app.delete("/users/{username}/cards/{card_id}")
def remove_user_card(
    username: str,
    card_id: int,
    quantity: int = 1,
    account_repo: AccountRepository = Depends(get_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    try:
        account_repo.remove_card(username, card_id, quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "username": username,
        "card_id": card_id,
        "quantity": account_repo.get_card_quantity(username, card_id),
    }


@app.post("/users/{username}/cards/{card_id}/buy")
def buy_user_card(
    username: str,
    card_id: int,
    action: UserCardAction,
    account_repo: AccountRepository = Depends(get_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if action.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    success = account_repo.buy_card(username, card_id, action.quantity)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    return {
        "status": "success",
        "username": username,
        "card_id": card_id,
        "quantity": account_repo.get_card_quantity(username, card_id),
    }


@app.delete("/users/{username}/cards/{card_id}/sell")
def sell_user_card(
    username: str,
    card_id: int,
    quantity: int = 1,
    account_repo: AccountRepository = Depends(get_repo),
    card_repo: CardRepository = Depends(get_card_repo),
):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not card_repo.get(card_id):
        raise HTTPException(status_code=404, detail="Card not found")

    try:
        success = account_repo.sell_card(username, card_id, quantity)
        if not success:
            raise HTTPException(status_code=400, detail="Insufficient cards to sell")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "username": username,
        "card_id": card_id,
        "quantity": account_repo.get_card_quantity(username, card_id),
    }


@app.get("/effects")
def get_effects(repo: EffectRepository = Depends(get_effect_repo)):
    return [effect.to_dict() for effect in repo.get_all_effects()]


@app.get("/effects/by-type/{type_name}")
def get_effects_by_type(
    type_name: str, repo: EffectRepository = Depends(get_effect_repo)
):
    return [effect.to_dict() for effect in repo.get_effects_by_type(type_name)]


@app.post("/effects")
def create_effect(
    payload: EffectPayload,
    repo: EffectRepository = Depends(get_effect_repo),
):
    created = repo.create_effect(_effect_payload_to_dto(payload))
    return created.to_dict()


@app.delete("/effects/{effect_id}")
def delete_effect(effect_id: int, repo: EffectRepository = Depends(get_effect_repo)):
    deleted = repo.delete_effect(effect_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Effect not found")
    return {"status": "success", "effect_id": effect_id}


@app.get("/achievements")
def get_achievements(repo: AchievementRepository = Depends(get_achievement_repo)):
    return [achievement.to_dict() for achievement in repo.get_all()]


@app.post("/achievements")
def create_achievement(
    payload: AchievementCreate,
    repo: AchievementRepository = Depends(get_achievement_repo),
):
    created = repo.create(
        AchievementDTO(
            name=payload.name,
            description=payload.description,
            criteria=payload.criteria,
            illustration=payload.illustration,
        )
    )
    return created.to_dict()


@app.delete("/achievements/{achievement_id}")
def delete_achievement(
    achievement_id: int,
    repo: AchievementRepository = Depends(get_achievement_repo),
):
    deleted = repo.delete(achievement_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return {"status": "success", "achievement_id": achievement_id}


@app.get("/users/{username}/achievements")
def get_user_achievements(username: str, repo: AccountRepository = Depends(get_repo)):
    if not repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    achievements = repo.get_user_achievements(username)
    return [achievement.to_dict() for achievement in achievements]


@app.post("/users/{username}/achievements/{achievement_id}")
def add_user_achievement(
    username: str,
    achievement_id: int,
    account_repo: AccountRepository = Depends(get_repo),
    achievement_repo: AchievementRepository = Depends(get_achievement_repo),
):
    if not account_repo.get_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    if not achievement_repo.get(achievement_id):
        raise HTTPException(status_code=404, detail="Achievement not found")
    account_repo.add_achievement(username, achievement_id)
    return {
        "status": "success",
        "username": username,
        "achievement_id": achievement_id,
    }


@app.delete("/users/{username}/achievements/{achievement_id}")
def remove_user_achievement(
    username: str,
    achievement_id: int,
    repo: AccountRepository = Depends(get_repo),
):
    user = repo.session.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    unlocked = (
        repo.session.query(AchievementsCorrespondancy)
        .filter_by(user_id=user.id, achievement_id=achievement_id)
        .first()
    )
    if not unlocked:
        raise HTTPException(status_code=404, detail="Achievement not unlocked")

    repo.session.delete(unlocked)
    repo.session.commit()
    return {
        "status": "success",
        "username": username,
        "achievement_id": achievement_id,
    }


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(os.environ["UPLOAD_DIR"], file.filename)  # type: ignore
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "path": file_path}


# === Profile picture routes ===
@app.post("/users/{username}/profile-picture")
async def upload_profile_picture(
    username: str,
    file: UploadFile = File(...),
    repo: AccountRepository = Depends(get_repo),
):
    """Upload and process a profile picture for a user"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, and WebP images are allowed"
        )

    # Read file
    file_bytes = await file.read()

    # Validate image
    if not is_valid_image(file_bytes):
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

    # Check file size (max 5MB)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        # Process and convert image
        webp_path, jpeg_path = process_profile_picture(file_bytes, username)

        # Store relative path in database and persist to DB
        relative_path = f"profiles/{username}/profile.webp"
        # Update the actual DB record via repository to avoid stale Account instance
        repo.change_profile_picture(username, username)
        # Keep local in-memory value in sync for this response
        account.profile_picture = username

        return {
            "status": "success",
            "message": "Profile picture uploaded successfully",
            "username": username,
            "picture_path": relative_path,
            "formats": ["webp", "jpg"],
            "sizes": {
                "full": os.path.getsize(webp_path),
                "thumbnail": os.path.getsize(
                    os.path.join(get_profile_pic_dir(username), "profile_thumb.webp")
                ),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing profile picture: {str(e)}"
        )


@app.get("/users/{username}/profile-picture")
async def get_profile_picture(
    username: str,
    format: str = "webp",
    repo: AccountRepository = Depends(get_repo),
):
    """Get profile picture (full size) - supports WebP and JPEG"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    pic_dir = get_profile_pic_dir(account.profile_picture)

    # Determine file format
    if format.lower() == "jpg":
        file_path = os.path.join(pic_dir, "profile.jpg")
        media_type = "image/jpeg"
    else:  # default to webp
        file_path = os.path.join(pic_dir, "profile.webp")
        media_type = "image/webp"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Profile picture file not found")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/users/{username}/profile-picture/thumb")
async def get_profile_picture_thumb(
    username: str,
    format: str = "webp",
    repo: AccountRepository = Depends(get_repo),
):
    """Get profile picture thumbnail (150x150) - supports WebP and JPEG"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    pic_dir = get_profile_pic_dir(account.profile_picture)

    # Determine file format
    if format.lower() == "jpg":
        file_path = os.path.join(pic_dir, "profile_thumb.jpg")
        media_type = "image/jpeg"
    else:  # default to webp
        file_path = os.path.join(pic_dir, "profile_thumb.webp")
        media_type = "image/webp"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="Profile picture thumbnail not found"
        )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.delete("/users/{username}/profile-picture")
async def delete_profile_picture(
    username: str,
    repo: AccountRepository = Depends(get_repo),
):
    """Delete a user's profile picture"""
    # Check user exists
    account = repo.get_by_username(username)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    if not account.profile_picture:
        raise HTTPException(status_code=404, detail="User has no profile picture")

    try:
        # Store the profile picture identifier BEFORE clearing it
        pic_identifier = account.profile_picture
        pic_dir = get_profile_pic_dir(pic_identifier)

        # Delete files from disk
        if os.path.exists(pic_dir):
            shutil.rmtree(pic_dir)

        # Only update DB if files were actually deleted
        # This ensures the DB only says "default" if the files are gone
        repo.change_profile_picture(username, "default")

        return {
            "status": "success",
            "message": f"Profile picture deleted for user '{username}'",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting profile picture: {str(e)}"
        )


# === Routes de gestion des fichiers ===
@app.delete("/files/")
def delete_file(file_path: str):
    """Delete a file from UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR (security)
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Path does not point to a file")

    try:
        os.remove(full_path)
        return {"status": "success", "message": f"File '{file_path}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@app.post("/files/move/")
def move_file(source_path: str, destination_path: str):
    """Move a file within UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    source_full = os.path.join(upload_dir, source_path)
    destination_full = os.path.join(upload_dir, destination_path)

    # Check that paths stay within UPLOAD_DIR
    if not os.path.abspath(source_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.abspath(destination_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid destination path")

    if not os.path.exists(source_full):
        raise HTTPException(status_code=404, detail="Source file not found")

    if not os.path.isfile(source_full):
        raise HTTPException(status_code=400, detail="Source path is not a file")

    if os.path.exists(destination_full):
        raise HTTPException(status_code=400, detail="Destination file already exists")

    # Create destination directory if needed
    os.makedirs(os.path.dirname(destination_full), exist_ok=True)

    try:
        shutil.move(source_full, destination_full)
        return {
            "status": "success",
            "message": f"File moved from '{source_path}' to '{destination_path}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error moving file: {str(e)}")


@app.post("/files/rename/")
def rename_file(file_path: str, new_name: str):
    """Rename a file in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Path is not a file")

    if "/" in new_name or "\\" in new_name:
        raise HTTPException(
            status_code=400, detail="New name cannot contain path separators"
        )

    directory = os.path.dirname(full_path)
    new_full_path = os.path.join(directory, new_name)

    if os.path.exists(new_full_path):
        raise HTTPException(status_code=400, detail="File with new name already exists")

    try:
        os.rename(full_path, new_full_path)
        return {
            "status": "success",
            "message": f"File renamed from '{os.path.basename(file_path)}' to '{new_name}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error renaming file: {str(e)}")


@app.post("/folders/")
def create_folder(folder_path: str):
    """Create a folder in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if os.path.exists(full_path):
        raise HTTPException(status_code=400, detail="Folder already exists")

    try:
        os.makedirs(full_path, exist_ok=False)
        return {"status": "success", "message": f"Folder '{folder_path}' created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")


@app.delete("/folders/")
def delete_folder(folder_path: str):
    """Delete a folder and all its contents from UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a folder")

    try:
        shutil.rmtree(full_path)
        return {"status": "success", "message": f"Folder '{folder_path}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting folder: {str(e)}")


@app.post("/files/copy/")
def copy_file(source_path: str, destination_path: str):
    """Copy a file in UPLOAD_DIR"""
    upload_dir = os.environ["UPLOAD_DIR"]
    source_full = os.path.join(upload_dir, source_path)
    destination_full = os.path.join(upload_dir, destination_path)

    # Check that paths stay within UPLOAD_DIR
    if not os.path.abspath(source_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.abspath(destination_full).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid destination path")

    if not os.path.exists(source_full):
        raise HTTPException(status_code=404, detail="Source file not found")

    if not os.path.isfile(source_full):
        raise HTTPException(status_code=400, detail="Source path is not a file")

    if os.path.exists(destination_full):
        raise HTTPException(status_code=400, detail="Destination file already exists")

    # Create destination directory if needed
    os.makedirs(os.path.dirname(destination_full), exist_ok=True)

    try:
        shutil.copy2(source_full, destination_full)
        return {
            "status": "success",
            "message": f"File copied from '{source_path}' to '{destination_path}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error copying file: {str(e)}")


@app.get("/files/")
def list_files(folder_path: str = ""):
    """List all files and folders in a directory"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, folder_path) if folder_path else upload_dir

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a folder")

    try:
        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            size = None if is_dir else os.path.getsize(item_path)

            items.append(
                {
                    "name": item,
                    "type": "folder" if is_dir else "file",
                    "size": size,
                    "path": os.path.join(folder_path, item) if folder_path else item,
                }
            )

        return {
            "status": "success",
            "folder": folder_path or "root",
            "items": sorted(items, key=lambda x: (x["type"] != "folder", x["name"])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@app.get("/files/info/")
def get_file_info(file_path: str):
    """Get detailed information about a file or folder"""
    upload_dir = os.environ["UPLOAD_DIR"]
    full_path = os.path.join(upload_dir, file_path)

    # Check that the path stays within UPLOAD_DIR
    if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        stat_info = os.stat(full_path)
        is_dir = os.path.isdir(full_path)

        info = {
            "name": os.path.basename(full_path),
            "type": "folder" if is_dir else "file",
            "path": file_path,
            "size": stat_info.st_size if not is_dir else None,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "is_file": not is_dir,
            "is_folder": is_dir,
        }

        if is_dir:
            info["item_count"] = len(os.listdir(full_path))

        return {"status": "success", "info": info}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting file info: {str(e)}"
        )


# =============================
# Realtime (WebSocket) endpoints
# =============================


class WSManager:
    """In-memory manager for lobby connections, matchmaking, invites and rooms.

    This is a simple implementation suitable for a single process. For
    production scaling, consider using a shared store (Redis) for state.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.lobby_clients: dict[str, WebSocket] = {}
        self.client_levels: dict[str, int] = {}
        self.queue: list[str] = []
        self.invites: dict[str, dict] = {}
        self.rooms: dict[str, set[WebSocket]] = {}
        self.room_users: dict[str, set[str]] = {}
        self.room_colors: dict[str, dict[str, int]] = {}  # Goban.BLACK=1, WHITE=2

    async def send(self, ws: WebSocket, obj: dict) -> None:
        await ws.send_text(json.dumps(obj))

    async def broadcast_room(
        self, room_id: str, sender: WebSocket | None, obj: dict
    ) -> None:
        if room_id not in self.rooms:
            return
        payload = json.dumps(obj)
        for ws in list(self.rooms[room_id]):
            if sender is not None and ws is sender:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                # best effort
                pass


ws_manager = WSManager()


def extract_token(ws: WebSocket) -> str | None:
    """
    Extract Bearer token from WebSocket headers.

    Expected format: "Authorization: Bearer <token>"

    Args:
        ws: WebSocket connection object

    Returns:
        Token string if valid Bearer format, None otherwise
    """
    try:
        auth_header = ws.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:]  # strip "Bearer "
    except Exception:
        return None


@app.websocket("/ws/health")
async def ws_health(ws: WebSocket):
    """
    Simple WebSocket health check and echo endpoint (no auth required).

    Use this for diagnostics and to verify WebSocket connectivity without
    authentication overhead. Client sends any JSON message; server echoes
    it back with `type: "health.echo"`.

    Example:
        Send: {"message": "ping"}
        Recv: {"type": "health.echo", "payload": {"message": "ping"}}
    """
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue
            await ws.send_text(json.dumps({"type": "health.echo", "payload": data}))
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/lobby")
async def ws_lobby(ws: WebSocket):
    """
    WebSocket lobby endpoint.

    Authentication: Requires `Authorization: Bearer <token>` header.
    If missing or invalid, connection is rejected.

    Responsibilities:
    - Accept `client.hello { username }`
    - Handle matchmaking via `queue.join { level }` and `queue.leave`
    - Handle social invitations: `invite.send`, `invite.accept`, `invite.decline`
    - Emit `queue.match_found { room_id, opponent }` when a match is ready

    Messages are JSON objects with `type` and `payload` fields.
    """
    # Validate auth token
    token = extract_token(ws)
    if not token:
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    username: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue

            msg_type = data.get("type")
            payload = data.get("payload", {})

            # Identify client
            if msg_type == "client.hello":
                username = str(payload.get("username"))
                if not username:
                    await ws_manager.send(
                        ws,
                        {"type": "error", "payload": {"message": "username-required"}},
                    )
                    continue
                async with ws_manager.lock:
                    ws_manager.lobby_clients[username] = ws
                await ws_manager.send(
                    ws, {"type": "lobby.welcome", "payload": {"username": username}}
                )
                continue

            if username is None:
                await ws_manager.send(
                    ws, {"type": "error", "payload": {"message": "hello-first"}}
                )
                continue

            # Queue join/leave
            if msg_type == "queue.join":
                level = int(payload.get("level", 0))
                async with ws_manager.lock:
                    ws_manager.client_levels[username] = level
                    if username not in ws_manager.queue:
                        ws_manager.queue.append(username)

                    # Try to find the closest level opponent
                    opponent: str | None = None
                    best_diff = 1000000
                    for other in ws_manager.queue:
                        if other == username:
                            continue
                        diff = abs(level - ws_manager.client_levels.get(other, level))
                        if diff < best_diff:
                            best_diff = diff
                            opponent = other

                    if opponent:
                        # Create room
                        room_id = uuid.uuid4().hex
                        # Remove from queue
                        ws_manager.queue = [
                            u for u in ws_manager.queue if u not in (username, opponent)
                        ]
                        # Notify both
                        opp_ws = ws_manager.lobby_clients.get(opponent)
                        await ws_manager.send(
                            ws,
                            {
                                "type": "queue.match_found",
                                "payload": {
                                    "room_id": room_id,
                                    "opponent": {
                                        "username": opponent,
                                        "level": ws_manager.client_levels.get(opponent),
                                    },
                                },
                            },
                        )
                        if opp_ws:
                            await ws_manager.send(
                                opp_ws,
                                {
                                    "type": "queue.match_found",
                                    "payload": {
                                        "room_id": room_id,
                                        "opponent": {
                                            "username": username,
                                            "level": level,
                                        },
                                    },
                                },
                            )

                        # Assign colors randomly
                        colors = [1, 2]
                        random.shuffle(colors)  # type: ignore
                        ws_manager.room_colors[room_id] = {
                            username: colors[0],
                            opponent: colors[1],
                        }
                        ws_manager.room_users[room_id] = {username, opponent}
                continue

            if msg_type == "queue.leave":
                async with ws_manager.lock:
                    ws_manager.queue = [u for u in ws_manager.queue if u != username]
                await ws_manager.send(ws, {"type": "queue.left", "payload": {}})
                continue

            # Invitations
            if msg_type == "invite.send":
                to_user = payload.get("to")
                if not to_user:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "to-required"}}
                    )
                    continue
                invite_id = uuid.uuid4().hex
                async with ws_manager.lock:
                    ws_manager.invites[invite_id] = {"from": username, "to": to_user}
                to_ws = ws_manager.lobby_clients.get(str(to_user))
                if to_ws:
                    await ws_manager.send(
                        to_ws,
                        {
                            "type": "invite.received",
                            "payload": {"invite_id": invite_id, "from": username},
                        },
                    )
                    await ws_manager.send(
                        ws, {"type": "invite.sent", "payload": {"invite_id": invite_id}}
                    )
                else:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "user-offline"}}
                    )
                continue

            if msg_type == "invite.accept":
                invite_id = payload.get("invite_id")
                async with ws_manager.lock:
                    invite = ws_manager.invites.pop(str(invite_id), None)
                if not invite or invite.get("to") != username:
                    await ws_manager.send(
                        ws, {"type": "error", "payload": {"message": "invalid-invite"}}
                    )
                    continue
                room_id = uuid.uuid4().hex
                inviter = str(invite.get("from"))
                inviter_ws = ws_manager.lobby_clients.get(inviter)

                # Assign colors randomly
                colors = [1, 2]
                random.shuffle(colors)  # type: ignore
                ws_manager.room_colors[room_id] = {
                    inviter: colors[0],
                    username: colors[1],
                }
                ws_manager.room_users[room_id] = {inviter, username}
                await ws_manager.send(
                    ws,
                    {
                        "type": "queue.match_found",
                        "payload": {
                            "room_id": room_id,
                            "opponent": {"username": inviter},
                        },
                    },
                )
                if inviter_ws:
                    await ws_manager.send(
                        inviter_ws,
                        {
                            "type": "queue.match_found",
                            "payload": {
                                "room_id": room_id,
                                "opponent": {"username": username},
                            },
                        },
                    )
                continue

            if msg_type == "invite.decline":
                invite_id = payload.get("invite_id")
                async with ws_manager.lock:
                    invite = ws_manager.invites.pop(str(invite_id), None)
                if invite:
                    inviter = str(invite.get("from"))
                    inviter_ws = ws_manager.lobby_clients.get(inviter)
                    if inviter_ws:
                        await ws_manager.send(
                            inviter_ws,
                            {
                                "type": "invite.declined",
                                "payload": {
                                    "invite_id": str(invite_id),
                                    "to": username,
                                },
                            },
                        )
                await ws_manager.send(
                    ws,
                    {
                        "type": "invite.declined",
                        "payload": {"invite_id": str(invite_id)},
                    },
                )
                continue

            # Default: unknown message
            await ws_manager.send(
                ws,
                {
                    "type": "error",
                    "payload": {"message": "unknown-message", "received": msg_type},
                },
            )

    except WebSocketDisconnect:
        # Cleanup on disconnect
        async with ws_manager.lock:
            if username:
                ws_manager.lobby_clients.pop(username, None)
                ws_manager.client_levels.pop(username, None)
                ws_manager.queue = [u for u in ws_manager.queue if u != username]


@app.websocket("/ws/room/{room_id}")
async def ws_room(ws: WebSocket, room_id: str):
    """
    WebSocket room endpoint.

    Authentication: Requires `Authorization: Bearer <token>` header.
    If missing or invalid, connection is rejected.

    Responsibilities:
    - Accept `client.hello { username }` and join user to room
    - Broadcast `room.user_joined` and `room.user_left`
    - Relay `move.play { x, y }` as `move.played { x, y, from, color }`
    - Relay `chat.send { message }` as `chat.message { from, message }`

    Rooms are created on demand and kept in memory.
    """
    # Validate auth token
    token = extract_token(ws)
    if not token:
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    username: str | None = None

    # Create room on demand
    async with ws_manager.lock:
        ws_manager.rooms.setdefault(room_id, set())
        ws_manager.room_users.setdefault(room_id, set())
        ws_manager.room_colors.setdefault(room_id, {})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"message": "invalid-json"}}
                    )
                )
                continue

            msg_type = data.get("type")
            payload = data.get("payload", {})

            if msg_type == "client.hello":
                username = str(payload.get("username"))
                async with ws_manager.lock:
                    ws_manager.rooms[room_id].add(ws)
                    ws_manager.room_users[room_id].add(username)
                await ws_manager.send(
                    ws, {"type": "room.joined", "payload": {"room_id": room_id}}
                )

                # Broadcast presence
                await ws_manager.broadcast_room(
                    room_id,
                    sender=ws,
                    obj={"type": "room.user_joined", "payload": {"username": username}},
                )
                continue

            if username is None:
                await ws_manager.send(
                    ws, {"type": "error", "payload": {"message": "hello-first"}}
                )
                continue

            if msg_type == "move.play":
                x = int(payload.get("x", -1))
                y = int(payload.get("y", -1))
                color = ws_manager.room_colors.get(room_id, {}).get(username)
                await ws_manager.broadcast_room(
                    room_id,
                    sender=ws,
                    obj={
                        "type": "move.played",
                        "payload": {"x": x, "y": y, "from": username, "color": color},
                    },
                )
                continue

            if msg_type == "chat.send":
                message = str(payload.get("message", ""))
                await ws_manager.broadcast_room(
                    room_id,
                    sender=None,
                    obj={
                        "type": "chat.message",
                        "payload": {"from": username, "message": message},
                    },
                )
                continue

            if msg_type == "room.leave":
                async with ws_manager.lock:
                    if room_id in ws_manager.rooms and ws in ws_manager.rooms[room_id]:
                        ws_manager.rooms[room_id].remove(ws)
                await ws_manager.send(
                    ws, {"type": "room.left", "payload": {"room_id": room_id}}
                )
                break

            await ws_manager.send(
                ws,
                {
                    "type": "error",
                    "payload": {"message": "unknown-message", "received": msg_type},
                },
            )

    except WebSocketDisconnect:
        async with ws_manager.lock:
            if room_id in ws_manager.rooms and ws in ws_manager.rooms[room_id]:
                ws_manager.rooms[room_id].remove(ws)
        # Broadcast user left if we know the username
        if username:
            await ws_manager.broadcast_room(
                room_id,
                sender=None,
                obj={"type": "room.user_left", "payload": {"username": username}},
            )
