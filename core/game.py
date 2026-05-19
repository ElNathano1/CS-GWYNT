"""Game Model"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .card import Card
from .effect_resolver import EffectResolution, EffectResolver, ResolutionChoices
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
        self.state = GameState.WAITING
        self.current_turn = 0
        self.current_player = self.player1
        self.effect_resolver = EffectResolver()
        self.last_effect_resolution: Optional[EffectResolution] = None

        self.player1_has_passed = False
        self.player2_has_passed = False

        self.nbr_rounds_player1 = 0
        self.nbr_rounds_player2 = 0
        self.winner = None

        self.start_game()

    def start_game(self) -> bool:
        """Start the game"""

        if self.player2 and self.state == GameState.WAITING:
            self.state = GameState.FIRST_ROUND
            self.player1.update_power()
            self.player2.update_power()
            return True

        return False

    def end_game(self, winner: Player | None) -> None:
        """End the game and set winner, which can be None in case of a tie"""

        self.state = GameState.FINISHED
        self.winner = winner

    def get_current_round_winner(self) -> Optional[Player]:
        """Determine the winner of the current round"""

        try:
            assert self.player2 is not None, "Second player not set"
        except AssertionError as e:
            raise Exception(str(e))

        if self.player1.current_power > self.player2.current_power:
            return self.player1
        elif self.player2.current_power > self.player1.current_power:
            return self.player2
        else:
            return None  # Tie

    def get_winner(self) -> Optional[Player]:
        """Determine the overall winner of the game"""

        if self.nbr_rounds_player1 > self.nbr_rounds_player2:
            return self.player1
        elif self.nbr_rounds_player2 > self.nbr_rounds_player1:
            return self.player2
        else:
            return None  # Tie

    def next_turn(self) -> None:
        """Move to next turn"""

        self.current_turn += 1

        if self.player1_has_passed and self.player2_has_passed:
            round_winner = self.get_current_round_winner()
            if round_winner == self.player1:
                self.nbr_rounds_player1 += 1
            elif round_winner == self.player2:
                self.nbr_rounds_player2 += 1

            match self.state:

                case GameState.FIRST_ROUND:
                    self.state = GameState.SECOND_ROUND
                    self.current_player = round_winner or self.player2

                case GameState.SECOND_ROUND:
                    self.state = GameState.THIRD_ROUND
                    self.current_player = (
                        round_winner or self.player1
                        if self.nbr_rounds_player1 <= self.nbr_rounds_player2
                        else self.player2
                    )

                case GameState.THIRD_ROUND:
                    self.end_game(self.get_winner())

        elif self.player1_has_passed:
            self.current_player = self.player2

        elif self.player2_has_passed:
            self.current_player = self.player1

        elif self.current_player == self.player1:
            self.current_player = self.player2
        else:
            self.current_player = self.player1

    def _resolve_card_effect_if_any(
        self,
        player: Player,
        card: Card,
        choices: ResolutionChoices | None = None,
    ) -> None:
        """Resolve ON_PLAY effect for the card and store the report."""

        self.last_effect_resolution = self.effect_resolver.resolve_on_play(
            self,
            player,
            card,
            choices=choices,
        )

    def play_turn(self, action: tuple) -> EffectResolution | None:
        """Player takes an action during their turn"""

        self.last_effect_resolution = None
        actor = self.current_player
        if actor is None:
            raise Exception("No active player for this turn")

        if action[0] == "play_character_card":
            card = action[1]
            lane = action[2]
            raw_choices = action[3] if len(action) > 3 else None
            choices = ResolutionChoices.from_payload(raw_choices)

            actor.play_character_card(card, lane)  # type: ignore

            self._resolve_card_effect_if_any(actor, card, choices)

        elif action[0] == "play_event_card":
            card = action[1]
            raw_choices = action[2] if len(action) > 2 else None
            choices = ResolutionChoices.from_payload(raw_choices)

            actor.play_event_card(card)  # type: ignore

            self._resolve_card_effect_if_any(actor, card, choices)

        elif action[0] == "pass":
            if self.current_player == self.player1:
                self.player1_has_passed = True
            else:
                self.player2_has_passed = True

        else:
            raise Exception("Invalid action")

        self.next_turn()
        return self.last_effect_resolution
