from odmf.config import conf

from odmf import db
import pandas as pd
import os
import numpy as np
session = db.Session()

# Set default user
from odmf.webpage import auth
auth.users.load()
auth.users.set_default('philipp')
