"""
Test configuration for pytest
"""

import os
import sys

# Add the src directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
