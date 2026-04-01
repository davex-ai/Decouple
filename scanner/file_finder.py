import os

# Case-sensitive filenames to always collect.
TARGET_FILES = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "Dockerfile",
    ".gitignore",
    "Makefile",
    "go.mod",
    "Cargo.toml",
}

# File extensions to collect.
# SOURCE CODE EXTENSIONS ARE REQUIRED so that detect_imports() can scan
# actual import statements in .ts, .js, .py, .dart, etc.
TARGET_EXTENSIONS = {
    # Config / IaC
    ".yml", ".yaml",
    ".tf", ".tfvars",
    ".json", ".toml",
    ".conf", ".ini", ".properties",
    # Source code — needed for import-level detection
    ".js", ".mjs", ".cjs",
    ".ts", ".tsx", ".jsx",
    ".py",
    ".dart",
    ".go",
    ".rb",
    ".php",
    ".java", ".kt", ".scala",
    ".cs",
    ".rs",
    # Gradle build scripts
    ".gradle", ".gradle.kts",
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

            ext = os.path.splitext(filename)[1]
            if filename in TARGET_FILES or ext in TARGET_EXTENSIONS:
                matches.append(full_path)

    return matches