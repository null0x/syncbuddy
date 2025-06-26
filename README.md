
<img src="logo.png" width="500"/>


**SyncMate** helps you synchronize your data between multiple locations with just a few clicks. Once configured properly, it allows you to quickly and securely transfer data between trusted and untrusted destinations.

Configuration is handled via a separate file that defines *locations*. A location can be your personal computer, a connected hard drive or USB stick, or even a remote machine over SSH.

If data is marked as *sensitive* and the destination is *untrusted*, SyncMate automatically encrypts it. Similarly, it decrypts data behind the scenes when transferring to trusted locations.

SyncMate supports a **pick mode** that enables quick transmission of a specific directory between two locations without modifying the configuration file. This mode is especially useful when the general synchronization setup should remain unchanged, but you need immediate access to a particular set of data. 

Under the hood, SyncMate uses `rsync` for efficient file synchronization, `gpg` for encryption and decryption, and `ssh` for secure remote access. Instead of manually building complex command-line calls, SyncMate provides a simple, robust interface for seamless data sync.


## Usage

The usage of SyncMate is easy and straightforward:

```python
python3 main.py --src=<source-location> --dst=<destination-location> [--dry] [--remove] [--config]
```

Before running SyncMate, the user must define both `source-location` and `destination-location` in the configuration file (see below). The optional `dry` parameter indicates a test run which is helpful if you are unsure of how `rsync` will move data. The `remove` argument is also passed to `rsync` indicating to delete those files at the destination location that no longer exist at the source location. The `config` parameter enables the user to specify a configuration file with a custom name.



### Pick Mode

Pick mode enables quick transmission of a specific directory, either to the directory provided in the configuration or to another user-defined directory. To use Pick Mode, append a *relative path* to the source or destination location using a colon (`:`). The path must be*relative to the location’s root directory as defined in the configuration.


The following command transfers the directory `this/is_a/path` from the `<source-location>` to `copy/data/here` inside the `<destination-location>`:


```python
python3 main.py --src=<source-location>:this/is_a/path --dst=<destination-location>:copy/data/here [--encrypted]
```

If the `--encrypt` flag is provided, SyncMate will encrypt the source directory before transmission. 

If the source path ends with `.syncmate`, SyncMate assumes the data is already encrypted. If the destination location is marked as trusted in the configuration, SyncMate will automatically decrypt the data:

```python
python3 main.py --src=<source-location>:this/is_a/path.syncmate --dst=<destination-location>:copy/data/here 
```


## Configuration

SyncMate is configured via a `config.yaml`. This file defines *locations* - each representing either a source or a destination in the synchronization process. If necessary, the user can provide the path to a  file with a custom name using the command line argument `--config`.


### Trusted vs. Untrusted Locations
Data is not **encrypted** when transferred between **trusted** locations (though SSH ensures a secure transmission). A trusted location might be your personal computer or an encrypted external hard drive.

In contrast, an **untrusted** location could be a remote server or storage system you do not control. When transferring to an untrusted location, **sensitive data** will be automatically encrypted.

### Location Structure

Each location includes

- `name`: A unique identifer
- `root_dir`: The base directory of that location
- `trusted`: Boolean indicating trust level
- `dirs`: A list of relative directories to sync from `root_dir`

Each directory (`dirs`) entry supports the following fields:
- `path`: The relative path to be synchronized
- `sensitive`: Marks the entire directory sensitive
- `exclude_folders` (*optional*): Subdirectories or files to exclude from synchronization
- `sensitive_folders`(*optional): Subdirectories within a non-sensitive directory that should still be encrypted

**Note**: If a directory is marked as `sensitive: true`, the `sensitive_folders`setting is ignored - everything inside will be treated as sensitive. SyncMate does not allow synchronization of directories with mixed sensitivity, as this may lead to security leaks.

### Remote Locations

If the location is remote, an `ssh` block must be provided, specifying: `username` (SSH login user), `hostname` (Address of the remote machine), `port`: SSH port (defaul it 22).

### Example Configuration

```yaml
locations:
  sample-source:
    name: sample-source
    root_dir: /home/user/personal_files
    trusted: true
    dirs:
      - path: pictures/vacation_2025
        sensitive: false
        exclude_folders:
          - AllPictures.zip
          - Videos/Large/Stuff
      - path: documents/thesis
        sensitive: false
        exclude_folders:
          - "*/.git/"
      - path: documents/letters
        sensitive: false
        sensitive_folders:
          - family

  sample-destination:
    name: sample-remote-destination
    root_dir: /home/remote-user
    trusted: false
    dirs:
      - path: pictures/vacation/2025
        sensitive: false
      - path: documents/latex/thesis
        sensitive: true
      - path: documents/my_letters
    ssh:
      username: remote-user
      hostname: remote-user.my-remote-storage.com
      port: 23

gpg:
  recipient: my_email@address.com
  tmp_dir: /tmp/syncmate

 ``` 

### Path Matching

SyncMate matches the directories in the order they are listed within each location. That means the first directory in the source location is synchronized with the first directory in the destination location, the second with the second, and so on.

In the example above, the contents of `/home/user/personal_files/pictures/vacation_2025` are synchronized with `remote-user.my-remote-storage.com:/home/remote-user/pictures/vacation/2025`.

### GPG

The optional `gpg` block is required when synchronizing sensitive data with an untrusted location. In this case, SyncMate encrypts the data using GPG before transmission and decrypts it upon receipt when pulling from an untrusted to a trusted location.

The user must set up GPG in advance, ensuring that a valid key pair and associated identity exist.

```yaml
gpg:
  recipient: my_gpg_identity@email.com
  tmp_dir: /tmp/sync
```

The `recipient` field specifies the GPG identity (public key) to use for encryption. `tmp_dir` defines the temporary directory where SyncMate stores intermediate data during encryption and decryption. This directory is deleted when SyncMate terminates.

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.