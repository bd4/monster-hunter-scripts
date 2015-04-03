#!/usr/bin/env python

import os.path
import codecs

import _pathfix

from mhapi.db import MHDB, Quest


RANK_NUM = dict(LR=0, HR=1, G=2)
RANK_NAME = ["LR", "HR", "G"]


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)


def set_quest_ranks(db):
    quests = db.get_quests()
    for quest in quests:
        if not quest["name"]:
            assert quest["hub"] == "Event"
            print "WARN: skipping non localized event quest: %d" % quest["_id"]
            continue
        set_quest_rank(db, quest)


def set_quest_rank(db, quest_row):
    quest_id = quest_row["_id"]
    hub = quest_row["hub"]
    stars = quest_row["stars"]
    rank_stars_guess = guess_rank(hub, stars)
    if isinstance(rank_stars_guess, tuple):
        rewards = db.get_quest_rewards(quest_id)
        rank = guess_quest_rank_from_rewards(db, rewards)
        if rank is None:
            print "WARN: quest '%s' has no flesh rewards, assuming lower rank"\
                % (quest_row["name"].encode("utf8"),)
            rank = rank_stars_guess[0]
        elif rank not in rank_stars_guess:
            print "ERROR: quest '%s' reward guess '%s' not in stars guess '%s'"\
             % (quest_row["name"], rank, rank_stars_guess)
    else:
        rank = rank_stars_guess

    assert rank in "LR HR G".split()

    quest = Quest(quest_row)
    quest.rank = rank
    print quest.one_line_u()
    cur = db.cursor()
    cur.execute("UPDATE quests SET rank=? WHERE _id=?", (rank, quest_id))


def guess_rank(hub, stars):
    if hub == "Caravan":
        # 6 * is actually a mix of LR and HR,
        # and 10 * is mix of HR and G
        if stars < 6:
            return "LR"
        elif stars == 6:
            return ("LR", "HR")
        elif stars == 10:
            return ("HR", "G")
        return "HR"
    if hub in ("Guild", "Event"):
        if stars < 4:
            return "LR"
        elif stars < 8:
            return "HR"
        return "G"
    else:
        raise ValueError("Unknown hub '%s'" % hub)


def guess_quest_rank_from_rewards(db, rewards_rows):
    max_min_rank = RANK_NUM["LR"]
    has_flesh_rewards = False
    for reward in rewards_rows:
        # for each flesh quest reward, see if it's only available from
        # HR or G monsters
        item = db.get_item(reward["item_id"])
        if item["type"] not in ("Flesh", "Sac/Fluid"):
            continue
        has_flesh_rewards = True
        monsters = db.get_item_monsters(reward["item_id"])
        min_rank = 3
        for m in monsters:
            rank = m["rank"]
            if RANK_NUM[rank] < min_rank:
                min_rank = RANK_NUM[rank]
        if min_rank > max_min_rank and min_rank != 3:
            max_min_rank = min_rank
    if not has_flesh_rewards:
        # Can't make useful guess from the rewards
        return None
    return RANK_NAME[max_min_rank]


if __name__ == '__main__':
    from _pathfix import db_path
    db_file = os.path.join(db_path, "mh4u.db")
    db = MHDB(db_file)

    import sys
    sys.stdout = get_utf8_writer(sys.stdout)
    sys.stderr = get_utf8_writer(sys.stderr)
    set_quest_ranks(db)
    db.commit()
    db.close()
