from src.log import logger
from src.path_wrapper import DirectoryWrapper, MyPath
from src.sync_job import SyncJob
from src.security import check_security
from src.utils import ask_yes_no
from pathlib import Path

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
			dst_rel_parent = Path(sens_dir.sub_pth).parent

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


def select_sync_jobs(args : dict, jobs : list):
	"""
	Display planned synchronization jobs and key settings, then prompt the user for selection.

	Parameters:
		config (dict): Configuration flags like 'dry_run' and 'remove_remote_files'.
		jobs (list): List of synchronization job objects, each must have a `describe()` method.

	Returns:
		list: List of selected jobs, or an empty list if the user cancels.
	"""
	if not jobs:
		print("No synchronization jobs scheduled.")
		return []
	
	print("\nThe following synchronization jobs are scheduled:\n")

	for i, job in enumerate(jobs, 1):
		print(f"  {i}. {job.describe()}")

	print("\nSettings:")
	print(f"  • Dry Run:                         {'Yes' if args['dry_run'] else 'No'}")
	print(f"  • Remove files at destination:     {'Yes' if args['remove_remote_files'] else 'No'}")

	print("")

	selected_jobs = list()
	canceled = False

	while True:
		selection = input("Select jobs to execute ([all], [X], [X:Y], [X,Y,Z], or [q] to quit): ").strip().lower()

		if selection in {"q", "quit"}:
			print("Selection canceled. No jobs selected.")
			canceled = True
			break 
		
		if selection == "all":
			selected_jobs = [(i, job) for i, job in enumerate(jobs)]
			break

		# Single index
		if selection.isdigit():
			index = int(selection)
			if 1 <= index <= len(jobs):
				selected_jobs = [(index-1, jobs[index - 1])]
				break
			else:
				print(f"Invalid number: must be between 1 and {len(jobs)}.")

		# Range like 2:5
		elif ":" in selection:
			try:
				start_str, end_str = selection.split(":")
				start, end = int(start_str), int(end_str)
				if 1 <= start < end <= len(jobs):
					selected_jobs = [(i, jobs[i]) for i in range(start-1, end)]
					break
				else:
					print(f"Invalid range: start must be < end and both within 1–{len(jobs)}.")
			except ValueError:
				print("Invalid range format. Use X:Y with numeric values.")

		# Comma-separated list like 1,3,5
		elif "," in selection:
			try:
				indices = [int(s.strip()) for s in selection.split(",")]
				if all(1 <= i <= len(jobs) for i in indices):
					# Use set to remove duplicates while preserving order
					unique_indices = sorted(set(indices), key=indices.index)
					selected_jobs = [(i, jobs[i - 1]) for i in unique_indices]
					break
				else:
					print(f"One or more numbers out of valid range (1–{len(jobs)}).")
			except ValueError:
				print("Invalid list format. Use digits separated by commas, like 1,3,5.")

		else:
			print("Unrecognized input. Try again.")

	if canceled:
		return list()
	
	print("\n You selected the following synchronization jobs:\n")

	for i, job in selected_jobs:
		print(f"  {i+1}. {job.describe()}")

	if not ask_yes_no("\nDo you want to continue? (y/n): "):
		selected_jobs = list()
	
	return [job for _, job in selected_jobs]