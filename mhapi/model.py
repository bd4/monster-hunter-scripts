import string
import json
import urllib
from collections import defaultdict
import re

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
        item = dict((k, self[k]) for k in value_fields)
        key_value = self[key_field]
        if key_value not in data:
            data[key_value] = []
        data[key_value].append(item)

    def __str__(self):
        if "name" in self._data:
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

    _modifier = {
        RED:    (0.50, 0.25),
        ORANGE: (0.75, 0.50),
        YELLOW: (1.00, 0.75),
        GREEN:  (1.05, 1.00),
        BLUE:   (1.20, 1.06),
        WHITE:  (1.32, 1.12),
        PURPLE: (1.44, 1.20),
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
    def __init__(self, db_string):
        self.value_list = [int(s) for s in db_string.split(".")]
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


class Weapon(RowModel):
    _list_fields = ["id", "wtype", "name"]
    _indexes = { "name": ["id"],
                 "wtype": ["id", "name"] }

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
        parts = self._row["sharpness"].split(" ")
        if len(parts) != 2:
            raise ValueError("Bad sharpness value in db: '%s'"
                             % self._row["sharpness"])
        normal, plus = parts
        self._data["sharpness"] = WeaponSharpness(normal)
        self._data["sharpness_plus"] = WeaponSharpness(plus)


class Monster(RowModel):
    _list_fields = ["id", "class", "name"]


class Item(RowModel):
    _list_fields = ["id", "type", "name"]
    _indexes = { "name": ["id"],
                 "type": ["id", "name"] }


class Location(RowModel):
    pass


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


class MonsterPartDamage(ModelBase):
    """
    Model for collecting the damage to the monster on a particular hitbox
    across different states.
    """
    def __init__(self, part):
        self.part = part
        self.states = {}

    def add_state(self, state, damage_row):
        self.states[state] = MonsterPartStateDamage(self.part, state,
                                                    damage_row)

    def as_data(self):
        return self.states


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
            part = row["body_part"]
            state = "Normal"
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
