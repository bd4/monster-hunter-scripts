import string
import json


class RowModel(object):
    def __init__(self, row):
        self._row = row
        self.id = row["_id"]

    def __getattr__(self, name):
        try:
            return self._row[name]
        except IndexError:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, name))

    def as_dict(self):
        d = dict(self._row)
        d["id"] = d["_id"]
        del d["_id"]
        return d

    def as_json(self):
        data = self.as_dict()
        return json.dumps(data)


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
        return self._one_line_template.substitute(self.as_dict())

    def full_u(self):
        return self._full_template.substitute(self.as_dict())

    def __unicode__(self):
        return self.full_u()

