TARGET_FILES = [
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "pipfile",
    "pyproject.toml",
    "Dockerfile",
    ".gitignore",
    "makefile",
    "go.mod",
    "cargo.toml"
]

TARGET_EXTENSIONS = [
    ".yml",
    ".yaml",
    ".tf",
    ".tfvars",
    ".json",
    ".toml",
    ".conf",
    ".ini",
    ".properties"
]

import os

def find_relevant_files(repo_path):
    matches = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file in ["package.json", "requirements.txt", "Dockerfile", ".gitignore", "makefile", "go.mod", "cargo.toml", "pipfile", "pyproject.toml", "docker-compose.yml", "docker-compose.yaml"]:
                matches.append(os.path.join(root, file))

            if file.endswith((".yml", ".yaml", ".tf", ".tfvars", ".json", ".toml", ".conf", ".ini", ".properties")):
                matches.append(os.path.join(root, file))

    return matches