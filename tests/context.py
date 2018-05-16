# As recommended in http://docs.python-guide.org/en/latest/writing/structure/#test-suite

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tools
import conf