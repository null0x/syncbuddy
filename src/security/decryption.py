import subprocess

from pathlib import Path
from src.log import logger
from src.globals import Globals

def decrypt_dir(ciphertext: Path, remove_top_level_dir=False) -> bool:
    """
    Decrypts a GPG-encrypted file and optionally extracts its contents if it's a compressed directory (resulting from the encryption mode "directory").

    Parameters:
        ciphertext (Path): Path to the GPG-encrypted file.
        remove_top_level_dir (bool): If True and the decrypted file is a tar archive, 
                                     removes the top-level directory during extraction 
                                     (via `--strip-components=1`).

    Returns:
        bool: True if decryption (and extraction, if applicable) succeeds; False otherwise.

    Behavior:
        - Decrypts the given ciphertext file using GPG.
        - Deletes the ciphertext file after successful decryption.
        - If the decrypted file ends with `Globals.ARCHIVE_ENDING`, extracts its contents.
        - Deletes the decrypted archive after successful extraction.
    """
    if not ciphertext.is_file():
        logger.error(f"Ciphertext does not exist at {ciphertext}")
        return False

    out_file = ciphertext.with_suffix('')

    # Decrypt the ciphertext
    try:
        subprocess.run(
            ["gpg", "--decrypt", "--output", str(out_file), str(ciphertext)],
            check=True
        )
        ciphertext.unlink(missing_ok=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to decrypt \"{ciphertext}\".")
        return False


    # If the output is a tar archive, extract it
    if out_file.suffix == Globals.ARCHIVE_ENDING:
        tar_cmd = [
            "tar",
            "-xzf", str(out_file),
            "-C", str(ciphertext.parent)
        ]

        if remove_top_level_dir:
            tar_cmd.insert(1, "--strip-components=1")

        try:
            subprocess.run(tar_cmd, check=True)
            out_file.unlink(missing_ok=True)
        except subprocess.CalledProcessError:
            logger.error(f"Failed to unpack \"{out_file}\".")
            return False

    logger.debug(f"Successfully decrypted and extracted: {ciphertext}")
    return True