"""
GUBS: A Game of Wit and Luck — Full Rules Engine
=================================================

COMPLETE RULES IMPLEMENTED:
─────────────────────────────────────────────────────────────────────────────
OBJECT
  Be the player with the most Free and Protected Gubs in play when the third
  letter card (G, U, or B) is drawn from the deck.

CARD TYPES (72 cards total):
  GUB (14):        13 standard Gubs + 1 Esteemed Elder
  LETTER (3):      G, U, B — game-ending events drawn from deck
  BARRICADE (13):  Mushroom (7), Toad Rider (4), Velvet Moth (2)
  TRAP (3):        Single Ring (1), Double Ring (1), Triple Ring (1)
  TOOL_HAZARD (4): Sud Spout (4) — dual use
  HAZARD (12):     Lure (7), Super Lure (2), Cyclone (1), Lightning (1),
                   Smahl Thief (1), Omen Beetle (1)
  TOOL (8):        Haki Flute (2), Spear (4), Scout (1), Retreat (1)
  INTERRUPT (5):   Feather (2), Flop Boat (1), Age Old Cure (2), Blind Fold (1)
  EVENT (5):       Dangerous Alchemy (1), Gargok Plague (1), Rumor of Wasps (1),
                   Flash Flood (1), Traveling Merchant (1)
  WILD (1):        Cricket Song

SETUP:
  1. Remove one standard Gub per player and deal them out (each starts with 1 Gub in play).
  2. Remove G, U, B letter cards. Shuffle remainder thoroughly.
     Re-insert letter cards spaced through deck. Shuffle again.
  3. Deal each player 3 cards (no Event cards in starting hand).
  4. Place deck face-down in centre; discard pile beside it.

TURN STRUCTURE:
  1. DRAW: Draw one card from the deck (optional; cannot skip two turns in a row).
     - EVENT card drawn → interrupt window opens (Flop Boat / Cricket Song), then resolves.
     - LETTER card drawn → interrupt window opens (Flop Boat / Cricket Song), then added.
     - Normal card → added to hand.
  2. PLAY: Play any number of cards from your hand.
     - After each Hazard or Trap is played → interrupt window opens for all other players
       (Feather / Blind Fold / Cricket Song).
  3. DISCARD: Discard down to 8 cards if over the limit.

INTERRUPT SYSTEM:
  When a Hazard/Trap is played, or an Event/Letter is drawn, the engine enters
  phase="interrupt". Each non-acting player (in turn order) is asked whether
  they want to respond. They may play:
    Feather      — cancel any Hazard or Trap (played against a Hazard/Trap)
    Blind Fold   — cancel a Lure or Super Lure specifically
    Flop Boat    — cancel any Event or Letter card as it is drawn
    Age Old Cure — (not truly a reactive interrupt for hazards; used proactively)
    Cricket Song — can mimic Feather, Blind Fold, or Flop Boat as an interrupt,
                   or mimic any Hazard/Tool on own turn
  Once all players have passed (or an interrupt fires), the pending action resolves.

CARD EFFECTS:
  Mushroom (Barricade, 7):
    Play on own Free Gub → Protected.
    Play on any Mushroom in play → destroy that Mushroom (Gub becomes Free).

  Toad Rider (Barricade, 4):
    Play on own Free Gub → Protected.
    Play on any Barricade on the field (any player, any type) → destroy it (Gub becomes Free).
    If Rumor of Wasps: Toad Rider, and the Gub it protects, are shuffled into the deck.

  Velvet Moth (Barricade, 2):
    Play on own Free Gub → Protected.

  Lure (Hazard, 7):
    Steal one Free Gub from any opponent. Opens interrupt window.

  Super Lure (Hazard, 2):
    Steal ALL Free AND Protected Gubs from one opponent (barricades return to opponent).
    Opens interrupt window.

  Cyclone (Hazard, 1):
    Strip all barricades from one opponent's colony (Gubs become Free). Opens interrupt window.

  Haki Flute (Tool, 2):
    Shatter one Ring Trap; claim all Gubs beneath it to your side.

  Spear (Tool, 4):
    Mode 1: Destroy a Sud Spout (Gub stays on its side, becomes Free).
    Mode 2: Discard any one Free Gub in play (any player).

  Sud Spout (Tool/Hazard, 4):
    Trap a Free Gub in place on its current side. Opens interrupt window.

  Single Ring (Trap, 1) / Double Ring (Trap, 1) / Triple Ring (Trap, 1):
    Trap 1/2/3 Free Gubs and bring them to your side. Opens interrupt window.

  Feather (Interrupt, 2):
    Cancel any Hazard or Trap card the moment it is played. Reactive only.

  Flop Boat (Interrupt, 1):
    Cancel any Event card or Letter card when drawn. Reactive only.
    If cancelling a Letter, it is re-inserted into the deck.

  Age Old Cure (Interrupt, 2):
    On own turn: retrieve one Gub from the discard pile into your hand.
    During Gargok Plague: automatically consumed to save your hand.

  Blind Fold (Interrupt, 1):
    Cancel a Lure or Super Lure. Reactive only.

  Scout (Tool, 1):
    Mode 1: Look at the top 3 cards of the deck.
    Mode 2: Look at one opponent's hand.

  Retreat (Tool, 1):
    Reclaim everything from your colony back into your hand: all your in-play
    Gubs (except the Esteemed Elder, which stays in play), plus all barricades
    and traps attached to them. Any opponent Gubs you were holding in a Ring
    trap are released back to their owners as Free Gubs.

  Traveling Merchant (Event, 1):
    Hands rotate right; each player keeps ONE card, rest shuffled into deck.

  Gargok Plague (Event, 1):
    All hands shuffled into deck unless player discards an Age Old Cure.

  Rumor of Wasps (Event, 1):
    Every Toad Rider barricade in play, along with the Gub it was protecting,
    is shuffled into the deck (the Esteemed Elder is never affected, since it
    can never be Protected).

  Omen Beetle (Hazard, 1):
    Played from hand. Discards ALL Mushroom-protected Gubs and their Mushrooms.
    Opens interrupt window.

  Flash Flood (Event, 1):
    All Free non-Elder Gubs shuffled back into the deck.

  Lightning (Hazard, 1):
    Played from hand. Mode 1: destroy Esteemed Elder. Mode 2: discard opponent's hand.
    Opens interrupt window.

  Dangerous Alchemy (Event, 1):
    Drawing player discards entire colony (Elder immune).

  Smahl Thief (Hazard, 1):
    Steal any non-Elder, non-Ring-trapped Gub or any Barricade from opponent's colony.
    If stealing Protected Gub: Gub → your hand; Barricade → original owner's hand.
    If stealing Barricade: Gub stays (now Free). Opens interrupt window.

  Cricket Song (Wild, 1):
    On own turn: mimic any Hazard or Tool card.
    As interrupt (any player's turn): mimic Feather, Blind Fold, or Flop Boat.

  Esteemed Elder (Special Gub, 1):
    Immune to everything except Lightning (or Cricket Song as Lightning).
    Cannot be Protected or retrieved by Age Old Cure.
    Tiebreaker: holder wins ties.

  G, U, B (Letter, 3):
    Third letter drawn = game over immediately.

SCORING:
  Free Gubs: 1 pt. Protected Gubs: 1 pt. Trapped Gubs: 0 pts.
  Tiebreaker 1: player with Esteemed Elder. Tiebreaker 2: fewest cards in hand.
"""

import random
import copy
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
#  Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class CardType(Enum):
    GUB        = "gub"
    LETTER     = "letter"
    BARRICADE  = "barricade"
    TRAP       = "trap"
    HAZARD     = "hazard"
    TOOL       = "tool"
    TOOL_HAZARD= "tool_hazard"
    INTERRUPT  = "interrupt"
    EVENT      = "event"
    WILD       = "wild"

class GubState(Enum):
    FREE      = "free"
    PROTECTED = "protected"
    TRAPPED   = "trapped"

class BarricadeKind(Enum):
    MUSHROOM    = "Mushroom"
    TOAD_RIDER  = "Toad Rider"
    VELVET_MOTH = "Velvet Moth"

class TrapKind(Enum):
    SINGLE_RING = "Single Ring"
    DOUBLE_RING = "Double Ring"
    TRIPLE_RING = "Triple Ring"
    SUD_SPOUT   = "Sud Spout"

# Interrupt triggers — what kind of pending action each interrupt card responds to
INTERRUPT_TRIGGERS: Dict[str, List[str]] = {
    # card_name -> list of pending_kind values it can cancel
    "Feather":    ["hazard", "trap", "spear"],
    "Blind Fold": ["lure", "super_lure"],
    "Flop Boat":  ["event", "letter"],
    # Age Old Cure is used proactively on own turn (or auto-consumed by Gargok Plague)
    # Cricket Song handled separately
}


# ─────────────────────────────────────────────────────────────────────────────
#  Card definition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Card:
    name: str
    card_type: CardType
    count: int = 1
    barricade_kind: Optional[BarricadeKind] = None
    trap_kind: Optional[TrapKind] = None
    trap_capacity: int = 0
    letter: Optional[str] = None
    is_elder: bool = False

    def __repr__(self):
        return f"<{self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Full card catalogue
# ─────────────────────────────────────────────────────────────────────────────

def _make_catalogue() -> List[Card]:
    C  = CardType
    B  = BarricadeKind
    T  = TrapKind
    return [
        Card("G", C.LETTER, 1, letter="G"),
        Card("U", C.LETTER, 1, letter="U"),
        Card("B", C.LETTER, 1, letter="B"),

        Card("Gub",            C.GUB, 13),
        Card("Esteemed Elder", C.GUB,  1, is_elder=True),

        Card("Mushroom",    C.BARRICADE, 7, barricade_kind=B.MUSHROOM),
        Card("Toad Rider",  C.BARRICADE, 4, barricade_kind=B.TOAD_RIDER),
        Card("Velvet Moth", C.BARRICADE, 2, barricade_kind=B.VELVET_MOTH),

        Card("Single Ring", C.TRAP, 1, trap_kind=T.SINGLE_RING, trap_capacity=1),
        Card("Double Ring", C.TRAP, 1, trap_kind=T.DOUBLE_RING, trap_capacity=2),
        Card("Triple Ring", C.TRAP, 1, trap_kind=T.TRIPLE_RING, trap_capacity=3),

        Card("Sud Spout",   C.TOOL_HAZARD, 4, trap_kind=T.SUD_SPOUT, trap_capacity=1),

        Card("Lure",        C.HAZARD, 7),
        Card("Super Lure",  C.HAZARD, 2),
        Card("Cyclone",     C.HAZARD, 1),
        Card("Lightning",   C.HAZARD, 1),
        Card("Smahl Thief", C.HAZARD, 1),
        Card("Omen Beetle", C.HAZARD, 1),

        Card("Haki Flute",  C.TOOL, 2),
        Card("Spear",       C.TOOL, 4),
        Card("Scout",       C.TOOL, 1),
        Card("Retreat",     C.TOOL, 1),

        Card("Feather",      C.INTERRUPT, 2),
        Card("Flop Boat",    C.INTERRUPT, 1),
        Card("Age Old Cure", C.INTERRUPT, 2),
        Card("Blind Fold",   C.INTERRUPT, 1),

        Card("Dangerous Alchemy", C.EVENT, 1),
        Card("Gargok Plague",     C.EVENT, 1),
        Card("Rumor of Wasps",    C.EVENT, 1),
        Card("Flash Flood",       C.EVENT, 1),
        Card("Traveling Merchant",C.EVENT, 1),

        Card("Cricket Song", C.WILD, 1),
    ]

CARD_CATALOGUE: List[Card] = _make_catalogue()
CARD_BY_NAME: Dict[str, Card] = {c.name: c for c in CARD_CATALOGUE}


def build_deck() -> List[Card]:
    deck = []
    for card in CARD_CATALOGUE:
        if card.card_type == CardType.LETTER:
            continue
        deck.extend([card] * card.count)
    random.shuffle(deck)
    n = len(deck)
    positions = [n // 5, n // 2, n * 4 // 5]
    letters = [CARD_BY_NAME["G"], CARD_BY_NAME["U"], CARD_BY_NAME["B"]]
    random.shuffle(letters)
    for i, pos in enumerate(sorted(positions)):
        deck.insert(pos + i, letters[i])
    return deck


# ─────────────────────────────────────────────────────────────────────────────
#  In-play Gub
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlayedGub:
    owner: int
    is_elder: bool = False
    barricade: Optional[Card] = None
    trap: Optional[Card] = None
    trapped_gubs: List['PlayedGub'] = field(default_factory=list)

    @property
    def state(self) -> GubState:
        if self.trap is not None:
            return GubState.TRAPPED
        if self.barricade is not None:
            return GubState.PROTECTED
        return GubState.FREE

    @property
    def points(self) -> int:
        return 1 if self.state in (GubState.FREE, GubState.PROTECTED) else 0

    def __repr__(self):
        kind = "Elder" if self.is_elder else "Gub"
        return f"<{kind}[P{self.owner}] {self.state.value}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Pending interrupt descriptor
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PendingAction:
    """Describes an action that is waiting in an interrupt window."""
    kind: str           # "hazard"|"trap"|"lure"|"super_lure"|"event"|"letter"
    action: Dict        # the original action dict that triggered the interrupt
    acting_player: int  # who played/drew the triggering card
    # Players still to be asked (in turn order, skipping acting_player)
    interrupt_queue: List[int] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
#  Game state
# ─────────────────────────────────────────────────────────────────────────────

class GubsGame:
    MAX_HAND = 8

    def __init__(self, num_players: int = 2, seed: Optional[int] = None,
                 reveal_draws: bool = False):
        """
        Args:
            num_players:  2-6 players.
            seed:         RNG seed for reproducibility.
            reveal_draws: If True, log messages include drawn card names for all players.
                          Default False — opponent draws are hidden to avoid information
                          advantage when a human is playing.
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        assert 2 <= num_players <= 6, "GUBS supports 2-6 players"
        self.num_players = num_players
        self.reveal_draws = reveal_draws

        self.hands:    List[List[Card]]       = [[] for _ in range(num_players)]
        self.colonies: List[List[PlayedGub]]  = [[] for _ in range(num_players)]

        self.letters_drawn: List[str] = []

        # ── Turn tracking ──
        self.current_player   = 0
        self.drawn_this_turn  = False
        self.skipped_last_turn: List[bool] = [False] * num_players
        # "draw"    : active player may draw or skip
        # "play"    : active player plays cards
        # "interrupt": an interrupt window is open; current_player is the player
        #              currently being asked to respond
        # "discard" : active player discards to hand limit
        # "game_over"
        self.phase = "draw"

        # ── Interrupt state ──
        # When phase=="interrupt", this holds what is pending
        self.pending: Optional[PendingAction] = None
        # After interrupt window closes, we remember the original active player
        self.active_player = 0   # the player whose turn it "really" is

        self.deck:    List[Card] = build_deck()
        self.discard: List[Card] = []
        self.log:     List[str]  = []

        # Gargok Plague choice state — used during phase="gargok_plague_choice"
        self._gargok_queue: List[int] = []   # players still to be asked
        self._gargok_pre_saved: set = set()  # players who used Age Old Cure during the interrupt window
        # Traveling Merchant choice state — used during phase="traveling_merchant_choose"
        self._tm_queue: List[int] = []       # players still to choose their keep card
        self._tm_kept: Dict[int, Optional[Card]] = {}     # player -> kept card
        self._tm_leftover: Dict[int, List[Card]] = {}     # player -> unchosen cards
        # Scout rearrange state — used during phase="scout_rearrange"
        self._scout_peek_player: int = -1    # player who played Scout (for rearrange phase)
        # Scout deck reorder state — used during phase="scout_reorder"
        self._scout_player: int = -1         # who played Scout

        self._setup(num_players)

    # ── Setup ─────────────────────────────────

    def _setup(self, num_players: int):
        for p in range(num_players):
            self.colonies[p].append(PlayedGub(owner=p))
        for p in range(num_players):
            while len(self.hands[p]) < 3:
                card = self.deck.pop(0)
                if card.card_type in (CardType.EVENT, CardType.LETTER):
                    # Letters and Events can never sit in a hand — they must be
                    # drawn and immediately played/resolved. Reshuffle back into
                    # the deck at a random later position and draw again.
                    idx = random.randint(0, len(self.deck) - 1)
                    self.deck.insert(idx, card)
                else:
                    self.hands[p].append(card)
        self._log("Game begins! Each player has 1 Gub and 3 cards.")

    def _log(self, msg: str):
        self.log.append(msg)

    # ── Scoring ───────────────────────────────

    def calculate_scores(self) -> List[int]:
        return [sum(g.points for g in self.colonies[p]) for p in range(self.num_players)]

    def get_winner(self) -> int:
        scores = self.calculate_scores()
        mx = max(scores)
        tied = [p for p, s in enumerate(scores) if s == mx]
        if len(tied) == 1:
            return tied[0]
        for p in tied:
            if any(g.is_elder and g.state != GubState.TRAPPED for g in self.colonies[p]):
                return p
        min_hand = min(len(self.hands[p]) for p in tied)
        still = [p for p in tied if len(self.hands[p]) == min_hand]
        return still[0] if len(still) == 1 else -1

    def is_terminal(self) -> bool:
        return self.phase == "game_over"

    # ── Interrupt helpers ─────────────────────

    def _interrupt_queue_for(self, acting_player: int) -> List[int]:
        """All other players in turn order starting after the acting player."""
        return [(acting_player + 1 + i) % self.num_players
                for i in range(self.num_players - 1)]

    def _open_interrupt(self, kind: str, action: Dict, acting_player: int):
        """
        Open an interrupt window. Sets phase="interrupt" and sets current_player
        to the first player in the queue who actually has an applicable interrupt card.
        If nobody has one, resolves the pending action immediately.

        For "event" and "letter" kinds, the acting player (the one who drew the
        card) is ALSO included in the queue — Flop Boat (and Cricket Song mimicking
        it) lets a player shuffle their own bad draw back into the deck. The acting
        player goes first, followed by the other players in turn order.
        """
        others = self._interrupt_queue_for(acting_player)
        if kind in ("event", "letter"):
            queue = [acting_player] + others
        else:
            queue = others
        # Pre-filter: only include players who could actually fire an interrupt
        eligible = [p for p in queue if self._has_applicable_interrupt(p, kind)]
        if not eligible:
            # No-one can interrupt — resolve immediately
            self._resolve_pending(action, kind, acting_player)
            return

        self.pending = PendingAction(
            kind=kind,
            action=action,
            acting_player=acting_player,
            interrupt_queue=queue,  # full queue; we skip ineligible ones in get_all_valid_actions
        )
        self.phase = "interrupt"
        self.current_player = eligible[0]

    def _has_applicable_interrupt(self, player: int, kind: str) -> bool:
        """Can player respond to the given interrupt kind?"""
        for card in self.hands[player]:
            if card.name == "Cricket Song":
                return True   # Cricket Song can always mimic an interrupt
            triggers = INTERRUPT_TRIGGERS.get(card.name, [])
            if kind in triggers:
                return True
            if card.name == "Age Old Cure" and self._pending_is_gargok_plague():
                return True
        return False

    def _pending_is_gargok_plague(self) -> bool:
        """True if the current pending interrupt action is a Gargok Plague event."""
        if self.pending is None:
            return False
        card = self.pending.action.get("card")
        return self.pending.kind == "event" and card is not None and card.name == "Gargok Plague"

    def _advance_interrupt_queue(self):
        """
        Move to the next player in the interrupt queue.
        If queue exhausted, resolve the pending action.
        """
        assert self.pending is not None
        queue = self.pending.interrupt_queue
        # Remove the current player from the queue
        if self.current_player in queue:
            queue.remove(self.current_player)

        # Find the next eligible player
        while queue:
            next_p = queue[0]
            if self._has_applicable_interrupt(next_p, self.pending.kind):
                self.current_player = next_p
                return
            else:
                queue.remove(next_p)

        # Queue exhausted — resolve
        pa = self.pending
        self.pending = None
        self._restore_active_player_phase()
        self._resolve_pending(pa.action, pa.kind, pa.acting_player)

    def _restore_active_player_phase(self):
        """After interrupt window closes, restore current_player and phase."""
        self.current_player = self.active_player
        self.phase = "play"  # always return to play phase after interrupt

    def _resolve_pending(self, action: Dict, kind: str, acting_player: int):
        """Actually execute the action that was pending interrupt."""
        atype = action["type"]
        self._log(f"  → Resolves: {atype}")

        if atype == "play_lure":
            self._exec_lure(acting_player, action)
        elif atype == "play_super_lure":
            self._exec_super_lure(acting_player, action)
        elif atype == "play_cyclone":
            self._exec_cyclone(acting_player, action)
        elif atype == "play_ring":
            self._exec_ring(acting_player, action)
        elif atype == "play_sud_spout":
            self._exec_sud_spout(acting_player, action)
        elif atype == "play_lightning_elder":
            self._exec_lightning_elder(acting_player)
        elif atype == "play_lightning_hand":
            self._exec_lightning_hand(acting_player, action["target_player"])
        elif atype == "play_omen_beetle":
            self._exec_omen_beetle(acting_player)
        elif atype == "play_smahl_thief_gub":
            self._exec_smahl_thief_gub(acting_player, action)
        elif atype == "play_smahl_thief_barricade":
            self._exec_smahl_thief_barricade(acting_player, action)
        elif atype == "play_spear_sud_spout":
            self._exec_spear_sud_spout(acting_player, action)
        elif atype == "play_spear_discard_gub":
            self._exec_spear_discard_gub(acting_player, action)
        elif atype in ("_event_resolve",):
            self._resolve_event_card(action["card"])
        elif atype == "_letter_resolve":
            self._exec_letter(action["card"])

    # ── Valid actions ─────────────────────────

    def get_all_valid_actions(self) -> List[Dict]:
        """
        Returns valid actions for the current player in the current phase.

        During phase="interrupt", returns interrupt actions available to the
        current player (i.e. someone other than the active player), plus
        "pass_interrupt" to decline.
        """
        cp = self.current_player

        # ── SCOUT REARRANGE PHASE ──────────────
        if self.phase == "scout_rearrange":
            from itertools import permutations
            n = min(3, len(self.deck))
            top_names = [self.deck[i].name for i in range(n)]
            return [{"type": "scout_rearrange", "order": list(perm), "top_names": top_names}
                    for perm in permutations(range(n))]

        # ── TRAVELING MERCHANT CHOOSE PHASE ────
        if self.phase == "traveling_merchant_choose":
            cp = self.current_player
            if not self.hands[cp]:
                # Nothing to keep — record empty and auto-advance
                self._tm_kept[cp] = None
                self._tm_leftover[cp] = []
                self._advance_tm_queue()
                return self.get_all_valid_actions()
            return [{"type": "tm_keep_card", "card_idx": i}
                    for i in range(len(self.hands[cp]))]

        # ── GARGOK PLAGUE CHOICE PHASE ─────────
        if self.phase == "gargok_plague_choice":
            cp = self.current_player
            cure_idx = next((i for i, c in enumerate(self.hands[cp])
                             if c.name == "Age Old Cure"), None)
            actions = []
            if cure_idx is not None:
                actions.append({"type": "gargok_use_cure", "card_idx": cure_idx})
            actions.append({"type": "gargok_decline_cure"})
            return actions

        # ── INTERRUPT PHASE ────────────────────
        if self.phase == "interrupt":
            assert self.pending is not None
            actions: List[Dict] = [{"type": "pass_interrupt"}]
            kind = self.pending.kind
            for i, card in enumerate(self.hands[cp]):
                cname = card.name
                triggers = INTERRUPT_TRIGGERS.get(cname, [])
                if kind in triggers:
                    actions.append({"type": "play_interrupt",
                                    "card_name": cname, "card_idx": i})
                elif cname == "Age Old Cure" and self._pending_is_gargok_plague():
                    # Age Old Cure can be played proactively here to save this
                    # player's hand from Gargok Plague, as an alternative to
                    # (or alongside) someone else playing Flop Boat.
                    actions.append({"type": "play_interrupt",
                                    "card_name": cname, "card_idx": i,
                                    "is_gargok_save": True})
                elif cname == "Cricket Song":
                    # Cricket Song can mimic the applicable interrupt
                    if kind in ("hazard", "trap", "spear"):
                        actions.append({"type": "play_interrupt",
                                        "card_name": "Feather", "card_idx": i,
                                        "is_cricket_song": True})
                    elif kind in ("lure", "super_lure"):
                        actions.append({"type": "play_interrupt",
                                        "card_name": "Blind Fold", "card_idx": i,
                                        "is_cricket_song": True})
                    elif kind in ("event", "letter"):
                        actions.append({"type": "play_interrupt",
                                        "card_name": "Flop Boat", "card_idx": i,
                                        "is_cricket_song": True})
                    if self._pending_is_gargok_plague():
                        # Cricket Song can also mimic Age Old Cure here, to
                        # protect this player's own hand from the plague.
                        actions.append({"type": "play_interrupt",
                                        "card_name": "Age Old Cure", "card_idx": i,
                                        "is_cricket_song": True,
                                        "is_gargok_save": True})
            return actions

        # ── DRAW PHASE ─────────────────────────
        if self.phase == "draw":
            actions = []
            if not self.drawn_this_turn:
                if self.deck:
                    actions.append({"type": "draw"})
                if not self.skipped_last_turn[cp]:
                    actions.append({"type": "skip_draw"})
                if not actions:
                    # Deck is empty AND we already skipped last turn — no legal
                    # move is possible. This can only happen if the deck ran out
                    # before the 3rd Letter was drawn (e.g. it's still buried in
                    # a hand from a Traveling Merchant/Gargok Plague reshuffle).
                    # End the game gracefully rather than stalling.
                    self._log("Deck exhausted with no legal draw/skip — GAME OVER!")
                    self.phase = "game_over"
                    return []
            else:
                actions.append({"type": "begin_play"})
            return actions

        # ── PLAY PHASE ─────────────────────────
        if self.phase == "play":
            hand = self.hands[cp]
            actions = [{"type": "end_play"}]

            for i, card in enumerate(hand):
                ctype = card.card_type
                cname = card.name

                # GUB
                if ctype == CardType.GUB:
                    actions.append({"type": "play_gub", "card_idx": i})

                # BARRICADE
                elif ctype == CardType.BARRICADE:
                    for gi, gub in enumerate(self.colonies[cp]):
                        if gub.state == GubState.FREE and not gub.is_elder:
                            actions.append({"type": "play_barricade",
                                            "card_idx": i, "target_player": cp,
                                            "target_gub_idx": gi})
                    if card.barricade_kind == BarricadeKind.MUSHROOM:
                        for tp in range(self.num_players):
                            for gi, gub in enumerate(self.colonies[tp]):
                                if (gub.barricade and
                                        gub.barricade.barricade_kind == BarricadeKind.MUSHROOM):
                                    actions.append({"type": "play_mushroom_destroy",
                                                    "card_idx": i, "target_player": tp,
                                                    "target_gub_idx": gi})
                    if card.barricade_kind == BarricadeKind.TOAD_RIDER:
                        for tp in range(self.num_players):
                            for gi, gub in enumerate(self.colonies[tp]):
                                if gub.barricade is not None:
                                    actions.append({"type": "play_toad_rider_destroy",
                                                    "card_idx": i, "target_player": tp,
                                                    "target_gub_idx": gi})

                # LURE — opens interrupt window
                elif cname == "Lure":
                    for tp in range(self.num_players):
                        if tp == cp:
                            continue
                        for gi, gub in enumerate(self.colonies[tp]):
                            if gub.state == GubState.FREE and not gub.is_elder:
                                actions.append({"type": "play_lure",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})

                # SUPER LURE — opens interrupt window
                elif cname == "Super Lure":
                    for tp in range(self.num_players):
                        if tp == cp:
                            continue
                        if any(g.state in (GubState.FREE, GubState.PROTECTED)
                               and not g.is_elder for g in self.colonies[tp]):
                            actions.append({"type": "play_super_lure",
                                            "card_idx": i, "target_player": tp})

                # CYCLONE — opens interrupt window
                elif cname == "Cyclone":
                    for tp in range(self.num_players):
                        if tp == cp:
                            continue
                        if any(g.state == GubState.PROTECTED for g in self.colonies[tp]):
                            actions.append({"type": "play_cyclone",
                                            "card_idx": i, "target_player": tp})

                # LIGHTNING — opens interrupt window
                elif cname == "Lightning":
                    elder_in_play = any(g.is_elder
                                        for tp in range(self.num_players)
                                        for g in self.colonies[tp])
                    if elder_in_play:
                        actions.append({"type": "play_lightning_elder", "card_idx": i})
                    for tp in range(self.num_players):
                        if tp != cp and self.hands[tp]:
                            actions.append({"type": "play_lightning_hand",
                                            "card_idx": i, "target_player": tp})

                # OMEN BEETLE — opens interrupt window
                elif cname == "Omen Beetle":
                    if any(g.barricade and
                           g.barricade.barricade_kind == BarricadeKind.MUSHROOM
                           for tp in range(self.num_players)
                           for g in self.colonies[tp]):
                        actions.append({"type": "play_omen_beetle", "card_idx": i})

                # SMAHL THIEF — opens interrupt window
                elif cname == "Smahl Thief":
                    for tp in range(self.num_players):
                        if tp == cp:
                            continue
                        for gi, gub in enumerate(self.colonies[tp]):
                            is_ring_trapped = (gub.trap is not None and
                                               gub.trap.trap_kind in (
                                                   TrapKind.SINGLE_RING,
                                                   TrapKind.DOUBLE_RING,
                                                   TrapKind.TRIPLE_RING))
                            if not gub.is_elder and not is_ring_trapped:
                                actions.append({"type": "play_smahl_thief_gub",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})
                            if gub.barricade is not None:
                                actions.append({"type": "play_smahl_thief_barricade",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})

                # RINGS — opens interrupt window
                elif ctype == CardType.TRAP and card.trap_kind in (
                        TrapKind.SINGLE_RING, TrapKind.DOUBLE_RING, TrapKind.TRIPLE_RING):
                    cap = card.trap_capacity
                    free_gubs = [(tp, gi)
                                 for tp in range(self.num_players)
                                 for gi, gub in enumerate(self.colonies[tp])
                                 if gub.state == GubState.FREE and not gub.is_elder]
                    if len(free_gubs) >= cap:
                        from itertools import combinations
                        count = 0
                        for combo in combinations(free_gubs, cap):
                            actions.append({"type": "play_ring",
                                            "card_idx": i, "gub_targets": list(combo)})
                            count += 1
                            if count >= 20:
                                break

                # SUD SPOUT — opens interrupt window
                elif ctype == CardType.TOOL_HAZARD and cname == "Sud Spout":
                    for tp in range(self.num_players):
                        for gi, gub in enumerate(self.colonies[tp]):
                            if gub.state == GubState.FREE and not gub.is_elder:
                                actions.append({"type": "play_sud_spout",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})

                # HAKI FLUTE — no interrupt
                elif cname == "Haki Flute":
                    for tp in range(self.num_players):
                        for gi, gub in enumerate(self.colonies[tp]):
                            if (gub.trap is not None and
                                    gub.trap.trap_kind in (TrapKind.SINGLE_RING,
                                                           TrapKind.DOUBLE_RING,
                                                           TrapKind.TRIPLE_RING)):
                                actions.append({"type": "play_haki_flute",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})

                # SPEAR — opens interrupt window (hazard/tool hybrid)
                elif cname == "Spear":
                    for tp in range(self.num_players):
                        for gi, gub in enumerate(self.colonies[tp]):
                            if (gub.trap is not None and
                                    gub.trap.trap_kind == TrapKind.SUD_SPOUT):
                                actions.append({"type": "play_spear_sud_spout",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})
                            if gub.state == GubState.FREE and not gub.is_elder:
                                actions.append({"type": "play_spear_discard_gub",
                                                "card_idx": i, "target_player": tp,
                                                "target_gub_idx": gi})

                # SCOUT — no interrupt
                elif cname == "Scout":
                    if self.deck:
                        actions.append({"type": "play_scout_deck", "card_idx": i})
                    for tp in range(self.num_players):
                        if tp != cp:
                            actions.append({"type": "play_scout_hand",
                                            "card_idx": i, "target_player": tp})

                # RETREAT — no interrupt
                elif cname == "Retreat":
                    if self.colonies[cp]:
                        actions.append({"type": "play_retreat", "card_idx": i})

                # AGE OLD CURE — proactive use on own turn
                elif cname == "Age Old Cure":
                    gubs_in_discard = [c for c in self.discard
                                       if c.card_type == CardType.GUB and not c.is_elder]
                    if gubs_in_discard:
                        actions.append({"type": "play_age_old_cure_retrieve",
                                        "card_idx": i})

                # CRICKET SONG — on own turn mimic a Hazard or Tool
                elif cname == "Cricket Song":
                    # Mimic each Hazard with their targeting variants
                    for tp in range(self.num_players):
                        if tp != cp:
                            for gi, gub in enumerate(self.colonies[tp]):
                                if gub.state == GubState.FREE and not gub.is_elder:
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Lure",
                                                    "target_player": tp, "target_gub_idx": gi})
                            if any(g.state in (GubState.FREE, GubState.PROTECTED)
                                   and not g.is_elder for g in self.colonies[tp]):
                                actions.append({"type": "play_cricket_song",
                                                "card_idx": i, "as_card": "Super Lure",
                                                "target_player": tp})
                            if any(g.state == GubState.PROTECTED for g in self.colonies[tp]):
                                actions.append({"type": "play_cricket_song",
                                                "card_idx": i, "as_card": "Cyclone",
                                                "target_player": tp})
                            if self.hands[tp]:
                                actions.append({"type": "play_cricket_song",
                                                "card_idx": i, "as_card": "Lightning",
                                                "type": "play_cricket_song",
                                                "card_idx": i, "as_card": "Lightning",
                                                "target_player": tp})
                                # store as lightning_hand action
                                actions[-1] = {"type": "play_cricket_song",
                                               "card_idx": i, "as_card": "Lightning",
                                               "as_action": "play_lightning_hand",
                                               "target_player": tp}
                            for gi, gub in enumerate(self.colonies[tp]):
                                if not gub.is_elder:
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Smahl Thief",
                                                    "as_action": "play_smahl_thief_gub",
                                                    "target_player": tp, "target_gub_idx": gi})
                                if gub.barricade:
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Smahl Thief",
                                                    "as_action": "play_smahl_thief_barricade",
                                                    "target_player": tp, "target_gub_idx": gi})
                                if gub.trap is not None and gub.trap.trap_kind == TrapKind.SUD_SPOUT:
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Spear",
                                                    "as_action": "play_spear_sud_spout",
                                                    "target_player": tp, "target_gub_idx": gi})
                                if gub.state == GubState.FREE and not gub.is_elder:
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Spear",
                                                    "as_action": "play_spear_discard_gub",
                                                    "target_player": tp, "target_gub_idx": gi})
                                if (gub.trap is not None and gub.trap.trap_kind in (
                                        TrapKind.SINGLE_RING, TrapKind.DOUBLE_RING, TrapKind.TRIPLE_RING)):
                                    actions.append({"type": "play_cricket_song",
                                                    "card_idx": i, "as_card": "Haki Flute",
                                                    "target_player": tp, "target_gub_idx": gi})
                    if any(g.is_elder for p in range(self.num_players)
                           for g in self.colonies[p]):
                        actions.append({"type": "play_cricket_song",
                                        "card_idx": i, "as_card": "Lightning",
                                        "as_action": "play_lightning_elder"})
                    if any(g.barricade and g.barricade.barricade_kind == BarricadeKind.MUSHROOM
                           for p in range(self.num_players) for g in self.colonies[p]):
                        actions.append({"type": "play_cricket_song",
                                        "card_idx": i, "as_card": "Omen Beetle"})
                    if self.deck:
                        actions.append({"type": "play_cricket_song",
                                        "card_idx": i, "as_card": "Scout",
                                        "as_action": "play_scout_deck"})
                    for tp in range(self.num_players):
                        if tp != cp:
                            actions.append({"type": "play_cricket_song",
                                            "card_idx": i, "as_card": "Scout",
                                            "as_action": "play_scout_hand",
                                            "target_player": tp})
                    if any(c.card_type == CardType.GUB and not c.is_elder
                           for c in self.discard):
                        actions.append({"type": "play_cricket_song",
                                        "card_idx": i, "as_card": "Age Old Cure",
                                        "as_action": "play_age_old_cure_retrieve"})
                    if self.colonies[cp]:
                        actions.append({"type": "play_cricket_song",
                                        "card_idx": i, "as_card": "Retreat"})

                # FEATHER / BLIND FOLD / FLOP BOAT:
                # These interrupt cards have NO proactive use on own turn.
                # They appear only during phase="interrupt".
                # (If held in hand doing nothing, that's fine — hand limit applies.)

            return actions

        # ── DISCARD PHASE ──────────────────────
        if self.phase == "discard":
            excess = len(self.hands[cp]) - self.MAX_HAND
            if excess > 0:
                return [{"type": "discard_card", "card_idx": i}
                        for i in range(len(self.hands[cp]))]
            else:
                return [{"type": "end_discard"}]

        return []

    # ── Apply action ──────────────────────────

    def apply_action(self, action: Dict) -> bool:
        atype = action["type"]
        cp    = self.current_player

        if atype == "scout_rearrange":
            order = action["order"]
            n = len(order)
            top = [self.deck[i] for i in range(n)]
            for i, orig_idx in enumerate(order):
                self.deck[i] = top[orig_idx]
            self._log(f"Player {self.current_player} rearranges top {n} deck cards: "
                      f"{[self.deck[i].name for i in range(n)]}")
            self._restore_active_player_phase()
            return True

        if atype == "tm_keep_card":
            cp = self.current_player
            keep_idx = action["card_idx"]
            kept = self.hands[cp][keep_idx]
            leftover = [c for j, c in enumerate(self.hands[cp]) if j != keep_idx]
            self._tm_kept[cp] = kept
            self._tm_leftover[cp] = leftover
            self._log(f"  Traveling Merchant: Player {cp} keeps {kept.name} "
                      f"({len(leftover)} card(s) pass to the right).")
            self._advance_tm_queue()
            return True

        if atype == "gargok_use_cure":
            cp = self.current_player
            cure_idx = action["card_idx"]
            self.discard.append(self.hands[cp].pop(cure_idx))
            self._log(f"  Player {cp} uses Age Old Cure — hand saved!")
            self._advance_gargok_queue()
            return True

        if atype == "gargok_decline_cure":
            cp = self.current_player
            self._log(f"  Player {cp} declines to use Age Old Cure — hand shuffled into deck!")
            for c in self.hands[cp]:
                self.deck.insert(random.randint(0, len(self.deck)), c)
            self.hands[cp] = []
            self._advance_gargok_queue()
            return True

        # ── INTERRUPT RESPONSES ────────────────
        if atype == "pass_interrupt":
            self._advance_interrupt_queue()
            return True

        if atype == "play_interrupt":
            return self._handle_interrupt_play(cp, action)

        # ── DRAW PHASE ─────────────────────────
        if atype == "draw":
            return self._do_draw()

        if atype == "skip_draw":
            self.skipped_last_turn[cp] = True
            self.drawn_this_turn = True
            self.active_player = cp
            self.phase = "play"
            self._log(f"Player {cp} skips drawing.")
            return True

        if atype == "begin_play":
            self.active_player = cp
            self.phase = "play"
            return True

        # ── PLAY PHASE TRANSITIONS ─────────────
        if atype == "end_play":
            self.phase = "discard"
            return True

        if atype == "end_discard":
            self._advance_turn()
            return True

        if atype == "discard_card":
            idx  = action["card_idx"]
            card = self.hands[cp].pop(idx)
            self.discard.append(card)
            self._log(f"Player {cp} discards {card.name}.")
            if len(self.hands[cp]) <= self.MAX_HAND:
                self._advance_turn()
            return True

        # ── PLAY ACTIONS ───────────────────────
        if atype == "play_gub":
            return self._play_gub(cp, action["card_idx"])

        if atype == "play_barricade":
            return self._play_barricade(cp, action["card_idx"],
                                        action["target_player"],
                                        action["target_gub_idx"])

        if atype == "play_mushroom_destroy":
            return self._play_mushroom_destroy(cp, action["card_idx"],
                                               action["target_player"],
                                               action["target_gub_idx"])

        if atype == "play_toad_rider_destroy":
            return self._play_toad_rider_destroy(cp, action["card_idx"],
                                                  action["target_player"],
                                                  action["target_gub_idx"])

        if atype == "play_haki_flute":
            return self._play_haki_flute(cp, action["card_idx"],
                                         action["target_player"],
                                         action["target_gub_idx"])

        if atype in ("play_spear_sud_spout", "play_spear_discard_gub"):
            self._discard_from_hand(cp, action["card_idx"])
            self._log(f"Player {cp} plays Spear! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("spear", action, cp)
            return True

        if atype == "play_scout_deck":
            return self._play_scout_deck(cp, action["card_idx"])

        if atype == "play_scout_hand":
            return self._play_scout_hand(cp, action["card_idx"],
                                         action["target_player"])

        if atype == "play_retreat":
            return self._play_retreat(cp, action["card_idx"])

        if atype == "play_age_old_cure_retrieve":
            return self._play_age_old_cure_retrieve(cp, action["card_idx"])

        if atype == "play_cricket_song":
            return self._play_cricket_song_own_turn(cp, action)

        # ── HAZARD / TRAP ACTIONS (open interrupt window) ──

        if atype in ("play_lure", "play_super_lure"):
            self._discard_from_hand(cp, action["card_idx"])
            kind = "lure" if atype == "play_lure" else "super_lure"
            self._log(f"Player {cp} plays {kind.replace('_', ' ').title()}! "
                      f"(interrupt window open)")
            self.active_player = cp
            self._open_interrupt(kind, action, cp)
            return True

        if atype == "play_cyclone":
            self._discard_from_hand(cp, action["card_idx"])
            self._log(f"Player {cp} plays Cyclone! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("hazard", action, cp)
            return True

        if atype in ("play_lightning_elder", "play_lightning_hand"):
            self._discard_from_hand(cp, action["card_idx"])
            self._log(f"Player {cp} plays Lightning! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("hazard", action, cp)
            return True

        if atype == "play_omen_beetle":
            self._discard_from_hand(cp, action["card_idx"])
            self._log(f"Player {cp} plays Omen Beetle! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("hazard", action, cp)
            return True

        if atype in ("play_smahl_thief_gub", "play_smahl_thief_barricade"):
            self._discard_from_hand(cp, action["card_idx"])
            self._log(f"Player {cp} plays Smahl Thief! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("hazard", action, cp)
            return True

        if atype == "play_ring":
            self.hands[cp].pop(action["card_idx"])
            # Card stays with ring — do NOT discard yet
            self._log(f"Player {cp} plays {action.get('card_idx', '?')}-Ring! "
                      f"(interrupt window open)")
            self.active_player = cp
            self._open_interrupt("trap", action, cp)
            return True

        if atype == "play_sud_spout":
            self.hands[cp].pop(action["card_idx"])
            self._log(f"Player {cp} plays Sud Spout! (interrupt window open)")
            self.active_player = cp
            self._open_interrupt("trap", action, cp)
            return True

        return False

    # ── Interrupt execution ───────────────────

    def _handle_interrupt_play(self, interruptor: int, action: Dict) -> bool:
        """A player fires an interrupt card to cancel the pending action."""
        assert self.pending is not None
        card_idx   = action["card_idx"]
        card_name  = action["card_name"]
        is_cricket = action.get("is_cricket_song", False)

        # Age Old Cure played during the interrupt window for Gargok Plague:
        # this doesn't cancel the pending event — it just protects this
        # player's hand from being shuffled away when the plague resolves.
        if action.get("is_gargok_save"):
            card = self.hands[interruptor].pop(card_idx)
            self.discard.append(card)
            self._gargok_pre_saved.add(interruptor)
            self._log(f"⚡ Player {interruptor} plays "
                      f"{'Cricket Song as Age Old Cure' if is_cricket else 'Age Old Cure'} — "
                      f"hand protected from the pending Gargok Plague!")
            self._advance_interrupt_queue()
            return True

        # Remove the card from hand
        card = self.hands[interruptor].pop(card_idx)
        self.discard.append(card)

        kind = self.pending.kind
        pa   = self.pending
        self._log(f"⚡ Player {interruptor} plays "
                  f"{'Cricket Song as ' if is_cricket else ''}{card_name} "
                  f"— INTERRUPTS the {pa.kind}!")

        # Flop Boat cancelling a Letter or Event: always shuffle the card back into the deck.
        if card_name == "Flop Boat" and kind in ("letter", "event"):
            drawn_card = pa.action.get("card")
            if drawn_card is not None:
                if kind == "letter":
                    self.letters_drawn.remove(drawn_card.letter)
                # Remove from discard (it was placed there when drawn) and shuffle back in.
                if drawn_card in self.discard:
                    self.discard.remove(drawn_card)
                ins = random.randint(0, len(self.deck))
                self.deck.insert(ins, drawn_card)
                if kind == "letter":
                    self._log(f"  Flop Boat shuffles Letter '{drawn_card.letter}' back into the deck!")
                else:
                    self._log(f"  Flop Boat shuffles Event '{drawn_card.name}' back into the deck!")

        # Clear pending and put the ring/sud-spout card back if applicable
        pending_atype = pa.action["type"]
        if pending_atype == "play_ring":
            # The ring card was already popped from hand but not placed —
            # it is now cancelled, so discard it
            ring_card_name = None
            if pa.action.get("card_idx") is not None:
                # We can't recover card_idx easily after pop; discard a representative card
                # In practice the card was already popped; just move to discard
                pass  # card is already gone from hand; discard the ring card via name lookup
            self.discard.append(CARD_BY_NAME.get("Single Ring") or CARD_BY_NAME.get("Gub"))
        elif pending_atype == "play_sud_spout":
            self.discard.append(CARD_BY_NAME["Sud Spout"])

        self.pending = None
        self._restore_active_player_phase()
        return True

    # ── Draw logic ────────────────────────────

    def _do_draw(self) -> bool:
        if not self.deck:
            self._log("Deck empty! Game ends.")
            self.phase = "game_over"
            return True

        cp = self.current_player
        self.drawn_this_turn = True
        self.skipped_last_turn[cp] = False
        card = self.deck.pop(0)
        self.active_player = cp

        if card.card_type == CardType.LETTER:
            self.letters_drawn.append(card.letter)
            self.discard.append(card)
            self._log(f"Letter '{card.letter}' drawn! "
                      f"Letters so far: {self.letters_drawn}")
            if len(self.letters_drawn) >= 3:
                self._log("Third letter drawn — GAME OVER!")
                self.phase = "game_over"
                return True
            # Open interrupt window for Flop Boat
            self._open_interrupt("letter",
                                  {"type": "_letter_resolve", "card": card}, cp)
            return True

        if card.card_type == CardType.EVENT:
            self._log(f"EVENT drawn: {card.name}!")
            self.discard.append(card)
            # Open interrupt window for Flop Boat
            self._open_interrupt("event",
                                  {"type": "_event_resolve", "card": card}, cp)
            return True

        # Normal card goes to hand (hidden by default)
        self.hands[cp].append(card)
        if self.reveal_draws:
            self._log(f"Player {cp} draws {card.name}.")
        else:
            self._log(f"Player {cp} draws a card. [{len(self.hands[cp])} in hand]")
        self.phase = "play"
        return True

    # ── Event resolution ──────────────────────

    def _resolve_event_card(self, card: Card):
        """Called after interrupt window closes with no cancellation."""
        n = card.name
        self._log(f"  EVENT resolves: {n}")

        if n == "Dangerous Alchemy":
            cp = self.active_player
            remove = [g for g in self.colonies[cp] if not g.is_elder]
            for g in remove:
                if g.barricade:
                    self.discard.append(g.barricade)
                if g.trap:
                    self.discard.append(g.trap)
                self.discard.append(CARD_BY_NAME["Gub"])
                self.colonies[cp].remove(g)
            self._log(f"  Dangerous Alchemy! Player {cp} loses {len(remove)} Gubs! "
                      f"Elder is immune.")

        elif n == "Rumor of Wasps":
            for p in range(self.num_players):
                remaining = []
                for g in self.colonies[p]:
                    if (not g.is_elder and g.barricade
                            and g.barricade.barricade_kind == BarricadeKind.TOAD_RIDER):
                        # The Toad Rider and the Gub it was protecting are both
                        # shuffled into the deck.
                        self.deck.insert(random.randint(0, len(self.deck)), g.barricade)
                        self.deck.insert(random.randint(0, len(self.deck)), CARD_BY_NAME["Gub"])
                        self._log(f"  Player {p}'s Toad Rider and the Gub behind it "
                                  f"are shuffled into the deck!")
                    else:
                        remaining.append(g)
                self.colonies[p] = remaining

        elif n == "Flash Flood":
            total = 0
            for p in range(self.num_players):
                keep = []
                for g in self.colonies[p]:
                    if g.state == GubState.FREE and not g.is_elder:
                        self.deck.insert(random.randint(0, len(self.deck)),
                                         CARD_BY_NAME["Gub"])
                        total += 1
                    else:
                        keep.append(g)
                self.colonies[p] = keep
            self._log(f"  Flash Flood! {total} Free Gub(s) shuffled back into deck!")

        elif n == "Gargok Plague":
            # Give every player who holds an Age Old Cure the choice to use it.
            # Build the queue of players who have one; others lose their hand immediately.
            # Players who already used Age Old Cure during the interrupt window
            # are skipped here — their hand is already protected.
            self._gargok_queue = []
            for p in range(self.num_players):
                if p in self._gargok_pre_saved:
                    self._log(f"  Player {p} already used Age Old Cure — hand protected!")
                    continue
                has_cure = any(c.name == "Age Old Cure" for c in self.hands[p])
                if has_cure:
                    self._gargok_queue.append(p)
                else:
                    self._log(f"  Player {p} has no Age Old Cure — hand shuffled into deck!")
                    for c in self.hands[p]:
                        self.deck.insert(random.randint(0, len(self.deck)), c)
                    self.hands[p] = []
            self._gargok_pre_saved = set()
            if self._gargok_queue:
                self.phase = "gargok_plague_choice"
                self.current_player = self._gargok_queue[0]
                self._log(f"  Gargok Plague: Player {self.current_player} — use Age Old Cure? (yes/no)")
            # If nobody has a cure the queue is empty and we just stay in play phase.

        elif n == "Traveling Merchant":
            # Step 1: each player chooses ONE card from their OWN current hand
            # to keep. Step 2 (after everyone has chosen): the unchosen cards
            # from each player pass to the next player (to their right), and
            # each player's new hand = [kept card] + [leftovers from the
            # player on their left].
            self._tm_kept     = {}   # player -> kept Card (or None if hand empty)
            self._tm_leftover = {}   # player -> List[Card] of unchosen cards
            self._tm_queue    = list(range(self.num_players))
            self._log("  Traveling Merchant: each player chooses one card "
                      "from their hand to keep. The rest pass to the next player.")
            self.phase = "traveling_merchant_choose"
            self.current_player = self._tm_queue[0]
            # If the first player's hand is empty, get_all_valid_actions will
            # auto-advance via _advance_tm_queue.

    def _exec_letter(self, card: Card):
        """Called when a letter resolves (wasn't cancelled by Flop Boat)."""
        # Already added to letters_drawn in _do_draw; nothing more to do
        # unless it's the third letter
        if len(self.letters_drawn) >= 3:
            self.phase = "game_over"

    # ── Pending action executors ──────────────

    def _exec_lure(self, player: int, action: Dict):
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi < len(self.colonies[tp]):
            gub = self.colonies[tp].pop(gi)
            gub.owner = player
            self.colonies[player].append(gub)
            self._log(f"Player {player} lures a Gub from Player {tp}!")

    def _exec_super_lure(self, player: int, action: Dict):
        tp = action["target_player"]
        stolen = [g for g in self.colonies[tp]
                  if g.state in (GubState.FREE, GubState.PROTECTED) and not g.is_elder]
        for g in stolen:
            self.colonies[tp].remove(g)
            if g.barricade:
                self.hands[tp].append(g.barricade)
                self._log(f"  {g.barricade.name} returned to Player {tp}'s hand.")
                g.barricade = None
            g.owner = player
            self.colonies[player].append(g)
        self._log(f"Player {player} Super Lures {len(stolen)} Gubs from Player {tp}! "
                  f"(Free + Protected)")

    def _exec_cyclone(self, player: int, action: Dict):
        tp = action["target_player"]
        for g in self.colonies[tp]:
            if g.barricade:
                self.discard.append(g.barricade)
                g.barricade = None
        self._log(f"Cyclone! Player {player} strips all barricades from Player {tp}!")

    def _exec_ring(self, player: int, action: Dict):
        card_idx = action["card_idx"]
        # Card was already popped from hand before interrupt window opened
        # Look up which ring card was played by trap capacity
        targets = action["gub_targets"]
        cap     = len(targets)
        card    = (CARD_BY_NAME["Single Ring"] if cap == 1
                   else CARD_BY_NAME["Double Ring"] if cap == 2
                   else CARD_BY_NAME["Triple Ring"])
        ring_gub = PlayedGub(owner=player)
        ring_gub.trap = card
        self.colonies[player].append(ring_gub)
        for (tp, gi) in sorted(targets, key=lambda x: -x[1]):
            if gi < len(self.colonies[tp]):
                gub = self.colonies[tp].pop(gi)
                gub.trap = card
                ring_gub.trapped_gubs.append(gub)
                self._log(f"  Ring traps Gub from Player {tp}!")

    def _exec_sud_spout(self, player: int, action: Dict):
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi < len(self.colonies[tp]):
            gub = self.colonies[tp][gi]
            gub.trap = CARD_BY_NAME["Sud Spout"]
            self._log(f"Sud Spout traps Player {tp}'s Gub!")

    def _exec_lightning_elder(self, player: int):
        for p in range(self.num_players):
            for i, gub in enumerate(self.colonies[p]):
                if gub.is_elder:
                    self.colonies[p].pop(i)
                    self._log(f"⚡ Lightning destroys the Esteemed Elder (was on "
                              f"Player {p}'s side)!")
                    return

    def _exec_lightning_hand(self, player: int, target: int):
        n = len(self.hands[target])
        for c in self.hands[target]:
            self.discard.append(c)
        self.hands[target] = []
        self._log(f"⚡ Lightning! Player {player} discards Player {target}'s "
                  f"hand ({n} cards)!")

    def _exec_omen_beetle(self, player: int):
        for p in range(self.num_players):
            remove = [g for g in self.colonies[p]
                      if g.barricade and
                      g.barricade.barricade_kind == BarricadeKind.MUSHROOM]
            for g in remove:
                self.discard.append(g.barricade)
                self.discard.append(CARD_BY_NAME["Gub"])
                self.colonies[p].remove(g)
                self._log(f"  Omen Beetle: Player {p} loses a Mushroom-protected Gub!")

    def _exec_smahl_thief_gub(self, player: int, action: Dict):
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi >= len(self.colonies[tp]):
            return
        gub = self.colonies[tp].pop(gi)
        if gub.barricade:
            self.hands[tp].append(gub.barricade)
            self._log(f"  {gub.barricade.name} returned to Player {tp}'s hand.")
            gub.barricade = None
        if gub.trap and gub.trap.trap_kind == TrapKind.SUD_SPOUT:
            self.discard.append(gub.trap)
            gub.trap = None
        self.hands[player].append(CARD_BY_NAME["Gub"])
        self._log(f"Smahl Thief! Player {player} steals a Gub from Player {tp} "
                  f"into hand!")

    def _exec_smahl_thief_barricade(self, player: int, action: Dict):
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi >= len(self.colonies[tp]):
            return
        gub = self.colonies[tp][gi]
        if gub.barricade:
            self.hands[player].append(gub.barricade)
            self._log(f"Smahl Thief! Player {player} steals {gub.barricade.name} "
                      f"from Player {tp} (Gub now Free).")
            gub.barricade = None

    # ── Non-interrupt card implementations ───

    def _discard_from_hand(self, player: int, card_idx: int) -> Card:
        card = self.hands[player].pop(card_idx)
        self.discard.append(card)
        return card

    def _play_gub(self, player: int, card_idx: int) -> bool:
        card = self.hands[player].pop(card_idx)
        gub  = PlayedGub(owner=player, is_elder=card.is_elder)
        self.colonies[player].append(gub)
        self._log(f"Player {player} plays "
                  f"{'Esteemed Elder' if card.is_elder else 'Gub'} into colony.")
        return True

    def _play_barricade(self, player: int, card_idx: int,
                        tp: int, gi: int) -> bool:
        card = self.hands[player].pop(card_idx)
        self.colonies[tp][gi].barricade = card
        self._log(f"Player {player} protects Gub with {card.name}.")
        return True

    def _play_mushroom_destroy(self, player: int, card_idx: int,
                               tp: int, gi: int) -> bool:
        card = self.hands[player].pop(card_idx)
        self.discard.append(card)
        gub = self.colonies[tp][gi]
        self.discard.append(gub.barricade)
        gub.barricade = None
        self._log(f"Player {player} uses Mushroom to destroy a Mushroom on "
                  f"Player {tp}'s Gub!")
        return True

    def _play_toad_rider_destroy(self, player: int, card_idx: int,
                                  tp: int, gi: int) -> bool:
        card = self.hands[player].pop(card_idx)
        self.discard.append(card)
        gub  = self.colonies[tp][gi]
        name = gub.barricade.name
        self.discard.append(gub.barricade)
        gub.barricade = None
        self._log(f"Player {player} uses Toad Rider to destroy {name} on "
                  f"Player {tp}'s Gub!")
        return True

    def _play_haki_flute(self, player: int, card_idx: int,
                         tp: int, gi: int) -> bool:
        self._discard_from_hand(player, card_idx)
        ring_gub = self.colonies[tp].pop(gi)
        for g in ring_gub.trapped_gubs:
            g.trap  = None
            g.owner = player
            self.colonies[player].append(g)
        self.discard.append(ring_gub.trap)
        self._log(f"Player {player} shatters a Ring, claiming "
                  f"{len(ring_gub.trapped_gubs)} Gubs!")
        return True

    def _exec_spear_sud_spout(self, player: int, action: Dict) -> bool:
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi < len(self.colonies[tp]):
            gub = self.colonies[tp][gi]
            self.discard.append(gub.trap)
            gub.trap = None
            self._log(f"Player {player} uses Spear to free Player {tp}'s Gub "
                      f"from Sud Spout (stays in place).")
        return True

    def _exec_spear_discard_gub(self, player: int, action: Dict) -> bool:
        tp = action["target_player"]
        gi = action["target_gub_idx"]
        if gi < len(self.colonies[tp]):
            self.colonies[tp].pop(gi)
            self.discard.append(CARD_BY_NAME["Gub"])
            self._log(f"Player {player} uses Spear to discard Player {tp}'s Free Gub!")
        return True

    def _play_scout_deck(self, player: int, card_idx: int) -> bool:
        self._discard_from_hand(player, card_idx)
        top = self.deck[:min(3, len(self.deck))]
        self._log(f"Player {player} scouts deck: top 3 = "
                  f"{[c.name for c in top]}")
        if len(top) > 1:
            # Open rearrange phase: player picks the order for these cards
            self._scout_peek_player = player
            self.phase = "scout_rearrange"
            self.current_player = player
        # If 0 or 1 cards there is nothing to rearrange; stay in play phase
        return True

    def _play_scout_hand(self, player: int, card_idx: int, tp: int) -> bool:
        self._discard_from_hand(player, card_idx)
        self._log(f"Player {player} scouts Player {tp}'s hand: "
                  f"{[c.name for c in self.hands[tp]]}")
        return True

    def _play_retreat(self, player: int, card_idx: int) -> bool:
        self._discard_from_hand(player, card_idx)
        reclaimed = []
        remaining = []
        for gub in self.colonies[player]:
            # Reclaim any barricade/trap attached to this gub.
            if gub.barricade:
                reclaimed.append(gub.barricade)
                gub.barricade = None
            if gub.trap:
                reclaimed.append(gub.trap)
                gub.trap = None
                # If this gub was a Ring holding opponents' Gubs, release them
                # back to their owners as Free Gubs.
                for g in gub.trapped_gubs:
                    g.trap  = None
                    self.colonies[g.owner].append(g)
                gub.trapped_gubs = []

            if gub.is_elder:
                # Esteemed Elder stays in play — only its barricade/trap (if any)
                # is reclaimed above; restrictions on the Elder still apply.
                remaining.append(gub)
            else:
                # The Gub itself returns to hand.
                reclaimed.append(CARD_BY_NAME["Gub"])

        self.colonies[player] = remaining
        self.hands[player].extend(reclaimed)
        while len(self.hands[player]) > self.MAX_HAND:
            self.discard.append(self.hands[player].pop())
        self._log(f"Player {player} retreats, reclaiming {len(reclaimed)} cards.")
        return True

    def _play_age_old_cure_retrieve(self, player: int, card_idx: int) -> bool:
        self._discard_from_hand(player, card_idx)
        for i, c in enumerate(self.discard):
            if c.card_type == CardType.GUB and not c.is_elder:
                self.discard.pop(i)
                self.hands[player].append(c)
                self._log(f"Player {player} uses Age Old Cure to retrieve a Gub to hand!")
                while len(self.hands[player]) > self.MAX_HAND:
                    self.discard.append(self.hands[player].pop())
                return True
        return False

    def _play_cricket_song_own_turn(self, player: int, action: Dict) -> bool:
        """Cricket Song mimics a Hazard or Tool on the player's own turn.

        The Cricket Song card is discarded, then a synthetic action is built for
        the mimicked card and dispatched through the normal apply_action pipeline
        (which handles interrupt windows, targeting, etc. exactly as if the real
        card had been played).  The card_idx in the synthetic action is set to -1
        because Cricket Song is already gone from the hand; exec helpers that call
        _discard_from_hand must not be called a second time — so we pop first and
        then call the right sub-handler directly.
        """
        # Remove Cricket Song from hand and discard it.
        self.hands[player].pop(action["card_idx"])
        self.discard.append(CARD_BY_NAME["Cricket Song"])
        mimic = action["as_card"]
        self._log(f"Player {player} plays Cricket Song as {mimic}!")

        # Build a synthetic action mirroring the mimicked card, carrying over
        # all targeting keys supplied by the caller.
        passthrough = {k: v for k, v in action.items()
                       if k not in ("type", "card_idx", "as_card")}

        # Map mimic target to the correct action type.
        # as_action allows callers to specify a variant (e.g. play_lightning_hand vs play_lightning_elder).
        mimic_action_type = action.get("as_action") or {
            "Lure":         "play_lure",
            "Super Lure":   "play_super_lure",
            "Cyclone":      "play_cyclone",
            "Lightning":    "play_lightning_elder",
            "Smahl Thief":  "play_smahl_thief_gub",
            "Omen Beetle":  "play_omen_beetle",
            "Haki Flute":   "play_haki_flute",
            "Spear":        "play_spear_discard_gub",
            "Scout":        "play_scout_deck",
            "Retreat":      "play_retreat",
            "Age Old Cure": "play_age_old_cure_retrieve",
        }.get(mimic)

        if mimic_action_type is None:
            self._log(f"  (Cricket Song: unknown mimic target '{mimic}' — no effect)")
            return True

        # For cards that consume the card from hand via _discard_from_hand we need
        # a valid card_idx.  Since Cricket Song is already gone, we temporarily
        # inject a sentinel; the hazard/interrupt path only pops before opening the
        # interrupt window, and we've already done that — so we set card_idx to 0
        # and handle this by injecting the action AFTER removal is done.
        # Instead, for hazard/tool cards that call _discard_from_hand internally
        # we patch the hand to avoid a second discard: we just pass a dummy idx
        # that can't exist (the methods that pop from hand via _discard_from_hand
        # will receive card_idx=-1 which would raise; so we use a different approach:
        # directly call _open_interrupt or the exec helper, bypassing the pop).

        # Cards that open an interrupt window (hazards / spear / traps):
        if mimic_action_type in ("play_lure", "play_super_lure"):
            kind = "lure" if mimic == "Lure" else "super_lure"
            self._log(f"  Cricket Song → {mimic}! (interrupt window open)")
            self.active_player = player
            self._open_interrupt(kind, {**passthrough, "type": mimic_action_type}, player)
            return True

        if mimic_action_type == "play_cyclone":
            self._log(f"  Cricket Song → Cyclone! (interrupt window open)")
            self.active_player = player
            self._open_interrupt("hazard", {**passthrough, "type": mimic_action_type}, player)
            return True

        if mimic_action_type in ("play_lightning_elder", "play_lightning_hand"):
            self._log(f"  Cricket Song → Lightning! (interrupt window open)")
            self.active_player = player
            self._open_interrupt("hazard", {**passthrough, "type": mimic_action_type}, player)
            return True

        if mimic_action_type == "play_omen_beetle":
            self._log(f"  Cricket Song → Omen Beetle! (interrupt window open)")
            self.active_player = player
            self._open_interrupt("hazard", {**passthrough, "type": mimic_action_type}, player)
            return True

        if mimic_action_type in ("play_smahl_thief_gub", "play_smahl_thief_barricade"):
            self._log(f"  Cricket Song → Smahl Thief! (interrupt window open)")
            self.active_player = player
            self._open_interrupt("hazard", {**passthrough, "type": mimic_action_type}, player)
            return True

        if mimic_action_type in ("play_spear_discard_gub", "play_spear_sud_spout"):
            self._log(f"  Cricket Song → Spear! (interrupt window open)")
            self.active_player = player
            self._open_interrupt("spear", {**passthrough, "type": mimic_action_type}, player)
            return True

        # Tools that execute immediately (no interrupt window):
        if mimic_action_type == "play_haki_flute":
            tp = passthrough.get("target_player", 0)
            gi = passthrough.get("target_gub_idx", 0)
            ring_gub = self.colonies[tp].pop(gi)
            for g in ring_gub.trapped_gubs:
                g.trap  = None
                g.owner = player
                self.colonies[player].append(g)
            self.discard.append(ring_gub.trap)
            self._log(f"  Cricket Song → Haki Flute: Player {player} claims "
                      f"{len(ring_gub.trapped_gubs)} Gub(s)!")
            return True

        if mimic_action_type in ("play_scout_deck", "play_scout_hand"):
            if mimic_action_type == "play_scout_deck":
                top = self.deck[:min(3, len(self.deck))]
                self._log(f"  Cricket Song → Scout: top 3 = {[c.name for c in top]}")
                if len(top) > 1:
                    self._scout_peek_player = player
                    self.phase = "scout_rearrange"
                    self.current_player = player
            else:
                tp = passthrough.get("target_player", 0)
                self._log(f"  Cricket Song → Scout: Player {tp}'s hand = "
                          f"{[c.name for c in self.hands[tp]]}")
            return True

        if mimic_action_type == "play_retreat":
            reclaimed = []
            remaining = []
            for gub in self.colonies[player]:
                if gub.barricade:
                    reclaimed.append(gub.barricade)
                    gub.barricade = None
                if gub.trap:
                    reclaimed.append(gub.trap)
                    gub.trap = None
                    for g in gub.trapped_gubs:
                        g.trap  = None
                        self.colonies[g.owner].append(g)
                    gub.trapped_gubs = []

                if gub.is_elder:
                    remaining.append(gub)
                else:
                    reclaimed.append(CARD_BY_NAME["Gub"])

            self.colonies[player] = remaining
            self.hands[player].extend(reclaimed)
            while len(self.hands[player]) > self.MAX_HAND:
                self.discard.append(self.hands[player].pop())
            self._log(f"  Cricket Song → Retreat: Player {player} reclaims "
                      f"{len(reclaimed)} card(s).")
            return True

        if mimic_action_type == "play_age_old_cure_retrieve":
            for i, c in enumerate(self.discard):
                if c.card_type == CardType.GUB and not c.is_elder:
                    self.discard.pop(i)
                    self.hands[player].append(c)
                    self._log(f"  Cricket Song → Age Old Cure: Player {player} "
                              f"retrieves a Gub to hand!")
                    while len(self.hands[player]) > self.MAX_HAND:
                        self.discard.append(self.hands[player].pop())
                    break
            return True

        self._log(f"  (Cricket Song: no handler for '{mimic}' — no effect)")
        return True

    def _advance_tm_queue(self):
        """Move to next player in Traveling Merchant choice queue. Once everyone
        has chosen a card to keep, pass each player's leftover cards to the
        next player (to their right) and finalize new hands."""
        if self.current_player in self._tm_queue:
            self._tm_queue.remove(self.current_player)
        if self._tm_queue:
            self.current_player = self._tm_queue[0]
        else:
            self._finalize_traveling_merchant()
            self._restore_active_player_phase()

    def _finalize_traveling_merchant(self):
        """Build new hands: each player keeps their chosen card plus the
        leftovers passed from the player on their left (previous player)."""
        n = self.num_players
        new_hands: List[List[Card]] = [[] for _ in range(n)]
        for p in range(n):
            kept = self._tm_kept.get(p)
            if kept is not None:
                new_hands[p].append(kept)
            # Receive leftovers from the player to the left (p-1), who passes
            # to the player on their right (p).
            received = self._tm_leftover.get((p - 1) % n, [])
            new_hands[p].extend(received)
            if received:
                self._log(f"  Traveling Merchant: Player {p} receives "
                          f"{len(received)} card(s) from Player {(p-1) % n}: "
                          f"{[c.name for c in received]}")
        self.hands = new_hands
        self._tm_kept     = {}
        self._tm_leftover = {}

    def _advance_gargok_queue(self):
        """Move to the next player in the Gargok Plague choice queue, or return to play."""
        if self.current_player in self._gargok_queue:
            self._gargok_queue.remove(self.current_player)
        if self._gargok_queue:
            self.current_player = self._gargok_queue[0]
            self._log(f"  Gargok Plague: Player {self.current_player} — use Age Old Cure? (yes/no)")
        else:
            self._restore_active_player_phase()

    # ── Turn management ───────────────────────

    def _advance_turn(self):
        self.current_player  = (self.active_player + 1) % self.num_players
        self.active_player   = self.current_player
        self.drawn_this_turn = False
        self.phase           = "draw"

    # ── Observation for RL ────────────────────

    def get_observation(self, player: int) -> np.ndarray:
        obs = []

        def colony_feats(p):
            col = self.colonies[p]
            return [
                sum(1 for g in col if g.state == GubState.FREE      and not g.is_elder),
                sum(1 for g in col if g.state == GubState.PROTECTED  and not g.is_elder),
                sum(1 for g in col if g.state == GubState.TRAPPED),
                float(any(g.is_elder for g in col)),
            ]

        obs.extend(colony_feats(player))
        for p in range(self.num_players):
            if p != player:
                obs.extend(colony_feats(p))
        for _ in range(self.num_players, 6):
            obs.extend([0.0, 0.0, 0.0, 0.0])

        buckets = {
            "gub":0,"elder":0,"mushroom":0,"toad":0,"moth":0,
            "lure":0,"super_lure":0,"cyclone":0,"lightning":0,
            "ring":0,"sud_spout":0,"haki":0,"spear":0,
            "interrupt":0,"event":0,"other":0,
        }
        for c in self.hands[player]:
            if   c.card_type == CardType.GUB and not c.is_elder: buckets["gub"]       += 1
            elif c.is_elder:                                       buckets["elder"]     += 1
            elif c.name == "Mushroom":                             buckets["mushroom"]  += 1
            elif c.name == "Toad Rider":                           buckets["toad"]      += 1
            elif c.name == "Velvet Moth":                          buckets["moth"]      += 1
            elif c.name == "Lure":                                 buckets["lure"]      += 1
            elif c.name == "Super Lure":                           buckets["super_lure"]+= 1
            elif c.name == "Cyclone":                              buckets["cyclone"]   += 1
            elif c.name == "Lightning":                            buckets["lightning"] += 1
            elif c.card_type == CardType.TRAP:                     buckets["ring"]      += 1
            elif c.name == "Sud Spout":                            buckets["sud_spout"] += 1
            elif c.name == "Haki Flute":                           buckets["haki"]      += 1
            elif c.name == "Spear":                                buckets["spear"]     += 1
            elif c.card_type == CardType.INTERRUPT:                buckets["interrupt"] += 1
            elif c.card_type == CardType.EVENT:                    buckets["event"]     += 1
            else:                                                   buckets["other"]     += 1

        for v in buckets.values():
            obs.append(float(v) / 8.0)

        obs.append(float("G" in self.letters_drawn))
        obs.append(float("U" in self.letters_drawn))
        obs.append(float("B" in self.letters_drawn))

        obs.append(len(self.deck) / 72.0)

        obs.append(float(self.phase == "draw"))
        obs.append(float(self.phase == "play"))
        obs.append(float(self.phase == "discard"))
        obs.append(float(self.phase == "interrupt"))

        obs.append(float(self.current_player == player))

        return np.array(obs, dtype=np.float32)

    @property
    def obs_size(self) -> int:
        return 6*4 + 16 + 3 + 1 + 4 + 1  # = 50

    def board_to_dict(self) -> dict:
        return {
            "players": [
                {
                    "id": p,
                    "score": self.calculate_scores()[p],
                    "hand_size": len(self.hands[p]),
                    "colony": [
                        {"is_elder": g.is_elder, "state": g.state.value,
                         "barricade": g.barricade.name if g.barricade else None,
                         "trap": g.trap.name if g.trap else None}
                        for g in self.colonies[p]
                    ],
                }
                for p in range(self.num_players)
            ],
            "letters_drawn": self.letters_drawn,
            "deck_size": len(self.deck),
            "discard_size": len(self.discard),
            "current_player": self.current_player,
            "active_player": self.active_player,
            "phase": self.phase,
            "pending": self.pending.kind if self.pending else None,
            "log": self.log[-10:],
        }

    def clone(self) -> 'GubsGame':
        return copy.deepcopy(self)


# ─────────────────────────────────────────────────────────────────────────────
#  Agents
# ─────────────────────────────────────────────────────────────────────────────

class RandomAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id

    def select_action(self, game: GubsGame) -> Optional[Dict]:
        actions = game.get_all_valid_actions()
        return random.choice(actions) if actions else None


class GreedyAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id

    def select_action(self, game: GubsGame) -> Optional[Dict]:
        actions = game.get_all_valid_actions()
        if not actions:
            return None

        scores = game.calculate_scores()
        cp     = game.current_player

        def score_action(a: Dict) -> float:
            t = a["type"]
            # Interrupt phase: always fire the interrupt if we have one
            if t == "play_interrupt":
                return 10.0 if a["card_name"] != "Flop Boat" else 8.0
            if t == "pass_interrupt":
                return 0.0
            if t == "draw":
                return 9.0
            if t == "play_gub":
                return 8.0
            if t in ("play_lure", "play_super_lure",
                     "play_smahl_thief_gub", "play_smahl_thief_barricade"):
                tp = a.get("target_player", -1)
                return 9.0 if tp >= 0 and scores[tp] >= max(scores) else 7.0
            if t == "play_barricade":
                return 6.0
            if t in ("play_haki_flute", "play_cyclone"):
                return 8.5
            if t in ("play_ring", "play_sud_spout"):
                return 7.5
            if t in ("play_omen_beetle", "play_lightning_elder", "play_lightning_hand"):
                return 8.0
            if t in ("play_spear_discard_gub", "play_spear_sud_spout"):
                return 6.5
            if t == "end_play":
                return 0.0
            # New phases — greedy choices
            if t == "gargok_use_cure":   return 10.0  # always save your hand
            if t == "gargok_decline_cure": return 0.0
            if t == "tm_keep_card":
                # Prefer highest-value cards: Gubs > Hazards > Tools > others
                from gubs_engine import CardType as CT
                hand = game.hands[self.player_id] if a.get("card_idx", 0) < len(game.hands[game.current_player]) else []
                # Score based on card_idx position as a proxy
                return 5.0 + a.get("card_idx", 0) * 0.01
            if t == "scout_rearrange":
                # Prefer to put the best card on top (first in order goes to top)
                return 5.0
            if t.startswith("play_"):
                return 5.0
            if t == "skip_draw":
                return 1.0
            return 0.0

        return max(actions, key=score_action)


if __name__ == "__main__":
    game = GubsGame(num_players=2, seed=42, reveal_draws=True)
    agents = [RandomAgent(0), RandomAgent(1)]
    moves  = 0
    while not game.is_terminal() and moves < 3000:
        cp = game.current_player
        action = agents[cp].select_action(game)
        if action is None:
            break
        game.apply_action(action)
        moves += 1

    scores = game.calculate_scores()
    print(f"Game over after {moves} moves. Scores: {scores}")
    print(f"Winner: Player {game.get_winner()}")
    print(f"Letters drawn: {game.letters_drawn}")