import hashlib
import os

file_hashes = {}
dev_mode: bool = False
base_folder = ''


def global_init(development_mode: bool, os_base_folder: str):
    global dev_mode, file_hashes, base_folder
    base_folder = os_base_folder.strip()
    file_hashes = {}
    dev_mode = development_mode


def cache_id(filename: str):
    if not filename:
        return 'ERROR_NO_FILE'

    file_lw = filename.strip().lower()
    if not dev_mode and file_lw in file_hashes:
        return file_hashes[file_lw]

    fullname = os.path.abspath(os.path.join(base_folder, filename.lstrip('/')))

    if not os.path.exists(fullname):
        return 'ERROR_MISSING_FILE'
    if os.path.isdir(fullname):
        return 'ERROR_IS_DIRECTORY'

    file_hashes[file_lw] = get_file_hash(fullname)[:6]

    return file_hashes[file_lw]


def get_file_hash(filename):
    md5 = hashlib.md5()

    with open(filename, 'rb') as fin:
        data = fin.read()
        md5.update(data)

    return md5.hexdigest()
