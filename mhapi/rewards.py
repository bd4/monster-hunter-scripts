"""
Calculate expected values for monster hunter items and find the best quests
and hunts for getting an item with specified skills.
"""

from __future__ import print_function
from collections import OrderedDict

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
    def __init__(self, item_id, quest):
        self.item_id = item_id
        self.quest = quest

        self.fixed_rewards = dict(A=0, B=0, Sub=0)
        self.total_reward_p = dict(A=0, B=0, Sub=0)

        # dict mapping slot name to list of lists
        # of the form (slot, list_of_expected_values).
        self.slot_rewards = dict(A=[], B=[], Sub=[])
        self.total_expected_values = [0, 0, 0]

        self._set_rewards(quest.rewards)

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
        if self.condition == "Tail Carve":
            self.skill = SKILL_CARVING
            self.cap = True
            self.kill = True
            counts = [
                1 + stats.carve_delta_expected_c(skill)
                for skill in xrange(stats.CARVING_SKILL_PRO,
                                    stats.CARVING_SKILL_GOD+1)
            ]
        elif self.condition == "Body Carve (Apparent Death)":
            # Gypceros fake death. Assume one carve, it's dangerous to try
            # for two.
            counts = [1]
            self.cap = True
            self.kill = True
        elif self.condition == "Body Carve":
            self.skill = SKILL_CARVING
            self.cap = False
            self.kill = True
            counts = [
                3 + stats.carve_delta_expected_c(skill)
                for skill in xrange(stats.CARVING_SKILL_PRO,
                                    stats.CARVING_SKILL_GOD+1)
            ]
        elif self.condition.startswith("Body Carve (KO"):
            # Kelbi
            self.skill = SKILL_CARVING
            self.cap = True
            self.kill = True
            counts = [
                1 + stats.carve_delta_expected_c(skill)
                for skill in xrange(stats.CARVING_SKILL_PRO,
                                    stats.CARVING_SKILL_GOD+1)
            ]
        elif "Carve" in self.condition:
            # Mouth Carve: Dah'ren Mohran
            # Upper Body Carve: Dalamadur
            # Lower Body Carve: Dalamadur
            # Head Carve: Dalamadur
            # TODO: separate these out, some have >3 carves, not sure
            # about others
            self.skill = SKILL_CARVING
            self.cap = False
            self.kill = True
            counts = [
                3 + stats.carve_delta_expected_c(skill)
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
        elif self.condition == "Virus Reward":
            # TODO: not sure how these work
            # Assume 1 always for easy comparison. My guess is that you
            # always get 1 from frenzied monsters and have a chance at 2+.
            # The question is do the cances of getting more than one
            # change depending on the monster, e.g. do Apex monsters
            # give more rewards or just higher rarity crystals?
            self.cap = True
            self.kill = True
            counts = [1]
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
            elif self.condition in ("Bug-Catching Back", "Mining Back",
                                    "Mining Ore", "Mining Scale"):
                # TODO: it's easy to get more than one here, would be nice
                # to separate these out like shinys.
                self.cap = True
                self.kill = True
            else:
                raise ValueError("Unknown condition: '%s'"
                                 % self.condition)

        evs = [(i *  self.stack_size * self.percentage) for i in counts]
        return evs


class RankAndSkills(object):
    """
    Helper to track the best strategy with a given set of skills and hunter
    rank.
    """
    def __init__(self, rank="G",
                 luck_skill=stats.LUCK_SKILL_NONE,
                 cap_skill=stats.CAP_SKILL_NONE,
                 carving_skill=stats.CARVING_SKILL_NONE):
        self.rank = rank
        self.luck_skill = luck_skill
        self.cap_skill = cap_skill
        self.carving_skill = carving_skill
        self.best = None

    def add_hunt_item(self, hunt_item):
        if self.rank == "LR" and hunt_item.monster_rank != "LR":
            return False
        if self.rank == "HR" and hunt_item.monster_rank == "G":
            return False

        strat = hunt_item.get_best_strategy(cap_skill=self.cap_skill,
                                            carving_skill=self.carving_skill)
        if self.best is None:
            self.best = strat
            return True
        elif strat > self.best:
            self.best = strat
            return True
        return False

    def add_quest_item(self, quest_item):
        if self.rank == "LR" and quest_item.rank != "LR":
            return False
        if self.rank == "HR" and quest_item.monster_rank == "G":
            return False


class HuntItemStrategy(object):
    """
    Encapsulate a specific strategy for getting an item, including kill vs
    cap and skills.
    """
    def __init__(self, hunt_item, strat, cap_skill=None, carving_skill=None):
        self.hunt_item = hunt_item
        self.strat = strat
        self.cap_skill = cap_skill
        self.carving_skill = carving_skill

        self.ev = self.hunt_item.expected_value(strat,
                                                carving_skill=carving_skill,
                                                cap_skill=cap_skill)

    def print(self, out):
        out.write("%s %s %s (%5.2f)\n" %
                  (self.hunt_item.monster_name,
                   self.hunt_item.monster_rank,
                   self.strat, self.ev))

    def is_same_strat(self, other):
        return (self.hunt_item.monster_name == other.hunt_item.monster_name
            and self.hunt_item.monster_rank == other.hunt_item.monster_rank
            and self.strat == other.strat
            and self.ev == other.ev)

    def __cmp__(self, other):
        return cmp(self.ev, other.ev)


class HuntItemExpectedValue(object):
    """
    Calculate the expected value for an item from hunting a monster, including
    all ways of getting the item.

    @param item_id: database id of item
    @param hunt_rewards: list of rows from hunt_rewards table for a single
                         monster and rank
    """
    def __init__(self, item_id, monster_name, monster_rank, hunt_rewards):
        self.item_id = item_id
        self.monster_name = monster_name
        self.monster_rank = monster_rank
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

    def get_best_strategy(self, cap_skill=stats.CAP_SKILL_NONE,
                          carving_skill=stats.CARVING_SKILL_NONE):
        kill = HuntItemStrategy(self, STRAT_KILL,
                                cap_skill=cap_skill,
                                carving_skill=carving_skill)
        cap =  HuntItemStrategy(self, STRAT_CAP,
                                cap_skill=cap_skill,
                                carving_skill=carving_skill)
        if kill > cap:
            return kill
        else:
            return cap

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


class ItemRewards(object):
    def __init__(self, db, item_row):
        self.db = db
        self.item_row = item_row
        self.item_id = item_row["_id"]

        self. skill_sets = OrderedDict([
            ("No skills", RankAndSkills("G")),
            ("Capture God", RankAndSkills("G", cap_skill=stats.CAP_SKILL_GOD)),
            ("Carving God",
               RankAndSkills("G", carving_skill=stats.CARVING_SKILL_GOD)),
            ("Great Luck",
               RankAndSkills("G", luck_skill=stats.LUCK_SKILL_GREAT)),
            ("Low  Rank", RankAndSkills("LR")),
            ("High Rank", RankAndSkills("HR")),
        ])

        self._hunt_items = OrderedDict()
        self._quest_items = OrderedDict()

        self._find_hunt_items()
        self._find_quest_items()

    def _find_hunt_items(self):
        monsters = self.db.get_item_monsters(self.item_id)

        for m in monsters:
            mid = m["monster_id"]
            rank = m["rank"]
            monster = self.db.get_monster(mid)
            reward_rows = self.db.get_monster_rewards(mid, rank)
            hunt_item = HuntItemExpectedValue(self.item_id, monster["name"],
                                              rank, reward_rows)
            key = (mid, rank)
            self._hunt_items[key] = hunt_item

            for s in self.skill_sets.values():
                s.add_hunt_item(hunt_item)

    def get_hunt_item(self, monster_id, monster_rank):
        key = (monster_id, monster_rank)
        return self._hunt_items.get(key)

    def _find_quest_items(self):
        """
        Get a list of the quests for acquiring a given item and the probability
        of getting the item, depending on cap or kill and luck skills.
        """
        quests = self.db.get_item_quest_objects(self.item_id)
        if not quests:
            return
        for q in quests:
            quest_item = QuestItemExpectedValue(self.item_id, q)
            self._quest_items[q.id] = quest_item

    def print_monsters(self, out):
        for hunt_item in self._hunt_items.itervalues():
            out.write("%s %s\n"
                      % (hunt_item.monster_name, hunt_item.monster_rank))
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

    def print_recommended_hunts(self, out):
        out.write("*** Poogie Recommends ***\n")
        no_skill_best = self.skill_sets["No skills"].best
        for name, skill_set in self.skill_sets.iteritems():
            if skill_set.best is None:
                # Don't print out a rank with no options
                continue
            if (name != "No skills"
            and skill_set.best.is_same_strat(no_skill_best)):
                # Don't print out a skill set/rank that doesn't differ from
                # no skills any rank
                continue
            out.write("[%-11s] " % name)
            skill_set.best.print(out)
        out.write("\n")

    def print_quests(self, out):
        """
        Get a list of the quests for acquiring a given item and the probability
        of getting the item, depending on cap or kill and luck skills.
        """
        for quest_item in self._quest_items.itervalues():
            out.write(unicode(quest_item.quest) + "\n")
            out.write("  %20s" % "= Quest\n")

            quest_item.check_totals(out)
            quest_item.print(out, indent=2)

            quest_monsters = self.db.get_quest_monsters(quest_item.quest.id)

            quest_ev = quest_item.expected_value()

            cap_ev = [quest_ev, quest_ev]
            kill_ev = [quest_ev, quest_ev]
            shiny_ev = 0
            for m in quest_monsters:
                mid = m["monster_id"]
                hunt_item = self.get_hunt_item(mid, quest_item.quest.rank)

                kill_ev[0] += hunt_item.expected_value(STRAT_KILL)
                kill_ev[1] += hunt_item.expected_value(STRAT_KILL,
                                          carving_skill=stats.CARVING_SKILL_GOD)
                cap_ev[0] += hunt_item.expected_value(STRAT_CAP)
                cap_ev[1] += hunt_item.expected_value(STRAT_CAP,
                                              cap_skill=stats.CAP_SKILL_GOD)
                shiny_ev = hunt_item.expected_value(STRAT_SHINY)

                if kill_ev[0] == 0 and cap_ev[0] == 0 and shiny_ev == 0:
                    continue

                out.write("  %20s\n"
                          % ("= " + hunt_item.monster_name
                             + " " + hunt_item.monster_rank))

                hunt_item.print(out, indent=2)

                out.write("  %20s\n" % "= Totals")
                out.write("  %20s %s / 100\n"
                          % ("Kill", _format_range(*kill_ev)))
                out.write("  %20s %s / 100\n"
                          % ("Cap", _format_range(*cap_ev)))
                if shiny_ev:
                    out.write("  %20s %5.2f / 100\n" % ("Shiny", shiny_ev))
                out.write("\n")
