"""
Module for accessing the sqlite monster hunter db from
"""

import sqlite3

from mhapi import model

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

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()

    def get_item_names(self, item_types):
        item_types.sort()
        placeholders = ", ".join(["?"] * len(item_types))
        v = self._get_memoized("item_names", """
            SELECT _id, name FROM items
            WHERE type IN (%s)
        """ % placeholders, *item_types)
        return v

    def get_monster_names(self):
        v = self._get_memoized("monster_names", """
            SELECT name FROM monsters
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

    def get_wyporium_trade(self, item_id):
        v = self._get_memoized("wyporium", """
            SELECT * FROM wyporium
            WHERE item_in_id=?
        """, item_id)
        return v[0] if v else None

    def search_item_name(self, term, item_type=None):
        """
        Search for items containing @term somewhere in the name. Returns
        list of matching items.

        Not memoized.
        """
        query = """
            SELECT * FROM items
            WHERE name LIKE ?
        """
        args = ["%%%s%%" % term]
        if item_type is not None:
            if isinstance(item_type, (list, tuple)):
                query += "AND type IN (%s)" % (",".join(["?"] * len(item_type)))
                args += item_type
            else:
                query += "AND type = ?"
                args += [item_type]

        cursor = self.conn.execute(query, args)
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

    def get_quests(self):
        v = self._get_memoized("quests", """
            SELECT * FROM quests
        """)
        return v

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
            SELECT monster_id, unstable FROM monster_to_quest
            WHERE quest_id=?
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
            quests.append(model.Quest(quest_row, rewards_rows))

        return quests

    def get_item_monsters(self, item_id):
        v = self._get_memoized("item_monsters", """
            SELECT DISTINCT monster_id, rank FROM hunting_rewards
            WHERE item_id=?
        """, item_id)

        return v

    def get_item_gathering(self, item_id):
        v = self._get_memoized("item_gathering", """
            SELECT * FROM gathering
            WHERE item_id=?
        """, item_id)

        return v

    def get_location(self, location_id):
        v = self._get_memoized("location", """
            SELECT * FROM locations
            WHERE _id=?
        """, location_id)

        return v

    def get_locations(self):
        v = self._get_memoized("locations", """
            SELECT * FROM locations
        """)

        return v

    def get_weapons(self):
        v = self._get_memoized("weapons", """
            SELECT * FROM weapons
            LEFT JOIN items ON weapons._id = items._id
        """)

        return v
