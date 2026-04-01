import os

# Case-sensitive filenames to always include.
TARGET_FILES = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "Pipfile",           # capital P (Python convention)
    "pyproject.toml",
    "Dockerfile",        # capital D
    ".gitignore",
    "Makefile",          # capital M
    "go.mod",
    "Cargo.toml",        # capital C (Rust convention)
}

TARGET_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".tf",
    ".tfvars",
    ".json",
    ".toml",
    ".conf",
    ".ini",
    ".properties",
}

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".next", ".venv", "venv", "env",
}

MAX_FILE_SIZE = 200_000  # bytes


def find_relevant_files(repo_path: str) -> list[str]:
    matches: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in files:
            full_path = os.path.join(root, filename)
            try:
                if os.path.getsize(full_path) > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            if filename in TARGET_FILES or os.path.splitext(filename)[1] in TARGET_EXTENSIONS:
                matches.append(full_path)

    return matches
