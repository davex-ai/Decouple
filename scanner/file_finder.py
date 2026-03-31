import os

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

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".next", ".venv", "venv", "env"
}

MAX_FILE_SIZE = 200_000

def find_relevant_files(repo_path):
    matches = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            full_path = os.path.join(root, file)
            try:
                if os.path.getsize(full_path) > MAX_FILE_SIZE:
                    continue
            except:
                continue

            if file in TARGET_FILES or file.endswith(tuple(TARGET_EXTENSIONS)):
                matches.append(full_path)

    return matches