import json
import re


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def parse_package_json(file_path):
    """Handles Node.js package.json"""
    try:
        data = json.loads(read_file(file_path))
        deps = {}
        for section in ["dependencies", "devDependencies", "peerDependencies"]:
            for name in data.get(section, {}):
                deps[name.lower()] = 1
        return deps
    except Exception:
        return {}

def parse_composer_json(file_path):
    """Handles PHP composer.json"""
    try:
        data = json.loads(read_file(file_path))
        deps = {}
        for section in ["require", "require-dev"]:
            for name in data.get(section, {}):
                # Filter out the PHP version requirement
                if name.lower() != "php":
                    deps[name.lower()] = 1
        return deps
    except Exception:
        return {}

def parse_gemfile(file_path):
    """Handles Ruby Gemfile"""
    deps = {}
    content = read_file(file_path)
    # Matches: gem "rails" or gem 'nokogiri'
    matches = re.findall(r"gem\s+['\"]([^'\"]+)['\"]", content)
    for name in matches:
        deps[name.lower()] = 1
    return deps

def parse_cargo_toml(file_path):
    """Handles Rust Cargo.toml"""
    deps = {}
    content = read_file(file_path)
    # Basic logic to find lines under [dependencies] or [dev-dependencies]
    sections = re.split(r'\[(.*?)\]', content)
    for i in range(1, len(sections), 2):
        if "dependencies" in sections[i]:
            lines = sections[i+1].split('\n')
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    name = line.split('=')[0].strip()
                    deps[name.lower()] = 1
    return deps

def parse_go_mod(file_path):
    """Handles Go go.mod"""
    deps = {}
    content = read_file(file_path)
    # Matches single-line: require ://github.com v1.7.7
    single_matches = re.findall(r"^require\s+([^\s]+)", content, re.MULTILINE)
    # Matches block: require ( ... )
    block_match = re.search(r"require\s*\((.*?)\)", content, re.DOTALL)
    if block_match:
        for line in block_match.group(1).split('\n'):
            parts = line.strip().split()
            if parts:
                deps[parts[0].lower()] = 1
    for m in single_matches:
        deps[m.lower()] = 1
    return deps

def parse_pom_xml(file_path):
    """Handles Java Maven pom.xml"""
    content = read_file(file_path)
    # Regex-based extraction of artifactIds
    deps = {}
    artifacts = re.findall(r"<artifactId>(.*?)</artifactId>", content)
    for name in artifacts:
        deps[name.lower()] = 1
    return deps

def parse_csproj(file_path):
    """Handles .NET .csproj or packages.config"""
    content = read_file(file_path)
    deps = {}
    # Matches <PackageReference Include="Newtonsoft.Json" ... />
    matches = re.findall(r'Include=["\']([^"\']+)["\']', content)
    for name in matches:
        deps[name.lower()] = 1
    return deps

def parse_pubspec_yaml(file_path):
    """Handles Flutter/Dart pubspec.yaml"""
    deps = {}
    content = read_file(file_path)
    in_deps = False
    for line in content.split('\n'):
        if line.startswith(("dependencies:", "dev_dependencies:")):
            in_deps = True
            continue
        if in_deps:
            if line.startswith("  ") and ":" in line:
                name = line.split(":")[0].strip()
                if not name.startswith("#"):
                    deps[name.lower()] = 1
            elif line and not line.startswith(" "):
                in_deps = False
    return deps

def parse_pyproject_toml(file_path):
    """Handles Python pyproject.toml (Poetry/Flit/Setuptools)"""
    deps = {}
    content = read_file(file_path)
    # Look for list-style dependencies: dependencies = ["requests>=2.0"]
    matches = re.findall(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
    for match in matches:
        names = re.findall(r'["\']([^"\'\s>=<~!]+)', match)
        for name in names:
            deps[name.lower()] = 1
    return deps

def parse_requirements(file_path):
    """Original helper for requirements.txt"""
    deps = {}
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Strip version specifiers
                    dep = re.split(r'[<>=!]', line)[0].strip().lower()
                    deps[dep] = 1
    except:
        pass
    return deps


# Transiitive deps
def parse_composer_lock(file_path):
    """Handles PHP composer.lock (JSON)"""
    try:
        data = json.loads(read_file(file_path))
        deps = {}
        # Transitive dependencies are in 'packages', dev ones in 'packages-dev'
        for section in ["packages", "packages-dev"]:
            for pkg in data.get(section, []):
                if "name" in pkg:
                    deps[pkg["name"].lower()] = 1
        return deps
    except Exception:
        return {}

def parse_yarn_lock(file_path):
    """Handles yarn.lock (Custom format)"""
    content = read_file(file_path)
    # Matches the beginning of package blocks: "package-name@version:"
    # Note: Yarn 1.x uses "package@version, package@version:", Yarn 2+ uses different styles
    deps = {}
    matches = re.findall(r'^"?([^@\s:]+)@', content, re.MULTILINE)
    for name in matches:
        deps[name.strip('"').lower()] = 1
    return deps

def parse_cargo_lock(file_path):
    """Handles Rust Cargo.lock (TOML-like)"""
    content = read_file(file_path)
    deps = {}
    # Matches: name = "package-name" inside [[package]] blocks
    matches = re.findall(r'\[\[package\]\]\s+name\s*=\s*"([^"]+)"', content, re.DOTALL | re.MULTILINE)
    # Also handle simpler name = "..." lines if the block match is too strict
    if not matches:
        matches = re.findall(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    for name in matches:
        deps[name.lower()] = 1
    return deps

def parse_gemfile_lock(file_path):
    """Handles Ruby Gemfile.lock"""
    content = read_file(file_path)
    deps = {}
    # Specs are listed under the GEM section, usually indented with 4-6 spaces
    matches = re.findall(r'^\s{4,6}([a-z0-9\-_]+)\s+\(', content, re.MULTILINE | re.IGNORECASE)
    for name in matches:
        deps[name.lower()] = 1
    return deps


def parse_gradle(file_path):
    """
    Handles Groovy (.gradle) and Kotlin (.gradle.kts) build scripts.
    Extracts external libraries and internal project dependencies.
    """
    content = read_file(file_path)
    deps = {}

    # 1. Match standard string notation: implementation 'com.google.guava:guava:30.0-jre'
    # Supports single or double quotes and handles various scopes (implementation, api, etc.)
    string_pattern = r'(?:implementation|api|testImplementation|runtimeOnly|compileOnly)\s*\(?[\'"]([^:\'"]+):([^:\'"]+)'
    matches = re.findall(string_pattern, content)
    for group, artifact in matches:
        # We store the artifact name, or group:artifact for better uniqueness
        deps[f"{group}:{artifact}".lower()] = 1

    # 2. Match project dependencies: implementation project(':shared-library')
    project_pattern = r'project\([\'"](?::)?([^:\'"]+)[\'"]\)'
    project_matches = re.findall(project_pattern, content)
    for project_name in project_matches:
        deps[f"project:{project_name}".lower()] = 1

    # 3. Handle version catalog aliases: implementation(libs.junit.jupiter)
    catalog_pattern = r'(?:implementation|api|testImplementation)\s*\(?libs\.([a-zA-Z0-9\.]+)\)?'
    catalog_matches = re.findall(catalog_pattern, content)
    for alias in catalog_matches:
        deps[f"catalog:{alias}".lower()] = 1

    return deps

