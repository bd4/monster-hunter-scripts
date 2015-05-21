"""
Module for accessing the sqlite monster hunter db from
"""

import os.path
import sqlite3

from mhapi import model


def field_model(key):
    """
    Model to replace each row with the value of single field in the row,
    with the specified key.
    """
    def model_fn(row):
        return row[key]
    return model_fn


def _db_path():
    module_path = os.path.dirname(__file__)
    project_path = os.path.abspath(os.path.join(module_path, ".."))
    return os.path.join(project_path, "db", "mh4u.db")


class MHDB(object):
    """
    Wrapper around the Android App sqlite3 db. The following conventions
    are used:

    - get_ENTITY_NAME will return a single entity by id
    - get_ENTITY_NAME_by_name will return a single entity by name
    - get_ENTITY_NAMEs will return a list of all entities in the db
    - get_ENTITY_NAME_names will return a list of all names of the
          entities in the db, possibly with a type param.
    """

    def __init__(self, path=None, use_cache=False):
        """
        If use_cache=True, a lot of memory could be used. No attempt is
        made to de-dupe data between keys, e.g. if you access an item
        by id and by name, it will be fetched and stored in the cache
        twice. Disk cache, sqlite caching, and the smallness of the
        database should make in-memory caching unnecessary for most use
        cases.
        """
        if path is None:
            path = _db_path()
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.use_cache = use_cache
        self.cache = {}

    def _query_one(self, key, query, args=(), model_cls=None,
                   no_cache=False):
        values = self._query_all(key, query, args, model_cls, no_cache)
        if values:
            return values[0]
        else:
            return None

    def _query_all(self, key, query, args=(), model_cls=None,
                   no_cache=False, collection_cls=None):
        assert isinstance(args, tuple)
        assert model_cls is None or collection_cls is None
        if self.use_cache and not no_cache:
            if key in self.cache:
                v = self.cache[key].get(args)
                if v is not None:
                    return v
            else:
                self.cache[key] = {}
        cursor = self.conn.execute(query, args)
        rows = cursor.fetchall()
        if model_cls:
            rows = [model_cls(row) for row in rows]
        if collection_cls:
            rows = collection_cls(rows)
        if self.use_cache and not no_cache:
            self.cache[key][args] = rows
        return rows

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()

    def get_item_types(self):
        """
        List of strings.
        """
        return self._query_all("item_types", """
            SELECT DISTINCT type FROM items
        """, model_cls=field_model("type"))

    def get_item_names(self, item_types):
        """
        List of unicode strings.
        """
        args = sorted(item_types)
        placeholders = ", ".join(["?"] * len(item_types))
        return self._query_all("item_names", """
            SELECT _id, name FROM items
            WHERE type IN (%s)
        """ % placeholders, tuple(args), model_cls=field_model("name"))

    def get_items(self, item_types=None):
        """
        List of item objects.
        """
        q = "SELECT * FROM items"
        if item_types:
            item_types = sorted(item_types)
            placeholders = ", ".join(["?"] * len(item_types))
            q += "\nWHERE type IN (%s)" % placeholders
            item_types = tuple(item_types)
        else:
            item_types = ()
        return self._query_all("items", q, item_types, model_cls=model.Item)

    def get_item(self, item_id):
        """
        Single item object or None.
        """
        return self._query_one("item", """
            SELECT * FROM items
            WHERE _id=?
        """, (item_id,), model_cls=model.Item)

    def get_item_by_name(self, name):
        """
        Single item object or None.
        """
        return self._query_one("item", """
            SELECT * FROM items
            WHERE name=?
        """, (name,), model_cls=model.Item)

    def get_wyporium_trade(self, item_id):
        """
        Single wyporium row or None.
        """
        return self._query_one("wyporium", """
            SELECT * FROM wyporium
            WHERE item_in_id=?
        """, (item_id,))

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

        return self._query_all("search_item", query, tuple(args),
                               no_cache=True, model_cls=model.Item)

    def get_monsters(self):
        return self._query_all("monsters", """
            SELECT * FROM monsters
        """, model_cls=model.Monster)

    def get_monster_names(self):
        """
        List of unicode strings.
        """
        return self._query_all("monster_names", """
            SELECT name FROM monsters
        """, model_cls=field_model("name"))

    def get_monster(self, monster_id):
        return self._query_one("monster", """
            SELECT * FROM monsters
            WHERE _id=?
        """, (monster_id,), model_cls=model.Monster)

    def get_monster_by_name(self, name):
        return self._query_one("monster", """
            SELECT * FROM monsters
            WHERE name=?
        """, (name,), model_cls=model.Monster)

    def get_quest(self, quest_id):
        return self._query_one("quest", """
            SELECT * FROM quests
            WHERE _id=?
        """, (quest_id,), model_cls=model.Quest)

    def get_quests(self):
        return self._query_all("quests", """
            SELECT * FROM quests
        """, model_cls=model.Quest)

    def get_quest_rewards(self, quest_id):
        return self._query_all("quest_rewards", """
            SELECT * FROM quest_rewards
            WHERE quest_id=?
        """, (quest_id,))

    def get_monster_rewards(self, monster_id, rank=None):
        q = """
            SELECT * FROM hunting_rewards
            WHERE monster_id=?
        """
        if rank is not None:
            q += "AND rank=?"
            args = (monster_id, rank)
        else:
            args = (monster_id,)
        return self._query_all("monster_rewards", q, args)

    def get_quest_monsters(self, quest_id):
        return self._query_all("quest_monsters", """
            SELECT monster_id, unstable FROM monster_to_quest
            WHERE quest_id=?
        """, (quest_id,))

    def get_item_quests(self, item_id):
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
            quest_id = r["quest_id"]
            quest = self.get_quest(quest_id)
            quest.rewards = self.get_quest_rewards(quest_id)
            quests.append(quest)

        return quests

    def get_item_monsters(self, item_id):
        return self._query_all("item_monsters", """
            SELECT DISTINCT monster_id, rank FROM hunting_rewards
            WHERE item_id=?
        """, (item_id,))

    def get_item_gathering(self, item_id):
        return self._query_all("item_gathering", """
            SELECT * FROM gathering
            WHERE item_id=?
        """, (item_id,))

    def get_location(self, location_id):
        self._query_one("location", """
            SELECT * FROM locations
            WHERE _id=?
        """, (location_id,), model_cls=model.Location)

    def get_locations(self):
        return self._query_all("locations", """
            SELECT * FROM locations
        """, model_cls=model.Location)

    def get_monster_damage(self, monster_id):
        return self._query_all("monster_damage", """
            SELECT * FROM monster_damage
            WHERE monster_id=?
        """, (monster_id,), collection_cls=model.MonsterDamage)

    def get_weapons(self, get_components=False):
        results = self._query_all("weapons", """
            SELECT * FROM weapons
            LEFT JOIN items ON weapons._id = items._id
        """, model_cls=model.Weapon)
        if results and get_components:
            for r in results:
                self._add_components(r)
        return results

    def _add_components(self, item_data):
        ccomps = self.get_item_components(item_data.id, "Create")
        ucomps = self.get_item_components(item_data.id, "Improve")
        item_data.set_components(ccomps, ucomps)

    def get_weapon(self, weapon_id, get_components=False):
        weapon = self._query_one("weapon", """
            SELECT * FROM weapons
            LEFT JOIN items ON weapons._id = items._id
            WHERE weapons._id=?
        """, (weapon_id,), model_cls=model.Weapon)
        if weapon and get_components:
            self._add_components(weapon)
        return weapon

    def get_weapon_by_name(self, name, get_components=False):
        weapon = self._query_one("weapon", """
            SELECT items._id, items.name, items.buy, weapons.*
            FROM weapons
            LEFT JOIN items ON weapons._id = items._id
            WHERE items.name=?
        """, (name,), model_cls=model.Weapon)
        if weapon and get_components:
            self._add_components(weapon)
        return weapon

    def get_armors(self):
        return self._query_all("armors", """
            SELECT items._id, items.name, items.buy, armor.*
            FROM armor
            LEFT JOIN items ON armor._id = items._id
        """, model_cls=model.Armor)

    def get_armor(self, armor_id):
        return self._query_one("armor", """
            SELECT items._id, items.name, items.buy, armor.*
            FROM armor
            LEFT JOIN items ON armor._id = items._id
            WHERE armor._id=?
        """, (armor_id,), model_cls=model.Armor)

    def get_armor_by_name(self, name):
        return self._query_one("armor", """
            SELECT items._id, items.name, items.buy, armor.*
            FROM armor
            LEFT JOIN items ON armor._id = items._id
            WHERE items.name=?
        """, (name,), model_cls=model.Armor)

    def get_item_skills(self, item_id):
        return self._query_all("item_skills", """
            SELECT item_to_skill_tree.*, skill_trees.name
            FROM item_to_skill_tree
            LEFT JOIN skill_trees
              ON item_to_skill_tree.skill_tree_id = skill_trees._id
            WHERE item_to_skill_tree.item_id=?
        """, (item_id,), model_cls=model.ItemSkill)

    def get_decorations(self):
        return self._query_all("decorations", """
            SELECT items._id, items.name, items.buy, decorations.*
            FROM decorations
            INNER JOIN items
              ON items._id = decorations._id
        """, model_cls=model.Decoration)

    def get_decoration(self, decoration_id):
        return self._query_one("decoration", """
            SELECT items._id, items.name, items.buy, decorations.*
            FROM decorations
            INNER JOIN items
              ON items._id = decorations._id
            WHERE decorations._id = ?
        """, (decoration_id,), model_cls=model.Decoration)

    def get_decoration_by_name(self, name):
        return self._query_all("decoration", """
            SELECT items._id, items.name, items.buy, decorations.*
            FROM decorations
            INNER JOIN items
              ON items._id = decorations._id
            WHERE items.name = ?
        """, (name,), model_cls=model.Decoration)

    def get_skill_trees(self):
        return self._query_all("skill_trees", """
            SELECT _id, name FROM skill_trees
        """, model_cls=model.SkillTree)

    def get_skill_tree_id(self, skill_tree_name):
        result = self._query_one("skill", """
            SELECT _id FROM skill_trees
            WHERE name=?
        """, (skill_tree_name,))
        if result:
            return result["_id"]
        return None

    def get_skills(self):
        return self._query_all("skills", """
            SELECT _id, skill_tree_id, required_skill_tree_points,
                   name, description
            FROM skills
        """, model_cls=model.Skill)

    def get_decorations_by_skills(self, skill_tree_ids):
        args = sorted(skill_tree_ids)
        placeholders = ", ".join(["?"] * len(skill_tree_ids))
        return self._query_all("decorations", """
            SELECT items._id, items.name, items.buy, decorations.*
            FROM item_to_skill_tree
            LEFT JOIN items
              ON items._id = item_to_skill_tree.item_id
            LEFT JOIN decorations
              ON decorations._id = item_to_skill_tree.item_id
            WHERE items.type = 'Decoration'
              AND item_to_skill_tree.skill_tree_id IN (%s)
              AND item_to_skill_tree.point_value > 0
            GROUP BY item_to_skill_tree.item_id
        """ % placeholders, tuple(args), model_cls=model.Decoration)

    def get_armors_by_skills(self, skill_tree_ids, hunter_type):
        args = sorted(skill_tree_ids)
        placeholders = ", ".join(["?"] * len(skill_tree_ids))
        args += [hunter_type]
        return self._query_all("decorations", """
            SELECT items._id, items.name, items.buy, armor.*
            FROM item_to_skill_tree
            LEFT JOIN items
              ON items._id = item_to_skill_tree.item_id
            LEFT JOIN armor
              ON armor._id = item_to_skill_tree.item_id
            WHERE items.type = 'Armor'
              AND item_to_skill_tree.skill_tree_id IN (%s)
              AND item_to_skill_tree.point_value > 0
              AND armor.hunter_type IN ('Both', ?)
            GROUP BY item_to_skill_tree.item_id
        """ % placeholders, tuple(args), model_cls=model.Armor)

    def get_monster_breaks(self, monster_id):
        """
        List of strings.
        """
        def model(row):
            condition = row["condition"]
            if condition == "Tail Carve":
                return "Tail"
            else:
                return condition[len("Break "):]

        return self._query_all("monster_breaks", """
            SELECT DISTINCT condition FROM hunting_rewards
            WHERE monster_id=?
            AND (condition LIKE 'Break %' OR condition = 'Tail Carve')
        """, (monster_id,), model_cls=model)

    def get_item_components(self, item_id, method="Create"):
        return self._query_all("item_components", """
            SELECT items._id, items.name, items.type,
                   components.quantity, components.type AS method
            FROM components
            LEFT JOIN items
              ON items._id = components.component_item_id
            WHERE created_item_id=? AND components.type=?
        """, (item_id, method), model_cls=model.ItemComponent)
