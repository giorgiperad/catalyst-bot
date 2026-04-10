"""Compatibility shim for the legacy chia_node module name.

The primary wallet runtime module is now sage_node.py. Importing from this file
keeps older code paths working during the transition.
"""

from sage_node import *  # noqa: F401,F403

