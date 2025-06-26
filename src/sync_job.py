from dataclasses import dataclass
from typing import List, Optional

from src.path_wrapper import MyPath


@dataclass
class SyncJob:
    """
    Represents a synchronization job between a source and destination path,
    with optional encryption, decryption, and SSH configuration.

    Attributes:
        src (MyPath): Source directory or file path to synchronize.
        dst (MyPath): Destination directory or file path.
        encrypt (bool): Whether to encrypt data before sending.
        decrypt (bool): Whether to decrypt data after receiving.
        excludes (List[str]): List of directory or file patterns to exclude from synchronization.
        ssh (Optional[dict]): Optional SSH connection details (e.g., host, port).

    Methods:
        is_remote() -> bool:
            Returns True if the synchronization job involves a remote SSH connection.

    describe() -> str:
        Returns a human-readable string describing the sync operation, including
        whether encryption or decryption is involved.
    """
    src: MyPath
    dst: MyPath
    encrypt: bool
    decrypt: bool
    excludes: List[str]
    ssh: Optional[dict] = None

    def is_remote(self) -> bool:
        return self.ssh is not None

    def describe(self) -> str:
        if self.encrypt:
         return f"{self.src} ---(encrypt)--> {self.dst}"
        elif self.decrypt:
            return f"{self.src} ---(decrypt)--> {self.dst}"
        else: 
            return f"{self.src}  -->  {self.dst}"  
