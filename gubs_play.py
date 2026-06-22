"""
GUBS CLI — Play Against a Trained Model or AI
=============================================
Usage:
  python gubs_play.py                                  # Human vs Random (draws hidden)
  python gubs_play.py --opponent greedy
  python gubs_play.py --opponent model --weights gubs_weights/best.pt
  python gubs_play.py --reveal-draws                   # Show what opponent draws
  python gubs_play.py --watch random greedy
  python gubs_play.py --benchmark 100
"""

import argparse
import sys
import time
import random
from typing import Optional, Dict

from gubs_engine import (
    GubsGame, RandomAgent, GreedyAgent, GubState, CardType, BarricadeKind
)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# ─────────────────────────────────────────────
#  ANSI colours
# ─────────────────────────────────────────────
class C:
    RESET   = '\033[0m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    ORANGE  = '\033[33m'

PLAYER_COLORS = [C.RED, C.BLUE, C.GREEN, C.YELLOW, C.MAGENTA, C.CYAN]
PLAYER_NAMES  = ['Crimson', 'Sapphire', 'Emerald', 'Amber', 'Violet', 'Teal']

STATE_ICONS = {
    GubState.FREE:      f"{C.GREEN}◉{C.RESET}",
    GubState.PROTECTED: f"{C.YELLOW}⬡{C.RESET}",
    GubState.TRAPPED:   f"{C.RED}✕{C.RESET}",
}

BARRICADE_ICONS = {
    BarricadeKind.MUSHROOM:    f"{C.GREEN}🍄{C.RESET}",
    BarricadeKind.TOAD_RIDER:  f"{C.ORANGE}🐸{C.RESET}",
    BarricadeKind.VELVET_MOTH: f"{C.MAGENTA}🦋{C.RESET}",
}

CARD_TYPE_COLORS = {
    CardType.GUB:        C.GREEN,
    CardType.BARRICADE:  C.YELLOW,
    CardType.HAZARD:     C.RED,
    CardType.TOOL:       C.CYAN,
    CardType.TRAP:       C.MAGENTA,
    CardType.TOOL_HAZARD:C.ORANGE,
    CardType.INTERRUPT:  C.BLUE,
    CardType.EVENT:      C.WHITE,
    CardType.WILD:       C.MAGENTA,
    CardType.LETTER:     C.RED,
}

def colorize_card(card) -> str:
    col = CARD_TYPE_COLORS.get(card.card_type, C.WHITE)
    return f"{col}{card.name}{C.RESET}"

# ─────────────────────────────────────────────
#  Board display
# ─────────────────────────────────────────────
def render_colony(game: GubsGame, player: int) -> str:
    col = PLAYER_COLORS[player]
    name = PLAYER_NAMES[player]
    scores = game.calculate_scores()
    lines = []

    active = " ◀ YOUR TURN" if player == game.current_player else ""
    lines.append(f"{col}{C.BOLD}  ── {name} Colony ── {scores[player]} pts{C.RESET}"
                 f"{C.DIM}{active}{C.RESET}")

    colony = game.colonies[player]
    if not colony:
        lines.append(f"  {C.DIM}(empty colony){C.RESET}")
    else:
        for i, gub in enumerate(colony):
            icon = STATE_ICONS[gub.state]
            kind = f"{col}{'Elder' if gub.is_elder else 'Gub'}{C.RESET}"
            barr = (f" [{BARRICADE_ICONS.get(gub.barricade.barricade_kind, '?')} "
                    f"{gub.barricade.name}]") if gub.barricade else ""
            trap = f" [{C.RED}⛓ {gub.trap.name}{C.RESET}]" if gub.trap else ""
            pts  = f" {C.DIM}({gub.points}pt){C.RESET}"
            lines.append(f"  [{i}] {icon} {kind}{barr}{trap}{pts}")

    return "\n".join(lines)


def render_header(game: GubsGame):
    letters = "".join(
        f"{C.RED}{C.BOLD}{l}{C.RESET}" if l in game.letters_drawn
        else f"{C.DIM}_{C.RESET}"
        for l in "GUB"
    )
    drawn_count = len(game.letters_drawn)
    danger = ["", f"{C.YELLOW}⚠ One letter drawn{C.RESET}",
              f"{C.RED}{C.BOLD}⚠⚠ TWO LETTERS — GAME ALMOST OVER!{C.RESET}", ""][drawn_count]

    print(f"\n{C.YELLOW}{'═'*65}{C.RESET}")
    print(f"  {C.BOLD}{C.YELLOW}GUBS{C.RESET}  "
          f"Letters: G-U-B → {letters}  "
          f"Deck: {C.CYAN}{len(game.deck)}{C.RESET} cards  "
          f"Phase: {C.DIM}{game.phase}{C.RESET}"
          + (f"  {danger}" if danger else ""))
    reveal_note = f"  {C.DIM}[--reveal-draws is OFF]{C.RESET}" if not game.reveal_draws else ""
    print(f"{C.YELLOW}{'─'*65}{C.RESET}{reveal_note}")
    scores = game.calculate_scores()
    for p in range(game.num_players):
        hand_sz = len(game.hands[p])
        col = PLAYER_COLORS[p]
        active = " ◀" if p == game.current_player else "  "
        print(f"  {col}{PLAYER_NAMES[p]:8}{C.RESET}  "
              f"Score: {C.BOLD}{scores[p]:>2}{C.RESET}  "
              f"Hand: {C.DIM}{hand_sz:>2} cards{C.RESET}  "
              f"Colony: {C.DIM}{len(game.colonies[p]):>2} Gubs{C.RESET}{active}")
    print(f"{C.YELLOW}{'═'*65}{C.RESET}\n")


def render_board(game: GubsGame):
    for p in range(game.num_players):
        print(render_colony(game, p))
        print()


def render_hand(hand) -> str:
    if not hand:
        return f"  {C.DIM}(empty hand){C.RESET}"
    lines = []
    for i, card in enumerate(hand):
        col = CARD_TYPE_COLORS.get(card.card_type, C.WHITE)
        ctype = card.card_type.value.upper()
        lines.append(f"  [{i:>2}] {col}{card.name:<22}{C.RESET} {C.DIM}({ctype}){C.RESET}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  Action descriptions
# ─────────────────────────────────────────────
_ACTION_DESCRIPTIONS = {
    "draw":                          "Draw a card from the deck",
    "skip_draw":                     "Skip drawing this turn",
    "begin_play":                    "Begin playing cards",
    "end_play":                      "End your play phase",
    "end_discard":                   "Done discarding",
    "play_gub":                      "Play a Gub into your colony",
    "play_barricade":                "Protect own Gub with a Barricade",
    "play_mushroom_destroy":         "Mushroom: destroy a Mushroom barricade on the field",
    "play_toad_rider_destroy":       "Toad Rider: destroy ANY barricade on the field",
    "play_lure":                     "Lure: steal one Free Gub from opponent",
    "play_super_lure":               "Super Lure: steal ALL Free+Protected Gubs from opponent",
    "play_cyclone":                  "Cyclone: strip all barricades from one opponent",
    "play_ring":                     "Ring Trap: trap Gubs under a Ring",
    "play_sud_spout":                "Sud Spout: trap a Free Gub in place",
    "play_haki_flute":               "Haki Flute: shatter a Ring and claim its Gubs",
    "play_spear_sud_spout":          "Spear: destroy a Sud Spout (Gub stays free)",
    "play_spear_discard_gub":        "Spear: discard a Free Gub from the field",
    "play_scout_deck":               "Scout: peek at top 3 deck cards (then rearrange them)",
    "play_scout_hand":               "Scout: peek at an opponent's hand",
    "scout_rearrange":               "Scout: choose the new order for the top 3 cards",
    "play_retreat":                  "Retreat: reclaim all your colony cards to hand",
    "play_lightning_elder":          "Lightning: DESTROY the Esteemed Elder",
    "play_lightning_hand":           "Lightning: DISCARD an opponent's entire hand",
    "play_omen_beetle":              "Omen Beetle: discard ALL Mushroom-protected Gubs on field",
    "play_smahl_thief_gub":          "Smahl Thief: steal a GUB to your hand",
    "play_smahl_thief_barricade":    "Smahl Thief: steal a BARRICADE (Gub becomes Free)",
    "play_age_old_cure_retrieve":    "Age Old Cure: retrieve a Gub from the discard pile",
    "discard_card":                  "Discard a card from hand",
    "pass_interrupt":                "Pass — let the action resolve",
    # New phases
    "gargok_use_cure":               "Age Old Cure: USE it to save your hand from Gargok Plague",
    "gargok_decline_cure":           "Gargok Plague: DECLINE to use Age Old Cure — lose your hand",
    "tm_keep_card":                  "Traveling Merchant: KEEP this card (rest go to deck)",
}

# Cricket Song mimic descriptions (own turn)
_CRICKET_MIMIC_DESC = {
    "Lure":        "Cricket Song → Lure: steal one Free Gub",
    "Super Lure":  "Cricket Song → Super Lure: steal ALL Free+Protected Gubs",
    "Cyclone":     "Cricket Song → Cyclone: strip all barricades",
    "Omen Beetle": "Cricket Song → Omen Beetle: discard all Mushroom-protected Gubs",
    "Haki Flute":  "Cricket Song → Haki Flute: shatter a Ring and claim Gubs",
    "Retreat":     "Cricket Song → Retreat: reclaim your colony cards to hand",
}
_CRICKET_LIGHTNING_DESC = {
    "play_lightning_elder": "Cricket Song → Lightning: DESTROY the Esteemed Elder",
    "play_lightning_hand":  "Cricket Song → Lightning: DISCARD opponent's entire hand",
}
_CRICKET_SMAHL_DESC = {
    "play_smahl_thief_gub":       "Cricket Song → Smahl Thief: steal a GUB to your hand",
    "play_smahl_thief_barricade": "Cricket Song → Smahl Thief: steal a BARRICADE (Gub becomes Free)",
}
_CRICKET_SPEAR_DESC = {
    "play_spear_discard_gub":  "Cricket Song → Spear: DISCARD a Free Gub",
    "play_spear_sud_spout":    "Cricket Song → Spear: DESTROY a Sud Spout (Gub goes free)",
}
_CRICKET_SCOUT_DESC = {
    "play_scout_deck":  "Cricket Song → Scout: peek at top 3 deck cards (then rearrange)",
    "play_scout_hand":  "Cricket Song → Scout: peek at an opponent's hand",
}


def describe_action(action: Dict, game: Optional['GubsGame'] = None) -> str:
    t = action["type"]

    # ── Cricket Song: fully descriptive per variant ──────────────────────────
    if t == "play_cricket_song":
        mimic    = action.get("as_card", "?")
        as_action = action.get("as_action", "")

        if mimic == "Lightning":
            desc = _CRICKET_LIGHTNING_DESC.get(as_action,
                   "Cricket Song → Lightning")
        elif mimic == "Smahl Thief":
            desc = _CRICKET_SMAHL_DESC.get(as_action,
                   "Cricket Song → Smahl Thief")
        elif mimic == "Spear":
            desc = _CRICKET_SPEAR_DESC.get(as_action,
                   "Cricket Song → Spear")
        elif mimic == "Scout":
            desc = _CRICKET_SCOUT_DESC.get(as_action,
                   "Cricket Song → Scout")
        else:
            desc = _CRICKET_MIMIC_DESC.get(mimic, f"Cricket Song → {mimic}")

        extras = []
        if "target_player" in action:
            extras.append(f"→ {PLAYER_NAMES[action['target_player']]}")
        if "target_gub_idx" in action:
            # Try to show the gub description from the game state
            if game is not None:
                tp = action["target_player"]
                gi = action["target_gub_idx"]
                if gi < len(game.colonies[tp]):
                    gub = game.colonies[tp][gi]
                    gub_label = "Elder" if gub.is_elder else "Gub"
                    barr = f"+{gub.barricade.name}" if gub.barricade else ""
                    extras.append(f"[{gub_label}{barr} #{gi}]")
                else:
                    extras.append(f"Gub[{gi}]")
            else:
                extras.append(f"Gub[{action['target_gub_idx']}]")
        if extras:
            desc = f"{desc} ({', '.join(extras)})"
        return desc

    # ── Scout rearrange: show the new ordering clearly ───────────────────────
    if t == "scout_rearrange":
        order     = action.get("order", [])
        top_names = action.get("top_names", [])
        if top_names and order:
            new_order = [top_names[i] for i in order]
            return (f"Scout rearrange: top → {' / '.join(new_order)}")
        return "Scout: rearrange top deck cards"

    # ── play_interrupt: name the card being used ─────────────────────────────
    if t == "play_interrupt":
        cn = action.get("card_name", "?")
        if action.get("is_gargok_save"):
            cricket = " (via Cricket Song)" if action.get("is_cricket_song") else ""
            return f"{cn}{cricket}: discard now to protect your hand from Gargok Plague"
        cricket = " (via Cricket Song)" if action.get("is_cricket_song") else ""
        return f"{cn}{cricket}: cancel the pending action"

    # ── Generic fallback ─────────────────────────────────────────────────────
    base = _ACTION_DESCRIPTIONS.get(t, t)
    extras = []
    if t == "play_smahl_thief_gub" and game is not None:
        tp = action.get("target_player")
        gi = action.get("target_gub_idx")
        if tp is not None and gi is not None and gi < len(game.colonies[tp]):
            gub = game.colonies[tp][gi]
            barr = f" (w/ {gub.barricade.name})" if gub.barricade else ""
            extras.append(f"→ {PLAYER_NAMES[tp]} Gub[{gi}]{barr}")
    elif t == "play_smahl_thief_barricade" and game is not None:
        tp = action.get("target_player")
        gi = action.get("target_gub_idx")
        if tp is not None and gi is not None and gi < len(game.colonies[tp]):
            gub = game.colonies[tp][gi]
            barr_name = gub.barricade.name if gub.barricade else "?"
            extras.append(f"→ {PLAYER_NAMES[tp]} [{barr_name}]")
    else:
        if "card_idx" in action and t not in ("play_gub", "discard_card",
                                               "tm_keep_card", "play_age_old_cure_retrieve",
                                               "gargok_use_cure"):
            extras.append(f"card [{action['card_idx']}]")
        if "target_player" in action:
            extras.append(f"→ {PLAYER_NAMES[action['target_player']]}")
        if "target_gub_idx" in action:
            if game is not None:
                tp = action.get("target_player", 0)
                gi = action["target_gub_idx"]
                if gi < len(game.colonies[tp]):
                    gub = game.colonies[tp][gi]
                    gub_label = "Elder" if gub.is_elder else "Gub"
                    barr = f"+{gub.barricade.name}" if gub.barricade else ""
                    extras.append(f"[{gub_label}{barr} #{gi}]")
                else:
                    extras.append(f"Gub[{gi}]")
            else:
                extras.append(f"Gub[{action['target_gub_idx']}]")
        if "gub_targets" in action:
            targets_str = ", ".join(f"P{tp}G{gi}"
                                    for tp, gi in action["gub_targets"])
            extras.append(f"targets: {targets_str}")

    # For tm_keep_card show which card will be kept
    if t == "tm_keep_card" and game is not None:
        cp = game.current_player
        ci = action.get("card_idx", 0)
        if ci < len(game.hands[cp]):
            card = game.hands[cp][ci]
            col  = CARD_TYPE_COLORS.get(card.card_type, C.WHITE)
            base = (f"Traveling Merchant: KEEP "
                    f"{col}{card.name}{C.RESET}  "
                    f"{C.DIM}({card.card_type.value}){C.RESET}")
            return base

    if extras:
        return f"{base} ({', '.join(extras)})"
    return base


# ─────────────────────────────────────────────
#  Human input
# ─────────────────────────────────────────────
def human_choose_action(game: GubsGame) -> Optional[Dict]:
    """Show valid actions and let human choose."""
    cp = game.current_player
    actions = game.get_all_valid_actions()

    # For Gargok Plague and Traveling Merchant choice phases, show a special header
    if game.phase == "gargok_plague_choice":
        print(f"\n{C.RED}{C.BOLD}  ☠  GARGOK PLAGUE — your hand will be lost!{C.RESET}")
        if any(a["type"] == "gargok_use_cure" for a in actions):
            print(f"  {C.YELLOW}You hold an Age Old Cure. Will you use it?{C.RESET}")
    elif game.phase == "traveling_merchant_choose":
        print(f"\n{C.YELLOW}  ⚖  TRAVELING MERCHANT — choose ONE card to keep!{C.RESET}")
        print(f"  {C.DIM}All others are shuffled back into the deck.{C.RESET}")
    elif game.phase == "scout_rearrange":
        n = min(3, len(game.deck))
        top = [game.deck[i].name for i in range(n)]
        print(f"\n{C.CYAN}  🔍 SCOUT — top {n} cards: "
              f"{', '.join(top)}{C.RESET}")
        print(f"  {C.DIM}Choose a new order for those cards (top = drawn next).{C.RESET}")

    print(f"\n{C.YELLOW}Your hand:{C.RESET}")
    print(render_hand(game.hands[cp]))
    print(f"\n{C.CYAN}Valid actions:{C.RESET}")
    for i, a in enumerate(actions):
        print(f"  {C.BOLD}[{i:>2}]{C.RESET} {describe_action(a, game)}")

    while True:
        try:
            raw = input(
                f"\n  {C.YELLOW}Choose action (0–{len(actions)-1})  "
                f"or 'q' to quit:{C.RESET} "
            ).strip()
            if raw.lower() == 'q':
                sys.exit(0)
            idx = int(raw)
            if 0 <= idx < len(actions):
                return actions[idx]
            print(f"  {C.RED}Invalid choice.{C.RESET}")
        except (ValueError, EOFError):
            print(f"  {C.RED}Please enter a number.{C.RESET}")
        except KeyboardInterrupt:
            sys.exit(0)


# ─────────────────────────────────────────────
#  Action application wrapper
#  Traveling Merchant is now fully engine-driven (tm_keep_card phase), so
#  the old interception hook is no longer needed.  We keep this thin wrapper
#  so the call site in play_game() doesn't need changing.
# ─────────────────────────────────────────────
def apply_with_merchant_hook(game: GubsGame, action: Dict,
                              human_player: int) -> None:
    game.apply_action(action)


# ─────────────────────────────────────────────
#  Game loop
# ─────────────────────────────────────────────
def play_game(opponent_type: str = "random",
              weights_path: Optional[str] = None,
              delay: float = 0.4,
              verbose: bool = True,
              reveal_draws: bool = False):
    """
    Args:
        opponent_type:  'random' | 'greedy' | 'model' | 'human'
        weights_path:   Path to .pt model weights (for opponent_type='model').
        delay:          Seconds to pause between AI moves (visual pacing).
        verbose:        Print board state each turn.
        reveal_draws:   If True, show what the opponent draws. Default False
                        (hidden to avoid giving human an unfair advantage).
    """
    game = GubsGame(num_players=2, seed=None, reveal_draws=reveal_draws)
    agents = [None, None]  # None = human

    if opponent_type == "random":
        agents[1] = RandomAgent(1)
    elif opponent_type == "greedy":
        agents[1] = GreedyAgent(1)
    elif opponent_type == "model":
        if not TORCH_AVAILABLE:
            print(f"{C.RED}PyTorch not installed. Falling back to greedy.{C.RESET}")
            agents[1] = GreedyAgent(1)
        else:
            from gubs_rl import PPOAgent, DEFAULTS
            cfg = dict(DEFAULTS); cfg["device"] = "cpu"
            agent_obj = PPOAgent(game.obs_size, cfg)
            agent_obj.load(weights_path)
            agents[1] = agent_obj
            print(f"{C.GREEN}Loaded model from {weights_path}{C.RESET}")
    elif opponent_type == "human":
        pass  # both agents stay None

    print(f"\n{C.BOLD}{C.YELLOW}{'─'*65}{C.RESET}")
    print(f"{C.YELLOW}{C.BOLD}  GUBS: A Game of Wit and Luck — Terminal Edition{C.RESET}")
    print(f"  {C.DIM}Collect the most Free/Protected Gubs when G-U-B is spelled out.{C.RESET}")
    if not reveal_draws:
        print(f"  {C.DIM}Opponent draws are HIDDEN. Use --reveal-draws to show them.{C.RESET}")
    print(f"{C.BOLD}{C.YELLOW}{'─'*65}{C.RESET}\n")

    step = 0
    while not game.is_terminal() and step < 2000:
        cp = game.current_player
        agent = agents[cp]

        if verbose:
            print("\033[2J\033[H", end="")  # clear screen
            render_header(game)
            render_board(game)

            # Show recent log
            if game.log:
                print(f"{C.DIM}  Recent events:{C.RESET}")
                for msg in game.log[-5:]:
                    print(f"  {C.DIM}» {msg}{C.RESET}")
                print()

        valid = game.get_all_valid_actions()
        if not valid:
            break

        if agent is not None:
            # AI turn
            if verbose:
                print(f"  {PLAYER_COLORS[cp]}{PLAYER_NAMES[cp]}{C.RESET} "
                      f"({type(agent).__name__}) is thinking…")
                time.sleep(delay)
            if hasattr(agent, "get_action_greedy"):
                action = agent.get_action_greedy(game)
            else:
                action = agent.select_action(game)
            if action is None:
                break
            game.apply_action(action)
            if verbose:
                # Only show action detail for non-draw actions
                # (draws are hidden unless reveal_draws)
                if action.get("type") != "draw" or reveal_draws:
                    print(f"  → {describe_action(action, game)}")
                else:
                    print(f"  → {PLAYER_NAMES[cp]} draws a card.")
                time.sleep(delay * 0.5)
        else:
            # Human turn
            action = human_choose_action(game)
            if action is None:
                break
            apply_with_merchant_hook(game, action, cp)

        step += 1

    # Game over
    if verbose:
        print("\033[2J\033[H", end="")
        render_header(game)
        render_board(game)
        scores = game.calculate_scores()
        print(f"\n{C.BOLD}{C.YELLOW}  ═══ GAME OVER ═══{C.RESET}")
        print(f"  Letters drawn: {game.letters_drawn}")
        for p in range(game.num_players):
            col = PLAYER_COLORS[p]
            free = sum(1 for g in game.colonies[p] if g.state == GubState.FREE)
            prot = sum(1 for g in game.colonies[p] if g.state == GubState.PROTECTED)
            trap = sum(1 for g in game.colonies[p] if g.state == GubState.TRAPPED)
            print(f"  {col}{PLAYER_NAMES[p]}{C.RESET}: "
                  f"{C.BOLD}{scores[p]} pts{C.RESET}  "
                  f"({free} free + {prot} protected, {trap} trapped)")
        w = game.get_winner()
        if w >= 0:
            print(f"\n  {PLAYER_COLORS[w]}{C.BOLD}{PLAYER_NAMES[w]} WINS!{C.RESET}")
        else:
            print(f"\n  {C.YELLOW}It's a TIE!{C.RESET}")

    return game


# ─────────────────────────────────────────────
#  Benchmark
# ─────────────────────────────────────────────
def benchmark(num_games: int = 100):
    import numpy as np
    print(f"\n{C.CYAN}Running {num_games} games: Random vs Greedy…{C.RESET}\n")
    wins = [0, 0, 0]
    score_totals: list = [[], []]
    durations = []
    start = time.time()
    for i in range(num_games):
        t0 = time.time()
        game = GubsGame(num_players=2)
        agents_b = [RandomAgent(0), GreedyAgent(1)]
        steps = 0
        while not game.is_terminal() and steps < 1000:
            cp = game.current_player
            action = agents_b[cp].select_action(game)
            if action is None:
                break
            game.apply_action(action)
            steps += 1
        scores = game.calculate_scores()
        w = game.get_winner()
        wins[w if w >= 0 else 2] += 1
        score_totals[0].append(scores[0])
        score_totals[1].append(scores[1])
        durations.append(time.time() - t0)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{num_games}…", end="\r")

    elapsed = time.time() - start
    print(f"\n  Results ({elapsed:.1f}s, {num_games/elapsed:.1f} games/sec, "
          f"avg {np.mean(durations)*1000:.0f}ms/game):")
    print(f"  Random wins: {wins[0]:>4} ({wins[0]/num_games:.1%})  "
          f"avg score: {np.mean(score_totals[0]):.2f}")
    print(f"  Greedy wins: {wins[1]:>4} ({wins[1]/num_games:.1%})  "
          f"avg score: {np.mean(score_totals[1]):.2f}")
    print(f"  Draws:       {wins[2]:>4} ({wins[2]/num_games:.1%})")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="GUBS — play against AI or watch agents compete",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gubs_play.py                              Play vs Random (draws hidden)
  python gubs_play.py --reveal-draws               Play vs Random (all draws shown)
  python gubs_play.py --opponent greedy            Play vs Greedy agent
  python gubs_play.py --opponent model \\
      --weights gubs_weights/best.pt               Play vs trained PPO model
  python gubs_play.py --watch random greedy        Watch two AIs play
  python gubs_play.py --watch random greedy \\
      --reveal-draws                               Watch with all draws visible
  python gubs_play.py --benchmark 200              Benchmark random vs greedy
        """
    )
    parser.add_argument("--opponent",      default="random",
                        choices=["random", "greedy", "model", "human"])
    parser.add_argument("--weights",       default="gubs_weights/best.pt")
    parser.add_argument("--delay",         type=float, default=0.4)
    parser.add_argument("--reveal-draws",  action="store_true",
                        help="Show what each player draws (default: hidden to prevent "
                             "information advantage over the CPU)")
    parser.add_argument("--watch",         nargs=2, metavar=("A1", "A2"),
                        help="Watch two agents: random|greedy|model")
    parser.add_argument("--benchmark",     type=int, metavar="N")
    args = parser.parse_args()

    if args.benchmark:
        benchmark(args.benchmark)
        return

    if args.watch:
        a1t, a2t = args.watch
        print(f"\n{C.CYAN}Watching: {a1t} vs {a2t}"
              f"  (draws {'visible' if args.reveal_draws else 'hidden'}){C.RESET}\n")
        game = GubsGame(num_players=2, reveal_draws=args.reveal_draws)

        def mk(t, pid):
            if t == "random":
                return RandomAgent(pid)
            if t == "greedy":
                return GreedyAgent(pid)
            if t == "model":
                from gubs_rl import PPOAgent, DEFAULTS
                cfg = dict(DEFAULTS); cfg["device"] = "cpu"
                a = PPOAgent(game.obs_size, cfg)
                a.load(args.weights)
                return a
            raise ValueError(f"Unknown agent type: {t}")

        agents = [mk(a1t, 0), mk(a2t, 1)]
        steps = 0
        while not game.is_terminal() and steps < 2000:
            cp = game.current_player
            ag = agents[cp]
            action = (ag.get_action_greedy(game) if hasattr(ag, "get_action_greedy")
                      else ag.select_action(game))
            if action is None:
                break
            game.apply_action(action)
            steps += 1

        scores = game.calculate_scores()
        w = game.get_winner()
        print(f"Final: {scores}  →  "
              f"{'Player ' + PLAYER_NAMES[w] + ' wins!' if w >= 0 else 'Draw'}")
        print(f"Letters drawn: {game.letters_drawn}")
        return

    play_game(
        opponent_type=args.opponent,
        weights_path=args.weights,
        delay=args.delay,
        verbose=True,
        reveal_draws=args.reveal_draws,
    )


if __name__ == "__main__":
    main()