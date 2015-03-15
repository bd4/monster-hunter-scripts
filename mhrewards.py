#!/usr/bin/env python

from __future__ import print_function
import codecs

import mhdb
import mhprob


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)


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


def print_quests_and_rewards(db, item_row, out):
    """
    Get a list of the quests for acquiring a given item and the probability
    of getting the item, depending on cap or kill and luck skills.
    """
    item_id = item_row["_id"]
    quests = db.get_item_quest_objects(item_id)
    for q in quests:
        out.write(unicode(q) + "\n")
        out.write("  %20s" % "= Quest\n")
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
                print("WARNING: bad total p for %s = %d"
                      % (slot, total_reward_p[slot]), file=sys.stderr)

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

                out.write("  %20s %d %5.2f / 100" % (reward["reward_slot"],
                                                 reward["stack_size"],
                                                 evs[0]))
                out.write(" (%2d each)" % reward["percentage"])
                if len(totals) > 1:
                    out.write(" %s" % " ".join("%0.2f" % i for i in evs[1:]))
                out.write("\n")

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
            out.write("  %20s\n" % ("= " + monster["name"] + " " + q.rank))
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

                    out.write("  %20s %d %5.2f / 100" % (reward["condition"],
                                                         reward["stack_size"],
                                                         evs[0]))
                    out.write(" (%2d each)" % reward["percentage"])
                    if len(totals) > 1:
                        out.write(" " + " ".join("%0.2f" % i for i in evs[1:]))
                    out.write("\n")
            out.write("  %20s\n" % "= Totals")
            out.write("  %20s %s / 100\n" % ("Kill", _format_range(*kill_ev)))
            out.write("  %20s %s / 100\n" % ("Cap", _format_range(*cap_ev)))
            out.write("  %20s %5.2f / 100\n" % ("Shiny", shiny_ev))
            out.write("\n")


if __name__ == '__main__':
    import sys
    import os
    import os.path

    if len(sys.argv) != 2:
        print("Usage: %s 'item name'" % sys.argv[0])
        sys.exit(os.EX_USAGE)

    item_name = sys.argv[1]

    out = get_utf8_writer(sys.stdout)
    err_out = get_utf8_writer(sys.stderr)

    # TODO: doesn't work if script is symlinked
    db_path = os.path.dirname(sys.argv[0])
    db_path = os.path.join(db_path, "db", "mh4u.db")
    db = mhdb.MHDB(db_path)

    item_row = find_item(db, item_name, err_out)
    if item_row is None:
        sys.exit(os.EX_DATAERR)
    print_quests_and_rewards(db, item_row, out)
