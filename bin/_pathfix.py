"""
Hack to get scripts to run from source checkout without having to set
PYTHONPATH.
"""

import sys
from os.path import dirname, join, abspath

bin_path = dirname(__file__)
project_path = abspath(join(bin_path, ".."))
sys.path.insert(0, project_path)

db_path = join(project_path, "db", "mh4u.db")
motion_values_path = join(project_path, "db", "motion_values.json")
web_path = join(project_path, "web")
