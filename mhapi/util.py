"""
Shared utility classes and functions.
"""


class EnumBase(object):
    _names = dict()

    @classmethod
    def name(cls, enum_value):
        return cls._names[enum_value]
