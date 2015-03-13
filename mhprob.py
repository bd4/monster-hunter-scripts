#!/usr/bin/env python

# Calculate probability of getting at least one of a monster part from one
# line in the quest rewards. Also calculates expected value of part
# counts (N), and probabilities of getting a certain number of rewards (C).
#
# usage: mhprob.py reward_percent fixed_rewards gaurenteed_rewards \
#                  [extend_percent]
#
# reward_percent - chance of getting the monster part in %
# fixed_rewards - number of rewards in the reward list with 100% chance and
#                 are not the item you are looking for. Takes away from
#                 the total possible draw attempts for what you want.
#                 Default 1 which is typical for line A in many quests.
# gaurenteed_rewards - minimum number of quest rewards in the line,
#                      including any fixed rewards. In Tri (see link
#                      below) this is 3 for line A and 1 for line B.
#                      Defaults to 3.
# extend_percent - chance of getting one more reward in the line in %,
#                  default 69
#
# You can use http://kiranico.com to get reward percent and fixed rewards
# values.
#
# For extend percent, use the default unless you have the Lucky Cat or
# Ultra Lucky Cat food skills or Good Luck or Great Luck armor skills:
#
# normal extra reward %: 69
# good luck extra reward %: 81
# great luck extra %: 90
#
# Can also be used to calculate chance of getting a part from carving,
# using extend_percent=0, fixed_rewards=0, and gaurenteed_rewards=3 (or
# 4 for monsters with 4 carves).
#
# Source:
# http://www.gamefaqs.com/wii/943655-monster-hunter-tri/faqs/60448
# Not sure if there are differences in 3U or 4U.
#
# Example Plain dangerous in 3U, has 2 fixed rewards in A, one in B, hardhorns
# are 5% both A and B:
# A: ./mhprop.py 5 2 3 69
# B: ./mhprop.py 5 1 1 69
# For great luck, replace 69 with 90

import sys

def _quest_reward_p(reward_percent, reward_count):
    """
    Propability of getting at least one item from @reward_count draws
    with a @reward_percent chance.
    """
    fail_percent = (100 - reward_percent)
    return 1.0 - (fail_percent / 100.0)**reward_count

def _reward_count_p(reward_count, min_rewards, max_rewards, extend_percent):
    """
    Probability of getting a certain number of rewards for a given chance
    @extend_percent of getting one more drop.
    """
    if reward_count == min_rewards:
        return (100 - extend_percent) / 100.0
    p = 1.0
    extend_p = extend_percent / 100.0
    stop_p = 1.0 - extend_p
    for i in xrange(min_rewards+1, reward_count+1):
        p *= extend_p
    if reward_count < max_rewards:
        p *= stop_p
    return p

def quest_reward_p(reward_percent, min_rewards, max_rewards, extend_percent=69):
    """
    Probability of getting at least one of the item, given the item has
    @reward_percent chance, @min_rewards minimum number of attempts,
    @max_rewards max attempts, and @extend_percent chance of getting each
    extra attempt.
    """
    p = 0.0
    for reward_count in xrange(min_rewards, max_rewards + 1):
        p += (_reward_count_p(reward_count, min_rewards, max_rewards,
                              extend_percent)
              * _quest_reward_p(reward_percent, reward_count))
    return p * 100


if __name__ == '__main__':
    # in percent
    reward_percent = int(sys.argv[1])
    if len(sys.argv) > 2:
        fixed_rewards = int(sys.argv[2])
    else:
        fixed_rewards = 1
    if len(sys.argv) > 3:
        guarenteed_rewards = int(sys.argv[3])
    else:
        guarenteed_rewards = 3
    if len(sys.argv) > 4:
        extend_percent = int(sys.argv[4])
    else:
        extend_percent = 69

    min_rewards = guarenteed_rewards - fixed_rewards
    max_rewards = 8 - fixed_rewards

    if min_rewards < 0:
        print "Error: fixed_rewards (%d) must be less than or equal to " \
              "guaranteeed_rewards (%d)" % (fixed_rewards, guarenteed_rewards)
        sys.exit(1)

    total_p = 0.0
    expected_v = 0.0
    for reward_count in xrange(min_rewards, max_rewards + 1):
        p = _reward_count_p(reward_count, min_rewards, max_rewards,
                            extend_percent)
        expected_v += p * reward_count
        # probability of getting @reward_count rewards that could be the
        # desired item
        print "P(C = %d) = %0.4f" % (reward_count, p)
        total_p += p
    # expected value for number of rewards that could be the desired item
    print "E(C) = %0.2f" % expected_v

    # math check, make sure all possibilities add up to 1, allowing for
    # some floating point precision loss.
    assert abs(total_p - 1.0) < .00001, "total = %f" % total_p

    p_at_least_one = quest_reward_p(reward_percent, min_rewards, max_rewards,
                                    extend_percent)
    expected = expected_v * reward_percent / 100.0

    print "P(N > 0) =", p_at_least_one
    print "E(N)     =", expected
