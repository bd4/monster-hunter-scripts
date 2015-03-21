"""
Calculate expected values for monster hunter items and find the best quests
and hunts for getting an item with specified skills.
"""

from __future__ import print_function

from mhapi.db import MHDB
from mhapi import stats

SKILL_CARVING = "carving"
SKILL_CAP = "cap"
SKILL_NONE = None

STRAT_KILL = "kill"
STRAT_CAP = "cap"
STRAT_SHINY = "shiny"


def _format_range(min_v, max_v):
    if min_v == max_v:
        return "%5.2f" % min_v
    else:
        return "%5.2f to %5.2f" % (min_v, max_v)


def find_item(db, item_name, err_out):
    item_row = db.get_item_by_name(item_name)
    if item_row is None:
        print("Item '%s' not found. Listing partial matches:" % item_name,
              file=err_out)
        terms = item_name.split()
        for term in terms:
            if len(term) < 2:
                # single char terms aren't very useful, too many results
                continue
            print("= Matching term '%s'" % term, file=err_out)
            rows = db.search_item_name(term, "Flesh")
            for row in rows:
                print(" ", row["name"], file=err_out)
        return None
    return item_row


class QuestReward(object):
    def __init__(self, reward, fixed_rewards):
        self.slot = reward["reward_slot"]
        self.stack_size = reward["stack_size"]
        self.percentage = reward["percentage"]
        self.item_id = reward["item_id"]

        self.fixed_rewards = fixed_rewards[self.slot]

        self.skill_delta = 0
        self.evs = self._calculate_ev()

    def expected_value(self, luck_skill=stats.LUCK_SKILL_NONE,
                       cap_skill=None, carving_skill=None):
        return self.evs[luck_skill]

    def expected_values(self):
        return self.evs

    def _calculate_ev(self):
        if self.percentage == 100:
            # fixed reward, always one draw regardless of luck skill
            evs = [1 * self.percentage * self.stack_size] * 3
            self.skill_delta = 0
        else:
            # variable reward, expected number of draws depends on luck skill
            counts = [stats.quest_reward_expected_c(self.slot, skill)
                      for skill in xrange(stats.LUCK_SKILL_NONE,
                                          stats.LUCK_SKILL_GREAT+1)]


            evs = [((count - self.fixed_rewards)
                    *  self.stack_size * self.percentage)
                   for count in counts]
            self.skill_delta = evs[-1] - evs[0]
        return evs

    def print(self, out, indent=2):
        out.write("%s%20s %d %5.2f / 100"
                  % (" " * indent, self.slot, self.stack_size,
                     self.evs[0]))
        out.write(" (%2d each)" % self.percentage)
        if self.skill_delta:
            out.write(" %s" % " ".join("%0.2f" % i for i in self.evs[1:]))
        out.write("\n")


class QuestItemExpectedValue(object):
    """
    Calculate the expected value for an item across all rewards for a quest.

    @param item_id: database id of item
    @param quest_rewards: list of rows from quest_rewards table for a single
                          quest
    """
    def __init__(self, item_id, quest_rewards):
        self.item_id = item_id

        self.fixed_rewards = dict(A=0, B=0, Sub=0)
        self.total_reward_p = dict(A=0, B=0, Sub=0)

        # dict mapping slot name to list of lists
        # of the form (slot, list_of_expected_values).
        self.slot_rewards = dict(A=[], B=[], Sub=[])
        self.total_expected_values = [0, 0, 0]

        self._set_rewards(quest_rewards)

    def is_sub(self):
        """Item is available from sub quest"""
        return len(self.slot_rewards["Sub"]) > 0

    def is_main(self):
        """Item is available from main quest"""
        return (len(self.slot_rewards["A"]) > 0
                or len(self.slot_rewards["B"]) > 0)

    def expected_value(self, luck_skill=stats.LUCK_SKILL_NONE,
                       cap_skill=None, carving_skill=None):
        return self.total_expected_values[luck_skill]

    def check_totals(self, outfile):
        # sanity check values from the db
        for slot in self.total_reward_p.keys():
            if self.total_reward_p[slot] not in (0, 100):
                print("WARNING: bad total p for %s = %d"
                      % (slot, self.total_reward_p[slot]), file=outfile)

    def _set_rewards(self, rewards):
        # preprocessing step - figure out how many fixed rewards there
        # are, which we need to know in order to figure out how many
        # chances there are to get other rewards.
        for reward in rewards:
            slot = reward["reward_slot"]
            if reward["percentage"] == 100:
                self.fixed_rewards[slot] += 1
            else:
                self.total_reward_p[slot] += reward["percentage"]

        for reward in rewards:
            if reward["item_id"] != self.item_id:
                continue
            self._add_reward(reward)

    def _add_reward(self, r):
        reward = QuestReward(r, self.fixed_rewards)

        self.slot_rewards[reward.slot].append(reward)
        evs = reward.expected_values()
        for i in xrange(len(evs)):
            self.total_expected_values[i] += evs[i]

    def print(self, out, indent=2):
        for slot in ("A", "B", "Sub"):
            for qr in self.slot_rewards[slot]:
                qr.print(out, indent)


class HuntReward(object):
    def __init__(self, reward):
        self.condition = reward["condition"]
        self.stack_size = reward["stack_size"]
        self.percentage = reward["percentage"]
        self.item_id = reward["item_id"]

        self.cap = False
        self.kill = False
        self.shiny = False
        self.skill = SKILL_NONE

        self.evs = self._calculate_evs()

    def expected_value(self, strategy, luck_skill=None,
                       cap_skill=stats.CAP_SKILL_NONE,
                       carving_skill=stats.CARVING_SKILL_NONE):
        if strategy == STRAT_CAP:
            if not self.cap:
                return 0
        elif strategy == STRAT_KILL:
            if not self.kill:
                return 0
        elif strategy == STRAT_SHINY:
            if not self.shiny:
                return 0
        else:
            raise ValueError("strategy must be STRAT_CAP or STRAT_KILL")

        if self.skill == SKILL_CAP:
            return self.evs[cap_skill]
        elif self.skill == SKILL_CARVING:
            return self.evs[carving_skill]
        else:
            return self.evs[0]

    def print(self, out, indent=2):
        out.write("%s%20s %d %5.2f / 100"
                  % (" " * indent, self.condition,
                     self.stack_size, self.evs[0]))
        out.write(" (%2d each)" % self.percentage)
        if len(self.evs) > 1:
            out.write(" " + " ".join("%0.2f" % i for i in self.evs[1:]))
        out.write("\n")

    def _calculate_evs(self):
        if self.condition == "Body Carve":
            self.skill = SKILL_CARVING
            self.cap = False
            self.kill = True
            counts = [
                3 + stats.carve_delta_expected_c(skill)
                for skill in xrange(stats.CARVING_SKILL_PRO,
                                    stats.CARVING_SKILL_GOD+1)
            ]
        elif self.condition == "Body Carve (Apparent Death)":
            # assume one carve, it's dangerous to try for two
            counts = [1]
            self.cap = True
            self.kill = True
        elif self.condition == "Tail Carve":
            self.skill = SKILL_CARVING
            self.cap = True
            self.kill = True
            counts = [
                1 + stats.carve_delta_expected_c(skill)
                for skill in xrange(stats.CARVING_SKILL_PRO,
                                    stats.CARVING_SKILL_GOD+1)
            ]
        elif self.condition == "Capture":
            self.skill = SKILL_CAP
            self.cap = True
            self.kill = False
            counts = [
                stats.capture_reward_expected_c(skill)
                for skill in xrange(stats.CAP_SKILL_NONE,
                                    stats.CAP_SKILL_GOD+1)
            ]
        else:
            counts = [1]
            if self.condition.startswith("Shiny"):
                # don't include shiny in total, makes it easier to
                # calculate separately since shinys are variable by
                # monster
                self.cap = False
                self.kill = False
                self.shiny = True
            elif self.condition.startswith("Break"):
                self.cap = True
                self.kill = True
            else:
                raise ValueError("Unknown condition: '%s'"
                                 % self.condition)

        evs = [(i *  self.stack_size * self.percentage) for i in counts]
        return evs


class HuntItemExpectedValue(object):
    """
    Calculate the expected value for an item from hunting a monster, including
    all ways of getting the item.

    @param item_id: database id of item
    @param hunt_rewards: list of rows from hunt_rewards table for a single
                         monster and rank
    """

    def __init__(self, item_id, hunt_rewards):
        self.item_id = item_id
        self.matching_rewards = []
        self._set_rewards(hunt_rewards)

    def expected_value(self, strategy, luck_skill=None,
                       cap_skill=stats.CAP_SKILL_NONE,
                       carving_skill=stats.CARVING_SKILL_NONE):
        ev = 0
        for reward in self.matching_rewards:
            ev += reward.expected_value(strategy,
                                        luck_skill=luck_skill,
                                        cap_skill=cap_skill,
                                        carving_skill=carving_skill)
        return ev

    def print(self, out, indent=2):
        for hr in self.matching_rewards:
            hr.print(out, indent)

    def _set_rewards(self, rewards):
        for reward in rewards:
            if reward["item_id"] != self.item_id:
                continue
            self._add_reward(reward)

    def _add_reward(self, r):
        reward = HuntReward(r)
        self.matching_rewards.append(reward)


def print_monsters_and_rewards(db, item_row, out):
    item_id = item_row["_id"]
    monsters = db.get_item_monsters(item_id)
    for m in monsters:
        mid = m["monster_id"]
        rank = m["rank"]
        monster = db.get_monster(mid)
        reward_rows = db.get_monster_rewards(mid, rank)
        hunt_item = HuntItemExpectedValue(item_id, reward_rows)

        out.write("%s %s\n" % (monster["name"], rank))
        hunt_item.print(out, indent=2)

        kill_ev = [0, 0]
        kill_ev[0] = hunt_item.expected_value(STRAT_KILL)
        kill_ev[1] = hunt_item.expected_value(STRAT_KILL,
                                      carving_skill=stats.CARVING_SKILL_GOD)
        cap_ev = [0, 0]
        cap_ev[0] = hunt_item.expected_value(STRAT_CAP)
        cap_ev[1] = hunt_item.expected_value(STRAT_CAP,
                                      cap_skill=stats.CAP_SKILL_GOD)
        shiny_ev = hunt_item.expected_value(STRAT_SHINY)
        out.write("  %20s\n" % "= Totals")
        out.write("  %20s %s / 100\n"
                  % ("Kill", _format_range(*kill_ev)))
        out.write("  %20s %s / 100\n"
                  % ("Cap", _format_range(*cap_ev)))
        if shiny_ev:
            out.write("  %20s %5.2f / 100\n" % ("Shiny", shiny_ev))
        out.write("\n")


def print_quests_and_rewards(db, item_row, out):
    """
    Get a list of the quests for acquiring a given item and the probability
    of getting the item, depending on cap or kill and luck skills.
    """
    item_id = item_row["_id"]
    quests = db.get_item_quest_objects(item_id)
    print_monsters_and_rewards(db, item_row, out)
    if not quests:
        return
    for q in quests:
        out.write(unicode(q) + "\n")
        out.write("  %20s" % "= Quest\n")

        quest = QuestItemExpectedValue(item_id, q._rewards)
        quest.check_totals(out)
        quest.print(out, indent=2)

        monsters = db.get_quest_monsters(q.id)

        quest_ev = quest.expected_value()

        cap_ev = [quest_ev, quest_ev]
        kill_ev = [quest_ev, quest_ev]
        shiny_ev = 0
        for m in monsters:
            mid = m["monster_id"]
            monster = db.get_monster(mid)
            has_item = False
            reward_rows = db.get_monster_rewards(mid, q.rank)
            hunt_item = HuntItemExpectedValue(item_id, reward_rows)

            kill_ev[0] += hunt_item.expected_value(STRAT_KILL)
            kill_ev[1] += hunt_item.expected_value(STRAT_KILL,
                                      carving_skill=stats.CARVING_SKILL_GOD)
            cap_ev[0] += hunt_item.expected_value(STRAT_CAP)
            cap_ev[1] += hunt_item.expected_value(STRAT_CAP,
                                          cap_skill=stats.CAP_SKILL_GOD)
            shiny_ev = hunt_item.expected_value(STRAT_SHINY)

            if kill_ev[0] == 0 and cap_ev[0] == 0 and shiny_ev == 0:
                continue

            out.write("  %20s\n" % ("= " + monster["name"] + " " + q.rank))

            hunt_item.print(out, indent=2)

            out.write("  %20s\n" % "= Totals")
            out.write("  %20s %s / 100\n"
                      % ("Kill", _format_range(*kill_ev)))
            out.write("  %20s %s / 100\n"
                      % ("Cap", _format_range(*cap_ev)))
            if shiny_ev:
                out.write("  %20s %5.2f / 100\n" % ("Shiny", shiny_ev))
            out.write("\n")

