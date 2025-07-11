import subprocess

from syncbuddy.log import logger
from syncbuddy.security.encryption import encrypt_srcdir
from syncbuddy.security.decryption import decrypt_dir
from syncbuddy.security.encryption_mode import EncryptionMode
from syncbuddy.globals import Globals
from syncbuddy.sync.job import SyncJob
from syncbuddy.sync.helper import preprocess_location, build_sync_jobs, assemble_rsync_cmd, select_sync_jobs
from syncbuddy.sync.matching import match_locations, check_matching_locations


def sync_locations(config, args):
	"""
    Synchronizes the source location with the destination location.

    Parameters:
    config : YAML configuration with all available locations and paths to be excluded from synchronization
    args : User-selected locations and synchronization parameters 

    Returns:
    bool: True if synchronization worked
    """
	src = config["locations"][args["src_location"]]
	dst = config["locations"][args["dst_location"]]

	# Some preprocessing steps are only necessary for the destination
	src["type"] = "src"
	dst["type"] = "dst"
	
	# Preprocess paths
	if not preprocess_location(src):
		logger.debug(f"Failed to preprocess source location \"{src['name']}\"")
		return False
	if not preprocess_location(dst):
		logger.debug(f"Failed to preprocess destination location \"{dst['name']}\"")
		return False

	logger.debug("Directories successfully processed.")

	# Check if the user wants to manually match source to destination directories.
	if args["manual_matching"]:
		if not match_locations(src, dst):
			return False
		
	# If not perform automatic matching (first source to first destination etc.)
	elif not check_matching_locations(src["processed_dirs"], dst["processed_dirs"]):
		return False
		
	logger.debug("Location matching check was successful.")

	# Build synchronization jobs
	sync_jobs = build_sync_jobs(src, dst)

	if len(sync_jobs) == 0:
		logger.debug(f"No synchronization jobs created.")
		return True
	else:
		logger.debug(f"A total of {len(sync_jobs)} synchronization jobs were created.")

	# Present synchronization jobs to the user and ask for confirmation
	sync_jobs = select_sync_jobs(args, sync_jobs)
	
	if not execute_sync_jobs(config, args, sync_jobs):
		return False
	
	print("All synchronization jobs were successfully executed.")
	return True



def execute_sync_jobs(config, args, sync_jobs : list[SyncJob]) -> bool:
	"""
	Execute a list of synchronization jobs using rsync, with optional encryption and decryption.

	Each job may:
		- Encrypt the source directory before transmission
		- Use rsync to transfer files
		- Decrypt `globals.CIPHERTEXT_ENDING` files at the destination

	Parameters:
		config (dict): Global configuration dictionary.
		args (dict): Runtime arguments, such as dry-run and deletion flags.
		sync_jobs (list): List of SyncJob objects defining source, destination, and encryption behavior.

	Returns:
		bool: True if all jobs succeeded without errors, False otherwise.
	"""
	num_errors = 0
	for job in sync_jobs:

		# Create destination path if necessary (rsync only creates the parent)
		if not job.dst.create_dir():
			logger.error(f"Failed to create destination directory \"{str(job.dst)}\"")
			continue

		# Encrypt source if required
		src_path = encrypt_srcdir(config, job) if job.encrypt else job.src
		if src_path is None:
			num_errors += 1
			continue

		# Copy source into the destination directory
		raw_dst_path = str(job.dst)
		if not raw_dst_path.endswith("/"):
			raw_dst_path += "/"

		# Append a trailing slash to the source path to copy only the directory's contents (not the directory itself).
		# Do this only when the directory is unencrypted, because for encrypted directories,
		# the ciphertext is a single file and adding a slash would cause incorrect transfer.
		raw_src_path = str(src_path)
		strip_outer_dir = False
		if not src_path.suffix: # It's a directory

			# Case: Unencrypted transfer — include directory contents, not the directory itself
			# Case: Encrypting contents of a sensitive directory in 'file' mode — include directory contents
			if not job.encrypt or job.encryption_mode == EncryptionMode.FILE:
				raw_src_path += "/"

			# Case: Decrypting a previously encrypted directory — remove the outer directory level
			if job.decrypt:
				strip_outer_dir = True


		rsync_cmd = assemble_rsync_cmd(args, job)		
		rsync_cmd += [raw_src_path, raw_dst_path]
		logger.debug(rsync_cmd)
		
		try:
			subprocess.run(rsync_cmd, check=True)
		except subprocess.CalledProcessError:
			logger.error("Rsync failed for current job.")
			num_errors+=1
			continue

		# Post-processing: decryption
		dst_path = job.dst.get_abs_path()
		gpg_files = list(dst_path.rglob(f"*{Globals.CIPHERTEXT_ENDING}"))

		for ciphertext in gpg_files:
			if not decrypt_dir(ciphertext, strip_outer_dir):
				num_errors+=1
		
	return num_errors == 0