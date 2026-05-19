"""
Data access layer for user account operations using the Repository pattern.

This module provides the AccountRepository class which encapsulates all database
operations for user accounts, friendships, messaging, game history, cards, and
achievements. It translates between SQLAlchemy ORM models and the Account
business logic class and is designed to back every FastAPI route.

Classes:
- AccountRepository: Repository pattern implementation for User data access
"""

from datetime import datetime

from sqlalchemy.orm import Session

from database.account import Account
from database.achievement import AchievementDTO as _AchDTO
from database.card import CardDTO as _CardDTO
from database.effect_repository import EffectRepository
from database.loot_box_repository import LootBoxRepository
from database.models import (
    Achievement,
    AchievementsCorrespondancy,
    Card,
    CardsCorrespondancy,
    Friendship,
    Game,
    LootBox,
    Message,
    User,
    UserLootBoxCorrespondancy,
)
from typing import cast as _cast


class AccountRepository:
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    # internal helper

    def _orm_to_account(self, user: User) -> Account:
        """Convert a User ORM object to an Account DTO."""

        friends = [f.friend.username for f in user.friendships_initiated]  # type: ignore
        games = [*user.games_as_player1, *user.games_as_player2]  # type: ignore
        nbr_games = len(games)
        nbr_wins = len([g for g in games if g.get_winner() == user.id])
        effect_repo = EffectRepository(self.session)
        cards = [
            {
                "card": _CardDTO(
                    id=c.card.id,
                    name=c.card.name,
                    description=c.card.description,
                    rarity=c.card.rarity,
                    power_table=c.card.power_table,
                    face_artwork_url=_cast(str | None, c.card.face_artwork_url),
                    back_artwork_url=_cast(str | None, c.card.back_artwork_url),
                    animations=_cast(dict | None, c.card.get_animations()),
                    effect=(
                        effect_repo._orm_effect_to_dto(c.card.effect)
                        if c.card.effect
                        else None
                    ),
                    buying_price=c.card.buying_price,
                    selling_price=c.card.selling_price,
                ),
                "quantity": c.quantity,
            }
            for c in user.cards  # type: ignore
        ]
        achievements = [
            _AchDTO(
                id=c.achievement.id,  # type: ignore
                name=c.achievement.name,  # type: ignore
                description=c.achievement.description,  # type: ignore
                criteria=c.achievement.criteria,  # type: ignore
                illustration=c.achievement.illustration,  # type: ignore
            )
            for c in user.achievements  # type: ignore
        ]
        return Account(
            username=user.username,  # type: ignore
            password_hash=user.password_hash,  # type: ignore
            display_name=user.display_name,  # type: ignore
            level=user.level,  # type: ignore
            rank=user.rank,  # type: ignore
            profile_picture=user.profile_picture,  # type: ignore
            friends=friends,
            is_connected=user.is_connected,  # type: ignore
            in_game=user.in_game,  # type: ignore
            nbr_games=nbr_games,
            nbr_wins=nbr_wins,
            cards=cards,
            achievements=achievements,
        )

    # user CRUD

    def get_by_username(self, username: str) -> Account | None:
        """
        Retrieve a user account by username.

        Args:
            username: The username to search for

        Returns:
            Account object if user exists, None otherwise
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return None
        return self._orm_to_account(user)

    def get_all_users(self) -> list[Account]:
        """
        Retrieve all user accounts from the database.

        Returns:
            List of Account objects (empty list if no users exist)
        """
        users = self.session.query(User).all()
        return [self._orm_to_account(u) for u in users]

    def create(self, account: Account) -> None:
        """
        Create a new user account in the database.

        Args:
            account: The Account object to create
        """
        user = User(
            username=account.username,
            password_hash=account.password_hash,
            display_name=account.display_name,
            level=account.level,
            rank=account.rank,
            profile_picture=account.profile_picture,
            is_connected=account.is_connected,
        )
        self.session.add(user)
        self.session.commit()

    def remove_user(self, username: str) -> None:
        """
        Delete a user account and all associated data from the database.

        Args:
            username: The username of the account to delete
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return

        # Cascade delete handles most relations; friendships on the received
        # side need manual removal because they point at the user as friend_id.
        self.session.query(Friendship).filter(
            Friendship.friend_id == user.id  # type: ignore
        ).delete()

        self.session.delete(user)
        self.session.commit()

    # profile edits

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> bool:
        """
        Change a user's password if the old password is correct.

        Args:
            username: The username of the account
            old_password: The current password (plaintext)
            new_password: The new password (plaintext)

        Returns:
            True if the password was changed, False if old password is wrong
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return False
        if User.hash_password(old_password) != user.password_hash:  # type: ignore
            return False
        user.password_hash = User.hash_password(new_password)  # type: ignore
        self.session.commit()
        return True

    def reset_password(self, username: str, new_password: str) -> None:
        """
        Reset a user's password without verifying the old password.

        Args:
            username: The username of the account
            new_password: The new password (plaintext)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.password_hash = User.hash_password(new_password)  # type: ignore
            self.session.commit()

    def change_display_name(self, username: str, new_name: str) -> None:
        """
        Update a user's display name.

        Args:
            username: The username of the account
            new_name: The new display name
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.display_name = new_name  # type: ignore
            self.session.commit()

    def change_profile_picture(self, username: str, new_profile_picture: str) -> None:
        """
        Update a user's profile picture.

        Args:
            username: The username of the account
            new_profile_picture: Path identifier for the new profile picture
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.profile_picture = new_profile_picture  # type: ignore
            self.session.commit()

    def update_level(self, username: str, new_level: int) -> None:
        """
        Update a user's skill level.

        Args:
            username: The username of the account
            new_level: The new skill level (>= 0)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.level = new_level  # type: ignore
            self.session.commit()

    def update_rank(self, username: str, new_rank: int) -> None:
        """
        Update a user's matchmaking rank.

        Args:
            username: The username of the account
            new_rank: The new rank (>= 0)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.rank = new_rank  # type: ignore
            self.session.commit()

    def update_money(self, username: str, new_money: int) -> None:
        """
        Update a user's in-game currency balance.

        Args:
            username: The username of the account
            new_money: The new money balance (>= 0)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.money = new_money  # type: ignore
            self.session.commit()

    # connection status

    def connect(self, username: str) -> None:
        """Mark a user as connected/online."""
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 1  # type: ignore
            self.session.commit()

    def disconnect(self, username: str) -> None:
        """Mark a user as disconnected/offline."""
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.is_connected = 0  # type: ignore
            self.session.commit()

    def set_in_game(self, username: str, in_game: bool) -> None:
        """
        Update a user's in-game status.

        Args:
            username: The username of the account
            in_game: True if currently in a game, False otherwise
        """
        user = self.session.query(User).filter_by(username=username).first()
        if user:
            user.in_game = 1 if in_game else 0  # type: ignore
            self.session.commit()

    def get_connected(self) -> list[Account]:
        """Retrieve all currently connected/online users."""
        users = self.session.query(User).filter_by(is_connected=1).all()
        return [self._orm_to_account(u) for u in users]

    def get_free(self) -> list[Account]:
        """Retrieve all connected users who are not in a game."""
        users = self.session.query(User).filter_by(is_connected=1, in_game=0).all()
        return [self._orm_to_account(u) for u in users]

    def get_leaderboard(self, limit: int = 10) -> list[Account]:
        """
        Retrieve the top users ordered by rank (descending).

        Args:
            limit: Maximum number of users to return (default 10)

        Returns:
            List of Account objects sorted by rank
        """
        users = (
            self.session.query(User)
            .order_by(User.rank.desc())  # type: ignore
            .limit(limit)
            .all()
        )
        return [self._orm_to_account(u) for u in users]

    # friends

    def add_friend(self, username: str, friend_username: str) -> None:
        """
        Add a directional friendship (username -> friend_username).

        Args:
            username: The username of the user initiating the friendship
            friend_username: The username of the friend to add
        """
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()
        if not user or not friend:
            return
        already = (
            self.session.query(Friendship)
            .filter_by(user_id=user.id, friend_id=friend.id)
            .first()
        )
        if already:
            return
        self.session.add(Friendship(user_id=user.id, friend_id=friend.id))
        self.session.commit()

    def remove_friend(self, username: str, friend_username: str) -> None:
        """
        Remove the directional friendship (username -> friend_username).

        Args:
            username: The username of the user
            friend_username: The username of the friend to remove
        """
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()
        if not user or not friend:
            return
        friendship = (
            self.session.query(Friendship)
            .filter_by(user_id=user.id, friend_id=friend.id)
            .first()
        )
        if friendship:
            self.session.delete(friendship)
            self.session.commit()

    def get_friend_invitations(self, username: str) -> list[Message]:
        """
        Retrieve all pending friend invitations received by a user.

        Args:
            username: The username of the recipient

        Returns:
            List of Message objects of type "friend invite"
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        return [m for m in user.messages_received if m.type == "friend invite"]  # type: ignore

    def invite_friend(self, sender_username: str, recipient_username: str) -> None:
        """
        Send a friend invitation: add directional friendship and notify both parties.

        Args:
            sender_username: The username of the sender
            recipient_username: The username of the recipient
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        self.add_friend(sender_username, recipient_username)
        self._send_message(
            sender,
            recipient,
            f"{sender.display_name} vous a envoye une invitation d'ami.",
            "friend invite",
        )

    def accept_friend_invite(
        self, sender_username: str, recipient_username: str
    ) -> None:
        """
        Accept a friend invitation: create reciprocal friendship and notify both parties.

        Args:
            sender_username: The username of the original invite sender
            recipient_username: The username of the user accepting the invite
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        invitation = (
            self.session.query(Message)
            .filter_by(
                sender_id=sender.id, recipient_id=recipient.id, type="friend invite"
            )
            .first()
        )
        if invitation:
            invitation.type = "message"  # type: ignore
        self.add_friend(recipient_username, sender_username)
        self._send_message(
            recipient,
            sender,
            f"{recipient.display_name} a accepte votre invitation d'ami.",
            "message",
        )
        self.session.commit()

    def reject_friend_invite(
        self, sender_username: str, recipient_username: str
    ) -> None:
        """
        Reject a friend invitation: remove friendship and notify the sender.

        Args:
            sender_username: The username of the original invite sender
            recipient_username: The username of the user rejecting
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        invitation = (
            self.session.query(Message)
            .filter_by(
                sender_id=sender.id, recipient_id=recipient.id, type="friend invite"
            )
            .first()
        )
        if invitation:
            invitation.type = "message"  # type: ignore
        self.remove_friend(sender_username, recipient_username)
        self._send_message(
            recipient,
            sender,
            f"{recipient.display_name} a refuse votre invitation d'ami.",
            "message",
        )
        self.session.commit()

    def is_friend(self, username: str, friend_username: str) -> bool:
        """
        Check if two users are friends (directional: username -> friend_username).

        Args:
            username: The username of the potential initiator
            friend_username: The username of the potential friend

        Returns:
            True if username has added friend_username to their friend list
        """
        user = self.session.query(User).filter_by(username=username).first()
        friend = self.session.query(User).filter_by(username=friend_username).first()
        if not user or not friend:
            return False
        friendship = (
            self.session.query(Friendship)
            .filter_by(user_id=user.id, friend_id=friend.id)
            .first()
        )
        return friendship is not None

    def get_friend_count(self, username: str) -> int:
        """
        Get the number of friends a user has.

        Args:
            username: The username of the account

        Returns:
            Number of friends in the user's friend list
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return 0
        return len(user.friendships_initiated)  # type: ignore

    # messages

    def _send_message(
        self,
        sender: User,
        recipient: User,
        content: str,
        msg_type: str = "message",
    ) -> None:
        """Internal helper: create and persist a Message object."""
        message = Message(
            sender_id=sender.id,
            recipient_id=recipient.id,
            type=msg_type,
            content=content,
            timestamp=datetime.utcnow(),
        )
        self.session.add(message)
        self.session.commit()

    def post_message(
        self,
        sender_username: str,
        recipient_username: str,
        content: str,
        type: str = "message",
    ) -> None:
        """
        Post a message from one user to another.

        Args:
            sender_username: The username of the sender
            recipient_username: The username of the recipient
            content: The message content
            type: Message type ("message", "friend invite", "game invite", "system message")
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        self._send_message(sender, recipient, content, type)

    def get_messages(self, username: str) -> dict[str, list[Message]]:
        """
        Retrieve all messages sent or received by a user.

        Args:
            username: The username of the account

        Returns:
            Dict with keys "sent" and "received" containing lists of Message objects
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return {"sent": [], "received": []}
        sent = self.session.query(Message).filter_by(sender_id=user.id).all()
        received = self.session.query(Message).filter_by(recipient_id=user.id).all()
        return {"sent": sent, "received": received}

    def delete_message(self, username: str, message_id: int) -> bool:
        """
        Delete a message by ID if the requesting user is the sender or recipient.

        Args:
            username: The username requesting the deletion
            message_id: The ID of the message to delete

        Returns:
            True if the message was deleted, False otherwise
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return False
        message = (
            self.session.query(Message)
            .filter(
                Message.id == message_id,
                (Message.sender_id == user.id) | (Message.recipient_id == user.id),
            )
            .first()
        )
        if not message:
            return False
        self.session.delete(message)
        self.session.commit()
        return True

    # game invitations

    def get_game_invitations(self, username: str) -> list[Message]:
        """
        Retrieve all pending game invitations received by a user.

        Args:
            username: The username of the recipient

        Returns:
            List of Message objects of type "game invite"
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        return [m for m in user.messages_received if m.type == "game invite"]  # type: ignore

    def invite_to_game(self, sender_username: str, recipient_username: str) -> None:
        """
        Send a game invitation from sender to recipient.

        Args:
            sender_username: The username of the sender
            recipient_username: The username of the recipient
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        self._send_message(
            sender,
            recipient,
            f"{sender.display_name} vous invite a jouer une partie.",
            "game invite",
        )

    def accept_game_invite(self, sender_username: str, recipient_username: str) -> None:
        """
        Accept a game invitation: mark invitation as handled and notify the sender.

        Args:
            sender_username: The username of the original invite sender
            recipient_username: The username of the user accepting
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        invitation = (
            self.session.query(Message)
            .filter_by(
                sender_id=sender.id, recipient_id=recipient.id, type="game invite"
            )
            .first()
        )
        if invitation:
            invitation.type = "message"  # type: ignore
        self._send_message(
            recipient,
            sender,
            f"{recipient.display_name} a accepte votre invitation de jeu.",
            "message",
        )
        self.session.commit()

    def decline_game_invite(
        self, sender_username: str, recipient_username: str
    ) -> None:
        """
        Decline a game invitation: mark invitation as handled and notify the sender.

        Args:
            sender_username: The username of the original invite sender
            recipient_username: The username of the user declining
        """
        sender = self.session.query(User).filter_by(username=sender_username).first()
        recipient = (
            self.session.query(User).filter_by(username=recipient_username).first()
        )
        if not sender or not recipient:
            return
        invitation = (
            self.session.query(Message)
            .filter_by(
                sender_id=sender.id, recipient_id=recipient.id, type="game invite"
            )
            .first()
        )
        if invitation:
            invitation.type = "message"  # type: ignore
        self._send_message(
            recipient,
            sender,
            f"{recipient.display_name} a refuse votre invitation de jeu.",
            "message",
        )
        self.session.commit()

    # game history

    def save_game(
        self,
        player1_username: str,
        player2_username: str,
        nbr_rounds_player1: int,
        nbr_rounds_player2: int,
        timestamp: datetime | None = None,
        replay_data: str | None = None,
    ) -> None:
        """
        Persist a completed game record.

        Args:
            player1_username: The username of player 1
            player2_username: The username of player 2
            nbr_rounds_player1: Number of rounds won by player 1
            nbr_rounds_player2: Number of rounds won by player 2
            timestamp: Timestamp of the game (defaults to utcnow)
            replay_data: Optional serialized replay data
        """
        player1 = self.session.query(User).filter_by(username=player1_username).first()
        player2 = self.session.query(User).filter_by(username=player2_username).first()
        if not player1 or not player2:
            return
        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            timestamp=timestamp or datetime.utcnow(),
            nbr_rounds_player1=nbr_rounds_player1,
            nbr_rounds_player2=nbr_rounds_player2,
            replay_data=replay_data,
        )
        self.session.add(game)
        self.session.commit()

    def get_game_history(self, username: str) -> list[Game]:
        """
        Retrieve the full game history for a user, sorted newest first.

        Args:
            username: The username of the account

        Returns:
            List of Game objects the user participated in
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        return (
            self.session.query(Game)
            .filter((Game.player1_id == user.id) | (Game.player2_id == user.id))
            .order_by(Game.timestamp.desc())  # type: ignore
            .all()
        )

    # cards

    def add_card(self, username: str, card_id: int, quantity: int = 1) -> None:
        """
        Add copies of a card to a user's collection.

        Args:
            username: The username of the account
            card_id: The ID of the card to add
            quantity: Number of copies to add (default 1)
        """
        user = self.session.query(User).filter_by(username=username).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not user or not card:
            return
        correspondance = (
            self.session.query(CardsCorrespondancy)
            .filter_by(user_id=user.id, card_id=card.id)
            .first()
        )
        if correspondance:
            correspondance.quantity += quantity  # type: ignore
        else:
            self.session.add(
                CardsCorrespondancy(user_id=user.id, card_id=card.id, quantity=quantity)
            )
        self.session.commit()

    def remove_card(self, username: str, card_id: int, quantity: int = 1) -> None:
        """
        Remove copies of a card from a user's collection.

        Args:
            username: The username of the account
            card_id: The ID of the card to remove
            quantity: Number of copies to remove (default 1)

        Raises:
            ValueError: If the user does not own enough copies
        """
        user = self.session.query(User).filter_by(username=username).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not user or not card:
            return
        correspondance = (
            self.session.query(CardsCorrespondancy)
            .filter_by(user_id=user.id, card_id=card.id)
            .first()
        )
        if not correspondance:
            raise ValueError("Card not found in user's collection")
        if correspondance.quantity < quantity:  # type: ignore
            raise ValueError("Cannot remove more cards than owned")
        if correspondance.quantity == quantity:  # type: ignore
            self.session.delete(correspondance)
        else:
            correspondance.quantity -= quantity  # type: ignore
        self.session.commit()

    def buy_card(self, username: str, card_id: int, quantity: int) -> bool:
        """
        Purchase a card for a user if they have enough money.

        Args:
            username: The username of the account
            card_id: The ID of the card to buy
            quantity: The number of copies to buy

        Returns:
            True if the purchase was successful, False if insufficient funds
        """
        user = self.session.query(User).filter_by(username=username).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not user or not card:
            return False
        if user.money < quantity * card.buying_price:  # type: ignore
            return False
        user.money -= quantity * card.buying_price  # type: ignore
        self.add_card(username, card_id, quantity=quantity)
        self.session.commit()
        return True

    def sell_card(self, username: str, card_id: int, quantity: int) -> bool:
        """
        Sell a card from a user's collection for a specified price.

        Args:
            username: The username of the account
            card_id: The ID of the card to sell
            quantity: The number of copies to sell

        Returns:
            True if the sale was successful, False if the user does not own the card
        """
        user = self.session.query(User).filter_by(username=username).first()
        card = self.session.query(Card).filter_by(id=card_id).first()
        if not user or not card:
            return False
        try:
            self.remove_card(username, card_id, quantity=quantity)
        except ValueError:
            return False
        user.money += quantity * card.selling_price  # type: ignore
        self.session.commit()
        return True

    def get_user_cards(self, username: str) -> list[dict]:
        """
        Retrieve a user's card collection with quantities.

        Each entry is a dict with keys:
          - card: CardDTO (full card data)
          - quantity: int

        Args:
            username: The username of the account

        Returns:
            List of dicts {"card": CardDTO, "quantity": int}
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        effect_repo = EffectRepository(self.session)
        results = []
        for c in user.cards:  # type: ignore
            from typing import cast as _cast

            effect_dto = (
                effect_repo._orm_effect_to_dto(c.card.effect) if c.card.effect else None
            )
            card_dto = _CardDTO(
                id=c.card.id,
                name=c.card.name,
                description=c.card.description,
                rarity=c.card.rarity,
                power_table=c.card.power_table,
                face_artwork_url=_cast(str | None, c.card.face_artwork_url),
                back_artwork_url=_cast(str | None, c.card.back_artwork_url),
                effect=effect_dto,
            )
            results.append({"card": card_dto, "quantity": c.quantity})
        return results

    def get_card_quantity(self, username: str, card_id: int) -> int:
        """
        Get the quantity of a specific card owned by a user.

        Args:
            username: The username of the account
            card_id: The ID of the card

        Returns:
            Number of copies owned (0 if not owned)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return 0
        correspondance = (
            self.session.query(CardsCorrespondancy)
            .filter_by(user_id=user.id, card_id=card_id)
            .first()
        )
        return correspondance.quantity if correspondance else 0  # type: ignore

    # loot boxes

    def add_loot_box(self, username: str, loot_box_id: int, quantity: int = 1) -> None:
        """
        Add loot boxes to the system (for admin use).

        Args:
            loot_box_id: The ID of the loot box type to add
            quantity: Number of loot boxes to add (default 1)
        """
        user = self.session.query(User).filter_by(username=username).first()
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not user or not loot_box:
            return
        correspondance = (
            self.session.query(UserLootBoxCorrespondancy)
            .filter_by(user_id=user.id, loot_box_id=loot_box.id)
            .first()
        )
        if correspondance:
            correspondance.quantity += quantity  # type: ignore
        else:
            self.session.add(
                UserLootBoxCorrespondancy(
                    user_id=user.id, loot_box_id=loot_box.id, quantity=quantity
                )
            )
        self.session.commit()

    def buy_loot_box(self, username: str, loot_box_id: int, quantity: int = 1) -> bool:
        """
        Allow a user to purchase loot boxes if they have enough money.

        Args:
            username: The username of the account
            loot_box_id: The ID of the loot box type to buy
            quantity: Number of loot boxes to buy (default 1)

        Returns:
            True if the purchase was successful, False if insufficient funds or loot box not found
        """
        user = self.session.query(User).filter_by(username=username).first()
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not user or not loot_box:
            return False
        total_price = quantity * loot_box.price  # type: ignore
        if user.money < total_price:  # type: ignore
            return False
        user.money -= total_price  # type: ignore
        self.add_loot_box(username, loot_box_id, quantity=quantity)
        self.session.commit()
        return True

    def remove_loot_box(
        self, username: str, loot_box_id: int, quantity: int = 1
    ) -> None:
        """
        Remove loot boxes from the system (for admin use).

        Args:
            username: The username of the account
            loot_box_id: The ID of the loot box type to remove
            quantity: Number of loot boxes to remove (default 1)
        """
        user = self.session.query(User).filter_by(username=username).first()
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not user or not loot_box:
            return
        correspondance = (
            self.session.query(UserLootBoxCorrespondancy)
            .filter_by(user_id=user.id, loot_box_id=loot_box.id)
            .first()
        )
        if not correspondance:
            raise ValueError("Loot box not found in user's collection")
        if correspondance.quantity < quantity:  # type: ignore
            raise ValueError("Cannot remove more loot boxes than owned")
        if correspondance.quantity == quantity:  # type: ignore
            self.session.delete(correspondance)
        else:
            correspondance.quantity -= quantity  # type: ignore
        self.session.commit()

    def get_user_loot_boxes(self, username: str) -> list[dict]:
        """
        Retrieve a user's loot box collection with quantities.

        Each entry is a dict with keys:
          - loot_box: LootBoxDTO (full loot box data)
          - quantity: int

        Args:
            username: The username of the account

        Returns:
            List of dicts {"loot_box": LootBoxDTO, "quantity": int}
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        results = []
        for c in user.loot_boxes:  # type: ignore
            from database.loot_box import LootBoxDTO as _LootBoxDTO

            effect_repo = EffectRepository(self.session)

            loot_box_dto = _LootBoxDTO(
                id=c.loot_box.id,
                name=c.loot_box.name,
                description=c.loot_box.description,
                price=c.loot_box.price,
                nbr_random_cards=c.loot_box.nbr_random_cards,
                artwork=c.loot_box.artwork,
                animations=c.loot_box.get_animations(),
                mandatory_cards=[
                    (
                        _CardDTO(
                            id=mc.card_id,
                            name=mc.card.name,
                            description=mc.card.description,
                            rarity=mc.card.rarity,
                            power_table=mc.card.power_table,
                            face_artwork_url=mc.card.face_artwork_url,
                            back_artwork_url=mc.card.back_artwork_url,
                            animations=_cast(dict | None, mc.card.get_animations()),
                            effect=effect_repo._orm_effect_to_dto(mc.card.effect),
                            buying_price=mc.card.buying_price,
                            selling_price=mc.card.selling_price,
                        ),
                        mc.quantity,
                    )
                    for mc in c.loot_box.mandatory_cards  # type: ignore
                ],
                random_cards=[
                    (
                        _CardDTO(
                            id=rc.card_id,
                            name=rc.card.name,
                            description=rc.card.description,
                            rarity=rc.card.rarity,
                            power_table=rc.card.power_table,
                            face_artwork_url=rc.card.face_artwork_url,
                            back_artwork_url=rc.card.back_artwork_url,
                            animations=_cast(dict | None, rc.card.get_animations()),
                            effect=effect_repo._orm_effect_to_dto(rc.card.effect),
                            buying_price=rc.card.buying_price,
                            selling_price=rc.card.selling_price,
                        ),
                        rc.probability,
                    )
                    for rc in c.loot_box.random_cards  # type: ignore
                ],
            )
            results.append({"loot_box": loot_box_dto, "quantity": c.quantity})
        return results

    def get_loot_box_quantity(self, username: str, loot_box_id: int) -> int:
        """
        Get the quantity of a specific loot box owned by a user.

        Args:
            username: The username of the account
            loot_box_id: The ID of the loot box

        Returns:
            Number of copies owned (0 if not owned)
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return 0
        correspondance = (
            self.session.query(UserLootBoxCorrespondancy)
            .filter_by(user_id=user.id, loot_box_id=loot_box_id)
            .first()
        )
        return correspondance.quantity if correspondance else 0  # type: ignore

    def open_loot_box(self, username: str, loot_box_id: int) -> list[_CardDTO]:
        """
        Open a loot box for a user, granting them the contained cards.

        Args:
            username: The username of the account
            loot_box_id: The ID of the loot box to open

        Returns:
            List of CardDTO objects representing the cards obtained from the loot box
        """

        user = self.session.query(User).filter_by(username=username).first()
        loot_box = self.session.query(LootBox).filter_by(id=loot_box_id).first()
        if not user or not loot_box:
            return []
        correspondance = (
            self.session.query(UserLootBoxCorrespondancy)
            .filter_by(user_id=user.id, loot_box_id=loot_box.id)
            .first()
        )
        if not correspondance or correspondance.quantity <= 0:  # type: ignore
            return []

        # Decrease loot box quantity
        self.remove_loot_box(username, loot_box_id, quantity=1)
        self.session.commit()

        loot_box_repo = LootBoxRepository(self.session)
        obtained_cards = loot_box_repo.open_loot_box(loot_box_id)
        if not obtained_cards:
            return []
        for card in obtained_cards:
            self.add_card(username, card.id, quantity=1)  # type: ignore
        return obtained_cards

    # achievements

    def add_achievement(self, username: str, achievement_id: int) -> None:
        """
        Unlock an achievement for a user (idempotent).

        Args:
            username: The username of the account
            achievement_id: The ID of the achievement to unlock
        """
        user = self.session.query(User).filter_by(username=username).first()
        achievement = (
            self.session.query(Achievement).filter_by(id=achievement_id).first()
        )
        if not user or not achievement:
            return
        already = (
            self.session.query(AchievementsCorrespondancy)
            .filter_by(user_id=user.id, achievement_id=achievement.id)
            .first()
        )
        if already:
            return
        self.session.add(
            AchievementsCorrespondancy(
                user_id=user.id,
                achievement_id=achievement.id,
                date_unlocked=datetime.utcnow(),
            )
        )
        self.session.commit()

    def get_user_achievements(self, username: str) -> list[_AchDTO]:
        """
        Retrieve all achievements unlocked by a user.

        Args:
            username: The username of the account

        Returns:
            List of AchDTO objects
        """
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return []
        return [
            _AchDTO(
                id=c.achievement.id,  # type: ignore
                name=c.achievement.name,  # type: ignore
                description=c.achievement.description,  # type: ignore
                criteria=c.achievement.criteria,  # type: ignore
                illustration=c.achievement.illustration,  # type: ignore
            )
            for c in user.achievements  # type: ignore
        ]
