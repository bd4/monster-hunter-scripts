import string
import json
import urllib
import re
import difflib

from mhapi.util import EnumBase


class ModelJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "as_data"):
            return o.as_data()
        return json.JSONEncoder.default(self, o)


class ModelBase(object):
    def as_data(self):
        raise NotImplemented()

    def as_list_data(self):
        raise NotImplemented()

    def json_dumps(self, indent=2):
        data = self.as_data()
        return json.dumps(data, cls=ModelJSONEncoder, indent=indent)

    def json_dump(self, fp, indent=2):
        json.dump(self, fp, cls=ModelJSONEncoder, indent=indent)


class RowModel(ModelBase):
    _list_fields = ["id", "name"]
    _exclude_fields = []
    _indexes = { "name": ["id"] }

    def __init__(self, row):
        self.id = row["_id"]
        self._row = row
        self._data = dict(row)
        del self._data["_id"]
        self._data["id"] = self.id
        for f in self._exclude_fields:
            del self._data[f]

    def __getattr__(self, name):
        try:
            return self._data[name]
        except IndexError:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, name))

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def fields(self):
        return self._data.keys()

    def as_data(self):
        return self._data

    def as_list_data(self):
        list_data = {}
        for key in self._list_fields:
            list_data[key] = self[key]
        return list_data

    def update_indexes(self, data):
        for key_field, value_fields in self._indexes.iteritems():
            if key_field not in data:
                data[key_field] = {}
            self.update_index(key_field, value_fields, data[key_field])

    def update_index(self, key_field, value_fields, data):
        if isinstance(value_fields, str):
            item = self[value_fields]
        else:
            item = dict((k, self[k]) for k in value_fields)
        key_value = self[key_field]
        if key_value not in data:
            data[key_value] = []
        data[key_value].append(item)

    def __str__(self):
        if "name" in self._data and self.name is not None:
            name = urllib.quote(self.name, safe=" ")
        else:
            name = str(self.id)
        return "%s '%s'" % (self.__class__.__name__, name)

    def __repr__(self):
        return "<mhapi.model.%s %d>" % (self.__class__.__name__, self.id)


class Quest(RowModel):
    _full_template = string.Template(
           "$name ($hub $stars* $rank)"
           "\n Goal: $goal"
           "\n Sub : $sub_goal"
    )

    _one_line_template = string.Template(
       "$name ($hub $stars* $rank)"
    )

    def __init__(self, quest_row, quest_rewards=None):
        super(Quest, self).__init__(quest_row)

        self.rewards = quest_rewards

    def is_multi_monster(self):
        return (" and " in self.goal
                or "," in self.goal
                or " all " in self.goal)

    def one_line_u(self):
        return self._one_line_template.substitute(self.as_data())

    def full_u(self):
        return self._full_template.substitute(self.as_data())

    def __unicode__(self):
        return self.full_u()


class SharpnessLevel(EnumBase):
    """
    Enumeration for weapon sharpness levels.
    """

    RED = 0
    ORANGE = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4
    WHITE = 5
    PURPLE = 6

    ALL = range(0, PURPLE + 1)

    _names = {
        RED: "Red",
        ORANGE: "Orange",
        YELLOW: "Yellow",
        GREEN: "Green",
        BLUE: "Blue",
        WHITE: "White",
        PURPLE: "Purple",
    }

    # source: http://kiranico.com/en/mh4u/wiki/weapons
    _modifier = {
        RED:    (0.50, 0.25),
        ORANGE: (0.75, 0.50),
        YELLOW: (1.00, 0.75),
        GREEN:  (1.125, 1.00),
        BLUE:   (1.25, 1.0625),
        WHITE:  (1.32, 1.125),
        PURPLE: (1.44, 1.20),
    }

    # for mhx, mhgen, mhxx, and likely mhw
    _modifier_mhx = {
        RED:    (0.50, 0.25),
        ORANGE: (0.75, 0.50),
        YELLOW: (1.00, 0.75),
        GREEN:  (1.05, 1.00),
        BLUE:   (1.20, 1.0625),
        WHITE:  (1.32, 1.125),
    }


    @classmethod
    def raw_modifier(cls, sharpness):
        return cls._modifier[sharpness][0]

    @classmethod
    def element_modifier(cls, sharpness):
        return cls._modifier[sharpness][1]


class WeaponSharpness(ModelBase):
    """
    Representation of the sharpness of a weapon, as a list of sharpness
    points at each level. E.g. the 0th item in the list is the amount of
    RED sharpness, the 1st item is ORANGE, etc.
    """
    def __init__(self, db_string_or_list):
        if isinstance(db_string_or_list, list):
            self.value_list = db_string_or_list
        else:
            self.value_list = [int(s) for s in db_string_or_list.split(".")]
        # For MHX, Gen, no purple sharpness, but keep model the same for
        # simplicity
        if len(self.value_list) < SharpnessLevel.PURPLE + 1:
            self.value_list.append(0)
        self._max = None

    @property
    def max(self):
        if self._max is None:
            self._max = SharpnessLevel.RED
            for i in xrange(SharpnessLevel.PURPLE+1):
                if self.value_list[i] == 0:
                    break
                else:
                    self._max = i
        return self._max

    def as_data(self):
        return self.value_list


class ItemCraftable(RowModel):
    _list_fields = ["id", "name"]

    def __init__(self, item_row):
        super(ItemCraftable, self).__init__(item_row)
        self.create_components = None
        self.upgrade_components = None

    def set_components(self, create_components, upgrade_components):
        self.create_components = create_components
        self.upgrade_components = upgrade_components

    def as_data(self):
        data = super(ItemCraftable, self).as_data()
        if self.create_components is not None:
            data["create_components"] = dict((item.name, item.quantity)
                                             for item in self.create_components)
        if self.upgrade_components is not None:
            data["upgrade_components"] = dict((item.name, item.quantity)
                                         for item in self.upgrade_components)
        return data


class ItemWithSkills(ItemCraftable):
    def __init__(self, item_row):
        super(ItemWithSkills, self).__init__(item_row)
        self.skills = None
        self.skill_ids = []
        self.skill_names = []

    def set_skills(self, item_skills):
        self.skills = {}
        for s in item_skills:
            self.skills[s.skill_tree_id] = s.point_value
            self.skills[s.name] = s.point_value
            self.skill_ids.append(s.skill_tree_id)
            self.skill_names.append(s.name)

    def skill(self, skill_id_or_name):
        return self.skills.get(skill_id_or_name, 0)

    def one_line_skills_u(self, skill_names=None):
        """
        Get comma separated list of skills on the item. If @skill_names
        is passed, only include skills that are in that list.
        """
        if skill_names is None:
            skill_names = sorted(self.skill_names)
        return ", ".join("%s %d" % (name, self.skills[name])
                         for name in skill_names
                         if name in self.skills)

    def as_data(self):
        data = super(ItemWithSkills, self).as_data()
        if self.skills is not None:
            data["skills"] = dict((name, self.skills[name])
                                  for name in self.skill_names)
        #data["skills_by_id"] = dict((sid, self.skills[sid])
        #                            for sid in self.skill_ids)
        return data


class Armor(ItemWithSkills):
    _indexes = { "name": "id",
                 "slot": "name" }

    _one_line_template = string.Template(
       "$name ($slot) Def $defense-$max_defense Slot $num_slots"
    )

    def __init__(self, armor_item_row):
        super(Armor, self).__init__(armor_item_row)

    def one_line_u(self):
        return self._one_line_template.substitute(self.as_data())

    def skill(self, skill_id_or_name, decoration_values=()):
        """
        Get total value of skill from the armor and decorations based on
        the number of slots.

        decoration_values should be a list of points from the given
        number of slots, e.g. [1, 3] or [1, 3, 0] means that one slot
        gets 1 point and two slots get 3 points, [1, 0, 4] means that
        one slot gets 1 point, there is no two slot gem, and three slots
        gets 4 points. If not passed, just returns native skill points.
        """
        assert self.skills is not None
        total = self.skills.get(skill_id_or_name, 0)
        slots_left = self.num_slots
        for slots in xrange(len(decoration_values), 0, -1):
            if slots_left == 0:
                break
            decoration_value = decoration_values[slots-1]
            if not decoration_value:
                continue
            while slots <= slots_left:
                total += decoration_value
                slots_left -= slots
        return total


class Decoration(ItemWithSkills):
    pass


class ItemSkill(RowModel):
    pass


class SkillTree(RowModel):
    _list_fields = ["id", "name"]

    def __init__(self, skill_tree_row):
        super(SkillTree, self).__init__(skill_tree_row)
        self.decoration_values = None
        self.decoration_ids = None

    def set_decorations(self, decorations):
        if decorations is None:
            self.decoration_values = None
        else:
            self.decoration_ids, self.decoration_values = \
                        get_decoration_values(self.id, decorations)

    def as_data(self):
        data = super(SkillTree, self).as_data()
        if self.decoration_values is not None:
            data["decoration_values"] = self.decoration_values
            data["decoration_ids"] = self.decoration_ids
        return data


class Skill(RowModel):
    _list_fields = ["id", "name"]
    _indexes = { "skill_tree_id":
                 ["id", "required_skill_tree_points", "name", "description"] }

    def __init__(self, skill_row):
        super(Skill, self).__init__(skill_row)
        self.skill_tree = None

    def set_skill_tree(self, skill_tree):
        assert skill_tree.id == self.skill_tree_id
        self.skill_tree = skill_tree


class Weapon(ItemCraftable):
    _list_fields = ["id", "wtype", "name"]
    _indexes = { "name": "id",
                 "wtype": ["id", "name"],
                 # subset of all data that can be used for searching and
                 # not be too bloated
                 "id": ["name", "wtype", "final", "element", "element_2",
                        "awaken"] }

    def __init__(self, weapon_item_row):
        super(Weapon, self).__init__(weapon_item_row)
        self._parse_sharpness()

    def _parse_sharpness(self):
        """
        Replace the sharpness field with parsed models for the normal
        sharpness and the sharpness with Sharpness+1 skill.
        """
        if self.wtype in ("Light Bowgun", "Heavy Bowgun", "Bow"):
            self._data["sharpness"] = self._data["sharpness_plus"] = None
            return
        if isinstance(self._row["sharpness"], list):
            # MHX JSON data, already desired format, but doesn't have
            # purple so we append 0
            self.sharpness = WeaponSharpness(self._row["sharpness"] + [0])
            self.sharpness_plus = WeaponSharpness(
                                        self._row["sharpness_plus"] + [0])
            self.sharpness_plus2 = WeaponSharpness(
                                        self._row["sharpness_plus2"] + [0])
        else:
            # 4U or gen data from db
            parts = self._row["sharpness"].split(" ")
            if len(parts) == 2:
                normal, plus = parts
                plus2 = plus
            elif len(parts) == 3:
                normal, plus, plus2 = parts
            else:
                raise ValueError("Bad sharpness value in db: '%s'"
                                 % self._row["sharpness"])
            self._data["sharpness"] = WeaponSharpness(normal)
            self._data["sharpness_plus"] = WeaponSharpness(plus)
            self._data["sharpness_plus2"] = WeaponSharpness(plus2)

    def is_not_localized(self):
        # Check if first char is ascii, should be the case for all
        # english weapons, and not for Japanese DLC weapons.
        return ord(self.name[0]) < 128


class Monster(RowModel):
    _list_fields = ["id", "class", "name"]


class Item(RowModel):
    _list_fields = ["id", "type", "name"]
    _indexes = { "name": ["id"],
                 "type": ["id", "name"] }


class ItemComponent(RowModel):
    _list_fields = ["id", "name"]
    _indexes = { "method": ["id", "name"] }



class Location(RowModel):
    pass


class HornMelody(RowModel):
    _list_fields = ["notes", "song", "effect1", "effect2",
                    "duration", "extension"]
    _indexes = { "notes": ["song", "effect1", "effect2", "duration",
                           "extension"] }


class MonsterPartStateDamage(RowModel):
    """
    Model for the damage to the monster on a particular hitbox and in
    a particulare state.
    """
    _exclude_fields = ["monster_id", "body_part"]

    def __init__(self, part, state, row):
        super(MonsterPartStateDamage, self).__init__(row)
        self._data["part"] = part
        self._data["state"] = state

    def __eq__(self, other):
        for col in "impact cut shot ko ice dragon water fire thunder".split():
            if self[col] != other[col]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class MonsterPartDamage(ModelBase):
    """
    Model for collecting the damage to the monster on a particular hitbox
    across different states.
    """
    def __init__(self, part):
        self.part = part
        self.breakable = False
        self.states = {}

    def add_state(self, state, damage_row):
        self.states[state] = MonsterPartStateDamage(self.part, state,
                                                    damage_row)
        # TODO: what about state 'Without Hide' for S.Nerscylla, which
        # appears like it might be the same as Break Part, or might
        # affect across hitzones.
        if state == "Break Part":
            # the default damage should be sorted before the alternate
            # state damage
            assert "Default" in self.states
            if self.states[state] != self.states["Default"]:
                # if the damage is different for break state, the part
                # must be breakable, even if we couldn't find a match
                # when searching break rewards
                # print "%s is breakable [by hitzone diff]" % self.part
                self.breakable = True

    def as_data(self):
        return dict(
            breakable=self.breakable,
            damage=self.states
        )


class MonsterDamage(ModelBase):
    """
    Model for the damage weakness to the monster in all the
    different states and all the different hitboxes.
    """
    def __init__(self, damage_rows):
        self._rows = damage_rows
        self.parts = {}
        self.states = set()
        for row in damage_rows:
            if row["cut"] == -1:
                # -1 indicates missing data
                continue
            part = row["body_part"]
            state = "Default"
            m = re.match(r"([^(]+) \(([^)]+)\)", part)
            if m:
                part = m.group(1)
                state = m.group(2)
            self.states.add(state)
            if part not in self.parts:
                self.parts[part] = MonsterPartDamage(part)
            self.parts[part].add_state(state, row)

    def as_data(self):
        return dict(
            states=list(self.states),
            parts=self.parts
        )

    def set_breakable(self, breakable_list):
        """
        Set breakable flag on parts based on the breakable list from
        rewards (use MHDB.get_monster_breaks).
        """
        for name, part_damage in self.parts.iteritems():
            if _break_find(name, self.parts, breakable_list):
                #print "part %s is breakable [by rewards]" % name
                part_damage.breakable = True


def get_decoration_values(skill_id, decorations):
    """
    Given a list of decorations that provide the specified skill_id,
    figure out the best decoration for each number of slots from
    one to three. Returns (id_list, value_list), where both are 3 element
    arrays and id_list contains the decoration ids, and value_list contains
    the number of skill points provided by each.
    """
    # TODO: write script to compute this and shove into skill_tree table
    values = [0, 0, 0]
    ids = [None, None, None]
    for d in decorations:
        assert d.num_slots is not None
        # some skills like Handicraft have multiple decorations with
        # same number of slots - use the best one
        new = d.skills[skill_id]
        current = values[d.num_slots-1]
        if new > current:
            values[d.num_slots-1] = new
            ids[d.num_slots-1] = d.id
    return (ids, values)


def _break_find(part, parts, breaks):
    # favor 'Tail Tip' over Tail for Basarios
    if part == "Tail" and "Tail Tip" in parts:
        return None
    if part == "Tail Tip" and "Tail" in breaks:
        return "Tail"
    if part == "Neck/Tail" and "Tail" in breaks:
        return "Tail"
    if part == "Wing" and "Wing" not in breaks:
        if "Talon" in breaks and "Talon" not in parts:
            # for Teostra
            return "Talon"
    if part == "Head" and "Head" not in breaks:
        if "Horn" in breaks and "Horn" not in parts:
            # for Fatalis
            return "Horn"
        if "Ear" in breaks and "Ear" not in parts:
            # Kecha Wacha
            return "Ear"
    if part == "Winglegs" and "Winglegs" not in breaks:
        if "Wing Leg" in breaks and "Wing Leg" not in parts:
            # for Gore
            return "Wing Leg"
    #print "part_find", part, breaks
    matches = difflib.get_close_matches(part, breaks, 1, 0.8)
    if matches:
        return matches[0]
    return None


def get_costs(db, weapon):
    """
    Get a list of alternative ways of making a weapon, as a list of dicts
    containing item counts. The dicts also contain special keys _zenny
    for the total zenny needed, and _path for a list of weapons that
    make up the upgrade path.
    """
    costs = []
    if weapon.parent_id:
        if not weapon.upgrade_cost:
            # db has errors where upgrade cost is listed as create
            # cost and components are listed under create. Assume
            # parent_id is correct, and they are upgrade only.
            if not weapon.upgrade_components and weapon.create_components:
                weapon.upgrade_components = weapon.create_components
                weapon.create_components = []
            weapon.upgrade_cost = weapon.creation_cost
            weapon.creation_cost = 0
        try:
            upgrade_cost = int(weapon.upgrade_cost)
        except ValueError:
            upgrade_cost = 0
            print "WARN: bad upgrade cost for '%s' (%s): '%s'" \
                  % (weapon.name, weapon.id, weapon.upgrade_cost)
        except UnicodeError:
            upgrade_cost = 0
            cost_display = urllib.quote(weapon.upgrade_cost)
            print "WARN: bad upgrade cost for '%s' (%s): '%s'" \
                % (weapon.name, weapon.id, cost_display)
        parent_weapon = db.get_weapon(weapon.parent_id)
        costs = get_costs(db, parent_weapon)
        for cost in costs:
            cost["zenny"] += upgrade_cost
            cost["path"] += [weapon]
            for item in weapon.upgrade_components:
                if item.type == "Weapon":
                    continue
                if item.name not in cost["components"]:
                    cost["components"][item.name] = 0
                cost["components"][item.name] += item.quantity
    if weapon.create_components:
        try:
            zenny = int(weapon.creation_cost)
        except ValueError:
            print "WARN: bad creation cost for '%s': '%s'" \
                % (weapon.name, weapon.creation_cost)
            zenny = weapon.upgrade_cost or 0
        create_cost = dict(zenny=zenny,
                           path=[weapon],
                           components={})
        for item in weapon.create_components:
            create_cost["components"][item.name] = item.quantity
        costs = [create_cost] + costs
    return costs


class ItemStars(object):
    """
    Get the game progress (in hub stars) required to make an item. Caches
    values.
    """

    def __init__(self, db):
        self.db = db
        self._item_stars = {}   # item id -> stars dict
        self._weapon_stars = {} # weapon id -> stars dict
        self._wyporium_trades = {}

        if self.db.game == "4u":
            self.init_wyporium_trades()

    def init_wyporium_trades(self):
        trades = self.db.get_wyporium_trades()
        for item in trades:
            self._wyporium_trades[item.id] = item

    def get_weapon_stars(self, weapon):
        """
        Get lowest star levels needed to make weapon, among the different
        paths available.
        """
        stars = self._weapon_stars.get(weapon.id)
        if stars is not None:
            return stars

        stars = dict(Village=None, Guild=None, Permit=None, Arena=None,
                     Event=None)
        costs = get_costs(self.db, weapon)
        # find least 'expensive' path
        for c in costs:
            current_stars = self._get_component_stars(c)
            for k, v in current_stars.iteritems():
                if v is None:
                    continue
                if stars[k] is None or v < stars[k]:
                    stars[k] = v
        self._weapon_stars[weapon.id] = stars
        return stars

    def _get_component_stars(self, c):
        # need to track unititialized vs unavailable
        stars = dict(Village=0, Guild=0, Permit=0, Arena=0, Event=0)
        for item_name in c["components"].keys():
            item = self.db.get_item_by_name(item_name)
            if item.type == "Materials":
                current_stars = self.get_material_stars(item.id)
            else:
                current_stars = self.get_item_stars(item.id)
            # keep track of most 'expensive' item
            for k, v in current_stars.items():
                if stars[k] is None:
                    # another item was unavailable from the hub
                    continue
                if v is None:
                    if k == "Village" and current_stars["Guild"] is not None:
                        # available from guild and not from village,
                        # e.g. certain HR parts. Mark entire item as
                        # unavailable from village, don't allow override.
                        stars[k] = None
                    continue
                if v > stars[k]:
                    stars[k] = v

        # check for hubs that had no candidate item, and null them out
        for k in list(stars.keys()):
            if stars[k] == 0:
                stars[k] = None
        return stars

    def get_material_stars(self, material_item_id):
        """
        Find the level of the cheapest item that satisfies the material
        that is not a scrap.
        """
        stars = self._item_stars.get(material_item_id)
        if stars is not None:
            return stars

        stars = dict(Village=None, Guild=None, Permit=None, Arena=None,
                     Event=None)
        rows = self.db.get_material_items(material_item_id)
        for row in rows:
            item = self.db.get_item(row["item_id"])
            if "Scrap" in item.name:
                continue
            istars = self.get_item_stars(item.id)
            for k, v in stars.items():
                if istars[k] > v:
                    stars[k] = istars[k]
            break
        self._item_stars[material_item_id] = stars
        return stars

    def get_item_stars(self, item_id):
        stars = self._item_stars.get(item_id)
        if stars is not None:
            return stars

        stars = dict(Village=None, Guild=None, Permit=None, Arena=None,
                     Event=None)

        # for 4u wyporium trade items, use the stars from the unlock quest
        trade = self._wyporium_trades.get(item_id)
        if trade is not None:
            hub = trade.wyporium_quest_hub
            if hub == "Caravan":
                hub = "Village"
            stars[hub] = trade.wyporium_quest_stars
            self._item_stars[item_id] = stars
            return stars

        quests = self.db.get_item_quests(item_id)

        gathering = self.db.get_item_gathering(item_id)
        gather_locations = set()
        for gather in gathering:
            gather_locations.add((gather["location_id"], gather["rank"]))
        for location_id, rank in list(gather_locations):
            gather_quests = self.db.get_location_quests(location_id, rank)
            quests.extend(gather_quests)

        monsters = self.db.get_item_monsters(item_id)
        monster_ranks = set()
        for monster in monsters:
            monster_ranks.add((monster["monster_id"], monster["rank"]))
        for monster_id, rank in list(monster_ranks):
            monster_quests = self.db.get_monster_quests(monster_id, rank)
            quests.extend(monster_quests)

        # find least expensive quest for getting the item
        for quest in quests:
            if quest.hub == "Caravan":
                # For mh4u, map Caravan->Village
                quest.hub = "Village"
            if quest.stars == 0:
                # ignore training quests
                if "Training" not in quest.name:
                    print "Error: non training quest has 0 stars", \
                        quest.id, quest.name
                continue
            if quest.hub in stars:
                current = stars[quest.hub]
                if current is None or quest.stars < current:
                    stars[quest.hub] = quest.stars
            else:
                print "Error: unknown hub", quest.hub

        # if available guild or village, then null out permit/arena values,
        # because they are more useful for filtering if limited to items
        # exclusively available from permit or arena. Allows matching
        # on based on meeting specified critera for
        # (guild or village) and permit and arena.
        if stars["Village"] or stars["Guild"]:
            stars["Permit"] = None
            stars["Arena"] = None

        self._item_stars[item_id] = stars
        return stars

