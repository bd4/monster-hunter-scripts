"""
Module for accessing the sqlite monster hunter db from
"""

import string

import sqlite3


class Quest(object):
    def __init__(self, quest_row, quest_rewards):
        self._row = quest_row
        self.rewards = quest_rewards

        self._template = string.Template(
           "$name ($hub $stars* $rank)"
         + "\n Goal: $goal"
         + "\n Sub : $sub_goal"
        )

        self.id = quest_row["_id"]
        self.name = quest_row["name"]
        self.stars = quest_row["stars"]
        self.hub = quest_row["hub"]
        self.goal = quest_row["goal"]
        self.sub_goal = quest_row["sub_goal"]
        self.rank = get_rank(self.hub, self.stars)

    def __unicode__(self):
        return self._template.substitute(self.__dict__)


def get_rank(hub, stars):
    if hub == "Caravan":
        if stars < 6:
            return "LR"
        elif stars < 10:
            return "HR"
        return "G"
    if hub == "Guild":
        if stars < 4:
            return "LR"
        elif stars < 8:
            return "HR"
        return "G"


class MHDB(object):
    def __init__(self, path, use_cache=True):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.use_cache = use_cache
        self.cache = {}

    def _get_memoized(self, key, query, *args):
        if self.use_cache:
            if key in self.cache:
                v = self.cache[key].get(args)
                if v is not None:
                    return v
            else:
                self.cache[key] = {}
        cursor = self.conn.execute(query, args)
        v = cursor.fetchall()
        if self.use_cache:
            self.cache[key][args] = v
        return v

    def get_item_names(self):
        v = self._get_memoized("item_names", """
            SELECT _id, name FROM items
            WHERE type IN ('Bone', 'Flesh', 'Sac/Fluid')
        """)
        return v

    def get_item(self, item_id):
        v = self._get_memoized("item", """
            SELECT * FROM items
            WHERE _id=?
        """, item_id)
        return v[0] if v else None

    def get_item_by_name(self, name):
        v = self._get_memoized("item", """
            SELECT * FROM items
            WHERE name=?
        """, name)
        return v[0] if v else None

    def search_item_name(self, term, item_type):
        """
        Search for items containing @term somewhere in the name. Returns
        list of matching items.

        Not memoized.
        """
        cursor = self.conn.execute("""
            SELECT * FROM items
            WHERE name LIKE ?
            AND type = ?
        """, ("%%%s%%" % term, item_type))
        return cursor.fetchall()

    def get_monster_by_name(self, name):
        v = self._get_memoized("monster", """
            SELECT * FROM monsters
            WHERE name=?
        """, name)
        return v[0] if v else None

    def get_monster(self, monster_id):
        v = self._get_memoized("monster", """
            SELECT * FROM monsters
            WHERE _id=?
        """, monster_id)
        return v[0] if v else None

    def get_quest(self, quest_id):
        v = self._get_memoized("quest", """
            SELECT * FROM quests
            WHERE _id=?
        """, quest_id)
        return v[0] if v else None

    def get_quest_rewards(self, quest_id):
        v = self._get_memoized("quest_rewards", """
            SELECT * FROM quest_rewards
            WHERE quest_id=?
        """, quest_id)
        return v

    def get_monster_rewards(self, monster_id, rank=None):
        q = """
            SELECT * FROM hunting_rewards
            WHERE monster_id=?
        """
        if rank is not None:
            q += "AND rank=?"
            v = self._get_memoized("monster_rewards", q, monster_id, rank)
        else:
            v = self._get_memoized("monster_rewards", q, monster_id)
        return v

    def get_quest_monsters(self, quest_id):
        v = self._get_memoized("quest_monsters", """
            SELECT monster_id FROM monster_to_quest
            WHERE quest_id=? AND unstable='no'
        """, quest_id)
        return v

    def get_item_quest_objects(self, item_id):
        """
        Get a list of quests that provide the specified item in quest
        reqards. Returns a list of quest objects, which encapsulate the
        quest details and the list of rewards.
        """
        cursor = self.conn.execute("""
            SELECT DISTINCT quest_id FROM quest_rewards
            WHERE item_id=?
        """, (item_id,))

        rows = cursor.fetchall()

        quests = []
        for r in rows:
            quest_row = self.get_quest(r["quest_id"])
            rewards_rows = self.get_quest_rewards(r["quest_id"])
            quests.append(Quest(quest_row, rewards_rows))

        return quests

    def get_item_monsters(self, item_id):
        v = self._get_memoized("item_monsters", """
            SELECT DISTINCT monster_id, rank FROM hunting_rewards
            WHERE item_id=?
        """, item_id)

        return v
