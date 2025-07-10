import subprocess

from pathlib import Path
from src.log import logger
from src.globals import Globals

def decrypt_dir(ciphertext : Path, remove_top_level_dir=False):

    ret = True
#    remove_top_level_dir = False
    
    if not ciphertext.is_file():
        logger.error(f"Ciphertext does not exist at {ciphertext}")
        return False
    
	# Iterate over all ciphertext within destination directory
    out_file = ciphertext.with_suffix('')

    # Decrypt ciphertext
    gpg_cmd = ["gpg", "--decrypt", "--output", str(out_file), str(ciphertext)]

    try:
        subprocess.run(gpg_cmd, check=True)
        ciphertext.unlink(missing_ok=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to decrypt \"{ciphertext}\".")
        ret = False

    # Check if decrypted data is an archive that results from a previous encryption mode "directory"
    if out_file.suffix == Globals.ARCHIVE_ENDING:
        tar_cmd = ["tar", "-xzf", str(out_file)]

        if remove_top_level_dir:
            tar_cmd.append("--strip-components=1")

        tar_cmd += ["-C", str(ciphertext.parent)]

        try:
            subprocess.run(tar_cmd, check=True)
            out_file.unlink(missing_ok=True)
        except subprocess.CalledProcessError:
            logger.error(f"Failed to unpack \"{out_file}\".")
            ret = False
 
    logger.debug(f"Successfully decrypted and extracted: {ciphertext}")
    return ret