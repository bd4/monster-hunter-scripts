
from collections import defaultdict
HEAD, BODY, ARMS, WAIST, LEGS = 0, 1, 2, 3, 4

class ArmorSet(object):
    def __init__(self, armors, max_weapon_slots=1):
        if len(armors) == 6:
            self.armors = armors[:5]
            self.charm = armors[5]
        elif len(armors) == 5:
            self.armors = armors
            self.charm = None
        else:
            raise ValueError("armors must be 5 armors or 5 plus charm obj")
        self.max_weapon_slots = max_weapon_slots

        self.slots = { 1: 0, 2: 0, 3: 0 }
        self.torso_slots = 0
        self.skills = defaultdict(int)
        self.activated_strees = set()
        self.defense = 0
        self.max_defense = 0

        self.torso_up = 0

        for i, armor in enumerate(self.armors):
            if armor is None:
                continue
            self.defense += armor.defense
            self.max_defense += armor.max_defense

            torso_up = ("Torso Up" in armor.skills)
            if torso_up:
                armor = self.armors[BODY]
                self.torso_up += 1
            for sname in armor.skill_names:
                self.skills[sname] += armor.skills[sname]
                if self.skills[sname] > 10:
                    self.activated_strees.add(sname)
            if i == BODY:
                self.torso_slots = armor.num_slots
            elif not torso_up and armor.num_slots:
                self.slots[armor.num_slots] += 1
        if not self.torso_up:
            self.slots[self.torso_slots] += 1
            self.torso_slots = 0
        if self.charm:
            for sname, spoints in self.charm.skills.iteritems():
                self.skills[sname] += spoints

    def decorate(self, wanted_stree_points, decoration_values):
        missing_points = []
        ds = defaultdict(0)
        for stree_name, points_needed in wanted_stree_points.iteritems():
            missing = points_needed - self.skills.get(stree_name, 0)
            if missing > 0:
                dvs = decoration_values[stree_name][1]
                if dvs[2] == 0 and dvs[0] > 0:
                    dvs[2] = dvs[0] * 3
                missing_points.append([missing, dvs[1], stree_name])
        slots_left = dict(self.slots)
        def get_sort_key(num_slots):
            def sort_key(a):
                # sort by
                return a[1][:num_slots] + [a[0]]
        for nslots in (3, 2, 1):
            while slots_left[nslots]:
                missing_points.sort()
                for missing, dvs, stree_name in missing_points:
                    for slots_size in xrange(len(dvs), 0, -1):
                        slots_left, total = decorate_slots(3, dvs, missing)


class SkillTreeDecorationConfig(object):
    def __init__(self, slots_avialable, torso_slots, torso_up_points,
                 points_needed, dv):
        self.slots_available = slots_available
        self.torso_slots = torso_slots
        self.torso_up_points = torso_up_points
        self.points_needed = points_needed
        self.dv = dv
        self.tudv = torso_up_dv(torso_slots, torso_up_points, dv)

        self.current_max = dict(self.slots_available)
        self.nonzero_slots = [nslots for nslots in (3, 2, 1)
                              if dv[nslots-1] > 0]
        if torso_up_points:
            self.nonzero_slots.insert(0, 4)
            self.current_max[4] = torso_slots
            self.slots_available[4] = torso_slots
        else:
            self.current_max[4] = 0
            self.slots_available[4] = 0
        for nslots in (1, 2, 3):
            i = nslots - 1
            if dv[i] == 0:
                self.current_max[nslots] = 0
        self.nonzero_slot_idx = len(self.nonzer_slots) - 1


    def __iter__():
        points_left = self.points_needed
        slots_used = { 1: 0, 2: 0, 3: 0, 4: 0}

        # greedy based on best decoration, e.g. for 1 slot 2 point
        # skills, fill tup first, then singles

        while points_left > 0:
            # greedy - fill with as many torso up as we are allowed, then
            # go to 3 slot, then to 2 slots, etc
            if self.current_max[4]:
                nslots, points = best_decoration(points_left, self.tudv,
                                                 self.current_max[4])
                points_left -= points
                slots_used[4] += nslots
                continue

            max_slots = 3
            while max_slots > 0:
                if self.current_max[max_slots] - slots_used[max_slots]:
                    break
                max_slots -= 1
            if max_slots == 0:
                raise StopIteration()
            nslots, points = best_decoration(points_left, self.dv, max_slots)
            slots_used[nslots] += 1
            points_left -= points

        if self.current_nslots == 1:
            self.current_nslots = 4

        if self.current_slots == 4:
            self.current_max_tup_slots -= 1
        #elif self.current

        yield slots_used


class SlotConfig(object):
    def __init__(self, dv, points_needed):
        self.dv = db
        self.points_needed = points_needed
        # 7 locations, each can be 1, 2, or 3 slots, or 1, 2, or 3 tup
        # slots. Tup can be x2, x3, x4, or x5

        # 3 tup x5
        # 2 tup x5
        # 1 tup x5
        # 3 tup x4 + 1
        # 3 tup x4 + 2
        # 3 tup x4 + 3
        # 2 tup x4 + 3
        # 2 tup x4 + 2
        # 2 tup x4 + 1


def best_decoration(points_needed, dv, max_slots=3):
    rval = 0, 0
    for nslots in xrange(max_slots, 0, -1):
        i = nslots - 1
        if dv[i] == 0:
            continue
        if points_needed > dv[i]:
            break
        rval = nslots, dv[i]
    return rval


def decorate_slots(num_slots, decoration_values, needed):
    # Fill one piece with decorations
    max_slots = num_slots
    for i, value in enumerate(decoration_values):
        nslots = i + 1
        if nslots > max_slots:
            break
        if value >= needed:
            max_slots_needed = nslots
            break
    decoration_values = decoration_values[:max_slots_needed]

    slots_left = num_slots
    for slots in xrange(max_slots, 0, -1):
        if slots_left == 0:
            break
        decoration_value = decoration_values[slots-1]
        if not decoration_value:
            continue
        while slots <= slots_left and needed > 0:
            needed -= decoration_value
            slots_left -= slots
    return slots_left, needed


def torso_up_dv(torso_slots, torso_up_points, dv):
    """
    Given the specified number of available torso slots and torso up points,
    calculate the number of skill points given by each decoration type when
    slotted into the torso.
    """
    tudv = list(dv)
    for nslots in (1, 2, 3):
        i = nslots - 1
        if nslots > torso_slots:
            tudv[i] = 0
        else:
            tudv[i] = dv[i] * (torso_up_points + 1)
    return tudv


if __name__ == '__main__':
    dvlist = [(0,1,3), (1,0,0), (1,0,4), (1,3,0), (1,3,5), (2,0,0)]
    for torso_slots in (0, 1, 2, 3):
        for dv in dvlist:
            for torso_up_points in (1, 2, 3):
                print torso_slots, dv, torso_up_points, \
                      torso_up_dv(torso_slots, torso_up_points, dv)
