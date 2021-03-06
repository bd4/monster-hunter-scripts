"""
Module for accessing the sqlite monster hunter db from
"""

import os
import sqlite3
import json

from mhapi import model


def field_model(key):
    """
    Model to replace each row with the value of single field in the row,
    with the specified key.
    """
    def model_fn(row):
        return row[key]
    return model_fn


def _db_path(game=None):
    module_path = os.path.dirname(__file__)
    project_path = os.path.abspath(os.path.join(module_path, ".."))
    return os.path.join(project_path, "db", "mh%s.db" % game)


ARMOR_HUNTER_TYPES = {
    "Blade": 0,
    "Gunner": 1,
    "Both": 2,
}


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
    # buy and sell are empty, uses weapon.create_cost and upgrade_cost
    _weapon_select = """
        SELECT items.*, weapons.*
        FROM weapons
        LEFT JOIN items ON weapons._id = items._id
    """

    # sell has the a value, but not used at the moment
    _decoration_select = """
        SELECT items._id, items.type, items.name,
               items.rarity, decorations.*
        FROM decorations
        LEFT JOIN items ON decorations._id = items._id
    """

    # buy has the armor cost, sell is empty
    _armor_select = """
        SELECT items._id, items.type, items.name,
               items.rarity, items.buy, armor.*
        FROM armor
        LEFT JOIN items ON armor._id = items._id
    """

    def __init__(self, game=None, path=None, use_cache=False,
                 include_item_components=False):
        """
        If use_cache=True, a lot of memory could be used. No attempt is
        made to de-dupe data between keys, e.g. if you access an item
        by id and by name, it will be fetched and stored in the cache
        twice. Disk cache, sqlite caching, and the smallness of the
        database should make in-memory caching unnecessary for most use
        cases.
        """
        if game is None:
            game = os.environ.get("MHAPI_GAME")
        assert game in ("4u", "gen", "gu")
        self.game = game

        if game == "4u":
            # filter out non-localized DLC
            self._weapon_select = (MHDB._weapon_select
                                  + "WHERE items.name != items.name_jp\n")
        else:
            # no filter needed, but having where in all cases simplifies
            # queries below
            self._weapon_select = (MHDB._weapon_select
                                  + "WHERE 1=1\n")
        if path is None:
            path = _db_path(game)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.use_cache = use_cache
        self.include_item_components = include_item_components
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
        #print "query", query
        cursor = self.conn.execute(query, args)
        rows = cursor.fetchall()
        if model_cls:
            rows = [model_cls(row) for row in rows]
        if collection_cls:
            rows = collection_cls(rows)
        if self.use_cache and not no_cache:
            self.cache[key][args] = rows
        self._add_components(key, rows)
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

    def get_items(self, item_types=None, exclude_types=None, wyporium=False):
        """
        List of item objects.
        """
        fields = ["items.*"]
        where = []
        args = []
        if item_types:
            item_types = sorted(item_types)
            placeholders = ", ".join(["?"] * len(item_types))
            where.append("WHERE type IN (%s)" % placeholders)
            args.extend(item_types)
        if exclude_types:
            exclude_types = sorted(exclude_types)
            placeholders = ", ".join(["?"] * len(exclude_types))
            where.append("WHERE type NOT IN (%s)" % placeholders)
            args.extend(exclude_types)
        if wyporium:
            where.append("LEFT JOIN wyporium AS w ON w.item_in_id = items._id")
            where.append(
              "LEFT JOIN items AS wi ON w.item_out_id = wi._id")
            fields += ["w.item_out_id AS wyporium_item_id",
                       "wi.name AS wyporium_item_name"]
        q = "SELECT " + ", ".join(fields) + " FROM items " + "\n".join(where)
        args = tuple(args)
        return self._query_all("items", q, args, model_cls=model.Item)

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
        if self.game != "4u":
            return None
        return self._query_one("wyporium", """
            SELECT * FROM wyporium
            WHERE item_in_id=?
        """, (item_id,))

    def get_wyporium_trades(self):
        """
        Single wyporium row or None.
        """
        if self.game != "4u":
            return None
        return self._query_all("wyporium", """
            SELECT items.*,
              wyporium.item_out_id AS wyporium_item_id,
              trade_items.name AS wyporium_item_name,
              quests._id   AS wyporium_quest_id,
              quests.name  AS wyporium_quest_name,
              quests.hub   AS wyporium_quest_hub,
              quests.stars AS wyporium_quest_stars,
              quests.rank  AS wyporium_quest_rank
            FROM wyporium
            JOIN items ON items._id = wyporium.item_in_id
            JOIN items AS trade_items ON trade_items._id = wyporium.item_out_id
            JOIN quests ON wyporium.unlock_quest_id == quests._id
        """, model_cls=model.Item)

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

    def get_monster_quests(self, monster_id, rank):
        return self._query_all("monster_quests", """
            SELECT DISTINCT quests.* FROM quests, monster_to_quest
            WHERE monster_to_quest.quest_id = quests._id
              AND monster_to_quest.monster_id=? AND rank=?
        """, (monster_id, rank), model_cls=model.Quest)

    def get_item_quests(self, item_id):
        """
        Get a list of quests that provide the specified item in quest
        rewards. Returns a list of quest objects, which encapsulate the
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

    def get_location_quests(self, location_id, rank):
        return self._query_all("location_quests", """
            SELECT DISTINCT * FROM quests
            WHERE location_id=? AND rank=?
        """, (location_id, rank), model_cls=model.Quest)

    def get_monster_damage(self, monster_id):
        return self._query_all("monster_damage", """
            SELECT * FROM monster_damage
            WHERE monster_id=?
        """, (monster_id,), collection_cls=model.MonsterDamage)

    def get_weapons(self):
        # Note: weapons only available via JP DLC have no localized
        # name, filter them out.
        q = self._weapon_select
        return self._query_all("weapons", q, model_cls=model.Weapon)

    def get_weapons_by_query(self, wtype=None, element=None,
                             final=None):
        """
        @element can have the special value 'Raw' to search for weapons
        with no element. Otherwise @element is searched for in both
        awaken and native, and can be a status or an element.

        @final should be string '1' or '0'
        """
        q = self._weapon_select
        where = []
        args = []
        if wtype is not None:
            where.append("wtype = ?")
            args.append(wtype)
        if element is not None:
            if element == "Raw":
                where.append("(element = '' AND awaken = '')")
            else:
                where.append("(element = ? OR element_2 = ? OR awaken = ?)")
                args.extend([element] * 3)
        if final is not None:
            where.append("final = ?")
            args.append(final)
        if where:
            q += "AND " + "\nAND ".join(where)
        results = self._query_all("weapons", q, tuple(args),
                                  model_cls=model.Weapon)
        return results

    def get_weapon(self, weapon_id):
        return self._query_one("weapon", self._weapon_select + """
            AND weapons._id=?
        """, (weapon_id,), model_cls=model.Weapon)

    def get_weapon_by_name(self, name):
        return self._query_one("weapon", self._weapon_select + """
            AND items.name=?
        """, (name,), model_cls=model.Weapon)

    def get_weapons_by_parent(self, parent_id):
        return self._query_all("weapon_by_parent", self._weapon_select + """
            AND weapons.parent_id=?
        """, (parent_id,), model_cls=model.Weapon)

    def get_armors(self):
        return self._query_all("armors", MHDB._armor_select,
                               model_cls=model.Armor)

    def get_armor(self, armor_id):
        return self._query_one("armor", MHDB._armor_select + """
            WHERE armor._id=?
        """, (armor_id,), model_cls=model.Armor)

    def get_armor_by_name(self, name):
        return self._query_one("armor", MHDB._armor_select + """
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
        return self._query_all("decorations", MHDB._decoration_select,
                               model_cls=model.Decoration)

    def get_decoration(self, decoration_id):
        return self._query_one("decoration", MHDB._decoration_select + """
            WHERE decorations._id = ?
        """, (decoration_id,), model_cls=model.Decoration)

    def get_decoration_by_name(self, name):
        return self._query_all("decoration", MHDB._decoration_select + """
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
            SELECT items._id, items.type, items.name, items.rarity,
                   decorations.*
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
        both_type = "Both"
        if self.game in ("gen", "gu"):
            both_type = ARMOR_HUNTER_TYPES[both_type]
            hunter_type = ARMOR_HUNTER_TYPES[hunter_type]
        args += [both_type, hunter_type]
        return self._query_all("decorations", """
            SELECT items._id, items.type, items.name, items.rarity, items.buy,
                   armor.*
            FROM item_to_skill_tree
            LEFT JOIN items
              ON items._id = item_to_skill_tree.item_id
            LEFT JOIN armor
              ON armor._id = item_to_skill_tree.item_id
            WHERE items.type = 'Armor'
              AND item_to_skill_tree.skill_tree_id IN (%s)
              AND item_to_skill_tree.point_value > 0
              AND armor.hunter_type IN (?, ?)
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

    def get_horn_melodies(self):
        return self._query_all("horn_melodies", """
            SELECT *
            FROM horn_melodies
        """, model_cls=model.HornMelody)

    def get_horn_melodies_by_notes(self, notes):
        return self._query_all("horn_melodies", """
            SELECT *
            FROM horn_melodies
            WHERE notes=?
        """, (notes,), model_cls=model.HornMelody)

    def get_material_items(self, material_item_id):
        """
        Get dict rows of items that satisfy the given material, containing
        item_id and amount keys. MHGen only.
        """
        assert self.game in ("gen", "gu")
        return self._query_all("material_items", """
            SELECT item_id, amount FROM item_to_material
            WHERE item_to_material.material_item_id = ?
            ORDER BY amount ASC
        """, (material_item_id,))

    def _add_components(self, key, item_results):
        """
        Add component data to item results from _query_one or _query_all,
        if include_item_components is set. Uses the cache key to determine
        if it's one of the item types we care about having components for.

        TODO: use batches or single query to make this more efficient for
        large result sets.
        """
        if not self.include_item_components:
            return
        if key.rstrip("s") not in "weapon armor decoration".split():
            return
        if item_results is None:
            return
        if not isinstance(item_results, list):
            item_results = [item_results]
        for item_data in item_results:
            ccomps = self.get_item_components(item_data.id, "Create")
            if not ccomps:
                # might be two possible ways of making the item, just
                # get the first one for now
                ccomps = self.get_item_components(item_data.id, "Create A")
            if item_data["type"] == "Weapon":
                # only weapons have upgrade components
                ucomps = self.get_item_components(item_data.id, "Improve")
            else:
                ucomps = None
            item_data.set_components(ccomps, ucomps)



class MHDBX(object):
    """
    Wrapper around Monster Hunter JSON data, default to MHX. Attempts limited
    compatibility with original 4U MHDB class.

    Uses MHDB object, as temporariy hack for MHX/World data that is not yet
    available or integrated.
    """
    def __init__(self, game="mhx"):
        """
        Loads JSON data, keeps in memory.
        """
        module_path = os.path.dirname(__file__)
        self._mhx_db_path = os.path.abspath(os.path.join(module_path, "..",
                                            "db", game))
        self._4udb = MHDB()
        self._weapon_list = []
        self._weapons_by_name = {}

        self._monsters_by_name = {}
        self._monster_damage = {}
        self._monster_breaks = {}

        self._load_weapons()
        self._load_monsters()

    def _load_weapons(self):
        with open(os.path.join(self._mhx_db_path, "weapon_list.json")) as f:
            wlist = json.load(f)
            for i, wdata in enumerate(wlist):
                wdata["_id"] = i
                weapon = model.Weapon(wdata)
                self._weapon_list.append(weapon)
                self._weapons_by_name[weapon.name_jp] = weapon

    def _load_monsters(self):
        names_path = os.path.join(self._mhx_db_path,
                                  "monster_list.json")
        hitboxes_path = os.path.join(self._mhx_db_path,
                                     "monster_hitboxes.json")
        with open(names_path) as f:
            names = json.load(f)
            for i, d in enumerate(names):
                d["_id"] = -i
                d["class"] = "Large"
                self._monsters_by_name[d["name"]] = model.Monster(d)
        with open(hitboxes_path) as f:
            damage_map = json.load(f)
            for name, damage in damage_map.items():
                mid = self._monsters_by_name[name].id
                damage_rows = []
                for part, data in damage.items():
                    if part.startswith("_"):
                        continue
                    row = dict((k.lower(), v) for k, v in data.items())
                    row["body_part"] = part
                    row["ko"] = 100 if part == "Head" else 0
                    row["_id"] = 0
                    row["monster_id"] = mid
                    damage_rows.append(row)
                self._monster_damage[mid] = model.MonsterDamage(damage_rows)
                self._monster_breaks[mid] = damage["_breaks"]

    def get_weapon_by_name(self, name):
        return self._weapons_by_name.get(name)

    def get_monster_by_name(self, name):
        m = self._monsters_by_name.get(name)
        if m and m.id in self._monster_damage:
            return m
        return self._4udb.get_monster_by_name(name)

    def get_monster_damage(self, monster_id):
        d = self._monster_damage.get(monster_id)
        if d:
            return d
        return self._4udb.get_monster_damage(monster_id)

    def get_monster_breaks(self, monster_id):
        b = self._monster_breaks.get(monster_id)
        if b:
            return b
        return self._4udb.get_monster_breaks(monster_id)

    def get_weapons_by_query(self, wtype=None, element=None,
                             final=None):
        """
        @element can have the special value 'Raw' to search for weapons
        with no element. Otherwise @element is searched for in both
        awaken and native, and can be a status or an element.

        @final should be string '1' or '0'
        """
        final = int(final)
        results = []
        for w in self._weapon_list:
            if wtype is not None and w.wtype != wtype:
                continue
            if (element is not None
            and element not in (w.element, w.element_2)
            and not (element == "Raw" and not w.element)):
                continue
            if final is not None and w.final != final:
                continue
            results.append(w)
        return results
