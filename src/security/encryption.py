import subprocess
import os

from pathlib import Path
from src.globals import Globals
from src.log import logger
from src.security.encryption_mode import EncryptionMode

def encrypt_file(config, file_to_encrypt : Path, out_file : Path):

    # Remove ciphertext from previous synchronization run
    if out_file.exists():
        out_file.unlink()
        logger.debug(f"Old ciphertext removed: {out_file}")

    try:
        gpg_recipient = config["gpg"]["recipient"]
    except (KeyError, IndexError) as e:
        logger.error(f"Invalid configuration: {e}")
        return None


    gpg_cmd = [
        "gpg", "--encrypt",
        "--recipient", gpg_recipient,
        "--output", str(out_file),
        str(file_to_encrypt)
    ]

    try:
        subprocess.run(gpg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"GPG encryption failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while encrypting archive: {e}")
        return None

def _encrypt_as_archive(config, input_dir, excludes, output_dir):
    """
    Archives and encrypts an entire directory as a single file.

    This function first creates an archive of the specified input directory,
    excluding any paths specified in the `excludes` list. It then encrypts the archive
    using the `encrypt_file` function and saves the result to the output directory with
    a predefined ciphertext suffix.

    Parameters:
        config (dict): Configuration dictionary containing encryption parameters.
        input_dir (Path): Absolute path to the directory to archive and encrypt.
        excludes (list[Path]): Paths to exclude from the archive (relative to input_dir).
        output_dir (Path): Destination directory for the archive and encrypted output.

    Returns:
        Path | None: Path to the encrypted archive file on success, or None on failure.
    """
    logger.debug("Encryption in 'directory' mode")

    archive_path = output_dir.with_suffix(Globals.ARCHIVE_ENDING)
    ciphertext_path = output_dir.with_suffix(Globals.ARCHIVE_ENDING + Globals.CIPHERTEXT_ENDING)

    # Build tar command
    tar_cmd = [
        "tar", "-czf", str(archive_path),
        "-C", str(input_dir.parent),
        *sum([["--exclude", str(ex)] for ex in excludes], []),
        input_dir.name
    ]

    try:
        subprocess.run(tar_cmd, check=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to create archive from: {input_dir}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during archiving: {e}")
        return None

    encrypt_file(config, archive_path, ciphertext_path)

    if not ciphertext_path.exists():
        logger.error(f"Encryption succeeded but ciphertext not found: {ciphertext_path}")
        return None

    return ciphertext_path

def _encrypt_files_individually(config, input_dir, output_dir):
    """
    Recursively encrypts each file in the input directory individually.

    This function traverses the input directory tree and encrypts every file
    it encounters. The encrypted files are saved to the output directory,
    preserving the relative directory structure and appending a ciphertext
    suffix to each filename.

    Parameters:
        config (dict): Configuration dictionary containing encryption parameters.
        input_dir (Path): Root directory containing files to encrypt.
        output_dir (Path): Destination directory for encrypted files.

    Returns:
        Path: Path to the output directory containing all encrypted files.
    """
    logger.debug("Encryption in 'file' mode")

    for root, _, files in os.walk(input_dir):
        for file in files:
            input_file_path = Path(root) / file
            relative_path = input_file_path.relative_to(input_dir)
            output_file_path = (output_dir / relative_path).with_suffix(relative_path.suffix + Globals.CIPHERTEXT_ENDING)
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            encrypt_file(config, input_file_path, output_file_path)


    return output_dir


def encrypt_srcdir(config, job):
    """
    Encrypts the source directory of the provided job in one of two modes:
    - DIRECTORY: Archive the whole directory and encrypt the archive.
    - FILE: Encrypt each file individually.
    Returns the path to the encrypted data or None on failure.
    """

    dir_to_encrypt = job.src
    excludes = job.excludes
    enc_mode = job.encryption_mode

    logger.debug(f"Encrypting directory {dir_to_encrypt}")

    # Abort if directory does not exist
    if not dir_to_encrypt.is_dir():
        logger.error(f"Directory to encrypt does not exist: {dir_to_encrypt}")
        return None
    
    # Get directory for temporary files
    tmp_dir = config.get("gpg", {}).get("tmp_dir")
    if not tmp_dir:
        logger.error("Invalid configuration: missing 'gpg.tmp_dir'")
        return None
    
    # Specify output directory
    input_dir = dir_to_encrypt.get_abs_path()
    relative_dir = Path(*input_dir.parts[1:])
    output_dir = Path(tmp_dir) / relative_dir
    output_dir.mkdir(parents=True, exist_ok=True)


    # Encrypt directory depending on the encryption mode
    if enc_mode == EncryptionMode.DIRECTORY:
        return _encrypt_as_archive(config, input_dir, excludes, output_dir)

    elif enc_mode == EncryptionMode.FILE:
        return _encrypt_files_individually(config, input_dir, output_dir)

    else:
        logger.error(f"Unsupported encryption mode: {enc_mode}")
        return None