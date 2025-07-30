class Globals:
    CIPHERTEXT_ENDING  = ".crypt"
    ARCHIVE_ENDING  = ".synchive"
    DEFAULT_CONFIG_FILE = "config.yaml"
    DEFAULT_CONFIG_DIRS = [".", "~/.config/syncbuddy", "/etc/syncbuddy"]
    REQUIRED_SYSTEM_BINS = ["rsync", "ssh", "gpg"]