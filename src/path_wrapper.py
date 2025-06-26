from pathlib import Path
from typing import Optional

import subprocess
import shlex

from src.log import logger
from src.utils import assemble_base_ssh_cmd

class MyPath:
    def __init__(self, sys_root: str, pth_root: str = "", sub_pth: str = "", ssh_info: Optional[dict] = None):
        self.sys_root: Path = Path(sys_root)
        self.pth_root: Path = Path(pth_root)
        self.sub_pth: Path = Path(sub_pth)
        self.ssh_info = ssh_info  

    def is_dir(self) -> bool:
        return self.get_abs_path().is_dir()

    def get_abs_path(self) -> Path:
        return self.sys_root / self.pth_root / self.sub_pth
        
    def has_suffix(self, suffix: str) -> bool:
        """Check if the absolute path ends with the given suffix."""
        path_suffix = self.get_abs_path().suffix
        return path_suffix.lower() == suffix.lower()

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
        this_path = self.get_abs_path()
        if self.ssh_info is None:
            return this_path.exists()
        else:
            check_cmd = assemble_base_ssh_cmd(self.ssh_info)
            check_cmd += [f"stat {shlex.quote(str(this_path))}"]
            result = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.returncode == 0
        
    def create_dir(self):
        this_path = self.get_abs_path()
		
        # Create a local directory
        if self.ssh_info is None:	
            try:
                this_path.get_abs_path().mdkir(parent=True, exist_ok=True)
                return True
            except OSError as e:
                print(f"Failed to create target destination {this_path}: {e}")
                return False
            
        else:
            # Create a remote directory
            create_cmd = assemble_base_ssh_cmd(self.ssh_info)
            create_cmd += [f"mkdir -p '{this_path}'"]

            result = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)			

            if result.returncode == 0:
                logger.debug(f"Successfully created remote directory '{this_path}'.")
                return True
            else:
                return False


class DirectoryWrapper():

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
            logger.warning(f"Sensitive sub-folders are ignored because the entire directory is marked sensitive.")
        else:
            for subdir in sens_folders:
                #path = self._build_and_validate_path(subdir, tag="Sensitive folder")
                path = MyPath(self.root_path.sys_root, self.root_path.pth_root, subdir, self.ssh_info)
                if path:
                    self.sensitive_folders.append(path)
                    self.exclude_dirs.append(path)  # Assumes all sensitive dirs are also excluded

    def process_exclude_paths(self, exclude_subdirs: list[str]):
        """
        Register exclude folders and validate their existence, or ask user to ignore.
        """
        for subdir in exclude_subdirs:
            try:
                #path = self._build_and_validate_path(subdir, tag="Exclude directory")
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