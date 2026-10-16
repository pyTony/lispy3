"""Lispy regression tests; see tests/support.py for how to run them."""
import os
import sys

# Lets `python -m unittest` from the repository folder find tests/support.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
