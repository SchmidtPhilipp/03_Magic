from typing import List, Set, Dict, Any

class Card:
    """A class to represent a Magic: The Gathering card."""

    def __init__(self, card_data: Dict[str, Any]):
        """
        Initialize a Card object from a dictionary of card data.
        Typically, this data comes from Scryfall API.
        """
        self._data = card_data

    @property
    def name(self) -> str:
        """The card's name."""
        return self._data.get("name", "Unknown Card")

    @property
    def colors(self) -> Set[str]:
        """The card's colors, as a set of single-character strings (W, U, B, R, G)."""
        # Handle multi-faced cards
        if "card_faces" in self._data:
            all_colors = set()
            for face in self._data["card_faces"]:
                all_colors.update(face.get("colors", []))
            return all_colors
        return set(self._data.get("colors", []))

    @property
    def color_identity(self) -> Set[str]:
        """The card's color identity."""
        return set(self._data.get("color_identity", []))

    @property
    def cmc(self) -> float:
        """The card's converted mana cost."""
        return self._data.get("cmc", 0.0)

    @property
    def type_line(self) -> str:
        """The card's full type line (e.g., 'Creature — Human Soldier')."""
        return self._data.get("type_line", "")

    @property
    def main_type(self) -> str:
        """The card's main type (e.g., 'Creature', 'Instant', 'Land')."""
        return self.type_line.split("—")[0].strip()

    @property
    def power(self) -> str:
        """The card's power (for creatures)."""
        return self._data.get("power", "0")

    @property
    def toughness(self) -> str:
        """The card's toughness (for creatures)."""
        return self._data.get("toughness", "0")

    @property
    def rating(self) -> int:
        """The card's rating, if provided."""
        return self._data.get("rating", 0)

    @rating.setter
    def rating(self, value: int):
        """Setter for the card's rating."""
        self._data["rating"] = value

    @property
    def optimization_score(self) -> float:
        """The card's score used for optimization."""
        return self._data.get("optimization_score", 0.0)

    @optimization_score.setter
    def optimization_score(self, value: float):
        """Setter for the optimization score."""
        self._data["optimization_score"] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return the card's data as a dictionary."""
        return {
            "name": self.name,
            "colors": self.colors,
            "cmc": self.cmc,
            "type": self.main_type,
            "rating": self.rating,
            "optimization_score": self.optimization_score,
        }

    def __repr__(self) -> str:
        return f"Card({self.name})"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash(self.name) 