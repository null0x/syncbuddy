import subprocess


from pathlib import Path
from src.globals import Globals
from src.log import logger
from src.path_wrapper import DirectoryWrapper

def check_security(src : DirectoryWrapper, dst_trusted : bool) -> tuple[bool, bool]:
    """
    Determines whether encryption or decryption should be applied based on sensitivity
    and trust level of the source and destination.

    Returns
    -------
    (encrypt, decrypt) : tuple of bool
    """
    # Current directory to be synchronized
    src_path = src.get_dir_path()

    ## Encrypt source if unencrypted sensitive data is moved to an untrusted location.
    encrypt = src.is_sensitive and not dst_trusted and not src_path.has_suffix(Globals.CIPHERTEXT_ENDING)

    ## Decrypt if sensitive data is moved to a trusted location
    decrypt = src.is_sensitive and dst_trusted 

    ## Consistency check
    if encrypt and decrypt:
        raise ValueError("Invalid state: You're trying to encrypt and decrypt at the same time.")

    logger.debug(f"Encrypt: {encrypt}, Decrypt: {decrypt}, src: {src_path}, dst_trusted: {dst_trusted}")

    return encrypt, decrypt

def encrypt_dir(config, sync_job):
    """
    Encrypt a directory by first creating a compressed tar archive,
    then encrypting it using GPG with the given recipient.

    Parameters:
        config (dict): Configuration dictionary containing 'gpg.tmp_dir' and 'gpg.recipient'.
        sync_job (SyncJob): Sync job object providing source directory and optional excludes.

    Returns:
        Path | None: Path to the encrypted file if successful, None otherwise.
    """

    dir_to_encrypt = sync_job.src
    logger.debug(f"Encrypting directory {dir_to_encrypt}")

    try:
        tmp_dir = config["gpg"]["tmp_dir"]
        gpg_recipient = config["gpg"]["recipient"]
    except (KeyError, IndexError) as e:
        logger.error(f"Invalid configuration: {e}")
        return None

    # Abort if directory does not exist
    if not dir_to_encrypt.is_dir():
        logger.error(f"Directory to encrypt does not exist: {dir_to_encrypt}")
        return None

    # Prepare paths
    abs_dir = dir_to_encrypt.get_abs_path()
    relative_dir = Path(*abs_dir.parts[1:])
    archive_dir = Path(tmp_dir) / relative_dir
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_path = archive_dir.with_suffix(".tar.gz")
    ciphertext_path = archive_dir.with_suffix(Globals.CIPHERTEXT_ENDING)

    # Build tar command
    tar_cmd = [
        "tar", "-czf", str(archive_path),
        "-C", str(abs_dir.parent),
    ] + sum([["--exclude", str(ex)] for ex in sync_job.excludes], []) + [abs_dir.name]

    try:
        subprocess.run(tar_cmd, check=True)
    except subprocess.CalledProcessError:
        logger.error(f"Tar failed to create archive of \"{dir_to_encrypt}\"")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while creating archive: {e}")
        return None

    # Replace archive ending with Globals.CIPHERTEXT_ENDING
    if ciphertext_path.exists():
        ciphertext_path.unlink()
        logger.debug(f"Encrypted file \"{ciphertext_path}\" removed (from previous run).")

    # Encrypt archive
    gpg_cmd = [
        "gpg", "--encrypt",
        "--recipient", gpg_recipient,
        "--output", str(ciphertext_path),
        str(archive_path)
    ]

    try:
        subprocess.run(gpg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"GPG encryption failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while encrypting archive: {e}")
        return None

    if not ciphertext_path.exists():
        logger.error(f"Encryption completed but file not found: {ciphertext_path}")
        return None
        
    # Return path to ciphertext
    return ciphertext_path


def decrypt_dir(ciphertext : Path, remove_top_level_dir=False):
    """
    Decrypt and extract a GPG-encrypted archive file.

    This function performs the following steps:
    1. Decrypts the given ciphertext file into a `.tar.gz` archive.
    2. Extracts the `.tar.gz` archive into the same directory.
    3. Optionally strips the top-level directory when extracting (similar to `tar --strip-components=1`).
    4. Removes the original ciphertext and archive file after successful processing.

    Parameters:
        ciphertext (Path): Path to the encrypted file.
        remove_top_level_dir (bool): If True, removes the top-level folder when extracting the archive.

    Returns:
        bool: True if decryption and extraction succeeded, False otherwise.

    Logs:
        - Errors if the file does not exist, decryption fails, or extraction fails.
        - Debug message on success.
    """

    ret = True
    
    if not ciphertext.is_file():
        logger.error(f"Ciphertext does not exist at {ciphertext}")
        return False
    
	# Iterate over all ciphertext within destination directory
    archive_path = ciphertext.with_suffix(".tar.gz")

    # Decrypt ciphertext
    gpg_cmd = ["gpg", "--decrypt", "--output", str(archive_path), str(ciphertext)]

    try:
        subprocess.run(gpg_cmd, check=True)
        ciphertext.unlink(missing_ok=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to decrypt \"{ciphertext}\".")
        ret = False

    tar_cmd = ["tar", "-xzf", str(archive_path)]

    if remove_top_level_dir:
        tar_cmd.append("--strip-components=1")

    tar_cmd += ["-C", str(ciphertext.parent)]

    try:
        subprocess.run(tar_cmd, check=True)
        archive_path.unlink(missing_ok=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to unpack \"{archive_path}\".")
        ret = False
 
    logger.debug(f"Successfully decrypted and extracted: {ciphertext}")
    return ret