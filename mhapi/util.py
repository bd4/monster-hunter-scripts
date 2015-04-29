"""
Shared utility classes and functions.
"""

import codecs


class EnumBase(object):
    _names = dict()

    @classmethod
    def name(cls, enum_value):
        return cls._names[enum_value]


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)
