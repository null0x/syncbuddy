from syncbuddy.log import logger
from syncbuddy.path_wrapper import DirectoryWrapper

def match_locations(src, dst):

	src_dirs = src.get("processed_dirs")
	dst_dirs = dst.get("processed_dirs")

	ordered_src = list()
	ordered_dst = list()

	# Iterate over all source directories and present possible destinations
	for current_src in src_dirs:
	
		dst_candidates = [d for d in dst_dirs if DirectoryWrapper.are_syncable(current_src, d)]

		if not dst_candidates:
			logger.debug(f"No syncable destinations for source: {current_src.get_dir_path()}")
			continue

		print(f"\nType number of destination for: {current_src.get_dir_path()}")

		for i, current_candidate in enumerate(dst_candidates):
			print(f"{i + 1} - {current_candidate.get_dir_path()}")

	
		# Validate input
		while True:
			selected = input("Enter dst number: ")
			if selected.isdigit():
				selected_idx = int(selected) - 1
				if 0 <= selected_idx < len(dst_candidates):
					break
			print("Invalid input.")
		
		selected_dst = dst_candidates[int(selected_idx)]
		
		logger.debug(f"Selected {selected_dst.get_dir_path()}")

		ordered_src.append(current_src)
		ordered_dst.append(selected_dst)

	src["processed_dirs"] = ordered_src
	dst["processed_dirs"] = ordered_dst

	if(len(ordered_src) == 0):
		print("Nothing to synchronize!")
		
	return True

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