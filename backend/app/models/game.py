"""Game Model"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .player import Player


class GameState(str, Enum):
    """Game states"""

    WAITING = "waiting"
    FIRST_ROUND = "first_round"
    SECOND_ROUND = "second_round"
    THIRD_ROUND = "third_round"
    FINISHED = "finished"


@dataclass
class Game:
    """Represents a game session"""

    id: int
    player1: Player
    player2: Optional[Player] = None

    def __post_init__(self):
        self.state = (
            GameState.WAITING if self.player2 is None else GameState.FIRST_ROUND
        )
        self.current_turn = 0
        self.winner = None

    def start_game(self) -> bool:
        """Start the game"""

        if self.player2 and self.state == GameState.WAITING:
            self.state = GameState.FIRST_ROUND
            return True

        return False

    def end_game(self, winner: Player) -> None:
        """End the game and set winner"""

        self.state = GameState.FINISHED
        self.winner = winner

    def get_current_player(self) -> Player:
        """Get the player whose turn it is"""

        try:
            assert self.player2 is not None, "Second player not set"
        except AssertionError as e:
            raise Exception(str(e))

        return self.player1 if self.current_turn % 2 == 0 else self.player2

    def next_turn(self) -> None:
        """Move to next turn"""

        self.current_turn += 1
