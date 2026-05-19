import sys
from pathlib import Path

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.models import User
from database.achievement import AchievementDTO
from database.card import CardDTO


class Account:
    """
    A class representing a user account.

    Attributes:
        username (str): The username of the account.
        password_hash (str): The hash of the password of the account.
        display_name (str): The display name of the account holder.
        level (int): The skill level of the account holder.
        rank (int): The matchmaking rank of the account holder.
        money (int): The in-game currency balance of the account holder.
        profile_picture (str | None): The path to the profile picture of the account holder.

        friends (list[str]): The card collection as [{card_id, name, rarity, quantity}].
        cards (list[CardDTO]): The card collection with full card data and quantities.
        achievements (list[AchievementDTO]): The list of unlocked achievements.
    """

    def __init__(
        self,
        username: str,
        password: str | None = None,
        password_hash: str | None = None,
        display_name: str = "",
        level: int = 0,
        rank: int = 0,
        money: int = 0,
        profile_picture: str = "default",
        friends: list[str] | None = None,
        is_connected: int = 0,
        in_game: int = 0,
        nbr_games: int = 0,
        nbr_wins: int = 0,
        cards: list[dict] | None = None,
        achievements: list[AchievementDTO] | None = None,
    ):
        """
        Initializes the user account.

        Args:
            username (str): The username of the account.
            password (str): The password of the account.
            display_name (str): The display name of the account holder.
            level (int): The skill level of the account holder. Defaults to 0.
            rank (int): The matchmaking rank of the account holder. Defaults to 0.
            money (int): The in-game currency balance of the account holder. Defaults to 0.
            profile_picture (str): The path to the profile picture directory of the account holder. Defaults to "default".
            friends (list[str]): The list of usernames of friends. Defaults to empty list.
            nbr_games (int): Total number of games played. Defaults to 0.
            nbr_wins (int): Total number of games won. Defaults to 0.
            cards (list[dict]): Card collection as [{"card": CardDTO, "quantity": int}]. Defaults to empty list.
            achievements (list[AchievementDTO]): Unlocked achievements. Defaults to empty list.
        """

        self.username = username
        self.password_hash = User.hash_password(password) if password else password_hash
        self.display_name = display_name
        self.level = level
        self.rank = rank
        self.money = money
        self.profile_picture = profile_picture
        self.friends = friends or []
        self.is_connected = is_connected
        self.in_game = in_game
        self.nbr_games = nbr_games
        self.nbr_wins = nbr_wins
        self.cards = cards or []
        self.achievements = achievements or []

    def __str__(self) -> str:
        return f"Account: {self.username} - {self.display_name} (Level {self.level} ; Rank {self.rank})"

    def to_dict(self) -> dict:
        """
        Serialize the account to a plain dictionary (safe for JSON responses).

        Returns:
            dict with all public account fields (no password_hash).
        """
        return {
            "username": self.username,
            "display_name": self.display_name,
            "level": self.level,
            "rank": self.rank,
            "money": self.money,
            "profile_picture": self.profile_picture,
            "friends": self.friends,
            "is_connected": self.is_connected,
            "in_game": self.in_game,
            "nbr_games": self.nbr_games,
            "nbr_wins": self.nbr_wins,
            "cards": [
                {"card": e["card"].to_dict(), "quantity": e["quantity"]}
                for e in self.cards
            ],
            "achievements": [a.to_dict() for a in self.achievements],
        }

    def check_password(self, password: str) -> bool:
        """
        Checks if the given password matches the stored password hash.

        Args:
            password (str): The password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """

        return User.hash_password(password) == self.password_hash

    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        Changes the password of the account if the old password matches.

        Args:
            old_password (str): The current password.
            new_password (str): The new password to set.
        Returns:
            bool: True if the password was changed, False otherwise.
        """

        if self.check_password(old_password):
            self.password_hash = User.hash_password(new_password)
            return True
        return False

    def reset_password(self, new_password: str) -> None:
        """
        Resets the password of the account without checking the old password.

        Args:
            new_password (str): The new password to set.
        """

        self.password_hash = User.hash_password(new_password)

    def add_friend(self, friend_id: str) -> None:
        """
        Adds a friend to the account.

        Args:
            friend_id (str): The ID of the friend to add.
        """

        if friend_id not in self.friends:
            self.friends.append(friend_id)

    def remove_friend(self, friend_id: str) -> None:
        """
        Removes a friend from the account.

        Args:
            friend_id (str): The ID of the friend to remove.
        """

        if friend_id in self.friends:
            self.friends.remove(friend_id)
