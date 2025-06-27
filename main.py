#!/usr/bin/env python3

"""
backup.py

Synchronizes a source location with a destination location, supporting encryption and decryption
of sensitive data. Utilizes tar, gpg, and rsync for archiving, encrypting, and synchronization.

Author:   Dominik Püllen
Date:     2025-06-07
Version:  1.0
"""

from src.sync import sync_locations
from src.utils import init, clean_up


def main():

	# 1. Init SyncBuddy
	config, args = init()

	if config != None and args != None:

		# 2. Synchronize locations
		sync_locations(config, args)

		# 3. Clean up
		clean_up(config)
	
if __name__ == "__main__":
    main()