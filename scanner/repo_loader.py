import uuid

from git import Repo
import os
import shutil
import stat
import time

def remove_readonly(func, path, excinfo):
    """Clear the readonly bit and reattempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path, retries=5, delay=0.5):
    for i in range(retries):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            return
        except PermissionError:
            time.sleep(delay)
    raise Exception("Failed to delete temp repo after retries")

def clone_repo(repo_url: str):
    # clean old repo
    temp_dir = f"temp_repo_{uuid.uuid4().hex}"
    if os.path.exists(temp_dir):
        safe_rmtree(temp_dir)
    Repo.clone_from(repo_url, temp_dir, depth=1)
    return temp_dir
