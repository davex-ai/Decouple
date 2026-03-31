from git import Repo
import os
import shutil

def clone_repo(repo_url: str, temp_dir="temp_repo"):
    # clean old repo
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    Repo.clone_from(repo_url, temp_dir)
    return temp_dir