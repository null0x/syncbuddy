
<img src="logo.png" width="500"/>


**SyncBuddy** helps you synchronize your data between multiple locations with just a few clicks. Once configured properly, it allows you to quickly and securely transfer data between trusted and untrusted destinations.

Configuration is handled via a separate file that defines *locations*. A location can be your personal computer, a connected hard drive or USB stick, or even a remote machine over SSH.

If data is marked as *sensitive* and the destination is *untrusted*, SyncBuddy automatically encrypts it. Similarly, it decrypts data behind the scenes when transferring to trusted locations.

SyncBuddy supports a **pick mode** that enables quick transmission of a specific file or directory between two locations without modifying the configuration file. This mode is especially useful when the general synchronization setup should remain unchanged, but you need immediate access to a particular set of data. 

Under the hood, SyncBuddy uses `rsync` for efficient file synchronization, `gpg` for encryption and decryption, and `ssh` for secure remote access. Instead of manually building complex command-line calls, SyncBuddy provides a simple, robust interface for seamless data sync.


## Install

To install SyncBuddy for development, navigate to the project's root directory and run:

```
pip install -e .
```

This installs the project in editable mode, so you can run it and make changes without reinstalling. For a regular (non-editable) install, simply omit the `-e` flag.



## Usage

The usage of SyncBuddy is easy and straightforward:

```python
syncbuddy --src=<source-location> --dst=<destination-location> [--dry] [--remove] [--config] [--match] [--yes]
```

Before running SyncBuddy, the user must define both `source-location` and `destination-location` in the configuration file (see below). The optional `dry` parameter indicates a test run which is helpful if you are unsure of how `rsync` will move data. The `remove` argument is also passed to `rsync` indicating to delete those files at the destination location that no longer exist at the source location. The `config` parameter enables the user to specify a configuration file with a custom name.


### Directory Matching

SyncBuddy provides two methods for assigning destination directories to source directories:

-  **Automatic Matching (default):** Directories are matched in the order they appear in the configuration file. The first source directory syncs with the first destination directory, the second with the second, and so forth.

-  **Manual Matching:** By using the `--match` flag, SyncBuddy prompts the user to manually pair source and destination directories. This allows selective syncing of specific directories without changing the configuration file.



### Pick Mode

Pick mode enables quick transmission of a specific file or directory, either to the directory provided in the configuration or to another user-defined directory. To use Pick Mode, append a *relative path* to the source or destination location using a colon (`:`). The path must be *relative* to the location’s root directory as defined in the configuration.


The following command transfers the directory `this/is_a/path` from the `<source-location>` to `copy/data/here` inside the `<destination-location>`:


```python
syncbuddy --src=<source-location>:this/is_a/path --dst=<destination-location>:copy/data/here [--encrypt]
```

If the `--encrypt` flag is provided, SyncBuddy will encrypt the source directory before transmission. 

If the source path ends with `.crypt`, SyncBuddy assumes the data is encrypted. If the destination location is marked as trusted in the configuration, SyncBuddy will automatically decrypt the data:

```python
syncbuddy --src=<source-location>:this/is_an/encrypted/directory.syncbuddy --dst=<destination-location>:copy/data/here 
```


## Configuration

SyncBuddy is configured via a `config.yaml`. This file defines *locations* - each representing either a source or a destination in the synchronization process. If necessary, the user can provide the path to a  file with a custom name using the command line argument `--config`.


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
- `sensitive_folders`(*optional*): Subdirectories within a non-sensitive directory that should still be encrypted
- `encryption_mode`(*optional*): Determines whether to encrypt the entire directory or each file individually. 

**Note**: If a directory is marked as `sensitive: true`, the `sensitive_folders`setting is ignored - everything inside will be treated as sensitive. SyncBuddy does not allow synchronization of directories with mixed sensitivity, as this may lead to security leaks.

### Remote Locations

If the location is remote, an `ssh` block must be provided, specifying: `username` (SSH login user), `hostname` (Address of the remote machine), `port`: SSH port (default it 22).

### Encryption Mode

SyncBuddy supports two encryption modes, configurable via the encryption_mode field:

  1. *directory:* Encrypts the entire directory as a single archive. This hides both the directory structure and all filenames. However, accessing a single file requires decrypting the entire archiv
  2. *file:* Encrypts each file individually. This allows selective updates and retrieval of specific files. However, the directory structure and filenames remain visible. This is the **default mode**.

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
        encryption_mode: directory # vs. file
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
  tmp_dir: /tmp/SyncBuddy

 ``` 

### GPG

The optional `gpg` block is required when synchronizing sensitive data with an untrusted location. In this case, SyncBuddy encrypts the data using GPG before transmission and decrypts it upon receipt when pulling from an untrusted to a trusted location.

The user must set up GPG in advance, ensuring that a valid key pair and associated identity exist.

```yaml
gpg:
  recipient: my_gpg_identity@email.com
  tmp_dir: /tmp/sync
```

The `recipient` field specifies the GPG identity (public key) to use for encryption. `tmp_dir` defines the temporary directory where SyncBuddy stores intermediate data during encryption and decryption. This directory is deleted when SyncBuddy terminates.

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.