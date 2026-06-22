"""
gubs_analyse.py — Simulate 10,000 games of the trained PPO agent vs Random and
Greedy opponents and collect strategy-relevant statistics.

Usage:
    python gubs_analyse.py --weights gubs_weights/best.pt --games 5000
    python gubs_analyse.py --weights gubs_weights/best.pt --games 5000 --device cpu
    python gubs_analyse.py --weights gubs_weights/best.pt --games 5000 --workers 8

Each opponent type (random, greedy) receives --games games, so total simulations
= 2 * --games.  Defaults give 10,000 games total.

Output:
    gubs_analysis/
        summary.txt          — human-readable strategy report
        raw_games.jsonl      — one JSON object per game (for custom analysis)
        per_card_stats.csv   — per-card holding time, play rate, win association
        score_trajectory.csv — mean agent score per turn bucket, by outcome
"""

import argparse
import json
import os
import sys
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

# ── make sure gubs_engine and gubs_rl are importable ─────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gubs_engine import (
    GubsGame, RandomAgent, GreedyAgent,
    CardType, GubState, Card,
)
from gubs_rl import PPOAgent, GubsNet, build_action_mask, mask_to_best_action, DEFAULTS


# ─────────────────────────────────────────────────────────────────────────────
#  Instrumented game runner
# ─────────────────────────────────────────────────────────────────────────────

# Action types we classify as "aggressive" (attacking the opponent)
AGGRESSIVE_ACTIONS = {
    "play_lure", "play_super_lure", "play_cyclone",
    "play_lightning_elder", "play_lightning_hand",
    "play_omen_beetle", "play_ring", "play_sud_spout",
    "play_smahl_thief_gub", "play_smahl_thief_barricade",
    "play_spear_discard_gub",
}

# Cricket Song mimics that tell us what the agent "wished" it had
CRICKET_MIMIC_KEY = "as_card"

# Turn buckets for score trajectory (every N turns)
TRAJECTORY_BUCKET = 5


@dataclass
class CardEvent:
    """Tracks a card's lifecycle in a single player's hand."""
    name: str
    card_type: str
    turn_drawn: int           # turn the card entered the hand
    turn_left: int = -1       # turn the card left the hand (played or discarded)
    left_by: str = ""         # "played" | "discarded" | "event_wiped" | "end"


@dataclass
class GameRecord:
    """All statistics collected from a single simulated game."""
    game_id: int
    opponent_type: str          # "random" | "greedy"
    agent_seat: int             # 0 or 1
    winner: int                 # 0/1/-1 (draw)
    agent_won: bool
    agent_score: int
    opp_score: int
    total_turns: int
    deck_size_start: int        # always 72 but kept for completeness
    letters_drawn: List[str]

    # Per-turn score snapshots for the agent
    score_trajectory: List[Tuple[int, int]]  # (turn, agent_score)

    # Card lifecycle events for the agent
    card_events: List[CardEvent]

    # Actions taken by the agent (type strings only)
    agent_actions: List[str]

    # Interrupt decisions: (opportunity_kind, fired: bool)
    interrupt_decisions: List[Tuple[str, bool]]

    # Colony state snapshots at each turn-end for the agent
    #   list of (turn, free, protected, trapped, has_elder)
    colony_snapshots: List[Tuple[int, int, int, int, bool]]

    # Score when each letter was drawn: list of (letter, agent_score, opp_score)
    score_at_letter: List[Tuple[str, int, int]]

    # Events that fired and immediate score delta for agent (event_name, delta)
    event_impacts: List[Tuple[str, int]]

    # Cricket Song usage: list of mimicked card names
    cricket_mimics: List[str]

    # Whether agent behaviour shifted after the 2nd letter
    #   actions before and after 2nd letter drawn (action type → count)
    actions_pre_penultimate: Dict[str, int]
    actions_post_penultimate: Dict[str, int]

    # Times the agent was successfully lured/stolen from vs times agent stole
    times_stolen_from: int
    times_agent_stole: int

    # Peak colony score the agent held at any point
    peak_score: int


def _colony_counts(game: GubsGame, player: int):
    col = game.colonies[player]
    free      = sum(1 for g in col if g.state == GubState.FREE      and not g.is_elder)
    protected = sum(1 for g in col if g.state == GubState.PROTECTED)
    trapped   = sum(1 for g in col if g.state == GubState.TRAPPED)
    has_elder = any(g.is_elder and g.state != GubState.TRAPPED for g in col)
    return free, protected, trapped, has_elder


def run_game(
    agent: PPOAgent,
    opponent,
    opponent_type: str,
    game_id: int,
    device: torch.device,
    max_steps: int = 1000,
) -> GameRecord:
    """Run one game and return a fully-populated GameRecord."""
    game = GubsGame(num_players=2, seed=None)
    agent_seat = game_id % 2  # alternate seats for fairness

    turn = 0
    active_player_turn = 0   # increments when phase returns to "draw" for agent

    # Hand tracking: card_name -> CardEvent (only for agent)
    hand_tracker: Dict[int, CardEvent] = {}  # id(card) -> CardEvent
    card_events: List[CardEvent] = []

    agent_actions: List[str] = []
    interrupt_decisions: List[Tuple[str, bool]] = []
    score_trajectory: List[Tuple[int, int]] = []
    colony_snapshots: List[Tuple[int, int, int, int, bool]] = []
    score_at_letter: List[Tuple[str, int, int]] = []
    event_impacts: List[Tuple[str, int]] = []
    cricket_mimics: List[str] = []
    actions_pre_penultimate: Dict[str, int] = defaultdict(int)
    actions_post_penultimate: Dict[str, int] = defaultdict(int)

    times_stolen_from = 0
    times_agent_stole = 0
    peak_score = 0

    letters_seen_before = set(game.letters_drawn)
    penultimate_drawn = False

    # ── Snapshot helpers ──────────────────────────────────────────────────────

    def snap_colony():
        f, pr, tr, eld = _colony_counts(game, agent_seat)
        colony_snapshots.append((turn, f, pr, tr, eld))
        nonlocal peak_score
        score = f + pr
        if score > peak_score:
            peak_score = score

    def snap_score():
        scores = game.calculate_scores()
        score_trajectory.append((turn, scores[agent_seat]))

    def _track_hand_additions():
        """Detect newly added cards to the agent's hand."""
        for i, card in enumerate(game.hands[agent_seat]):
            key = id(card)
            if key not in hand_tracker:
                hand_tracker[key] = CardEvent(
                    name=card.name,
                    card_type=card.card_type.value,
                    turn_drawn=turn,
                )

    def _track_hand_removals(last_action_type: str = "", last_action_seat: int = -1):
        """Detect cards that left the agent's hand and classify how they left.

        We classify by the action that was just applied:
          - discard_card on the agent's turn           → "discarded"
          - any play_* action on the agent's turn      → "played"
          - everything else (events, opponent actions) → "event_wiped"
        """
        current_ids = {id(c) for c in game.hands[agent_seat]}
        for key, ev in list(hand_tracker.items()):
            if key not in current_ids and ev.turn_left == -1:
                ev.turn_left = turn
                if last_action_seat == agent_seat:
                    if last_action_type == "discard_card":
                        ev.left_by = "discarded"
                    elif last_action_type.startswith("play_") or last_action_type in (
                        "play_age_old_cure_retrieve", "gargok_use_cure",
                    ):
                        ev.left_by = "played"
                    else:
                        ev.left_by = "event_wiped"
                else:
                    # Opponent action or event caused the removal
                    ev.left_by = "event_wiped"
                card_events.append(ev)
                del hand_tracker[key]

    # Snapshot starting hand
    _track_hand_additions()
    snap_colony()
    snap_score()

    steps = 0
    while not game.is_terminal() and steps < max_steps:
        cp = game.current_player
        valid = game.get_all_valid_actions()
        if not valid:
            break

        # ── Detect letter events ───────────────────────────────────────────
        new_letters = set(game.letters_drawn) - letters_seen_before
        for ltr in new_letters:
            scores = game.calculate_scores()
            score_at_letter.append((ltr, scores[agent_seat], scores[1 - agent_seat]))
            if len(game.letters_drawn) == 2:
                penultimate_drawn = True
            letters_seen_before = set(game.letters_drawn)

        # ── Score at this point ────────────────────────────────────────────
        pre_scores = game.calculate_scores()

        # ── Agent's turn ───────────────────────────────────────────────────
        if cp == agent_seat:
            obs  = game.get_observation(agent_seat)
            mask = build_action_mask(valid)
            obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(device)
            mask_t = torch.BoolTensor(mask).unsqueeze(0).to(device)
            with torch.no_grad():
                h      = agent.net.shared(obs_t)
                logits = agent.net.policy_head(h).squeeze(0).cpu().numpy()
                logits_masked = logits + (mask.astype(float) - 1) * 1e9
            action = mask_to_best_action(mask, logits_masked, valid)

            atype = action["type"]
            agent_actions.append(atype)

            # Interrupt fire tracking
            if game.phase == "interrupt":
                fired = (atype == "play_interrupt")
                kind  = game.pending.kind if game.pending else "unknown"
                interrupt_decisions.append((kind, fired))

            # Cricket Song mimicry
            if atype == "play_cricket_song":
                mimic = action.get(CRICKET_MIMIC_KEY, "unknown")
                cricket_mimics.append(mimic)

            # Pre/post penultimate action split
            if penultimate_drawn:
                actions_post_penultimate[atype] += 1
            else:
                actions_pre_penultimate[atype] += 1

            # Aggression: did agent steal?
            if atype in ("play_lure", "play_super_lure", "play_smahl_thief_gub",
                         "play_smahl_thief_barricade", "play_ring"):
                times_agent_stole += 1

            log_len_before = len(game.log)
            game.apply_action(action)
            new_log_lines = game.log[log_len_before:]

        # ── Opponent's turn ────────────────────────────────────────────────
        else:
            action = opponent.select_action(game)
            if action is None:
                break

            atype = action.get("type", "")

            # Did opponent steal from agent?
            if atype in ("play_lure", "play_super_lure") and \
               action.get("target_player") == agent_seat:
                times_stolen_from += 1
            elif atype == "play_smahl_thief_gub" and \
               action.get("target_player") == agent_seat:
                times_stolen_from += 1

            log_len_before = len(game.log)
            game.apply_action(action)
            new_log_lines = game.log[log_len_before:]

        # ── Post-action bookkeeping ────────────────────────────────────────
        post_scores = game.calculate_scores()

        # ── Event impact detection ─────────────────────────────────────────
        # Scan all new log lines emitted during this apply_action call.
        # The resolution log format is:  "  EVENT resolves: <Name>"  (lowercase r).
        # Events like Gargok Plague and Traveling Merchant span multiple apply_action
        # calls, so we record the delta on the step where the resolution line appears.
        for line in new_log_lines:
            if "EVENT resolves:" in line:
                for ev_name in ("Gargok Plague", "Flash Flood", "Dangerous Alchemy",
                                "Traveling Merchant", "Rumor of Wasps"):
                    if ev_name in line:
                        delta = post_scores[agent_seat] - pre_scores[agent_seat]
                        event_impacts.append((ev_name, delta))
                        break

        _track_hand_additions()
        _track_hand_removals(last_action_type=atype, last_action_seat=cp)

        # Turn boundary: when phase returns to draw and it's agent's turn
        if game.phase == "draw" and game.current_player == agent_seat:
            turn += 1
            if turn % TRAJECTORY_BUCKET == 0:
                snap_score()
                snap_colony()

        steps += 1

    # ── Finalise ──────────────────────────────────────────────────────────────
    # Close any cards still in hand at game end
    for ev in hand_tracker.values():
        ev.turn_left = turn
        ev.left_by   = "end"
        card_events.append(ev)

    scores  = game.calculate_scores()
    winner  = game.get_winner()
    letters = list(game.letters_drawn)

    snap_score()
    snap_colony()

    return GameRecord(
        game_id                   = game_id,
        opponent_type             = opponent_type,
        agent_seat                = agent_seat,
        winner                    = winner,
        agent_won                 = (winner == agent_seat),
        agent_score               = scores[agent_seat],
        opp_score                 = scores[1 - agent_seat],
        total_turns               = turn,
        deck_size_start           = 72,
        letters_drawn             = letters,
        score_trajectory          = score_trajectory,
        card_events               = card_events,
        agent_actions             = agent_actions,
        interrupt_decisions       = interrupt_decisions,
        colony_snapshots          = colony_snapshots,
        score_at_letter           = score_at_letter,
        event_impacts             = event_impacts,
        cricket_mimics            = cricket_mimics,
        actions_pre_penultimate   = dict(actions_pre_penultimate),
        actions_post_penultimate  = dict(actions_post_penultimate),
        times_stolen_from         = times_stolen_from,
        times_agent_stole         = times_agent_stole,
        peak_score                = peak_score,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Aggregation & reporting
# ─────────────────────────────────────────────────────────────────────────────

def aggregate(records: List[GameRecord], opponent_type: str) -> Dict:
    """Aggregate a list of same-opponent GameRecords into summary statistics."""
    subset = [r for r in records if r.opponent_type == opponent_type]
    if not subset:
        return {}

    n        = len(subset)
    n_wins   = sum(r.agent_won for r in subset)
    win_rate = n_wins / n

    # ── 1. Game length ────────────────────────────────────────────────────────
    turns_list  = [r.total_turns for r in subset]
    turns_w     = [r.total_turns for r in subset if r.agent_won]
    turns_l     = [r.total_turns for r in subset if not r.agent_won]

    # ── 2. Card holding time per card name ────────────────────────────────────
    card_hold:   Dict[str, List[float]] = defaultdict(list)   # name -> [turns held]
    card_played: Dict[str, int]         = defaultdict(int)    # name -> times played
    card_drawn:  Dict[str, int]         = defaultdict(int)    # name -> times drawn
    card_discard:Dict[str, int]         = defaultdict(int)    # name -> times discarded

    card_drawn_won:  Dict[str, int] = defaultdict(int)  # drawn in a game the agent won
    card_drawn_lost: Dict[str, int] = defaultdict(int)  # drawn in a game the agent lost

    for r in subset:
        won = r.agent_won
        for ev in r.card_events:
            hold = ev.turn_left - ev.turn_drawn
            card_hold[ev.name].append(max(hold, 0))
            card_drawn[ev.name] += 1
            if ev.left_by == "played":
                card_played[ev.name] += 1
            elif ev.left_by == "discarded":
                card_discard[ev.name] += 1
            if won:
                card_drawn_won[ev.name] += 1
            else:
                card_drawn_lost[ev.name] += 1

    card_stats = {}
    for name in card_drawn:
        drawn  = card_drawn[name]
        holds  = card_hold[name]
        # Win association: fraction of times the card appeared in a won game
        # (normalised by how often it appears overall)
        total_drawn = card_drawn_won[name] + card_drawn_lost[name]
        win_assoc = card_drawn_won[name] / total_drawn if total_drawn else 0.0
        card_stats[name] = {
            "times_drawn":         drawn,
            "times_played":        card_played[name],
            "times_discarded":     card_discard[name],
            "play_rate":           card_played[name] / drawn if drawn else 0.0,
            "avg_turns_held":      float(np.mean(holds)) if holds else 0.0,
            "median_turns_held":   float(np.median(holds)) if holds else 0.0,
            "win_association":     win_assoc,
            # Win-rate lift: how much higher is win rate when this card appears?
            "win_rate_with_card":  win_assoc,   # fraction of appearances in winning games
        }

    # ── 3. Interrupt fire rate ─────────────────────────────────────────────────
    interrupt_by_kind: Dict[str, List[bool]] = defaultdict(list)
    for r in subset:
        for kind, fired in r.interrupt_decisions:
            interrupt_by_kind[kind].append(fired)
    interrupt_stats = {
        k: {
            "opportunities": len(v),
            "fire_rate":     sum(v) / len(v) if v else 0.0,
        }
        for k, v in interrupt_by_kind.items()
    }

    # ── 4. Aggression ─────────────────────────────────────────────────────────
    agg_counts = [
        sum(1 for a in r.agent_actions if a in AGGRESSIVE_ACTIONS)
        for r in subset
    ]
    agg_w = [
        sum(1 for a in r.agent_actions if a in AGGRESSIVE_ACTIONS)
        for r in subset if r.agent_won
    ]
    agg_l = [
        sum(1 for a in r.agent_actions if a in AGGRESSIVE_ACTIONS)
        for r in subset if not r.agent_won
    ]

    # ── 5. Barricade ratio ────────────────────────────────────────────────────
    # Average fraction of in-play Gubs that are protected across all snapshots
    prot_ratios = []
    for r in subset:
        for _, f, pr, tr, _ in r.colony_snapshots:
            total = f + pr + tr
            if total > 0:
                prot_ratios.append(pr / total)

    # ── 6. Peak score and score buffer ────────────────────────────────────────
    peak_scores_all = [r.peak_score for r in subset]
    score_at_l2_agent = []
    score_at_l2_opp   = []
    score_at_l2_delta  = []
    for r in subset:
        if len(r.score_at_letter) >= 2:
            ltr2, a2, o2 = r.score_at_letter[1]
            score_at_l2_agent.append(a2)
            score_at_l2_opp.append(o2)
            score_at_l2_delta.append(a2 - o2)

    # Win rate when ahead vs behind at letter 2
    ahead_at_l2_won  = sum(1 for r in subset if len(r.score_at_letter) >= 2 and
                           r.score_at_letter[1][1] > r.score_at_letter[1][2] and r.agent_won)
    ahead_at_l2_n    = sum(1 for r in subset if len(r.score_at_letter) >= 2 and
                           r.score_at_letter[1][1] > r.score_at_letter[1][2])
    behind_at_l2_won = sum(1 for r in subset if len(r.score_at_letter) >= 2 and
                           r.score_at_letter[1][1] < r.score_at_letter[1][2] and r.agent_won)
    behind_at_l2_n   = sum(1 for r in subset if len(r.score_at_letter) >= 2 and
                           r.score_at_letter[1][1] < r.score_at_letter[1][2])

    # ── 7. Penultimate-letter strategy shift ──────────────────────────────────
    def action_profile(counter: Dict[str, int]) -> Dict[str, float]:
        """Normalise an action-count dict to fractions."""
        total = sum(counter.values()) or 1
        return {k: v / total for k, v in sorted(counter.items(), key=lambda x: -x[1])}

    pre_agg:  Dict[str, int] = defaultdict(int)
    post_agg: Dict[str, int] = defaultdict(int)
    for r in subset:
        for k, v in r.actions_pre_penultimate.items():
            pre_agg[k]  += v
        for k, v in r.actions_post_penultimate.items():
            post_agg[k] += v

    pre_profile  = action_profile(dict(pre_agg))
    post_profile = action_profile(dict(post_agg))

    # Biggest shifts (post - pre)
    all_action_types = set(pre_profile) | set(post_profile)
    shifts = {
        k: post_profile.get(k, 0.0) - pre_profile.get(k, 0.0)
        for k in all_action_types
    }
    shifts_sorted = sorted(shifts.items(), key=lambda x: -abs(x[1]))

    # ── 8. Event impact ───────────────────────────────────────────────────────
    event_deltas: Dict[str, List[int]] = defaultdict(list)
    for r in subset:
        for ev_name, delta in r.event_impacts:
            event_deltas[ev_name].append(delta)
    event_stats = {
        ev: {
            "occurrences":  len(ds),
            "avg_delta":    float(np.mean(ds)) if ds else 0.0,
            "pct_harmful":  sum(1 for d in ds if d < 0) / len(ds) if ds else 0.0,
        }
        for ev, ds in event_deltas.items()
    }

    # ── 9. Cricket Song mimicry ───────────────────────────────────────────────
    mimic_counts: Dict[str, int] = defaultdict(int)
    for r in subset:
        for m in r.cricket_mimics:
            mimic_counts[m] += 1
    total_mimics = sum(mimic_counts.values()) or 1
    mimic_profile = {k: v / total_mimics
                     for k, v in sorted(mimic_counts.items(), key=lambda x: -x[1])}

    # ── 10. Theft dynamics ───────────────────────────────────────────────────
    stolen_from_list = [r.times_stolen_from for r in subset]
    agent_stole_list = [r.times_agent_stole  for r in subset]

    return {
        "opponent_type":   opponent_type,
        "n_games":         n,
        "win_rate":        win_rate,
        "avg_score":       float(np.mean([r.agent_score for r in subset])),
        "avg_opp_score":   float(np.mean([r.opp_score   for r in subset])),
        "avg_score_diff":  float(np.mean([r.agent_score - r.opp_score for r in subset])),

        "game_length": {
            "mean":  float(np.mean(turns_list)),
            "std":   float(np.std(turns_list)),
            "wins":  float(np.mean(turns_w)) if turns_w else None,
            "losses":float(np.mean(turns_l)) if turns_l else None,
        },

        "card_stats":      card_stats,

        "interrupt_stats": interrupt_stats,

        "aggression": {
            "mean_aggressive_actions_per_game":  float(np.mean(agg_counts)),
            "wins_mean":   float(np.mean(agg_w))  if agg_w  else None,
            "losses_mean": float(np.mean(agg_l))  if agg_l  else None,
        },

        "barricade_ratio": {
            "mean_protected_fraction": float(np.mean(prot_ratios)) if prot_ratios else 0.0,
        },

        "peak_score": {
            "mean":      float(np.mean(peak_scores_all)),
            "median":    float(np.median(peak_scores_all)),
            "wins_mean": float(np.mean([r.peak_score for r in subset if r.agent_won]))
                         if any(r.agent_won for r in subset) else None,
        },

        "endgame_buffer": {
            "mean_delta_at_letter_2":    float(np.mean(score_at_l2_delta))
                                         if score_at_l2_delta else None,
            "win_rate_if_ahead_at_l2":   ahead_at_l2_won  / ahead_at_l2_n
                                         if ahead_at_l2_n  else None,
            "win_rate_if_behind_at_l2":  behind_at_l2_won / behind_at_l2_n
                                         if behind_at_l2_n else None,
        },

        "penultimate_shift": {
            "pre_profile":  pre_profile,
            "post_profile": post_profile,
            "top_shifts":   shifts_sorted[:10],
        },

        "event_impact":    event_stats,

        "cricket_mimicry": mimic_profile,

        "theft": {
            "mean_times_stolen_from": float(np.mean(stolen_from_list)),
            "mean_times_agent_stole": float(np.mean(agent_stole_list)),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Human-readable report
# ─────────────────────────────────────────────────────────────────────────────

def _pct(x: Optional[float]) -> str:
    return f"{x*100:.1f}%" if x is not None else "N/A"

def _f(x: Optional[float], dp: int = 2) -> str:
    return f"{x:.{dp}f}" if x is not None else "N/A"


def write_report(agg_random: Dict, agg_greedy: Dict, out_path: str):
    lines = []

    def h(title: str):
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)

    def sub(title: str):
        lines.append("")
        lines.append(f"  ── {title}")

    def row(label: str, *vals):
        label_col = f"  {label:<42}"
        lines.append(label_col + "  ".join(str(v) for v in vals))

    lines.append("GUBS Strategy Analysis — Agent Simulation Report")
    lines.append(f"{'─'*70}")
    lines.append(f"  Games vs Random : {agg_random.get('n_games', 0):,}")
    lines.append(f"  Games vs Greedy : {agg_greedy.get('n_games', 0):,}")

    for agg, label in [(agg_random, "vs Random"), (agg_greedy, "vs Greedy")]:
        if not agg:
            continue

        h(f"Overall Results — {label}")
        row("Win rate",                _pct(agg["win_rate"]))
        row("Avg agent score",         _f(agg["avg_score"]))
        row("Avg opponent score",      _f(agg["avg_opp_score"]))
        row("Avg score difference",    _f(agg["avg_score_diff"]))

        sub("Game Length")
        gl = agg["game_length"]
        row("Mean turns per game",     _f(gl["mean"]))
        row("Std dev turns",           _f(gl["std"]))
        row("Mean turns in wins",      _f(gl["wins"]))
        row("Mean turns in losses",    _f(gl["losses"]))

        # ── Card analysis ─────────────────────────────────────────────────
        h(f"Card Strategy — {label}")
        lines.append("")
        lines.append(
            f"  {'Card':<22} {'Drawn':>6} {'Play%':>6} "
            f"{'AvgHeld':>8} {'WinAssoc':>9}"
        )
        lines.append(f"  {'-'*55}")

        cs = agg["card_stats"]
        # Sort by win association descending
        sorted_cards = sorted(cs.items(), key=lambda x: -x[1]["win_association"])
        for name, st in sorted_cards:
            if st["times_drawn"] < 5:   # skip statistical noise
                continue
            lines.append(
                f"  {name:<22} {st['times_drawn']:>6} "
                f"{_pct(st['play_rate']):>6} "
                f"{_f(st['avg_turns_held']):>8} "
                f"{_pct(st['win_association']):>9}"
            )

        lines.append("")
        lines.append("  Win Association = fraction of games where this card")
        lines.append("  appeared in agent hand that the agent won.")

        # ── Interrupt decisions ────────────────────────────────────────────
        h(f"Interrupt Usage — {label}")
        lines.append("")
        lines.append(f"  {'Interrupt kind':<20} {'Opportunities':>14} {'Fire rate':>10}")
        lines.append(f"  {'-'*48}")
        for kind, st in agg["interrupt_stats"].items():
            lines.append(
                f"  {kind:<20} {st['opportunities']:>14,} "
                f"{_pct(st['fire_rate']):>10}"
            )
        lines.append("")
        lines.append("  Fire rate = fraction of interrupt opportunities the agent")
        lines.append("  chose to use its interrupt card rather than pass.")

        # ── Aggression ─────────────────────────────────────────────────────
        h(f"Aggression — {label}")
        ag = agg["aggression"]
        row("Mean aggressive actions per game",    _f(ag["mean_aggressive_actions_per_game"]))
        row("Mean aggressive actions in wins",     _f(ag["wins_mean"]))
        row("Mean aggressive actions in losses",   _f(ag["losses_mean"]))

        # ── Colony composition ─────────────────────────────────────────────
        h(f"Colony Composition — {label}")
        sub("How protected should your colony be?")
        br = agg["barricade_ratio"]
        row("Mean fraction of Gubs protected",    _pct(br["mean_protected_fraction"]))

        sub("Peak colony score")
        pk = agg["peak_score"]
        row("Mean peak score reached",             _f(pk["mean"]))
        row("Median peak score",                   _f(pk["median"]))
        row("Mean peak score in wins",             _f(pk["wins_mean"]))

        # ── Endgame buffer ─────────────────────────────────────────────────
        h(f"Endgame Buffer (score at 2nd letter) — {label}")
        eb = agg["endgame_buffer"]
        row("Mean agent lead when 2nd letter drawn", _f(eb["mean_delta_at_letter_2"]))
        row("Win rate when ahead at 2nd letter",     _pct(eb["win_rate_if_ahead_at_l2"]))
        row("Win rate when behind at 2nd letter",    _pct(eb["win_rate_if_behind_at_l2"]))

        # ── Penultimate letter shift ────────────────────────────────────────
        h(f"Strategy Shift After 2nd Letter — {label}")
        lines.append("")
        lines.append("  Biggest changes in action frequency after the 2nd letter is drawn:")
        lines.append(f"  {'Action type':<35} {'Change':>10}")
        lines.append(f"  {'-'*48}")
        for atype, delta in agg["penultimate_shift"]["top_shifts"]:
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {atype:<35} {sign}{delta*100:+.1f}pp")

        # ── Events ─────────────────────────────────────────────────────────
        h(f"Event Card Impact — {label}")
        lines.append("")
        lines.append(f"  {'Event':<26} {'Count':>6} {'AvgΔ':>7} {'% Harmful':>10}")
        lines.append(f"  {'-'*53}")
        for ev, st in sorted(agg["event_impact"].items(), key=lambda x: x[1]["avg_delta"]):
            lines.append(
                f"  {ev:<26} {st['occurrences']:>6} "
                f"{_f(st['avg_delta']):>7} "
                f"{_pct(st['pct_harmful']):>10}"
            )
        lines.append("")
        lines.append("  AvgΔ = mean change in agent score immediately after event resolves.")
        lines.append("  Negative = event hurts the agent on average.")

        # ── Cricket Song ───────────────────────────────────────────────────
        h(f"Cricket Song Mimicry — {label}")
        lines.append("")
        lines.append("  What the agent uses Cricket Song as most often:")
        lines.append(f"  {'Mimicked card':<25} {'Fraction':>9}")
        lines.append(f"  {'-'*36}")
        for name, frac in list(agg["cricket_mimicry"].items())[:10]:
            lines.append(f"  {name:<25} {_pct(frac):>9}")

        # ── Theft ──────────────────────────────────────────────────────────
        h(f"Theft Dynamics — {label}")
        th = agg["theft"]
        row("Mean times stolen from per game",  _f(th["mean_times_stolen_from"]))
        row("Mean times agent stole per game",  _f(th["mean_times_agent_stole"]))

    lines.append("")
    lines.append("=" * 70)
    lines.append("  End of report")
    lines.append("=" * 70)
    lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  ✓ Summary report   → {out_path}")


def write_card_csv(agg_random: Dict, agg_greedy: Dict, out_path: str):
    import csv
    all_cards = set()
    for agg in (agg_random, agg_greedy):
        all_cards |= set(agg.get("card_stats", {}).keys())

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "card", "opponent",
            "times_drawn", "times_played", "times_discarded",
            "play_rate", "avg_turns_held", "median_turns_held", "win_association",
        ])
        for opp_label, agg in [("random", agg_random), ("greedy", agg_greedy)]:
            for name, st in agg.get("card_stats", {}).items():
                w.writerow([
                    name, opp_label,
                    st["times_drawn"], st["times_played"], st["times_discarded"],
                    f"{st['play_rate']:.4f}",
                    f"{st['avg_turns_held']:.2f}",
                    f"{st['median_turns_held']:.2f}",
                    f"{st['win_association']:.4f}",
                ])
    print(f"  ✓ Card stats CSV   → {out_path}")


def write_trajectory_csv(records: List[GameRecord], out_path: str):
    """Write mean agent score per turn bucket, broken down by outcome and opponent."""
    import csv

    # Collect (opponent_type, won, turn_bucket, score) tuples
    rows = []
    for r in records:
        for turn, score in r.score_trajectory:
            rows.append({
                "opponent":  r.opponent_type,
                "won":       int(r.agent_won),
                "turn":      turn,
                "score":     score,
            })

    # Aggregate: group by (opponent, won, turn) -> mean score
    from collections import defaultdict
    buckets: Dict[Tuple, List[int]] = defaultdict(list)
    for row in rows:
        key = (row["opponent"], row["won"], row["turn"])
        buckets[key].append(row["score"])

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["opponent", "outcome", "turn", "mean_score", "n"])
        for (opp, won, turn), scores in sorted(buckets.items()):
            w.writerow([
                opp,
                "win" if won else "loss",
                turn,
                f"{np.mean(scores):.3f}",
                len(scores),
            ])
    print(f"  ✓ Score trajectory → {out_path}")


def write_raw_jsonl(records: List[GameRecord], out_path: str):
    """Write one JSON object per game for offline analysis."""
    with open(out_path, "w") as f:
        for r in records:
            obj = {
                "game_id":          r.game_id,
                "opponent_type":    r.opponent_type,
                "agent_seat":       r.agent_seat,
                "winner":           r.winner,
                "agent_won":        r.agent_won,
                "agent_score":      r.agent_score,
                "opp_score":        r.opp_score,
                "total_turns":      r.total_turns,
                "letters_drawn":    r.letters_drawn,
                "peak_score":       r.peak_score,
                "times_stolen_from":r.times_stolen_from,
                "times_agent_stole":r.times_agent_stole,
                "score_trajectory": r.score_trajectory,
                "score_at_letter":  r.score_at_letter,
                "event_impacts":    r.event_impacts,
                "cricket_mimics":   r.cricket_mimics,
                "card_events": [
                    {
                        "name":       e.name,
                        "card_type":  e.card_type,
                        "turn_drawn": e.turn_drawn,
                        "turn_left":  e.turn_left,
                        "left_by":    e.left_by,
                    }
                    for e in r.card_events
                ],
                "agent_actions":              r.agent_actions,
                "interrupt_decisions":        r.interrupt_decisions,
                "actions_pre_penultimate":    r.actions_pre_penultimate,
                "actions_post_penultimate":   r.actions_post_penultimate,
            }
            f.write(json.dumps(obj) + "\n")
    print(f"  ✓ Raw JSONL        → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GUBS agent simulation & analysis")
    parser.add_argument("--weights",  type=str,  default="gubs_weights/best.pt",
                        help="Path to trained PPO weights")
    parser.add_argument("--games",    type=int,  default=5000,
                        help="Games per opponent type (total = 2x this)")
    parser.add_argument("--device",   type=str,  default="cpu")
    parser.add_argument("--out-dir",  type=str,  default="gubs_analysis")
    parser.add_argument("--workers",  type=int,  default=1,
                        help="Parallel worker processes (1 = serial)")
    parser.add_argument("--seed",     type=int,  default=0,
                        help="Base random seed")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device(args.device)

    # ── Load model ────────────────────────────────────────────────────────────
    print(f"\nLoading weights from {args.weights} ...")
    dummy   = GubsGame(num_players=2)
    cfg     = dict(DEFAULTS)
    cfg["device"] = args.device
    agent   = PPOAgent(dummy.obs_size, cfg)
    agent.load(args.weights)
    agent.net.eval()
    print(f"  Model loaded. Obs size={dummy.obs_size}, device={args.device}")

    # ── Run simulations ───────────────────────────────────────────────────────
    opponents = [
        ("random", RandomAgent),
        ("greedy", GreedyAgent),
    ]

    all_records: List[GameRecord] = []
    total_games = args.games * len(opponents)

    print(f"\nSimulating {total_games:,} games "
          f"({args.games:,} per opponent) ...\n")

    game_id = 0
    t0 = time.time()
    for opp_type, OppClass in opponents:
        opp_wins = 0
        agent_wins = 0
        for i in range(args.games):
            opp_seat = 1 - (game_id % 2)   # opponent always on opposite seat
            opponent = OppClass(opp_seat)
            rec = run_game(agent, opponent, opp_type, game_id, device)
            all_records.append(rec)
            if rec.agent_won:
                agent_wins += 1
            elif rec.winner >= 0:
                opp_wins += 1
            game_id += 1

            if (i + 1) % 500 == 0:
                elapsed = time.time() - t0
                rate    = game_id / elapsed
                eta     = (total_games - game_id) / rate
                wr      = agent_wins / (i + 1)
                print(f"  [{opp_type:>6}] {i+1:>5}/{args.games}  "
                      f"WR={wr:.1%}  "
                      f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\nAll {total_games:,} games complete in {elapsed:.1f}s "
          f"({elapsed/total_games*1000:.0f}ms/game)\n")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    print("Aggregating statistics ...")
    agg_random = aggregate(all_records, "random")
    agg_greedy = aggregate(all_records, "greedy")

    # ── Write outputs ─────────────────────────────────────────────────────────
    print("Writing outputs ...")
    write_report(agg_random, agg_greedy,
                 os.path.join(args.out_dir, "summary.txt"))
    write_card_csv(agg_random, agg_greedy,
                   os.path.join(args.out_dir, "per_card_stats.csv"))
    write_trajectory_csv(all_records,
                         os.path.join(args.out_dir, "score_trajectory.csv"))
    write_raw_jsonl(all_records,
                    os.path.join(args.out_dir, "raw_games.jsonl"))

    # ── Quick headline stats to stdout ────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  Headline results")
    print("─" * 50)
    for agg, label in [(agg_random, "vs Random"), (agg_greedy, "vs Greedy")]:
        if agg:
            wr = agg["win_rate"]
            sd = agg["avg_score_diff"]
            print(f"  {label:<12}  Win rate: {wr:.1%}   Avg score diff: {sd:+.2f}")
    print("─" * 50)
    print(f"\nResults written to: {args.out_dir}/\n")


if __name__ == "__main__":
    main()
