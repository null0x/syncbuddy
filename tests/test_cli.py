# tests/test_cli.py

from unittest.mock import patch
from src.parser import get_sync_arguments

@patch("sys.argv", ["prog", "--src", "local", "--dst", "remote", "--config", "test_config"])
def test_minimal_required_arguments():
    args = get_sync_arguments()
    assert args.get("src_location") == "local"
    assert args.get("dst_location") == "remote"
    assert args.get("src_path") == None
    assert args.get("dst_path") == None
    assert args.get("config_file") == "test_config"
    assert args.get("dry_run") == False
    assert args.get("remove_remote_files") == True
    