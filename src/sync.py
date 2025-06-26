import subprocess

from src.log import logger
from src.utils import confirm_sync_jobs
from src.security import encrypt_dir, decrypt_dir, check_security
from src.path_wrapper import DirectoryWrapper, MyPath
from src.sync_job import SyncJob
from src.globals import Globals

def check_matching_locations(src_paths, dst_paths):
	"""
    Verify that each source path has a corresponding destination path and that
    their sensitivity levels match.
    Parameters:
        src_paths (list): List of source location objects with `get_dir_path()` and `is_sensitive`.
        dst_paths (list): List of destination location objects with `get_dir_path()` and `is_sensitive`.

    Returns:
        bool: True if all checks pass, False otherwise.
    """

	# Print destination paths without a source.
	if len(src_paths) < len(dst_paths):
		for i in range(len(src_paths),  len(dst_paths)):
			logger.warning(f"No source for \"{dst_paths[i].get_dir_path()}\".")

	# Check sensitivity (Transmitting sensitive data to a non-sensitive location may be a security concern)
	for i, src in enumerate(src_paths):
		src_path = src.get_dir_path()

		if i >= len(dst_paths):
			logger.error(f"Source directory \"{src_path}\" does not have a matching destination.")
			return False
		
		dst = dst_paths[i]
		dst_path = dst.get_dir_path()

		if src.is_sensitive != dst.is_sensitive:
			logger.error(
                f"Sensitivity mismatch: \"{src_path}\" (sensitive={src.is_sensitive}) and "
                f"\"{dst_path}\" (sensitive={dst.is_sensitive}) must match."
            )
			return False
		
	return True

def assemble_rsync_cmd(args, sync_job: SyncJob) -> list[str]:
	"""
	Assemble the rsync command used to synchronize files for a given sync job.

	Parameters:
		args (dict): Global arguments such as 'dry_run' and 'remove_remote_files'.
		sync_job (SyncJob): Job configuration, including excludes and optional SSH info.

	Returns:
		list[str]: A list of rsync command components ready to be executed via subprocess.
	"""
	rsync_command = ["rsync", "-avz", "--info=progress2"]

	# Add exclude patterns
	rsync_command.extend(["--exclude", str(ex)] for ex in sync_job.excludes)
	rsync_command = [item for sublist in rsync_command for item in (sublist if isinstance(sublist, list) else [sublist])]

	# Add dry-run flag
	if args.get("dry_run", False):
		rsync_command.append("--dry-run")

	# Add deletion of remote files
	if args.get("remove_remote_files", False):
		rsync_command.append("--delete")

	# Use SSH if port is specified
	ssh_info = sync_job.ssh
	if ssh_info and ssh_info.get("port"):
		rsync_command.extend(["-e", f"ssh -p {ssh_info['port']}"])

	return rsync_command

def build_sync_jobs(src_location: dict, dst_location: dict) -> list[dict]:
	sync_jobs = []
	dst_trusted = dst_location.get("trusted", False)

	for src_dir, dst_dir in zip(src_location["processed_dirs"], dst_location["processed_dirs"]):
		dst_ssh = dst_dir.ssh_info
		src_ssh = src_dir.ssh_info

		# Check if exclude directory exists
		src_dir.check_exclude_dirs()

		# Main sync job
		encrypt, decrypt = check_security(src_dir, dst_trusted)
		sync_jobs.append(SyncJob(
			src=src_dir.get_dir_path(),
			dst=dst_dir.get_dir_path(),
			encrypt=encrypt,
			decrypt=decrypt,
			excludes=src_dir.get_exclude_dirs(),
			ssh=dst_ssh or src_ssh
		))

		# Create an individual sync job for each sensitive folder (always encrypted)
		dst_base_path = dst_dir.get_dir_path()
		for sens_dir in src_dir.sensitive_folders:
			dst_rel_parent = sens_dir.sub_pth.parent

			# Necessary to keep directory structure at the destination
			dst_abs_path = MyPath(dst_base_path.sys_root, dst_base_path.pth_root, dst_rel_parent, ssh_info=dst_ssh)

			sync_jobs.append(SyncJob(
				src=sens_dir,
				dst=dst_abs_path,
				encrypt=True,
				decrypt=False,
				excludes=[],
				ssh=dst_ssh
			))

	logger.debug("Created %d synchronization job(s).", len(sync_jobs))
	return sync_jobs


def preprocess_location(location):
	"""
    Preprocesses a location configuration by computing absolute paths, cleaning them,
    ensuring remote directories exist, and constructing remote access paths when needed.

    Parameters
    ----------
    location : dict

    Returns
    -------
    bool
        True if preprocessing succeeded, False otherwise.
    """
	logger.debug(f'Processing location "{location.get("name")}"')
	ssh_info = location.get("ssh")
	location_type = location.get("type")
	root_dir = location.get("root_dir")
	location["processed_dirs"] = []

	# Parse directories
	for loc_to_sync in location.get("dirs", []):
		sensitive = loc_to_sync.get("sensitive", False)
		loc = DirectoryWrapper(root_dir, loc_to_sync["path"], ssh_info, sensitive)

		# Check if source directory exist
		dir_path = loc.get_dir_path()
		if location_type == "src" and not dir_path.exists():
			logger.warning(f"Source directory {dir_path} does not exist. Nothing to synchronize!")
			continue

		else:
			logger.debug(f"Directory {dir_path} exists.")

				
		# Process exclude and sensitive directories
		try:
			if location_type == "src":
				if "exclude_folders" in loc_to_sync:
					loc.process_exclude_paths(loc_to_sync["exclude_folders"])
				if "sensitive_folders" in loc_to_sync:
					loc.process_sensitive_folders(loc_to_sync["sensitive_folders"])
		except FileNotFoundError as e:
			logger.error(f"Error processing directory: {e}")
			return False

		location["processed_dirs"].append(loc)
	

	return True


def execute_sync_jobs(config, args, sync_jobs):
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
		rsync_cmd = assemble_rsync_cmd(args, job)
		src_path_str = job.src.get_abs_path()

		# Encrypt source if required
		if job.encrypt:		
			src_path_str = encrypt_dir(config, job)	
			if src_path_str is None:
				num_errors += 1
				continue

		# Append a trailing slash to the source path to copy only the directory's contents (not the directory itself).
		# Do this only when the directory is unencrypted, because for encrypted directories,
		# the ciphertext is a single file and adding a slash would cause incorrect transfer.
		raw_dst_path = str(job.dst)
		if not raw_dst_path.endswith("/"):
			raw_dst_path += "/"

		raw_src_path = str(job.src) if not job.encrypt else str(src_path_str)
		if not src_path_str.suffix:
			raw_src_path += "/"

		rsync_cmd += [raw_src_path, raw_dst_path]

		try:
			subprocess.run(rsync_cmd, check=True)
		except subprocess.CalledProcessError:
			logger.error("Rsync failed for current job.")
			num_errors+=1
			continue

		# Check if there are any encrypted directories
		dst_path = job.dst.get_abs_path()
		gpg_files = list(dst_path.rglob(f"*{Globals.CIPHERTEXT_ENDING}"))

		for ciphertext in gpg_files:
			if not decrypt_dir(ciphertext, job.decrypt):
				num_errors+=1
		
	return num_errors == 0


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

	# Check if each source location has a matching destination location
	if not check_matching_locations(src["processed_dirs"], dst["processed_dirs"]):
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
	if not confirm_sync_jobs(args, sync_jobs):
		return False
	
	if not execute_sync_jobs(config, args, sync_jobs):
		return False
	
	logger.debug(f"All synchronization jobs were successfully executed.")
	return True