# GUBS_agent
Vibe-coded implementation of the GUBS card game, with RL agent training code.
Coded with Claude Sonnet. I give no guarantees that the code is free of bugs, but I did play-test and it seems to work as it should.

GUBS is a card game by Cole and Alex Medeiros (https://gamewright.com/product/GUBS). The aim is to have more of the odd creatures called Gubs on your field at the end of the game than your opponent(s). It's very fun so do go buy a copy!

gubs_engine contains the engine which sets out the rules for playing a game.

gubs_play allows you to play a game on the command line. 

To play against a simple baseline run the code using the following command.

```
python gubs_play.py --opponent greedy
```

We also trained a reinforcement learning agent for 1,000,000 episodes. Best performance was around 500,000 episodes, see gubs_analysis/training_log.csv. The weights for this model are included in best.pt. To play against this model run:

```
 python gubs_play.py --opponent model --weights best.pt
```

You can train your own model using the gubs_rl script:

```
python gubs_rl.py train \
    --episodes 1000000 \
    --device cuda \
    --weights-dir gubs_weights \
    --save-every 10000 \
    --eval-every 10000 \
```

Finally, I was interested in seeing what a good GUBS strategy might look like. The gubs_analysis script contains code to simulate games and collect statistics. A summary output is available in gubs_analysis/summary. The headlines include: the best cards are the Esteemed Elder, Super Lure, and Cricket Song; always interrupt Lures/Super Lures if possible.
