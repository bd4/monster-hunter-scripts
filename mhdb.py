import sqlite3


class Quest(object):
    def __init__(self, quest_row, quest_rewards):
        self._row = quest_row
        self._rewards = quest_rewards

        self.id = quest_row["_id"]
        self.name = quest_row["name"]
        self.stars = quest_row["stars"]
        self.hub = quest_row["hub"]
        self.goal = quest_row["goal"]
        self.rank = get_rank(self.hub, self.stars)

    def __str__(self):
        return "%s (%s %s* %s)" % (self.name, self.hub, self.stars, self.rank)


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
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.cache = {}

    def _get_memoized(self, key, query, *args):
        if key in self.cache:
            v = self.cache[key].get(args)
            if v is not None:
                return v
        else:
            self.cache[key] = {}
        cursor = self.conn.execute(query, args)
        v = self.cache[key][args] = cursor.fetchall()
        return v

    def get_item(self, item_id):
        v = self._get_memoized("item", """
            SELECT * FROM items
            WHERE _id=?
        """, item_id)
        return v[0]

    def get_item_by_name(self, name):
        v = self._get_memoized("item", """
            SELECT * FROM items
            WHERE name=?
        """, name)
        return v[0]

    def get_monster_by_name(self, name):
        v = self._get_memoized("monster", """
            SELECT * FROM monsters
            WHERE name=?
        """, name)
        return v[0]

    def get_monster(self, monster_id):
        v = self._get_memoized("monster", """
            SELECT * FROM monsters
            WHERE _id=?
        """, monster_id)
        return v[0]

    def get_quest(self, quest_id):
        v = self._get_memoized("quest", """
            SELECT * FROM quests
            WHERE _id=?
        """, quest_id)
        return v[0]

    def get_quest_rewards(self, quest_id):
        v = self._get_memoized("quest_rewards", """
            SELECT * FROM quest_rewards
            WHERE quest_id=?
        """, quest_id)
        return v

    def get_monster_rewards(self, monster_id, rank):
        v = self._get_memoized("monster_rewards", """
            SELECT * FROM hunting_rewards
            WHERE monster_id=? AND rank=?
        """, monster_id, rank)
        return v

    def get_quest_monsters(self, quest_id):
        v = self._get_memoized("quest_monsters", """
            SELECT monster_id FROM monster_to_quest
            WHERE quest_id=? AND unstable='no'
        """, quest_id)
        return v

    def get_item_quests(self, item_id):
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
