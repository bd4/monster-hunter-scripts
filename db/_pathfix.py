"""
Hack to get scripts to run from source checkout without having to set
PYTHONPATH.
"""

import sys
from os.path import dirname, join, abspath

db_path = dirname(__file__)
project_path = abspath(join(db_path, ".."))
sys.path.insert(0, project_path)
