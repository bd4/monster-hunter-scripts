#!/usr/bin/env python

import mhdb
import mhprob

db = mhdb.MHDB("mh4u.db")


def _format_range(min_v, max_v):
    if min_v == max_v:
        return "%5.2f%%" % min_v
    else:
        return "%5.2f%% to %5.2f%%" % (min_v, max_v)


def get_quests(item_name):
    """
    Get a list of the quests for acquiring a given item and the probability
    of getting the item, depending on cap or kill and luck skills.
    """
    item_row = db.get_item_by_name(item_name)
    item_id = item_row["_id"]
    quests = db.get_item_quests(item_id)
    for q in quests:
        print q
        print "  %20s" % "= Quest"
        quest_ev = 0
        sub_used = False

        fixed_other_rewards = dict(A=0, B=0, Sub=0)
        total_reward_p = dict(A=0, B=0, Sub=0)
        for reward in q._rewards:
            slot = reward["reward_slot"]
            #reward_item_row = db.get_item(reward["item_id"])
            #print slot, reward_item_row["name"], reward["percentage"]
            if reward["percentage"] == 100:
                if reward["item_id"] != item_id:
                    fixed_other_rewards[slot] += 1
            else:
                total_reward_p[slot] += reward["percentage"]

        # sanity check values from the db
        for slot in total_reward_p.keys():
            if total_reward_p[slot] not in (0, 100):
                print "WARNING: bad total p for %s = %d" \
                        % (slot, total_reward_p[slot])

        for reward in q._rewards:
            slot = reward["reward_slot"]
            #reward_item_row = db.get_item(reward["item_id"])
            #print slot, reward_item_row["name"], reward["percentage"]
            if reward["item_id"] == item_id:
                totals = [mhprob.quest_reward_expected_c(slot, skill)
                          for skill in xrange(mhprob.LUCK_SKILL_NONE,
                                              mhprob.LUCK_SKILL_GREAT+1)]


                evs = [((i - fixed_other_rewards[slot])
                        *  reward["stack_size"] * reward["percentage"])
                       for i in totals]

                print "  %20s %d %5.2f%%" % (reward["reward_slot"],
                                             reward["stack_size"],
                                             evs[0]),
                print " (%2d%% each)" % reward["percentage"],
                if len(totals) > 1:
                    print " %s" % " ".join("%0.2f" % i for i in evs[1:]),
                print

                quest_ev += evs[0]
                if reward["reward_slot"] == "Sub":
                    sub_used = True
        monsters = db.get_quest_monsters(q.id)

        cap_ev = [quest_ev, quest_ev]
        kill_ev = [quest_ev, quest_ev]
        shiny_ev = 0
        for m in monsters:
            mid = m["monster_id"]
            monster = db.get_monster(mid)
            print "  %20s" % ("= " + monster["name"] + " " + q.rank)
            rewards = db.get_monster_rewards(mid, q.rank)
            for reward in rewards:
                cap = kill = shiny = False
                if reward["item_id"] == item_id:
                    if reward["condition"] == "Body Carve":
                        totals = [
                            3 + mhprob.carve_delta_expected_c(skill)
                            for skill in xrange(mhprob.CARVING_SKILL_PRO,
                                                mhprob.CARVING_SKILL_GOD+1)
                        ]
                        cap = False
                        kill = True
                    elif reward["condition"] == "Tail Carve":
                        totals = [
                            1 + mhprob.carve_delta_expected_c(skill)
                            for skill in xrange(mhprob.CARVING_SKILL_PRO,
                                                mhprob.CARVING_SKILL_GOD+1)
                        ]
                        cap = kill = True
                    elif reward["condition"] == "Capture":
                        totals = [
                            mhprob.capture_reward_expected_c(skill)
                            for skill in xrange(mhprob.CAP_SKILL_NONE,
                                                mhprob.CAP_SKILL_GOD+1)
                        ]
                        cap = True
                        kill = False
                    else:
                        totals = [1]
                        # don't include Shiny in ev calculations
                        if reward["condition"].startswith("Shiny"):
                            cap = kill = False
                            shiny = True
                        elif reward["condition"].startswith("Break"):
                            cap = kill = True
                        else:
                            raise ValueError("Unknown condition: "
                                             + reward["condition"])

                    evs = [i *  reward["stack_size"] * reward["percentage"]
                           for i in totals]
                    if cap:
                        cap_ev[0] += evs[0]
                        cap_ev[1] += evs[-1]
                    if kill:
                        kill_ev[0] += evs[0]
                        kill_ev[1] += evs[-1]
                    if shiny:
                        shiny_ev += evs[0]

                    print "  %20s %d %5.2f%%" % (reward["condition"],
                                                 reward["stack_size"],
                                                 evs[0]),
                    print " (%2d%% each)" % reward["percentage"],
                    if len(totals) > 1:
                        print " %s" % " ".join("%0.2f" % i for i in evs[1:]),
                    print
            print "  %20s" % "= Totals"
            print "  %20s %s" % \
                ("Kill", _format_range(*kill_ev))
            print "  %20s %s" % \
                ("Cap", _format_range(*cap_ev))
            print "  %20s %5.2f%%" % ("Shiny", shiny_ev)
            print


if __name__ == '__main__':
    import sys

    get_quests(sys.argv[1])
