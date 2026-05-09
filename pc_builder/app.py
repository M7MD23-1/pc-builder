import sys
import os

# Add backend directory to Python path so it can resolve imports like 'from data_loader import load_components'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import app

if __name__ == "__main__":
    app.run()
