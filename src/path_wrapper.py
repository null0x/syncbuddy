from pathlib import Path
from typing import Optional

import os
import glob
import subprocess
import shlex

from src.log import logger
from src.utils import assemble_base_ssh_cmd

class MyPath:
    def __init__(self, sys_root: str, pth_root: str = "", sub_pth: str = "", ssh_info: Optional[dict] = None):
        # Store components
        self.sys_root = sys_root
        self.pth_root = pth_root
        self.sub_pth = sub_pth

        self.abs_path = Path(self.sys_root) / self.pth_root / self.sub_pth # strips wildcards
        self.raw_path = os.path.join(self.sys_root, self.pth_root, self.sub_pth)

        self.has_wildcards = glob.has_magic(self.raw_path)
        self.ssh_info = ssh_info

    def is_dir(self) -> bool:
        # TODO Extend for remote path
        return self.abs_path.is_dir() if self.ssh_info is None else False

    def get_abs_path(self) -> Path:
        return self.abs_path
          
        
    def has_suffix(self, suffix: str) -> bool:
        return self.abs_path.suffix.lower() == suffix.lower()

    def __str__(self) -> str:
        """String representation using POSIX path."""
        if self.ssh_info == None:
            return self.get_abs_path().as_posix()
        
        user = self.ssh_info.get("username")
        host = self.ssh_info.get("hostname")
        if user and host:
            return f"{user}@{host}:{str(self.get_abs_path())}"
        return None

    def exists(self) -> bool:

        if self.ssh_info is None:
            if self.has_wildcards:
                logger.debug(f"Path {self.abs_path} has wildcards.")
                return glob.glob(self.raw_path)
            return self.abs_path.exists()
        else:
            check_cmd = assemble_base_ssh_cmd(self.ssh_info)
            check_cmd += [f"stat {shlex.quote(str(self.abs_path))}"]
            result = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.returncode == 0
        
    def create_dir(self):
		
        # Create a local directory
        if self.ssh_info is None:	
            try:
                self.abs_path.mdkir(parent=True, exist_ok=True)
                return True
            except OSError as e:
                print(f"Failed to create local directory {self.abs_path}: {e}")
                return False
            
        else:
            # Create a remote directory
            create_cmd = assemble_base_ssh_cmd(self.ssh_info)
            cmd += [f"mkdir -p {shlex.quote(str(self.abs_path))}"]

            result = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)			

            if result.returncode == 0:
                logger.debug(f"Successfully created remote directory '{self.abs_path}'.")
                return True
            else:
                logger.debug(f"Failed to create remote directory: {result.stderr.strip()}")
                return False


class DirectoryWrapper():
    """Represents a path inside a location"""

    def __init__(self, sys_root: str, pth_dir: str, ssh_info: dict = None, sensitive : bool = False):
        """
        Initialize a directory wrapper from a root path.
        Validates the root path and prepares for processing subdirectories.
        """
        if pth_dir.startswith("/"):
            raise ValueError(f"Absolute path ignored: {pth_dir}")

        cleaned_pth_root = pth_dir.rstrip("/")
        if cleaned_pth_root != pth_dir:
            logger.warning(f"Removed trailing slash from path {pth_dir} to avoid misinterpretations.")

        self.ssh_info: dict = ssh_info
        self.root_path: MyPath = MyPath(sys_root, cleaned_pth_root, "", ssh_info)
        self.sensitive_folders: list[MyPath] = []
        self.exclude_dirs: list[MyPath] = []
        self.is_sensitive: bool = sensitive

    
    @staticmethod
    def are_syncable(src : "DirectoryWrapper", dst : "DirectoryWrapper") -> bool:
        return src.is_sensitive == dst.is_sensitive

    def get_dir_path(self) -> MyPath:
        return self.root_path
    

    def __str__(self) -> str:
        if self.ssh_info == None:
            return str(self.root_path)
        
        username = self.ssh_info["username"]
        hostname = self.ssh_info["hostname"]
        if username and hostname:
            return f"{username}@{hostname}:{self.root_path}"
        
    def is_remote(self):
        return self.ssh_info != None  

    def process_sensitive_folders(self, sens_folders: list[str]):
        """
        Register sensitive folders and validate their existence.
        """
        if self.is_sensitive:
            logger.debug(f"Sensitive sub-folders are ignored because the entire directory is marked sensitive.")
        else:
            for subdir in sens_folders:
                try:
                    # Ignore empty directories
                    if subdir == None:
                        logger.warning("Ignoring empty sensitive directory.")
                        continue

                    path = MyPath(self.root_path.sys_root, self.root_path.pth_root, subdir, self.ssh_info)
                    if path:
                        self.sensitive_folders.append(path)
                        self.exclude_dirs.append(path)  # Assumes all sensitive dirs are also excluded
                except FileNotFoundError as e:
                    logger.warning(str(e))

    def process_exclude_paths(self, exclude_subdirs: list[str]):
        """
        Register exclude folders and validate their existence, or ask user to ignore.
        """
        for subdir in exclude_subdirs:
            try:
                # Ignore empty directories
                if subdir == None:
                    logger.warning("Ignoring empty exclude directory.")
                    continue
                
                path = MyPath(self.root_path.sys_root, self.root_path.pth_root, subdir, self.ssh_info)
                if path:
                    self.exclude_dirs.append(path)
            except FileNotFoundError as e:
                logger.warning(str(e))

    def check_exclude_dirs(self):
        for exclude_dir in self.exclude_dirs:
            if not exclude_dir.exists():
                logger.warning(f"Exclude directory {exclude_dir} does not exist.")


    def get_exclude_dirs(self):
        '''
        Returns list of exclude paths that are relative to self.pth_root (required by rsync)
        '''

        return [ex_pth.sub_pth for ex_pth in self.exclude_dirs]