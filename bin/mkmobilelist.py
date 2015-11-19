#!/usr/bin/env python

import sys
import json

import _pathfix

from mhapi.util import get_utf8_writer


def mk_html_list(dict_list, keys, sort_key):
    print '<ul data-role="listview" data-filter="true" data-autodividers="true">'
    for d in sorted(dict_list, key=lambda x: x[sort_key]):
        print "  <li>"
        for k in keys:
            print '    <span class="%s">%s</span>' % (k, d[k])
        print "  </li>"
    print '</ul>'


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        data = json.load(f)

    sys.stdout = get_utf8_writer(sys.stdout)
    mk_html_list(data, ("name", "name_jp"), "name")
