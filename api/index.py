import sys
import os

# Add the project root to the Python path so it can find app.py and utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app instance from the main app.py file
from app import app
