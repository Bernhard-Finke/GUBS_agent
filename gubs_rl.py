"""
GUBS RL Training — PPO Agent
==============================

Training strategy:
  - Self-play vs a pool of past checkpoints + random + greedy agents
  - Reward = Gub score delta vs best opponent + win bonus
  - Action space: discrete over the action list (variable per state → masked softmax)

Estimated training time (single GPU, RTX 3080+):
  - Beat Random >70%:   ~20k episodes (~2-4h)
  - Beat Random >90%:   ~80k episodes (~8-12h)
  - Beat Greedy >60%:   ~200k episodes (~1.5-2 days)
  - Beat Greedy >75%:   ~600k episodes (~4-5 days)

Usage:
  python gubs_rl.py train --episodes 200000
  python gubs_rl.py train --resume weights/checkpoint_0050000.pt
  python gubs_rl.py eval  --weights weights/best.pt --games 200
  python gubs_rl.py agent-vs-agent --agent1 weights/best.pt --agent2 greedy --games 20
"""

import argparse
import os
import time
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical
from collections import deque
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from gubs_engine import GubsGame, RandomAgent, GreedyAgent, CardType

# ─────────────────────────────────────────────
#  Hyperparameters
# ─────────────────────────────────────────────
DEFAULTS = dict(
    episodes         = 300_000,
    lr               = 3e-4,
    gamma            = 0.99,
    gae_lambda       = 0.95,
    clip_eps         = 0.2,
    value_coef       = 0.5,
    entropy_coef     = 0.02,       # higher entropy for more exploration (GUBS is stochastic)
    max_grad_norm    = 0.5,
    ppo_epochs       = 4,
    batch_size       = 256,
    rollout_len      = 256,
    hidden_size      = 256,
    num_layers       = 3,
    save_every       = 10_000,
    eval_every       = 10_000,
    eval_games       = 100,
    self_play_update = 2_000,
    opponent_pool    = 5,
    device           = "cuda" if torch.cuda.is_available() else "cpu",
    weights_dir      = "gubs_weights",
    log_dir          = "gubs_logs",
)

# ─────────────────────────────────────────────
#  Action encoding
#
#  GUBS actions are variable and semantically rich. We use a fixed
# ─────────────────────────────────────────────
#  Action encoding
#
#  GUBS actions are variable and semantically rich. We map every distinct
#  valid action to its own slot in a fixed-size action vector; the network
#  outputs logits over MAX_ACTIONS slots and we mask invalid ones.
#
#  Key sizing constants:
#    GUB_SLOTS  = 14  -- max colony positions per player (13 Gub cards +
#                        1 Esteemed Elder). Any Ring-trap placeholder that
#                        would push a colony past this is clamped into the
#                        last slot (extremely rare edge case).
#    PLAYERS    = 2   -- this RL setup always trains 2-player games.
#    HAND_SLOTS = 8   -- matches GubsGame.MAX_HAND.
#    TG         = PLAYERS * GUB_SLOTS  -- one slot per (target_player,
#                        target_gub_idx) combination, so every Gub on the
#                        board can be targeted independently (previously
#                        these were hashed mod 5, which collided whenever
#                        more than ~5 Gubs were on the field).
#
#  Layout (non-overlapping, allocated via _alloc below):
#    single-slot actions (draw, pass_interrupt, play_retreat, ...)
#    hand-indexed actions (play_gub, discard_card, tm_keep_card,
#        play_interrupt) -- HAND_SLOTS each, so every hand position can be
#        chosen independently (needed for the "multiple interrupts in
#        hand" fix)
#    target_player-only actions (play_super_lure, play_lightning_hand,
#        play_scout_hand) -- PLAYERS each
#    (target_player, target_gub_idx) actions (play_barricade,
#        play_mushroom_destroy, play_toad_rider_destroy, play_lure,
#        play_smahl_thief_gub/barricade, play_sud_spout, play_haki_flute,
#        play_spear_sud_spout/discard_gub) -- TG each
#    play_ring -- TG * 3 slots (hashed combination of up to 3 targets)
#    scout_rearrange -- small permutation block
#    play_cricket_song mimic variants -- one block per (mimic, as_action)
# ─────────────────────────────────────────────
GUB_SLOTS  = 14
PLAYERS    = 2
HAND_SLOTS = 8
TG         = PLAYERS * GUB_SLOTS   # 28


def _tg_idx(action: Dict) -> int:
    """Encode (target_player, target_gub_idx) into 0..TG-1, with every
    distinct (player, gub-on-field) combination getting its own slot."""
    tp = action.get("target_player", 0) % PLAYERS
    gi = min(action.get("target_gub_idx", 0), GUB_SLOTS - 1)
    return tp * GUB_SLOTS + gi


_next_idx = [0]


def _alloc(n: int = 1) -> int:
    start = _next_idx[0]
    _next_idx[0] += n
    return start


# Single-slot, non-targeted actions
IDX_DRAW                 = _alloc()
IDX_SKIP_DRAW            = _alloc()
IDX_BEGIN_PLAY           = _alloc()
IDX_END_PLAY             = _alloc()
IDX_END_DISCARD          = _alloc()
IDX_PASS_INTERRUPT       = _alloc()
IDX_PLAY_CYCLONE         = _alloc()
IDX_PLAY_LIGHTNING_ELDER = _alloc()
IDX_PLAY_OMEN_BEETLE     = _alloc()
IDX_PLAY_RETREAT         = _alloc()
IDX_AGE_OLD_CURE         = _alloc()
IDX_GARGOK_USE_CURE      = _alloc()
IDX_GARGOK_DECLINE_CURE  = _alloc()
IDX_PLAY_SCOUT_DECK      = _alloc()

# Hand-indexed actions (one slot per hand position)
PLAY_GUB       = _alloc(HAND_SLOTS)
DISCARD_CARD   = _alloc(HAND_SLOTS)
TM_KEEP_CARD   = _alloc(HAND_SLOTS)
PLAY_INTERRUPT = _alloc(HAND_SLOTS)
CRICKET_GARGOK_SAVE = _alloc()

# target_player-only actions
SUPER_LURE     = _alloc(PLAYERS)
LIGHTNING_HAND = _alloc(PLAYERS)
SCOUT_HAND     = _alloc(PLAYERS)

# (target_player, target_gub_idx) actions -- one slot per Gub on the board
BARRICADE          = _alloc(TG)
MUSHROOM_DESTROY   = _alloc(TG)
TOAD_RIDER_DESTROY = _alloc(TG)
LURE               = _alloc(TG)
SMAHL_GUB          = _alloc(TG)
SMAHL_BARRICADE    = _alloc(TG)
SUD_SPOUT          = _alloc(TG)
HAKI_FLUTE         = _alloc(TG)
SPEAR_SUD          = _alloc(TG)
SPEAR_DISCARD      = _alloc(TG)

# play_ring: combinations of up to 3 (player, gub_idx) targets, hashed
RING      = _alloc(TG * 3)
RING_SPAN = TG * 3

# scout_rearrange: permutation of top 3 deck cards
SCOUT_REARRANGE      = _alloc(10)
SCOUT_REARRANGE_SPAN = 10

# play_cricket_song mimic variants
CRICKET_LURE            = _alloc(TG)
CRICKET_SUPER_LURE      = _alloc(PLAYERS)
CRICKET_CYCLONE         = _alloc(PLAYERS)
CRICKET_LIGHTNING_HAND  = _alloc(PLAYERS)
CRICKET_LIGHTNING_ELDER = _alloc()
CRICKET_SMAHL_GUB       = _alloc(TG)
CRICKET_SMAHL_BARRICADE = _alloc(TG)
CRICKET_SPEAR_SUD       = _alloc(TG)
CRICKET_SPEAR_DISCARD   = _alloc(TG)
CRICKET_HAKI_FLUTE      = _alloc(TG)
CRICKET_OMEN_BEETLE     = _alloc()
CRICKET_SCOUT_DECK      = _alloc()
CRICKET_SCOUT_HAND      = _alloc(PLAYERS)
CRICKET_RETREAT         = _alloc()
CRICKET_AGE_OLD_CURE    = _alloc()

MAX_ACTIONS = _next_idx[0]


def action_to_idx(action: Dict) -> int:
    """Map an action dict to a unique integer index 0..MAX_ACTIONS-1.

    Every distinct valid action available in a given state maps to its own
    index (no mod-N hashing), so the policy can independently target any
    Gub on the board and can choose between multiple cards of the same
    type sitting in different hand slots (e.g. two interrupts at once).
    """
    t = action["type"]

    if t == "draw":           return IDX_DRAW
    if t == "skip_draw":      return IDX_SKIP_DRAW
    if t == "begin_play":     return IDX_BEGIN_PLAY
    if t == "end_play":       return IDX_END_PLAY
    if t == "end_discard":    return IDX_END_DISCARD
    if t == "pass_interrupt": return IDX_PASS_INTERRUPT
    if t == "play_cyclone":         return IDX_PLAY_CYCLONE
    if t == "play_lightning_elder": return IDX_PLAY_LIGHTNING_ELDER
    if t == "play_omen_beetle":     return IDX_PLAY_OMEN_BEETLE
    if t == "play_retreat":         return IDX_PLAY_RETREAT
    if t == "play_age_old_cure_retrieve": return IDX_AGE_OLD_CURE
    if t == "gargok_use_cure":      return IDX_GARGOK_USE_CURE
    if t == "gargok_decline_cure":  return IDX_GARGOK_DECLINE_CURE
    if t == "play_scout_deck":      return IDX_PLAY_SCOUT_DECK

    if t == "play_gub":
        return PLAY_GUB + action.get("card_idx", 0) % HAND_SLOTS
    if t == "discard_card":
        return DISCARD_CARD + action.get("card_idx", 0) % HAND_SLOTS
    if t == "tm_keep_card":
        return TM_KEEP_CARD + action.get("card_idx", 0) % HAND_SLOTS
    if t == "play_interrupt":
        # A Cricket Song mimicking Age Old Cure to self-save during a Gargok
        # Plague interrupt gets its own slot, since the same Cricket Song
        # hand slot may also offer a Flop Boat mimic (cancel the event) --
        # both need to be independently selectable.
        if action.get("is_gargok_save") and action.get("is_cricket_song"):
            return CRICKET_GARGOK_SAVE
        # card_idx distinguishes between multiple held interrupts (even of
        # the same card type), letting the agent choose any/all of them.
        return PLAY_INTERRUPT + action.get("card_idx", 0) % HAND_SLOTS

    if t == "play_super_lure":
        return SUPER_LURE + action.get("target_player", 0) % PLAYERS
    if t == "play_lightning_hand":
        return LIGHTNING_HAND + action.get("target_player", 0) % PLAYERS
    if t == "play_scout_hand":
        return SCOUT_HAND + action.get("target_player", 0) % PLAYERS

    if t == "play_barricade":          return BARRICADE + _tg_idx(action)
    if t == "play_mushroom_destroy":   return MUSHROOM_DESTROY + _tg_idx(action)
    if t == "play_toad_rider_destroy": return TOAD_RIDER_DESTROY + _tg_idx(action)
    if t == "play_lure":               return LURE + _tg_idx(action)
    if t == "play_smahl_thief_gub":       return SMAHL_GUB + _tg_idx(action)
    if t == "play_smahl_thief_barricade": return SMAHL_BARRICADE + _tg_idx(action)
    if t == "play_sud_spout":          return SUD_SPOUT + _tg_idx(action)
    if t == "play_haki_flute":         return HAKI_FLUTE + _tg_idx(action)
    if t == "play_spear_sud_spout":    return SPEAR_SUD + _tg_idx(action)
    if t == "play_spear_discard_gub":  return SPEAR_DISCARD + _tg_idx(action)

    if t == "play_ring":
        targets = action.get("gub_targets", [])
        h = sum(tp * GUB_SLOTS + min(gi, GUB_SLOTS - 1) for tp, gi in targets)
        return RING + h % RING_SPAN

    if t == "scout_rearrange":
        order = action.get("order", [0, 1, 2])
        h = sum(v * (10 ** i) for i, v in enumerate(order))
        return SCOUT_REARRANGE + h % SCOUT_REARRANGE_SPAN

    if t == "play_cricket_song":
        mimic     = action.get("as_card", "")
        as_action = action.get("as_action", "")
        if mimic == "Lure":
            return CRICKET_LURE + _tg_idx(action)
        if mimic == "Super Lure":
            return CRICKET_SUPER_LURE + action.get("target_player", 0) % PLAYERS
        if mimic == "Cyclone":
            return CRICKET_CYCLONE + action.get("target_player", 0) % PLAYERS
        if mimic == "Lightning":
            if as_action == "play_lightning_elder":
                return CRICKET_LIGHTNING_ELDER
            return CRICKET_LIGHTNING_HAND + action.get("target_player", 0) % PLAYERS
        if mimic == "Smahl Thief":
            if as_action == "play_smahl_thief_barricade":
                return CRICKET_SMAHL_BARRICADE + _tg_idx(action)
            return CRICKET_SMAHL_GUB + _tg_idx(action)
        if mimic == "Spear":
            if as_action == "play_spear_sud_spout":
                return CRICKET_SPEAR_SUD + _tg_idx(action)
            return CRICKET_SPEAR_DISCARD + _tg_idx(action)
        if mimic == "Haki Flute":
            return CRICKET_HAKI_FLUTE + _tg_idx(action)
        if mimic == "Omen Beetle":
            return CRICKET_OMEN_BEETLE
        if mimic == "Scout":
            if as_action == "play_scout_hand":
                return CRICKET_SCOUT_HAND + action.get("target_player", 0) % PLAYERS
            return CRICKET_SCOUT_DECK
        if mimic == "Retreat":
            return CRICKET_RETREAT
        if mimic == "Age Old Cure":
            return CRICKET_AGE_OLD_CURE
        return MAX_ACTIONS - 1  # unknown mimic, fallback

    # Fallback for any unrecognised types
    return MAX_ACTIONS - 1

def build_action_mask(actions: List[Dict]) -> np.ndarray:
    mask = np.zeros(MAX_ACTIONS, dtype=np.bool_)
    for a in actions:
        mask[action_to_idx(a)] = True
    return mask

def mask_to_best_action(mask: np.ndarray, logits: np.ndarray,
                         valid_actions: List[Dict]) -> Dict:
    """Pick the valid action corresponding to the highest logit."""
    best_score = -1e9
    best_action = valid_actions[0]
    for a in valid_actions:
        idx = action_to_idx(a)
        if logits[idx] > best_score:
            best_score = logits[idx]
            best_action = a
    return best_action

# ─────────────────────────────────────────────
#  Policy-Value Network
# ─────────────────────────────────────────────
class GubsNet(nn.Module):
    def __init__(self, obs_size: int, hidden_size: int = 256, num_layers: int = 3):
        super().__init__()
        layers = []
        in_dim = obs_size
        for _ in range(num_layers):
            layers += [nn.Linear(in_dim, hidden_size), nn.LayerNorm(hidden_size), nn.GELU()]
            in_dim = hidden_size
        self.shared = nn.Sequential(*layers)
        self.policy_head = nn.Linear(hidden_size, MAX_ACTIONS)
        self.value_head  = nn.Linear(hidden_size, 1)

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                nn.init.zeros_(m.bias)
        nn.init.orthogonal_(self.policy_head.weight, gain=0.01)
        nn.init.orthogonal_(self.value_head.weight,  gain=1.0)

    def forward(self, obs: torch.Tensor, mask: torch.Tensor):
        h = self.shared(obs)
        logits = self.policy_head(h) + (mask.float() - 1) * 1e9
        dist = Categorical(logits=logits)
        value = self.value_head(h).squeeze(-1)
        return dist, value

    def get_action(self, obs, mask):
        dist, value = self.forward(obs, mask)
        action = dist.sample()
        return action, dist.log_prob(action), value

    def evaluate(self, obs, mask, actions):
        dist, value = self.forward(obs, mask)
        return dist.log_prob(actions), value, dist.entropy()

# ─────────────────────────────────────────────
#  PPO Agent
# ─────────────────────────────────────────────
class PPOAgent:
    def __init__(self, obs_size: int, cfg: dict):
        self.cfg = cfg
        self.device = torch.device(cfg["device"])
        self.net = GubsNet(obs_size, cfg["hidden_size"], cfg["num_layers"]).to(self.device)
        self.optimizer = optim.Adam(self.net.parameters(), lr=cfg["lr"], eps=1e-5)
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=cfg["episodes"], eta_min=1e-5)

        self.obs_buf:     List[np.ndarray] = []
        self.mask_buf:    List[np.ndarray] = []
        self.action_buf:  List[int]        = []
        self.reward_buf:  List[float]      = []
        self.value_buf:   List[float]      = []
        self.logprob_buf: List[float]      = []
        self.done_buf:    List[bool]       = []

        self.total_steps   = 0
        self.episode_count = 0

    def select_action_train(self, obs: np.ndarray, mask: np.ndarray,
                             valid_actions: List[Dict]) -> Dict:
        obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        mask_t = torch.BoolTensor(mask).unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_idx, log_prob, value = self.net.get_action(obs_t, mask_t)

        a_idx = action_idx.item()
        # Map sampled index back to a valid action
        action = self._idx_to_valid_action(a_idx, valid_actions)
        self.obs_buf.append(obs)
        self.mask_buf.append(mask)
        self.action_buf.append(a_idx)
        self.logprob_buf.append(log_prob.item())
        self.value_buf.append(value.item())
        self.total_steps += 1
        return action

    def _idx_to_valid_action(self, idx: int, valid_actions: List[Dict]) -> Dict:
        """Find the valid action closest to the sampled index."""
        # Direct match
        for a in valid_actions:
            if action_to_idx(a) == idx:
                return a
        # Fallback: pick random valid action
        return random.choice(valid_actions)

    def add_reward_done(self, reward: float, done: bool):
        self.reward_buf.append(reward)
        self.done_buf.append(done)

    def update(self, last_value: float = 0.0) -> Dict[str, float]:
        cfg = self.cfg
        n = len(self.reward_buf)
        if n == 0:
            return {}

        rewards = np.array(self.reward_buf, dtype=np.float32)
        values  = np.array(self.value_buf[:n], dtype=np.float32)
        dones   = np.array(self.done_buf, dtype=np.float32)

        advantages = np.zeros(n, dtype=np.float32)
        gae = 0.0
        for t in reversed(range(n)):
            nv = last_value if t == n-1 else values[t+1]
            delta = rewards[t] + cfg["gamma"] * nv * (1-dones[t]) - values[t]
            gae = delta + cfg["gamma"] * cfg["gae_lambda"] * (1-dones[t]) * gae
            advantages[t] = gae

        returns = advantages + values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        obs_t   = torch.FloatTensor(np.array(self.obs_buf[:n])).to(self.device)
        mask_t  = torch.BoolTensor(np.array(self.mask_buf[:n])).to(self.device)
        act_t   = torch.LongTensor(self.action_buf[:n]).to(self.device)
        lp_old  = torch.FloatTensor(self.logprob_buf[:n]).to(self.device)
        ret_t   = torch.FloatTensor(returns).to(self.device)
        adv_t   = torch.FloatTensor(advantages).to(self.device)

        total_loss = policy_loss_total = value_loss_total = entropy_total = 0.0
        update_count = 0
        indices = np.arange(n)
        for _ in range(cfg["ppo_epochs"]):
            np.random.shuffle(indices)
            for start in range(0, n, cfg["batch_size"]):
                idx = indices[start:min(start+cfg["batch_size"], n)]
                lp_new, val_new, ent = self.net.evaluate(obs_t[idx], mask_t[idx], act_t[idx])
                ratio = torch.exp(lp_new - lp_old[idx])
                adv_b = adv_t[idx]
                pol_loss = -torch.min(
                    ratio * adv_b,
                    torch.clamp(ratio, 1-cfg["clip_eps"], 1+cfg["clip_eps"]) * adv_b
                ).mean()
                val_loss = F.mse_loss(val_new, ret_t[idx])
                loss = pol_loss + cfg["value_coef"]*val_loss - cfg["entropy_coef"]*ent.mean()

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), cfg["max_grad_norm"])
                self.optimizer.step()

                total_loss        += loss.item()
                policy_loss_total += pol_loss.item()
                value_loss_total  += val_loss.item()
                entropy_total     += ent.mean().item()
                update_count      += 1

        self.scheduler.step()
        self.clear_buffers()
        k = max(update_count, 1)
        return {"loss": total_loss/k, "policy_loss": policy_loss_total/k,
                "value_loss": value_loss_total/k, "entropy": entropy_total/k}

    def clear_buffers(self):
        self.obs_buf.clear(); self.mask_buf.clear(); self.action_buf.clear()
        self.reward_buf.clear(); self.value_buf.clear()
        self.logprob_buf.clear(); self.done_buf.clear()

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"net": self.net.state_dict(),
                    "optimizer": self.optimizer.state_dict(),
                    "steps": self.total_steps,
                    "episodes": self.episode_count,
                    "cfg": self.cfg}, path)
        print(f"  ✓ Saved → {path}")

    def load(self, path: str):
        ckpt = torch.load(path, map_location=self.device)
        self.net.load_state_dict(ckpt["net"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.total_steps   = ckpt.get("steps", 0)
        self.episode_count = ckpt.get("episodes", 0)
        print(f"  ✓ Loaded ← {path}")

    def get_action_greedy(self, game: GubsGame) -> Optional[Dict]:
        valid = game.get_all_valid_actions()
        if not valid:
            return None
        obs  = game.get_observation(game.current_player)
        mask = build_action_mask(valid)
        obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        mask_t = torch.BoolTensor(mask).unsqueeze(0).to(self.device)
        with torch.no_grad():
            h = self.net.shared(obs_t)
            logits = self.net.policy_head(h).squeeze(0).cpu().numpy()
            logits_masked = logits + (mask.astype(float) - 1) * 1e9
        return mask_to_best_action(mask, logits_masked, valid)


# ─────────────────────────────────────────────
#  Model agent wrapper
# ─────────────────────────────────────────────
class ModelAgent:
    def __init__(self, net: GubsNet, player_id: int, device: str = "cpu"):
        self.net = net
        self.player_id = player_id
        self.device = torch.device(device)

    def select_action(self, game: GubsGame) -> Optional[Dict]:
        valid = game.get_all_valid_actions()
        if not valid:
            return None
        obs  = game.get_observation(self.player_id)
        mask = build_action_mask(valid)
        obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        mask_t = torch.BoolTensor(mask).unsqueeze(0).to(self.device)
        with torch.no_grad():
            h = self.net.shared(obs_t)
            logits = self.net.policy_head(h).squeeze(0).cpu().numpy()
            logits_masked = logits + (mask.astype(float) - 1) * 1e9
        return mask_to_best_action(mask, logits_masked, valid)


# ─────────────────────────────────────────────
#  Reward
# ─────────────────────────────────────────────
def compute_reward(before: GubsGame, after: GubsGame, player: int, done: bool) -> float:
    scores_b = before.calculate_scores()
    scores_a = after.calculate_scores()
    own_delta = scores_a[player] - scores_b[player]
    opp_delta = max(
        (scores_a[p] - scores_b[p] for p in range(after.num_players) if p != player),
        default=0.0
    )
    reward = (own_delta - opp_delta) / 3.0
    if done:
        winner = after.get_winner()
        if winner == player:      reward += 1.0
        elif winner < 0:          reward += 0.0
        else:                     reward -= 1.0
    return reward


# ─────────────────────────────────────────────
#  Evaluation
# ─────────────────────────────────────────────
def evaluate(agent: PPOAgent, opponent, num_games: int = 50) -> Dict:
    wins = 0
    score_diffs = []
    for g in range(num_games):
        game = GubsGame(num_players=2, seed=g)
        agent_player = g % 2
        opp_player   = 1 - agent_player

        steps = 0
        while not game.is_terminal() and steps < 1000:
            if game.current_player == agent_player:
                action = agent.get_action_greedy(game)
            else:
                action = opponent.select_action(game)
            if action is None:
                break
            game.apply_action(action)
            steps += 1

        scores = game.calculate_scores()
        if scores[agent_player] > scores[opp_player]:
            wins += 1
        score_diffs.append(scores[agent_player] - scores[opp_player])

    return {"win_rate": wins/num_games,
            "avg_score_diff": np.mean(score_diffs),
            "std_score_diff": np.std(score_diffs)}


# ─────────────────────────────────────────────
#  Training loop
# ─────────────────────────────────────────────
def train(cfg: dict):
    os.makedirs(cfg["weights_dir"], exist_ok=True)
    os.makedirs(cfg["log_dir"],     exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  GUBS PPO Training")
    print(f"  Device:   {cfg['device']}")
    print(f"  Episodes: {cfg['episodes']:,}")
    print(f"{'='*60}\n")

    dummy = GubsGame(2)
    obs_size = dummy.obs_size
    print(f"Obs size:      {obs_size}")
    print(f"Action space:  {MAX_ACTIONS} (masked)\n")

    agent = PPOAgent(obs_size, cfg)
    if cfg.get("resume"):
        agent.load(cfg["resume"])

    random_opp = RandomAgent(1)
    greedy_opp = GreedyAgent(1)
    opp_net_copies: deque = deque(maxlen=cfg["opponent_pool"])

    log_path = os.path.join(cfg["log_dir"], "training_log.csv")
    with open(log_path, "w") as f:
        f.write("episode,steps,reward,loss,entropy,win_vs_random,win_vs_greedy\n")

    ep_rewards = deque(maxlen=100)
    best_wr = 0.0
    steps_rollout = 0
    stats = {}
    start_time = time.time()

    for episode in range(agent.episode_count, cfg["episodes"]):
        game = GubsGame(num_players=2, seed=None)
        agent_player = episode % 2
        opp_player   = 1 - agent_player

        # Choose opponent
        if opp_net_copies and episode % 10 < 5:
            opp_net = random.choice(list(opp_net_copies))
            opponent = ModelAgent(opp_net, opp_player, cfg["device"])
        elif episode % 10 < 7:
            opponent = RandomAgent(opp_player)
        else:
            opponent = GreedyAgent(opp_player)

        ep_reward = 0.0
        steps_game = 0

        while not game.is_terminal() and steps_game < 500:
            cp = game.current_player
            valid = game.get_all_valid_actions()
            if not valid:
                break

            if cp == agent_player:
                obs  = game.get_observation(agent_player)
                mask = build_action_mask(valid)
                if not mask.any():
                    break
                game_snap = game.clone()
                action = agent.select_action_train(obs, mask, valid)
                ok = game.apply_action(action)
                if not ok:
                    break
                done   = game.is_terminal()
                reward = compute_reward(game_snap, game, agent_player, done)
                agent.add_reward_done(reward, done)
                ep_reward += reward
                steps_rollout += 1
                steps_game    += 1
            else:
                action = opponent.select_action(game)
                if action is None:
                    break
                game.apply_action(action)
                steps_game += 1

            if steps_rollout >= cfg["rollout_len"]:
                if not game.is_terminal():
                    obs_t  = torch.FloatTensor(
                        game.get_observation(agent_player)).unsqueeze(0).to(agent.device)
                    valid2 = game.get_all_valid_actions()
                    mask_t = torch.BoolTensor(
                        build_action_mask(valid2)).unsqueeze(0).to(agent.device)
                    with torch.no_grad():
                        _, last_val = agent.net.forward(obs_t, mask_t)
                    lv = last_val.item()
                else:
                    lv = 0.0
                stats = agent.update(lv)
                steps_rollout = 0

        if len(agent.reward_buf) > 0:
            stats = agent.update(0.0)
            steps_rollout = 0

        ep_rewards.append(ep_reward)
        agent.episode_count += 1

        if episode % cfg["self_play_update"] == 0 and episode > 0:
            copy_net = GubsNet(obs_size, cfg["hidden_size"], cfg["num_layers"]).to(agent.device)
            copy_net.load_state_dict(agent.net.state_dict())
            copy_net.eval()
            opp_net_copies.append(copy_net)
            print(f"  [ep {episode}] Self-play pool updated ({len(opp_net_copies)} copies)")

        if episode % 200 == 0:
            elapsed = time.time() - start_time
            print(f"Ep {episode:>7,} | "
                  f"AvgR: {np.mean(ep_rewards) if ep_rewards else 0:+.3f} | "
                  f"Steps: {agent.total_steps:>8,} | "
                  f"Loss: {stats.get('loss', 0):.4f} | "
                  f"Ent: {stats.get('entropy', 0):.3f} | "
                  f"Elapsed: {elapsed/3600:.1f}h")

        if episode % cfg["eval_every"] == 0 and episode > 0:
            print(f"\n  ── Evaluation at ep {episode} ──")
            r = evaluate(agent, RandomAgent(1), cfg["eval_games"])
            g = evaluate(agent, GreedyAgent(1), cfg["eval_games"])
            print(f"  vs Random: {r['win_rate']:.1%}  Δscore={r['avg_score_diff']:.2f}")
            print(f"  vs Greedy: {g['win_rate']:.1%}  Δscore={g['avg_score_diff']:.2f}\n")
            with open(log_path, "a") as f:
                f.write(f"{episode},{agent.total_steps},{np.mean(ep_rewards):.4f},"
                        f"{stats.get('loss',0):.4f},{stats.get('entropy',0):.4f},"
                        f"{r['win_rate']:.4f},{g['win_rate']:.4f}\n")
            if r["win_rate"] > best_wr:
                best_wr = r["win_rate"]
                agent.save(os.path.join(cfg["weights_dir"], "best.pt"))

        if episode % cfg["save_every"] == 0 and episode > 0:
            agent.save(os.path.join(cfg["weights_dir"], f"checkpoint_{episode:07d}.pt"))

    agent.save(os.path.join(cfg["weights_dir"], "final.pt"))
    elapsed = time.time() - start_time
    print(f"\nTraining complete in {elapsed/3600:.2f}h. Best win rate: {best_wr:.1%}")


# ─────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="GUBS PPO RL Trainer")
    subs = parser.add_subparsers(dest="command")

    tp = subs.add_parser("train")
    tp.add_argument("--episodes",   type=int,   default=DEFAULTS["episodes"])
    tp.add_argument("--lr",         type=float, default=DEFAULTS["lr"])
    tp.add_argument("--hidden",     type=int,   default=DEFAULTS["hidden_size"])
    tp.add_argument("--save-every", type=int,   default=DEFAULTS["save_every"])
    tp.add_argument("--eval-every", type=int,   default=DEFAULTS["eval_every"])
    tp.add_argument("--resume",     type=str,   default=None)
    tp.add_argument("--device",     type=str,   default=DEFAULTS["device"])
    tp.add_argument("--weights-dir",type=str,   default=DEFAULTS["weights_dir"])

    ep = subs.add_parser("eval")
    ep.add_argument("--weights", type=str, required=True)
    ep.add_argument("--games",   type=int, default=100)
    ep.add_argument("--device",  type=str, default=DEFAULTS["device"])

    ap = subs.add_parser("agent-vs-agent")
    ap.add_argument("--agent1",  type=str, required=True)
    ap.add_argument("--agent2",  type=str, default="random")
    ap.add_argument("--games",   type=int, default=10)
    ap.add_argument("--device",  type=str, default=DEFAULTS["device"])

    args = parser.parse_args()

    if args.command == "train":
        cfg = dict(DEFAULTS)
        cfg.update({"episodes": args.episodes, "lr": args.lr,
                    "hidden_size": args.hidden, "save_every": args.save_every,
                    "eval_every": args.eval_every, "resume": args.resume,
                    "device": args.device, "weights_dir": args.weights_dir})
        train(cfg)

    elif args.command == "eval":
        dummy = GubsGame(2)
        cfg = dict(DEFAULTS); cfg["device"] = args.device
        agent = PPOAgent(dummy.obs_size, cfg)
        agent.load(args.weights)
        print(f"\nEvaluating {args.games} games each...")
        r = evaluate(agent, RandomAgent(1), args.games)
        g = evaluate(agent, GreedyAgent(1), args.games)
        print(f"vs Random: {r['win_rate']:.1%} win, Δ={r['avg_score_diff']:.2f}±{r['std_score_diff']:.2f}")
        print(f"vs Greedy: {g['win_rate']:.1%} win, Δ={g['avg_score_diff']:.2f}±{g['std_score_diff']:.2f}")

    elif args.command == "agent-vs-agent":
        dummy = GubsGame(2)
        cfg = dict(DEFAULTS); cfg["device"] = args.device
        def load_agent(path, pid):
            if path == "random": return RandomAgent(pid)
            if path == "greedy": return GreedyAgent(pid)
            a = PPOAgent(dummy.obs_size, cfg)
            a.load(path)
            return a
        a1 = load_agent(args.agent1, 0)
        a2 = load_agent(args.agent2, 1)
        wins = [0,0,0]
        for g in range(args.games):
            game = GubsGame(2)
            steps = 0
            while not game.is_terminal() and steps < 1000:
                cp = game.current_player
                ag = a1 if cp == 0 else a2
                action = ag.get_action_greedy(game) if hasattr(ag, "get_action_greedy") \
                         else ag.select_action(game)
                if action is None: break
                game.apply_action(action)
                steps += 1
            w = game.get_winner()
            wins[w if w >= 0 else 2] += 1
            scores = game.calculate_scores()
            print(f"Game {g+1:>2}: {scores} → {'P'+str(w) if w>=0 else 'Draw'}")
        print(f"\nAgent1 wins: {wins[0]}/{args.games}  "
              f"Agent2 wins: {wins[1]}/{args.games}  "
              f"Draws: {wins[2]}/{args.games}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()