import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add your project folder to sys.path
project_home = os.path.expanduser('~/HomiMeet_FullApp')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
