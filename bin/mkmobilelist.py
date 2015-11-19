#!/usr/bin/env python

import sys
import json

import _pathfix

from mhapi.util import get_utf8_writer


def mk_html_list(dict_list, keys, sort_key):
    print """
<form class="ui-filterable">
  <input id="filterlist" data-type="search">
</form>
"""
    print '<ul data-role="listview" data-filter="true" input="#filterlist">'
    for d in sorted(dict_list, key=lambda x: x[sort_key]):
        print '<li>%s</li>' % " ".join(d[k] for k in keys)
    print '</ul>'


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        data = json.load(f)

    sys.stdout = get_utf8_writer(sys.stdout)
    mk_html_list(data, ("name", "name_jp"), "name")
