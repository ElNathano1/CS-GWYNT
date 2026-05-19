"""
Database models and ORM configuration for the CS-GWYNT backend services.

This module provides:
- SQLAlchemy ORM models (User, Card, Friendship, Game, Message)
- Database engine initialization
- Password hashing utilities
- Session management

Models:
- User: Represents a player account with profile, level, and friends
- Card: Represents a card in the game with attributes and effects
- CardsCorrespondancy: Represents the many-to-many relationship between users and cards (card ownership)
- Effect: Represents an effect that can be applied by a card
- Trigger: Represents a trigger that can activate an effect based on game events
- Achievement: Represents an achievement that can be unlocked by users
- AchievementsCorrespondancy: Represents the many-to-many relationship between users and achievements (achievement ownership
- Friendship: Represents a directional friendship relationship between users
- Game: Represents a game record between two users
- Message: Represents a message sent between users
"""

from __future__ import annotations

from datetime import datetime
import os
import json
from typing import cast
from sqlalchemy import (
    Float,
    create_engine,
    text,
    inspect,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship, Session
import hashlib

# Créer la base de données
engine = create_engine(os.environ["DATABASE_URL"], echo=False)
Base = declarative_base()


class User(Base):
    """
    SQLAlchemy ORM model for a user account.

    Attributes:
        id: Primary key
        username: Unique username (indexed for fast lookup)
        display_name: Display name of the user
        password_hash: SHA-256 hash of password
        profile_picture: Path identifier for user's profile picture

        level: Level (for progression)
        rank: Rank (for matchmaking)
        money: In-game currency balance

        is_connected: Connection status (1=connected, 0=offline)
        in_game: Game status (1=in game, 0=not in game)
        nbr_games: Total number of games played
        nbr_wins: Total number of games won

        friendships_initiated: List of friendships where this user is the initiator
        friendships_received: List of friendships where this user is the friend

        cards: List of cards owned by the user (for deck composing)
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_connected IN (0, 1)", name="ck_users_is_connected_bool"),
        CheckConstraint("in_game IN (0, 1)", name="ck_users_in_game_bool"),
        CheckConstraint("level >= 0", name="ck_users_level_non_negative"),
        CheckConstraint("`rank` >= 0", name="ck_users_rank_non_negative"),
        CheckConstraint("money >= 0", name="ck_users_money_non_negative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(64), nullable=False)
    profile_picture = Column(String(255), nullable=True)

    level = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    money = Column(Integer, default=0)

    is_connected = Column(Integer, nullable=False, default=0)
    in_game = Column(Integer, nullable=False, default=0)

    # Relations
    friendships_initiated = relationship(
        "Friendship",
        foreign_keys="Friendship.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    friendships_received = relationship(
        "Friendship",
        foreign_keys="Friendship.friend_id",
        back_populates="friend",
        cascade="all, delete-orphan",
    )

    messages_sent = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    messages_received = relationship(
        "Message",
        foreign_keys="Message.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan",
    )

    cards = relationship(
        "CardsCorrespondancy",
        foreign_keys="CardsCorrespondancy.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    loot_boxes = relationship(
        "UserLootBoxCorrespondancy",
        foreign_keys="UserLootBoxCorrespondancy.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    games_as_player1 = relationship(
        "Game",
        foreign_keys="Game.player1_id",
        back_populates="player1",
        cascade="all, delete-orphan",
    )
    games_as_player2 = relationship(
        "Game",
        foreign_keys="Game.player2_id",
        back_populates="player2",
        cascade="all, delete-orphan",
    )

    achievements = relationship(
        "AchievementsCorrespondancy",
        foreign_keys="AchievementsCorrespondancy.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username}, display_name={self.display_name}, level={self.level}, rank={self.rank})"

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using SHA-256.

        Args:
            password: The plaintext password to hash

        Returns:
            Hexadecimal SHA-256 hash of the password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def add_friend(self, friend: User, session: Session) -> None:
        """
        Add a friend to this user's friend list.

        Args:
            friend: The User object to add as friend
            session: SQLAlchemy session for database operations
        """
        if not self.is_friend(friend):
            friendship = Friendship(user_id=self.id, friend_id=friend.id)
            session.add(friendship)
            session.commit()

    def remove_friend(self, friend: User, session: Session) -> None:
        """
        Remove a friend from this user's friend list.

        Args:
            friend: The User object to remove from friends
            session: SQLAlchemy session for database operations
        """
        friendship = (
            session.query(Friendship)
            .filter(
                (Friendship.user_id == self.id) & (Friendship.friend_id == friend.id)
            )
            .first()
        )
        if friendship:
            session.delete(friendship)
            session.commit()

    def is_friend(self, friend: User) -> bool:
        """
        Check if another user is a friend of this user.

        Args:
            friend: The User object to check

        Returns:
            True if user is a friend, False otherwise
        """
        return any(f.friend_id == friend.id for f in self.friendships_initiated)

    def get_friends(self) -> list[User]:
        """
        Get list of all friends of this user.

        Returns:
            List of User objects that are friends
        """
        return [f.friend for f in self.friendships_initiated]

    def get_friend_count(self) -> int:
        """
        Get the number of friends.

        Returns:
            Integer count of friends
        """
        return len(self.friendships_initiated)

    def send_message(
        self, recipient: User, content: str, session: Session, type: str = "message"
    ) -> None:
        """
        Send a message to another user.

        Args:
            recipient: The User object to send the message to
            content: The text content of the message
            session: SQLAlchemy session for database operations
            type: The type of the message (e.g., "message", "friend invite", "game invite")
        """
        message = Message(
            sender_id=self.id,
            recipient_id=recipient.id,
            content=content,
            type=type,
            timestamp=datetime.utcnow(),
        )
        session.add(message)
        session.commit()

    def remove_message(self, message: Message, session: Session) -> None:
        """
        Remove a message from the user's inbox.

        Args:
            message: The Message object to remove
            session: SQLAlchemy session for database operations
        """
        if message in self.messages_received:
            session.delete(message)
            session.commit()

    def get_messages(self) -> list[Message]:
        """
        Get list of all messages received by this user.

        Returns:
            List of Message objects that this user has received
        """
        return self.messages_received

    def get_sent_messages(self) -> list[Message]:
        """
        Get list of all messages sent by this user.

        Returns:
            List of Message objects that this user has sent
        """
        return self.messages_sent

    def send_friend_invitation(self, recipient: User, session: Session) -> None:
        """
        Send a friend invitation to another user.

        Args:
            recipient: The User object to send the friend invitation to
            session: SQLAlchemy session for database operations
        """
        self.add_friend(recipient, session)
        self.send_message(
            recipient=recipient,
            content=f"{self.display_name} has sent you a friend invitation.",
            session=session,
            type="friend invite",
        )

    def accept_friend_invitation(self, sender: User, session: Session) -> None:
        """
        Accept a friend invitation from another user.

        Args:
            sender: The User object who sent the friend invitation
            session: SQLAlchemy session for database operations
        """
        invitation = (
            session.query(Message)
            .filter(
                (Message.sender_id == sender.id)
                & (Message.recipient_id == self.id)
                & (Message.type == "friend invite")
            )
            .first()
        )
        if invitation:
            self.add_friend(sender, session)
            self.send_message(
                recipient=sender,
                content=f"{self.display_name} has accepted your friend invitation.",
                session=session,
                type="message",
            )
            invitation.type = "message"  # type: ignore # Mark invitation as handled
            session.commit()

    def decline_friend_invitation(self, sender: User, session: Session) -> None:
        """
        Decline a friend invitation from another user.

        Args:
            sender: The User object who sent the friend invitation
            session: SQLAlchemy session for database operations
        """
        invitation = (
            session.query(Message)
            .filter(
                (Message.sender_id == sender.id)
                & (Message.recipient_id == self.id)
                & (Message.type == "friend invite")
            )
            .first()
        )
        if invitation:
            sender.remove_friend(self, session)
            self.send_message(
                recipient=sender,
                content=f"{self.display_name} has declined your friend invitation.",
                session=session,
                type="message",
            )
            invitation.type = "message"  # type: ignore # Mark invitation as handled
            session.commit()

    def get_friend_invitations(self) -> list[Message]:
        """
        Get list of all pending friend invitations received by this user.

        Returns:
            List of Message objects that are pending friend invitations
        """
        return [
            message
            for message in self.messages_received
            if message.type == "friend invite"  # type: ignore
        ]

    def send_game_invitation(self, recipient: User, session: Session) -> None:
        """
        Send a game invitation to another user.

        Args:
            recipient: The User object to send the game invitation to
            session: SQLAlchemy session for database operations
        """
        self.send_message(
            recipient=recipient,
            content=f"{self.display_name} has sent you a game invitation.",
            session=session,
            type="game invite",
        )

    def accept_game_invitation(self, sender: User, session: Session) -> None:
        """
        Accept a game invitation from another user.

        Args:
            sender: The User object who sent the game invitation
            session: SQLAlchemy session for database operations
        """
        invitation = (
            session.query(Message)
            .filter(
                (Message.sender_id == sender.id)
                & (Message.recipient_id == self.id)
                & (Message.type == "game invite")
            )
            .first()
        )
        if invitation:
            # Here you would typically create a new Game record and notify both players
            invitation.type = "message"  # type: ignore # Mark invitation as handled
            session.commit()

    def decline_game_invitation(self, sender: User, session: Session) -> None:
        """
        Decline a game invitation from another user.

        Args:
            sender: The User object who sent the game invitation
            session: SQLAlchemy session for database operations
        """
        invitation = (
            session.query(Message)
            .filter(
                (Message.sender_id == sender.id)
                & (Message.recipient_id == self.id)
                & (Message.type == "game invite")
            )
            .first()
        )
        if invitation:
            self.send_message(
                recipient=sender,
                content=f"{self.display_name} has declined your game invitation.",
                session=session,
                type="message",
            )
            invitation.type = "message"  # type: ignore # Mark invitation as handled
            session.commit()

    def get_game_invitations(self) -> list[Message]:
        """
        Get list of all pending game invitations received by this user.

        Returns:
            List of Message objects that are pending game invitations
        """
        return [
            message
            for message in self.messages_received
            if message.type == "game invite"  # type: ignore
        ]

    def add_card(self, card: Card, quantity: int, session: Session) -> None:
        """
        Add a card to the user's collection.

        Args:
            card: The Card object to add
            quantity: The number of copies of the card to add
            session: SQLAlchemy session for database operations
        """
        correspondance = (
            session.query(CardsCorrespondancy)
            .filter(
                (CardsCorrespondancy.user_id == self.id)
                & (CardsCorrespondancy.card_id == card.id)
            )
            .first()
        )
        if correspondance:
            correspondance.quantity += quantity  # type: ignore
        else:
            new_correspondance = CardsCorrespondancy(
                user_id=self.id, card_id=card.id, quantity=quantity
            )
            session.add(new_correspondance)
        session.commit()

    def remove_card(self, card: Card, quantity: int, session: Session) -> None:
        """
        Remove a card from the user's collection.

        Args:
            card: The Card object to remove
            quantity: The number of copies of the card to remove
            session: SQLAlchemy session for database operations
        """
        correspondance = (
            session.query(CardsCorrespondancy)
            .filter(
                (CardsCorrespondancy.user_id == self.id)
                & (CardsCorrespondancy.card_id == card.id)
            )
            .first()
        )
        if correspondance:
            if correspondance.quantity > quantity:  # type: ignore
                correspondance.quantity -= quantity  # type: ignore
                session.commit()
            elif correspondance.quantity == quantity:  # type: ignore
                session.delete(correspondance)
                session.commit()
            else:
                raise ValueError("Cannot remove more cards than owned")
        else:
            raise ValueError("Card not found in user's collection")

    def get_cards(self) -> list[Card]:
        """
        Get list of all cards owned by the user.

        Returns:
            List of Card objects that the user owns
        """
        return [correspondance.card for correspondance in self.cards]

    def get_card_quantity(self, card: Card, session: Session) -> int:
        """
        Get the quantity of a specific card owned by the user.

        Args:
            card: The Card object to check

        Returns:
            Integer quantity of the specified card owned by the user
        """
        correspondance = (
            session.query(CardsCorrespondancy)
            .filter(
                (CardsCorrespondancy.user_id == self.id)
                & (CardsCorrespondancy.card_id == card.id)
            )
            .first()
        )
        return correspondance.quantity if correspondance else 0  # type: ignore

    def get_games(self) -> list[Game]:
        """
        Get list of all games played by this user.

        Returns:
            List of Game objects that this user has played
        """
        return [*self.games_as_player1, *self.games_as_player2]

    def get_game_count(self) -> int:
        """
        Get the number of games played.

        Returns:
            Integer count of games played
        """
        return len(self.get_games())

    def get_win_count(self) -> int:
        """
        Get the number of games won by this user.

        Returns:
            Integer count of games won
        """
        return len([game for game in self.get_games() if game.get_winner() == self.id])

    def add_achievement(self, achievement: Achievement, session: Session) -> None:
        """
        Add an achievement to the user's profile.

        Args:
            achievement: The Achievement object to add
            session: SQLAlchemy session for database operations
        """
        correspondance = (
            session.query(AchievementsCorrespondancy)
            .filter(
                (AchievementsCorrespondancy.user_id == self.id)
                & (AchievementsCorrespondancy.achievement_id == achievement.id)
            )
            .first()
        )
        if not correspondance:
            new_correspondance = AchievementsCorrespondancy(
                user_id=self.id,
                achievement_id=achievement.id,
                date_unlocked=datetime.utcnow(),
            )
            session.add(new_correspondance)
            session.commit()

    def get_achievements(self) -> list[Achievement]:
        """
        Get list of all achievements unlocked by the user.

        Returns:
            List of Achievement objects that the user has unlocked
        """
        return [correspondance.achievement for correspondance in self.achievements]


class Card(Base):
    """
    SQLAlchemy ORM model for a card.

    Attributes:
        id: Primary key
        name: Name of the card
        description: Description of the card
        rarity: Rarity of the card (e.g., "common", "rare")
        power_table: Power table identifier for the card (for gameplay)

        effect: Effect (effect applied by the card)

        buying_price: The in-game currency cost to buy the card
        selling_price: The in-game currency value when selling the card
    """

    __tablename__ = "cards"
    __table_args__ = (Index("ix_cards_rarity", "rarity"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    rarity = Column(String(20), nullable=False)
    power_table = Column(Text, nullable=False)
    face_artwork_url = Column(String(255), nullable=True)
    back_artwork_url = Column(String(255), nullable=True)
    animations = Column(Text, nullable=True)
    effect_id = Column(Integer, ForeignKey("effects.id"), nullable=True)
    buying_price = Column(Integer, nullable=False, default=0)
    selling_price = Column(Integer, nullable=False, default=0)

    # Relations
    effect = relationship("Effect", foreign_keys=[effect_id], back_populates="cards")
    correspondances = relationship(
        "CardsCorrespondancy",
        foreign_keys="CardsCorrespondancy.card_id",
        back_populates="card",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Card(id={self.id}, name={self.name}, description={self.description}, rarity={self.rarity}, power_table={self.power_table}, effect={{{self.effect.__repr__() if self.effect else 'None'}}}, buying_price={self.buying_price}, selling_price={self.selling_price})"

    def set_animations(self, animations: dict[str, object] | None) -> None:
        """Persist card animations payload as JSON text."""

        self.animations = json.dumps(animations) if animations is not None else None

    def get_animations(self) -> dict[str, object] | None:
        """Rebuild card animations payload from JSON text."""

        payload = cast(str | None, self.animations)
        if payload is None:
            return None
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return None


class CardsCorrespondancy(Base):
    """
    SQLAlchemy ORM model for the many-to-many relationship between users and cards.

    Attributes:
        id: Primary key
        user_id: Foreign key to User (card owner)
        card_id: Foreign key to Card (card owned)
        quantity: Number of copies of the card owned by the user
    """

    __tablename__ = "cards_correspondancy"
    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_cards_correspondancy"),
        CheckConstraint("quantity >= 0", name="ck_cards_correspondancy_quantity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", foreign_keys=[user_id], back_populates="cards")
    card = relationship(
        "Card", foreign_keys=[card_id], back_populates="correspondances"
    )

    def __repr__(self) -> str:
        return f"CardsCorrespondancy(user_id={self.user_id}, card_id={self.card_id}, quantity={self.quantity})"


class Effect(Base):
    """
    SQLAlchemy ORM model for an effect.

    Attributes:
        id: Primary key
        name: Name of the effect
        description: Description of the effect
        type: Type of the effect (e.g., "damage", "heal")
        value: Value associated with the effect (e.g., damage amount)
    """

    __tablename__ = "effects"
    __table_args__ = (Index("ix_effects_type", "type"),)

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)
    artwork = Column(String(255), nullable=True)
    target_shape = Column(String(20), nullable=True)
    target_payload = Column(Text, nullable=True)
    animations = Column(Text, nullable=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"), nullable=False)
    value = Column(Integer, nullable=True)
    value_json = Column(Text, nullable=True)

    # Relations
    trigger = relationship(
        "Trigger", foreign_keys=[trigger_id], back_populates="effect", uselist=False
    )
    cards = relationship("Card", foreign_keys="Card.effect_id", back_populates="effect")

    def __repr__(self) -> str:
        return f"Effect(id={self.id}, description={self.description}, type={self.type}, trigger={self.trigger.__repr__() if self.trigger else 'None'}, value={self.value}, value_json={self.value_json})"

    def set_artwork(self, artwork: str | None) -> None:
        """Persist effect artwork path."""

        self.artwork = artwork

    def set_target(self, target: dict[str, object] | None) -> None:
        """Persist effect target payload in normalized columns."""

        if target is None:
            self.target_shape = None
            self.target_payload = None
            return

        self.target_shape = str(target.get("shape", "single"))
        self.target_payload = json.dumps(target)

    def get_target(self) -> dict[str, object] | None:
        """Rebuild effect target payload from normalized columns."""

        payload = cast(str | None, self.target_payload)
        if payload is None:
            return None
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return None

    def set_value_data(self, value_data: int | dict[str, object] | None) -> None:
        """Persist typed effect value in int or JSON form."""

        if value_data is None:
            self.value = None
            self.value_json = None
            return

        if isinstance(value_data, int):
            self.value = value_data
            self.value_json = None
            return

        self.value = None
        self.value_json = json.dumps(value_data)

    def get_value_data(self) -> int | dict[str, object] | None:
        """Return typed effect value from int/JSON storage."""

        value_json = cast(str | None, self.value_json)
        if value_json is not None:
            data = json.loads(value_json)
            if isinstance(data, dict):
                return data
            return None
        value_int = cast(int | None, self.value)
        return value_int

    def set_animations(self, animations: dict[str, object] | None) -> None:
        """Persist effect animations payload as JSON text."""

        self.animations = json.dumps(animations) if animations is not None else None

    def get_animations(self) -> dict[str, object] | None:
        """Rebuild effect animations payload from JSON text."""

        payload = cast(str | None, self.animations)
        if payload is None:
            return None
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return None


class Trigger(Base):
    """
    SQLAlchemy ORM model for a trigger.

    Attributes:
        id: Primary key
        name: Name of the trigger
        description: Description of the trigger
        type: Type of the trigger (e.g., "on play", "on discard")
    """

    __tablename__ = "triggers"
    __table_args__ = (
        CheckConstraint("countdown >= 0", name="ck_triggers_countdown_non_negative"),
        CheckConstraint(
            "repeat_interval >= 0", name="ck_triggers_repeat_interval_non_negative"
        ),
        CheckConstraint(
            "repeat_limit IS NULL OR repeat_limit > 0",
            name="ck_triggers_repeat_limit_positive",
        ),
        CheckConstraint(
            "initially_active IN (0, 1)", name="ck_triggers_initially_active_bool"
        ),
        Index("ix_triggers_event", "event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String(20), nullable=False)

    activate_on_logic = Column(String(20), nullable=True)
    activate_on_conditions = Column(Text, nullable=True)
    deactivate_on_logic = Column(String(20), nullable=True)
    deactivate_on_conditions = Column(Text, nullable=True)
    fire_when_logic = Column(String(20), nullable=True)
    fire_when_conditions = Column(Text, nullable=True)

    countdown = Column(Integer, nullable=False, default=0)
    repeat_limit = Column(Integer, nullable=True)
    repeat_interval = Column(Integer, nullable=False, default=0)
    initially_active = Column(Integer, nullable=False, default=1)

    # Relations
    effect = relationship(
        "Effect",
        foreign_keys="Effect.trigger_id",
        back_populates="trigger",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"Trigger(id={self.id}, event={self.event}, activate_on_logic={self.activate_on_logic}, activate_on_conditions={self.activate_on_conditions}, deactivate_on_logic={self.deactivate_on_logic}, deactivate_on_conditions={self.deactivate_on_conditions}, fire_when_logic={self.fire_when_logic}, fire_when_conditions={self.fire_when_conditions}, countdown={self.countdown}, repeat_limit={self.repeat_limit}, repeat_interval={self.repeat_interval}, initially_active={self.initially_active})"

    def set_condition_group(
        self,
        group: str,
        logic: str | None,
        conditions: list[dict[str, object]] | None,
    ) -> None:
        """Store trigger condition group in logic/text columns."""

        if group not in {"activate", "deactivate", "fire_when"}:
            raise ValueError("group must be one of: activate, deactivate, fire_when")

        logic_value = logic if logic is not None else None
        conditions_value = json.dumps(conditions) if conditions is not None else None

        if group == "activate":
            self.activate_on_logic = logic_value
            self.activate_on_conditions = conditions_value
        elif group == "deactivate":
            self.deactivate_on_logic = logic_value
            self.deactivate_on_conditions = conditions_value
        else:
            self.fire_when_logic = logic_value
            self.fire_when_conditions = conditions_value

    def get_condition_group(self, group: str) -> dict[str, object] | None:
        """Read trigger condition group from logic/text columns."""

        if group not in {"activate", "deactivate", "fire_when"}:
            raise ValueError("group must be one of: activate, deactivate, fire_when")

        if group == "activate":
            logic = self.activate_on_logic
            raw_conditions = self.activate_on_conditions
        elif group == "deactivate":
            logic = self.deactivate_on_logic
            raw_conditions = self.deactivate_on_conditions
        else:
            logic = self.fire_when_logic
            raw_conditions = self.fire_when_conditions

        if logic is None and raw_conditions is None:
            return None

        parsed_conditions: list[dict[str, object]] = []
        raw_conditions_str = cast(str | None, raw_conditions)
        if raw_conditions_str is not None:
            decoded = json.loads(raw_conditions_str)
            if isinstance(decoded, list):
                parsed_conditions = [x for x in decoded if isinstance(x, dict)]

        return {
            "logic": logic,
            "conditions": parsed_conditions,
        }


class LootBox(Base):
    """
    SQLAlchemy ORM model for a loot box.

    Attributes:
        id: Primary key
        name: Name of the loot box
        description: Description of the loot box
        price: The in-game currency cost to buy the loot box

        mandatory_cards: List of cards that are guaranteed to be included in the loot box
        random_cards: List of cards that can be randomly included in the loot box
    """

    __tablename__ = "loot_boxes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False, default=0)
    artwork = Column(String(255), nullable=True)
    animations = Column(Text, nullable=True)
    nbr_random_cards = Column(Integer, nullable=False, default=0)

    # Relations
    mandatory_cards = relationship(
        "LootBoxMandatoryCards",
        foreign_keys="LootBoxMandatoryCards.loot_box_id",
        back_populates="loot_box",
        cascade="all, delete-orphan",
    )
    random_cards = relationship(
        "LootBoxRandomCards",
        foreign_keys="LootBoxRandomCards.loot_box_id",
        back_populates="loot_box",
        cascade="all, delete-orphan",
    )

    correspondances = relationship(
        "UserLootBoxCorrespondancy",
        foreign_keys="UserLootBoxCorrespondancy.loot_box_id",
        back_populates="loot_box",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"LootBox(id={self.id}, name={self.name}, description={self.description}, price={self.price})"

    def set_animations(self, animations: dict[str, object] | None) -> None:
        """Persist loot box animations payload as JSON text."""

        self.animations = json.dumps(animations) if animations is not None else None

    def get_animations(self) -> dict[str, object] | None:
        """Rebuild loot box animations payload from JSON text."""

        payload = cast(str | None, self.animations)
        if payload is None:
            return None
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return None


class LootBoxMandatoryCards(Base):
    """
    SQLAlchemy ORM model for the mandatory cards included in a loot box.

    Attributes:
        id: Primary key
        loot_box_id: Foreign key to LootBox (the loot box this card belongs to)
        card_id: Foreign key to Card (the card that is included in the loot box)
    """

    __tablename__ = "loot_box_mandatory_cards"

    id = Column(Integer, primary_key=True, index=True)
    loot_box_id = Column(Integer, ForeignKey("loot_boxes.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    loot_box = relationship(
        "LootBox",
        foreign_keys=[loot_box_id],
        back_populates="mandatory_cards",
    )
    card = relationship("Card", foreign_keys=[card_id])


class LootBoxRandomCards(Base):
    """
    SQLAlchemy ORM model for the random cards included in a loot box.

    Attributes:
        id: Primary key
        loot_box_id: Foreign key to LootBox (the loot box this count belongs to)
        card_id: Foreign key to Card (the card that is included in the loot box)
        count: The number of random cards included in the loot box
        probability: The probability of this card being included in the loot box
    """

    __tablename__ = "loot_box_random_cards"

    id = Column(Integer, primary_key=True, index=True)
    loot_box_id = Column(Integer, ForeignKey("loot_boxes.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    probability = Column(Float, nullable=False, default=0.0)

    loot_box = relationship(
        "LootBox",
        foreign_keys=[loot_box_id],
        back_populates="random_cards",
    )
    card = relationship("Card", foreign_keys=[card_id])


class UserLootBoxCorrespondancy(Base):
    """
    SQLAlchemy ORM model for the many-to-many relationship between users and loot boxes.

    Attributes:
        id: Primary key
        user_id: Foreign key to User (loot box owner)
        loot_box_id: Foreign key to LootBox (loot box owned)
        quantity: Number of copies of the loot box owned by the user
    """

    __tablename__ = "user_loot_box_correspondancy"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "loot_box_id", name="uq_user_loot_box_correspondancy"
        ),
        CheckConstraint(
            "quantity >= 0", name="ck_user_loot_box_correspondancy_quantity"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loot_box_id = Column(Integer, ForeignKey("loot_boxes.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", foreign_keys=[user_id], back_populates="loot_boxes")
    loot_box = relationship(
        "LootBox",
        foreign_keys=[loot_box_id],
        back_populates="correspondances",
    )


class Achievement(Base):
    """
    SQLAlchemy ORM model for an achievement.

    Attributes:
        id: Primary key
        name: Name of the achievement
        description: Description of the achievement
        criteria: Criteria for unlocking the achievement (e.g., "win 10 games")
        illustration: Optional thumbnail/illustration path or URL
    """

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    criteria = Column(Text, nullable=False)
    illustration = Column(String(255), nullable=True)

    # Relations
    correspondances = relationship(
        "AchievementsCorrespondancy",
        foreign_keys="AchievementsCorrespondancy.achievement_id",
        back_populates="achievement",
        cascade="all, delete-orphan",
    )


class AchievementsCorrespondancy(Base):
    """
    SQLAlchemy ORM model for the many-to-many relationship between users and achievements.

    Attributes:
        id: Primary key
        user_id: Foreign key to User (achievement owner)
        achievement_id: Foreign key to Achievement (achievement unlocked)
        date_unlocked: Timestamp of when the achievement was unlocked
    """

    __tablename__ = "achievements_correspondancy"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "achievement_id", name="uq_achievements_correspondancy"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    date_unlocked = Column(DateTime, nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="achievements")
    achievement = relationship(
        "Achievement",
        foreign_keys=[achievement_id],
        back_populates="correspondances",
    )

    def __repr__(self) -> str:
        return f"AchievementsCorrespondancy(user_id={self.user_id}, achievement_id={self.achievement_id}, date_unlocked={self.date_unlocked})"


class Friendship(Base):
    """
    SQLAlchemy ORM model for a friendship relationship between two users.

    Represents a directional friendship from user_id to friend_id.
    Includes a unique constraint to prevent duplicate friendships.

    Attributes:
        id: Primary key
        user_id: Foreign key to User (friend initiator)
        friend_id: Foreign key to User (friend being followed)
        user: Relationship to the initiating User
        friend: Relationship to the friend User
    """

    __tablename__ = "friendships"

    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friendship"),
        CheckConstraint("user_id <> friend_id", name="ck_friendship_not_self"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="friendships_initiated"
    )
    friend = relationship(
        "User", foreign_keys=[friend_id], back_populates="friendships_received"
    )

    def __repr__(self) -> str:
        return f"Friendship(user_id={self.user_id}, friend_id={self.friend_id})"


class Game(Base):
    """
    SQLAlchemy ORM model for a game record.

    Attributes:
        id: Primary key
        black_player_id: Foreign key to User (first player)
        white_player_id: Foreign key to User (second player)
        timestamp: Timestamp of when the game was played
        result: String representing the game result (e.g., "1-0", "0-1", "0.5-0.5")
        moves: String representing the sequence of moves in the game
    """

    __tablename__ = "games"

    __table_args__ = (
        UniqueConstraint("player1_id", "player2_id", "timestamp", name="uq_game"),
        CheckConstraint("player1_id <> player2_id", name="ck_game_distinct_players"),
        CheckConstraint(
            "nbr_rounds_player1 >= 0", name="ck_game_rounds_player1_non_negative"
        ),
        CheckConstraint(
            "nbr_rounds_player2 >= 0", name="ck_game_rounds_player2_non_negative"
        ),
        Index("ix_games_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    finished = Column(Integer, nullable=False, default=0)
    nbr_rounds_player1 = Column(Integer, nullable=False)
    nbr_rounds_player2 = Column(Integer, nullable=False)
    replay_data = Column(Text, nullable=True)

    player1 = relationship(
        "User", foreign_keys=[player1_id], back_populates="games_as_player1"
    )
    player2 = relationship(
        "User", foreign_keys=[player2_id], back_populates="games_as_player2"
    )

    def __repr__(self) -> str:
        return f"Game(id={self.id}, player1_id={self.player1_id}, player2_id={self.player2_id}, timestamp={self.timestamp}, finished={self.finished}, nbr_rounds_player1={self.nbr_rounds_player1}, nbr_rounds_player2={self.nbr_rounds_player2})"

    def finish_game(
        self, nbr_rounds_player1: int, nbr_rounds_player2: int, replay_data: str | None
    ) -> None:
        """
        Mark the game as finished and set the number of rounds won by each player.

        Args:
            nbr_rounds_player1: Number of rounds won by player 1
            nbr_rounds_player2: Number of rounds won by player 2
            replay_data: Optional string data representing the game replay
        """
        self.finished = 1  # type: ignore
        self.nbr_rounds_player1 = nbr_rounds_player1  # type: ignore
        self.nbr_rounds_player2 = nbr_rounds_player2  # type: ignore
        self.replay_data = replay_data

    def is_finished(self) -> bool:
        """
        Check if the game has finished.

        Returns:
            True if the game is finished, False otherwise
        """
        return self.finished == 1  # type: ignore

    def get_winner(self) -> int:
        """
        Determine the winner of the game based on the number of rounds won.

        Returns:
            player1_id if player 1 wins, player2_id if player 2 wins, or 0 for a draw
        """
        if not self.is_finished():
            raise ValueError("Game is not finished yet")

        if self.nbr_rounds_player1 > self.nbr_rounds_player2:  # type: ignore
            return self.player1_id  # type: ignore
        elif self.nbr_rounds_player2 > self.nbr_rounds_player1:  # type: ignore
            return self.player2_id  # type: ignore
        else:
            return 0  # Draw


class Message(Base):
    """
    SQLAlchemy ORM model for a message sent between users.

    Attributes:
        id: Primary key
        sender_id: Foreign key to User (message sender)
        recipient_id: Foreign key to User (message recipient)
        timestamp: Timestamp of when the message was sent
        content: Text content of the message
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(
        String(20), nullable=False, default="message"
    )  # e.g., "message", "friend invite", "game invite", "system message"
    timestamp = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)

    sender = relationship(
        "User", foreign_keys=[sender_id], back_populates="messages_sent"
    )
    recipient = relationship(
        "User", foreign_keys=[recipient_id], back_populates="messages_received"
    )

    def __repr__(self) -> str:
        return f"Message(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, timestamp={self.timestamp})"

    def __str__(self) -> str:
        return f"Message from User {self.sender_id} to User {self.recipient_id} at {self.timestamp}:\n{self.content}"

    def is_friend_invitation(self) -> bool:
        """
        Check if the message content indicates a friend invitation.

        Returns:
            True if the message is a friend invitation, False otherwise
        """
        return self.type == "friend invite"  # type: ignore

    def is_game_invitation(self) -> bool:
        """
        Check if the message content indicates a game invitation.

        Returns:
            True if the message is a game invitation, False otherwise
        """
        return self.type == "game invite"  # type: ignore


# Database initialization
def init_db():
    """Initialize database and create all tables."""
    Base.metadata.create_all(bind=engine)


def ensure_schema() -> None:
    """Ensure required columns exist without failing on redeploys."""
    if os.environ.get("SKIP_SCHEMA_CHECK", "0").lower() in {"1", "true", "yes"}:
        return

    # Ensure all declared tables exist (safe: creates only missing tables)
    Base.metadata.create_all(bind=engine)

    def add_missing_columns(table_name: str, columns_sql: dict[str, str]) -> None:
        inspector = inspect(engine)
        if not inspector.has_table(table_name):
            return

        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        missing_columns = [
            (column_name, sql_def)
            for column_name, sql_def in columns_sql.items()
            if column_name not in existing_columns
        ]
        if not missing_columns:
            return

        with engine.begin() as connection:
            for column_name, sql_def in missing_columns:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_def}")
                )

    add_missing_columns(
        "users",
        {
            "is_connected": "INTEGER NOT NULL DEFAULT 0",
            "in_game": "INTEGER NOT NULL DEFAULT 0",
            "level": "INTEGER NOT NULL DEFAULT 0",
            "rank": "INTEGER NOT NULL DEFAULT 0",
            "money": "INTEGER NOT NULL DEFAULT 0",
        },
    )

    add_missing_columns(
        "messages",
        {
            "type": "VARCHAR(20) NOT NULL DEFAULT 'message'",
        },
    )

    add_missing_columns(
        "games",
        {
            "finished": "INTEGER NOT NULL DEFAULT 0",
            "replay_data": "TEXT",
        },
    )

    add_missing_columns(
        "cards",
        {
            "face_artwork_url": "VARCHAR(255)",
            "back_artwork_url": "VARCHAR(255)",
            "animations": "TEXT",
            "buying_price": "INTEGER NOT NULL DEFAULT 0",
            "selling_price": "INTEGER NOT NULL DEFAULT 0",
        },
    )

    add_missing_columns(
        "effects",
        {
            "artwork": "VARCHAR(255)",
            "target_shape": "VARCHAR(20)",
            "target_payload": "TEXT",
            "animations": "TEXT",
            "value_json": "TEXT",
        },
    )

    add_missing_columns(
        "triggers",
        {
            "event": "VARCHAR(20) NOT NULL DEFAULT 'on_play'",
            "activate_on_logic": "VARCHAR(20)",
            "activate_on_conditions": "TEXT",
            "deactivate_on_logic": "VARCHAR(20)",
            "deactivate_on_conditions": "TEXT",
            "fire_when_logic": "VARCHAR(20)",
            "fire_when_conditions": "TEXT",
            "countdown": "INTEGER NOT NULL DEFAULT 0",
            "repeat_limit": "INTEGER",
            "repeat_interval": "INTEGER NOT NULL DEFAULT 0",
            "initially_active": "INTEGER NOT NULL DEFAULT 1",
        },
    )

    add_missing_columns(
        "loot_boxes",
        {
            "price": "INTEGER NOT NULL DEFAULT 0",
            "artwork": "VARCHAR(255)",
            "animations": "TEXT",
            "nbr_random_cards": "INTEGER NOT NULL DEFAULT 0",
        },
    )

    add_missing_columns(
        "loot_box_mandatory_cards",
        {
            "quantity": "INTEGER NOT NULL DEFAULT 1",
        },
    )

    add_missing_columns(
        "loot_box_random_cards",
        {
            "count": "INTEGER NOT NULL DEFAULT 0",
            "probability": "FLOAT NOT NULL DEFAULT 0.0",
        },
    )

    add_missing_columns(
        "user_loot_box_correspondancy",
        {
            "quantity": "INTEGER NOT NULL DEFAULT 1",
        },
    )

    add_missing_columns(
        "achievements",
        {
            "illustration": "VARCHAR(255)",
        },
    )


def get_session() -> Session:
    """
    Get a new SQLAlchemy session.

    Returns:
        A new Session bound to the database engine
    """
    return Session(engine)


ensure_schema()
