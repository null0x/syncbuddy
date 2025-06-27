import os
import shutil

from src.log import logger
from src.globals import Globals
from src. parser import parse_config, get_sync_arguments, check_pick_mode

def check_system_dependencies():
    """
    Checks whether all required system binaries are available in the system's PATH.

    This function iterates over the list of required system binaries defined in
    `Globals.REQUIRED_SYSTEM_BINS` and uses `shutil.which` to verify their presence.
    If any binary is missing, an error is logged and the function returns False.
    If all binaries are found, it returns True.

    Returns:
        bool: True if all required binaries are found, False otherwise.
    """
    for current_bin in Globals.REQUIRED_SYSTEM_BINS:
        path = shutil.which(current_bin)
        if path is None:
            logger.error(f"SyncMate requires {current_bin}. Please install it on your system.")
            return False
    return True


def init():
	"""
	Initializes SyncMate by performing system checks, parsing configuration,
	handling CLI arguments, and applying optional pick mode.

	Returns:
		tuple: (config, args) if successful, otherwise (None, None)
	"""
	# Check system dependencies
	if not check_system_dependencies():
		return None, None

	# Parse command-line arguments
	args = get_sync_arguments()
	if args is None:
		return None, None
	
	print_welcome_banner(args)

	# Parse configuration
	config = parse_config(args["config_file"])
	if config is None:
		return None, None
	
	# Some consistency checks
	locations = config.get("locations", {})
	
	if not args["src_location"] in locations:
		print(f"Source \"{args['src_location']}\" location not found in YAML configuration.")
		print(f"Available locations: {', '.join(locations.keys())}")
		return None, None
		
	if not args["dst_location"] in locations:
		print(f"Destination \"{args['dst_location']}\" location not found in YAML configuration.")
		print(f"Available locations: {', '.join(locations.keys())}")
		return None, None

	# Apply pick mode if selected
	config = check_pick_mode(config, args)

	return config, args


def ask_yes_no(prompt):
	"""
    Prompt the user with a yes/no question and return their response as a boolean

    Parameters:
    prompt (str): The question to display to the user

    Returns:
        bool: True if the user answers 'y' or 'yes', False if the 'n' or 'no'

	The function will repeatedly prompt until a valid response is given.
    """
	while True: 
		answer = input(prompt).strip().lower()
		if answer == "y" or answer == "yes":
			return True
		elif answer == "n" or answer == "no":
			return False
		else:
			print ("Please answer 'y', 'yes', 'n', or 'no'.")


def assemble_base_ssh_cmd(ssh_info):
	"""
	Assemble the base SSH command for the given location.

	Args:
		location: Dictionary containing SSH connection details.

	Returns:
		A list representing the SSH command (e.g., ['ssh', '-p', '22', 'user@host']),
		or None if required fields are missing.
	"""
	user = ssh_info.get("username")
	host = ssh_info.get("hostname")
	port = ssh_info.get("port")

	if not user:
		logger.error(f"Please provide an SSH username.")
		return None
	if not host:
		logger.error(f"Please provide an SSH hostname.")
		return None

	# Assemble SSH base
	ssh_cmd = ["ssh"]
	if port:
		ssh_cmd += [f"-p{port}"]
	ssh_cmd.append(f"{user}@{host}")

	return ssh_cmd

def clean_up(config):
	"""
    Remove the temporary directory used for GPG operations after synchronization.

    This function checks if a temporary directory is configured under `config["gpg"]["tmp_dir"]`.
    If it exists on the file system, it attempts to delete it recursively. Any failure to remove
    the directory is logged as a warning.

    Parameters:
        config (dict): Configuration dictionary that may contain a "gpg" section with a "tmp_dir" path.

    Logs:
        - A debug message if the temporary directory is successfully removed.
        - A warning message if removal fails due to an exception.
    """
	tmp_dir = config["gpg"].get("tmp_dir")
	if tmp_dir and os.path.exists(tmp_dir):
		try:
			shutil.rmtree(tmp_dir)
			logger.debug(f"Temporary directory {tmp_dir} removed.")
		except Exception as e:
			logger.warning(f"Failed to remove temporary directory {tmp_dir}: {e}")
			
def confirm_sync_jobs(args : dict, jobs : list):
	"""
	Display planned synchronization jobs and key settings, then prompt the user for confirmation.

	Parameters:
		args (dict): Contains configuration flags like 'dry_run' and 'remove_remote_files'.
		jobs (list): List of synchronization job objects, each expected to implement a `describe()` method.

	Returns:
		bool: True if the user confirms, False otherwise.
	"""
	print("\nThe following synchronization jobs are scheduled:\n")

	for i, job in enumerate(jobs, 1):
		print(f"  {i}. {job.describe()}")

	print("\nSettings:")
	print(f"  • Dry Run:                         {'Yes' if args['dry_run'] else 'No'}")
	print(f"  • Remove files at destination:     {'Yes' if args['remove_remote_files'] else 'No'}")

	return ask_yes_no("\nDo you want to continue? (y/n): ")


def print_welcome_banner(args):
    banner = fr"""
  _____                    ____            _     _       
 / ____|                 |  _ \          | |   | |      
| (___  _   _ _ __   ___ | |_) |_   _  __| | __| |_   _ 
 \___ \| | | | '_ \ / __||  _ <| | | |/ _` |/ _` | | | |
 ____) | |_| | | | | (__ | |_) | |_| | (_| | (_| | |_| |
|_____/ \__, |_| |_|\___||____/ \__,_|\__,_|\__,_|\__, |
         __/ |                                      __/ |
        |___/                                      |___/ 
                           
Author: Dominik Püllen
Year:   2025

Config: {args["config_file"]}
"""
    print(banner)