import argparse
import yaml
import os

from src.log import logger
from src.globals import Globals

def parse_config(path_to_config):
	"""
    Parses a YAML configuration file that defines locations to be synchronized

    Returns:
        dict: A dictionary containing the configuration data, including:
        - 'locations': List of locations to be synchronized.

    Raises:
    FileNotFoundError: If the configuration file does not exist.
    yaml.YAMLError: If the file contains invalid YAML.
    KeyError: If expected keys like 'locations' or 'exclude_folders' are missing.
    """
	
	try:
		with open(path_to_config) as f:
			config = yaml.safe_load(f)
	except FileNotFoundError:
		logger.error(f"Configuration file \"{path_to_config}\" not found.")
		return None
		
	# Print some debug information
	logger.debug(f"Configuration contains {len(config['locations'])} locations.")
	
	return config

def get_sync_arguments():
	"""
	Parses and validates command-line arguments for SyncBuddy.

	Returns:
		dict: A dictionary of parsed and validated arguments,
				or None if validation fails.
	"""
	parser = argparse.ArgumentParser(description="Synchronizes a source location with a destination location.")
	parser.add_argument("--config", type=str, help="Path to the configuration YAML file")
	parser.add_argument("--src", required=True, help="Source location (e.g., local")
	parser.add_argument("--dst", required=True, help="Destination location (e.g., usb")
	parser.add_argument("--dry", action="store_true",  help="Make a dry (test) run.")
	parser.add_argument("--remove", action="store_const", const=True, default=True, help="Remove files from destination that do not exist on source.")
	parser.add_argument("--encrypt", action="store_true", default=False, help="Encrypt source if you are in pick mode.")
	parser.add_argument("--match", action="store_true", help="Manually pair source and destination directories.")
	args = parser.parse_args()

	dry_run = args.dry
	remove_remote_files = False #args.remove 

	src_location, src_path = args.src.split(":") if ":" in args.src else (args.src, None)
	dst_location, dst_path = args.dst.split(":") if ":" in args.dst else (args.dst, None)

	if dst_path == None and args.encrypt:
		print("Ignoring --encrypt option as you did not pick a destination.")

	if src_location == dst_location:
		print("Source and destination location must not be equal.")
		return None
	
	# Check if user provided a configuration file
	config_file = args.config if args.config is not None else Globals.DEFAULT_CONFIG_FILE

	return {
		"src_location" : src_location,
		"dst_location" : dst_location,
		"src_path": src_path,
		"dst_path": dst_path,
		"dry_run" : dry_run, 
		"manual_matching" : args.match,
		"encrypt_src" : args.encrypt,
		"config_file" : config_file,
		"remove_remote_files" : remove_remote_files}


def check_pick_mode(config, args):
	"""
	Modifies the configuration to enable 'pick mode' based on user-specified source or destination paths.

	In pick mode, the user provides a specific source (`src_path`) or destination (`dst_path`) path, 
	which overrides the corresponding location's configured directories. This allows ad-hoc syncing 
	of individual files or directories rather than using predefined config entries.

	The function also handles optional encryption/decryption flags:
		- If the source is a `.gpg` file and the destination appears to be a directory, decryption is enabled.
		- If the `--encrypt` flag (`encrypt_src`) is set, encryption is enabled for the destination and 
		the source is marked sensitive.
		- A warning is logged if encryption is requested on an already-encrypted (`.gpg`) source file.

	Args:
		config (dict): A configuration dictionary with a "locations" section containing 
						source/destination settings.
		args (dict): A dictionary containing user arguments. Expected keys:
			- "src_path" (str, optional): Custom source path to sync from.
			- "dst_path" (str, optional): Custom destination path to sync to.
			- "src_location" (str): Key in `config["locations"]` for the source.
			- "dst_location" (str): Key in `config["locations"]` for the destination.
			- "encrypt_src" (bool): Whether to encrypt data from the source.

	Returns:
		dict: The updated `config` dictionary with modified `dirs` and sensitivity flags based on user input.
	"""
	# Pick mode is enabled if the user provided a specific directory or file as part of the source or destination location
	# In that case, all the directories given in the configuration files are ignored and overwritten with the user-defined path
	src_path = args.get("src_path")
	dst_path = args.get("dst_path")
	new_src_dirs = None

	config["pickmode"] = False

	# True if user provided a specific path for the source location
	if src_path is not None:
		logger.debug("Pick mode enabled for source.")
		config["pickmode"] = True
		decryption = src_path.endswith(Globals.CIPHERTEXT_ENDING)
		new_src_dirs = [{"path": src_path}]
		_, dst_ext = os.path.splitext(dst_path or "")

		# Enable decryption if source is encrypted and destination is a directory
		if decryption and not dst_ext:
			logger.debug("Decryption enabled for source.")
			config["locations"][args["src_location"]]["trusted"] = False
			new_src_dirs[0]["sensitive"] = True
	
		else:
			logger.debug("Source now considered untrusted to prevent decryption.")
			config["locations"][args["src_location"]]["trusted"] = False


	# True if user provided a specific path for the destination location
	if dst_path is not None:
		logger.debug("Pick mode enabled for destination.")
		config["pickmode"] = True
		dst_dir = {"path": dst_path}

		# Check if data should be encrypted (provided by user as input argument)
		if args.get("encrypt_src"):
			logger.debug("Encryption enabled for source in pick mode.")
			if src_path and src_path.endswith(".gpg"):
				logger.warning("You are trying to encrypt an already encrypted source.")
			config["locations"][args["dst_location"]]["trusted"] = False

			# Mark source sensitive (create if missing)
			if new_src_dirs is not None:
				new_src_dirs[0]["sensitive"] = True

		# Tag the destination path sensitive if sensitive data will be decrypted from it or
		# encrypted before being stored there.
		if args.get("encrypt_src") or decryption:
			dst_dir["sensitive"] = True

		# Overwrite destination dirs from configuration
		config["locations"][args["dst_location"]]["dirs"] = [dst_dir]

	# Overwrite source dirs from configuration
	if new_src_dirs is not None:
		config["locations"][args["src_location"]]["dirs"] = new_src_dirs
		
	return config