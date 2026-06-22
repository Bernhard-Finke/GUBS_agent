# GUBS_agent
Vive-coded implementation of the GUBS card game, with RL agent training code




======================================================================
  Overall Results — vs Greedy
======================================================================
  Win rate                                  58.5%
  Avg agent score                           3.64
  Avg opponent score                        2.64
  Avg score difference                      0.99

  ── Game Length
  Mean turns per game                       29.59
  Std dev turns                             2.60
  Mean turns in wins                        29.50
  Mean turns in losses                      29.70

======================================================================
  Card Strategy — vs Greedy
======================================================================

  Card                    Drawn  Play%  AvgHeld  WinAssoc
  -------------------------------------------------------
  Esteemed Elder           3942  99.0%     0.07     68.4%
  Super Lure               7831  86.1%     2.27     68.3%
  Cricket Song             4012 100.0%     0.05     63.9%
  Double Ring              4363  55.6%     4.75     60.2%
  Blind Fold               4429  60.8%     3.65     60.0%
  Lure                    25766  91.1%     1.10     59.9%
  Haki Flute               8664  62.1%     4.31     59.8%
  Smahl Thief              4086  95.8%     0.48     59.3%
  Gub                     67563  99.4%     0.04     58.6%
  Lightning                4158  37.4%     7.04     58.6%
  Age Old Cure             7850  88.4%     2.31     58.3%
  Triple Ring              4410  48.3%     5.41     57.7%
  Omen Beetle              4382  53.9%     4.63     57.4%
  Mushroom                20181  56.6%     5.91     57.4%
  Spear                   14479  76.6%     2.91     57.3%
  Single Ring              4217  54.6%     4.71     57.3%
  Feather                  8488  70.7%     3.18     57.2%
  Retreat                  4061  26.9%     7.03     57.0%
  Velvet Moth              8362  46.9%     6.63     56.9%
  Toad Rider              14784  63.2%     4.93     56.8%
  Cyclone                  4804  63.4%     4.68     56.7%
  Sud Spout               14397  60.4%     4.54     56.6%
  Flop Boat                3934  71.5%     3.31     55.5%
  Scout                    4318   1.7%     8.74     55.5%

  Win Association = fraction of games where this card
  appeared in agent hand that the agent won.

======================================================================
  Interrupt Usage — vs Greedy
======================================================================

  Interrupt kind        Opportunities  Fire rate
  ------------------------------------------------
  super_lure                      616      98.5%
  trap                          3,943      76.8%
  letter                        1,432      81.4%
  lure                          2,258      98.2%
  spear                         2,001      77.7%
  event                         2,284      77.4%
  hazard                        2,060      86.5%

  Fire rate = fraction of interrupt opportunities the agent
  chose to use its interrupt card rather than pass.

======================================================================
  Aggression — vs Greedy
======================================================================
  Mean aggressive actions per game          6.90
  Mean aggressive actions in wins           6.71
  Mean aggressive actions in losses         7.16

======================================================================
  Colony Composition — vs Greedy
======================================================================

  ── How protected should your colony be?
  Mean fraction of Gubs protected           9.3%

  ── Peak colony score
  Mean peak score reached                   4.97
  Median peak score                         5.00
  Mean peak score in wins                   5.65

======================================================================
  Endgame Buffer (score at 2nd letter) — vs Greedy
======================================================================
  Mean agent lead when 2nd letter drawn     0.49
  Win rate when ahead at 2nd letter         63.4%
  Win rate when behind at 2nd letter        51.2%

======================================================================
  Strategy Shift After 2nd Letter — vs Greedy
======================================================================

  Biggest changes in action frequency after the 2nd letter is drawn:
  Action type                             Change
  ------------------------------------------------
  play_barricade                      ++3.5pp
  draw                                -1.1pp
  end_discard                         -0.9pp
  end_play                            -0.8pp
  play_gub                            -0.6pp
  play_lure                           -0.5pp
  skip_draw                           -0.4pp
  play_sud_spout                      ++0.3pp
  play_cyclone                        ++0.2pp
  play_haki_flute                     ++0.2pp

======================================================================
  Event Card Impact — vs Greedy
======================================================================

  Event                       Count    AvgΔ  % Harmful
  -----------------------------------------------------
  Flash Flood                  7420   -2.40      77.9%
  Dangerous Alchemy            7441   -1.16      37.0%
  Rumor of Wasps               7463   -0.08       6.3%
  Gargok Plague                7481    0.00       0.0%
  Traveling Merchant           7467    0.00       0.0%

  AvgΔ = mean change in agent score immediately after event resolves.
  Negative = event hurts the agent on average.

======================================================================
  Cricket Song Mimicry — vs Greedy
======================================================================

  What the agent uses Cricket Song as most often:
  Mimicked card              Fraction
  ------------------------------------
  Super Lure                    87.7%
  Age Old Cure                  10.1%
  Haki Flute                     2.0%
  Smahl Thief                    0.1%
  Retreat                        0.0%

======================================================================
  Theft Dynamics — vs Greedy
======================================================================
  Mean times stolen from per game           4.04
  Mean times agent stole per game           4.31

======================================================================
  End of report
======================================================================
