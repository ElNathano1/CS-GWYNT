"""Player Model"""

import random

from dataclasses import dataclass, field
from typing import List, Dict
from .card import Card
from .lane import LaneType, Lane, Hand, Pile


@dataclass
class Player:
    """Represents a player in the game"""

    id: int
    username: str
    display_name: str
    profile_picture_url: str

    deck: Pile

    hand: Hand = Hand()
    discard_pile: Pile = Pile()

    board: Dict[str, Lane] = {
        "frontstage": Lane(type=LaneType.FRONTSTAGE),
        "offstage": Lane(type=LaneType.OFFSTAGE),
        "backstage": Lane(type=LaneType.BACKSTAGE),
    }

    def __post_init__(self):
        """Initialize the player's terrain and other attributes"""

        self.deck.shuffle()

    def update_power(self) -> None:
        """Update the current power of all cards on the board"""

        for lane in self.board.values():
            lane.update_power()

        self.current_power = sum(lane.current_power for lane in self.board.values())

    def draw_card(self) -> None:
        """Draw a card from the deck"""

        try:
            card = self.deck.draw()
            self.hand.append(card)

        except Exception as e:
            raise e

    def play_character_card(self, card: Card, lane: LaneType) -> None:
        """Play a card from the hand"""

        try:
            self.hand.remove(card)
            self.board[lane.value].append(card)

            self.update_power()

        except Exception as e:
            raise e

    def play_event_card(self, card: Card) -> None:
        """Play an event card from the hand"""

        try:
            self.hand.remove(card)

            self.update_power()

        except Exception as e:
            raise e

    def discard_card(self, card: Card) -> None:
        """Discard a card from the hand, deck or board"""

        self.destroy_card(card)

        self.discard_pile.append(card)

    def destroy_card(self, card: Card) -> None:
        """Destroy a card from the hand, deck or board (removed from game)"""

        try:
            self.hand.remove(card)

        except ValueError:
            try:
                self.deck.remove(card)

            except ValueError:
                for lane in self.board.values():
                    try:
                        lane.remove(card)
                        self.update_power()
                        break

                    except ValueError:
                        continue

                else:
                    raise Exception("Card not found in hand, deck or board")
