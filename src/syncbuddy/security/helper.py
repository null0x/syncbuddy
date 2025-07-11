from syncbuddy.globals import Globals
from syncbuddy.log import logger
from syncbuddy.path_wrapper import DirectoryWrapper


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




