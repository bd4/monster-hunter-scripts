"""
Utility functions for calculating monster hunter related statistics.
"""

CAP_SKILL_NONE = 0
CAP_SKILL_EXPERT = 1
CAP_SKILL_MASTER = 2
CAP_SKILL_GOD = 3

LUCK_SKILL_NONE = 0
LUCK_SKILL_GOOD = 1
LUCK_SKILL_GREAT = 2
LUCK_SKILL_AMAZING = 3

QUEST_A = "A"
QUEST_B = "B"
QUEST_SUB = "Sub"

# In mhgen db, I think you get exactly one of each, but not sure
QUEST_C = "C"
QUEST_D = "D"

CARVING_SKILL_NONE = 0
CARVING_SKILL_PRO = 0 # prevent knockbacks but no extra carves
CARVING_SKILL_FELYNE_LOW = 1
CARVING_SKILL_FELYNE_HI = 2
CARVING_SKILL_CELEBRITY = 3
CARVING_SKILL_GOD = 4


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


def reward_expected_c(min_rewards, max_rewards, extend_percent):
    """
    Expected value for number of rewards, if @min_rewards are gauranteed
    and there is an @extend_percent chance of getting one more each time
    with at most @max_rewards.
    """
    total_p = 0.0
    expected_attempts = 0.0
    for reward_count in xrange(min_rewards, max_rewards + 1):
        p = _reward_count_p(reward_count, min_rewards, max_rewards,
                            extend_percent)
        expected_attempts += p * reward_count
        #print "P(C = %d) = %0.4f" % (reward_count, p)
        total_p += p
    assert abs(total_p - 1.0) < .00001, "total = %f" % total_p
    return expected_attempts


def quest_reward_expected_c(line=QUEST_A, luck_skill=LUCK_SKILL_NONE):
    """
    Expected number of rewards from specified quest line with given skills.

    Note: if the quest has fixed rewards that aren't the desired item, it will
    reduce the expected count for the desired item. Just subtract the number
    of fixed items from the output to get the actual value.
    """
    # TODO: verify this
    if line in (QUEST_C, QUEST_D):
        return 1.0

    if luck_skill == LUCK_SKILL_NONE:
        extend_p = 22 * 100.0 / 32
    elif luck_skill == LUCK_SKILL_GOOD:
        extend_p = 25 * 100.0 / 32
    elif luck_skill == LUCK_SKILL_GREAT:
        extend_p = 28 * 100.0 / 32
    elif luck_skill == LUCK_SKILL_AMAZING:
        extend_p = 31 * 100.0 / 32
    else:
        raise ValueError()

    # TODO: not sure if these are correct for 4U, but I've
    # heard that 3U had 4/2 gaurenteed for A/B.
    if line == QUEST_A:
        min_c = 4
        max_c = 8
    elif line == QUEST_B:
        min_c = 2
        max_c = 8
    elif line == QUEST_SUB:
        min_c = 1
        max_c = 4
        # luck skill does not work on sub quests, see
        # https://www.reddit.com/r/MonsterHunter/comments/307sda/fate_doesnt_appear_to_do_anything_to_subquest/
        extend_p = 22 * 100.0 / 32
    else:
        raise ValueError()

    return reward_expected_c(min_c, max_c, extend_p)


def capture_reward_expected_c(cap_skill=CAP_SKILL_NONE):
    """
    Expected value for number of capture rewards given the specified
    capture skill (none by default).
    """
    if cap_skill == CAP_SKILL_NONE:
        min_c = 2
        max_c = 3
        extend_p = 22 * 100.0 / 32
    elif cap_skill == CAP_SKILL_EXPERT:
        return 3
    elif cap_skill == CAP_SKILL_MASTER:
        min_c = 3
        max_c = 4
        extend_p = 22 * 100.0 / 32
    elif cap_skill == CAP_SKILL_GOD:
        return 4
    else:
        raise ValueError()
    return reward_expected_c(min_c, max_c, extend_p)


def carve_delta_expected_c(carve_skill):
    """
    Expected value for the number of extra carves with the given skill.

    Word on the street is that since Tri the felyne skills do not stack with
    the armor skills, i.e. if you have Carving Celebrity plus you get at
    least one extra carves and the felyne skills do nothing.
    """
    if carve_skill == CARVING_SKILL_CELEBRITY:
        # Description: Increases the number of carving chances by one and prevents knockbacks while carving.
        return 1
    elif carve_skill == CARVING_SKILL_GOD:
        # Description: Increases the number of carving chances by one (maybe more) and prevents knockbacks while carving.
        # From ShadyFigure on reddit, extend chance is 25 / 32
        min_c = 1
        max_c = 2
        extend_p = 25 * 100.0 / 32
    elif carve_skill == CARVING_SKILL_FELYNE_LOW:
        min_c = 0
        max_c = 1
        extend_p = 25
    elif carve_skill == CARVING_SKILL_FELYNE_HI:
        min_c = 0
        max_c = 1
        extend_p = 50
    elif carve_skill in (CARVING_SKILL_NONE, CARVING_SKILL_PRO):
        # Description: Prevents knockbacks from attacks while carving.
        return 0
    else:
        raise ValueError()
    return reward_expected_c(min_c, max_c, extend_p)

