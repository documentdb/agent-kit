import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / ".env"
REPORTS = ROOT / ".runtime"
WHEELS = ROOT / "starter" / ".wheels"
PYMONGO = {
    "amd64": (
        "pymongo-4.17.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl",
        "8e97e03fa13327c87e3fdc5656acd01e71817f0c1dc3221cd8f30de136bf4ec3",
    ),
    "arm64": (
        "pymongo-4.17.0-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl",
        "37a8385c29881b43eab31f584100fa0eaddedd5607adf010147ba1810118be90",
    ),
}
DNS = (
    "dnspython-2.9.2-py3-none-any.whl",
    "af15f7d385a6ae2fb35a796fde2138004c8c42c7389090e2addc83e3b3340fd8",
)


class SetupError(Exception):
    pass


def docker(*args):
    result = subprocess.run(["docker", *args], text=True, capture_output=True)
    if result.returncode:
        raise SetupError("Docker is unavailable. Start Docker and check that Compose is installed.")
    return result.stdout.strip()


def preflight():
    if not shutil.which("docker"):
        raise SetupError("Install Docker with Compose: https://docs.docker.com/get-started/get-docker/")
    version = docker("compose", "version", "--short").lstrip("v").split(".")
    if int(version[0]) < 2 or (int(version[0]) == 2 and int(version[1]) < 20):
        raise SetupError("Docker Compose 2.20 or newer is required.")
    target = docker("version", "--format", "{{.Server.Os}}/{{.Server.Arch}}")
    if target not in ("linux/amd64", "linux/arm64"):
        raise SetupError("Use a Linux-container Docker engine on amd64 or arm64.")
    return target.split("/")[1]


def read_config():
    if CONFIG.is_symlink():
        raise SetupError("Use a regular private .env file, not a symlink.")
    return dict(
        line.split("=", 1) for line in CONFIG.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )


def configure(args):
    if not CONFIG.exists():
        values = {
            "COMPOSE_PROJECT_NAME": "docdb-lean-" + secrets.token_hex(4),
            "DOCUMENTDB_USERNAME": "lean_dev",
            "DOCUMENTDB_PASSWORD": secrets.token_hex(24),
            "APP_PORT": str(args.app_port or 8000),
            "DOCUMENTDB_PORT": str(args.db_port or 10260),
        }
        with os.fdopen(os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
            file.write("".join(f"{key}={value}\n" for key, value in values.items()))
        print("Created private .env; credentials will be reused on later starts.", flush=True)
    elif args.app_port is not None or args.db_port is not None:
        read_config()
        replacements = {
            key: str(value) for key, value in (
                ("APP_PORT", args.app_port), ("DOCUMENTDB_PORT", args.db_port)
            ) if value is not None
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", prefix=".env.", suffix=".tmp", dir=ROOT, delete=False) as file:
                temporary = Path(file.name)
                for line in CONFIG.read_text().splitlines():
                    key = line.split("=", 1)[0]
                    file.write(f"{key}={replacements[key]}\n" if key in replacements else line + "\n")
            os.replace(temporary, CONFIG)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def download_wheel(package, version, filename, expected_hash):
    path = WHEELS / filename
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash:
        return
    print(f"Fetching verified {package} {version} dependency...", flush=True)
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/{version}/json", timeout=30) as response:
        metadata = json.load(response)
    entry = next(item for item in metadata["urls"] if item["filename"] == filename)
    if entry["digests"]["sha256"] != expected_hash:
        raise SetupError(f"{package} metadata does not match the reviewed dependency hash.")
    with urllib.request.urlopen(entry["url"], timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise SetupError(f"{package} download failed its integrity check.")
    WHEELS.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def compose(*args, capture=False, input=None):
    return subprocess.run(
        ["docker", "compose", "--env-file", str(CONFIG), "-f", str(ROOT / "starter" / "compose.yaml"), *args],
        env={**os.environ, **read_config()},
        text=True,
        capture_output=capture,
        input=input,
    )


def database_probe(features=""):
    script = (ROOT / "scripts" / "compatibility.js").read_text()
    result = compose(
        "exec", "-T", "-e", f"LEAN_FEATURES={features}",
        "documentdb", "mongosh", "--nodb", "--quiet", "--file", "/dev/stdin",
        capture=True,
        input=script,
    )
    marker = "LEAN_COMPATIBILITY_RESULT="
    lines = [line[len(marker):] for line in result.stdout.splitlines() if line.startswith(marker)]
    if not lines:
        raise SetupError("Database probe could not run. Start it with `python3 quickstart.py database`.")
    content = json.loads(lines[-1])
    container = compose("ps", "-q", "documentdb", capture=True)
    if container.returncode or not container.stdout.strip():
        raise SetupError("The kit's database container is not available.")
    image = json.loads(docker(
        "inspect", "--format", '{"configuredImage":{{json .Config.Image}},"resolvedImageId":{{json .Image}}}',
        container.stdout.strip(),
    ))
    content.update(image)
    version = compose("exec", "-T", "documentdb", "mongosh", "--version", capture=True)
    content["probeClient"] = "mongosh"
    content["probeClientVersion"] = version.stdout.strip() if version.returncode == 0 else None
    content["probeSha256"] = hashlib.sha256(script.encode()).hexdigest()
    return content, result.returncode


def start_database():
    result = compose("up", "--wait", "--wait-timeout", "600", "documentdb")
    if result.returncode:
        raise SetupError("Database startup failed. Check Docker/resources or choose --db-port.")
    content, code = database_probe()
    if code or not content.get("ready"):
        raise SetupError("DocumentDB did not pass authenticated readiness; existing credentials/data were retained.")
    print(f"Database ready: 127.0.0.1:{read_config()['DOCUMENTDB_PORT']} (MongoDB protocol, local TLS)")
    print(f"Image: {content['configuredImage']}")
    print("Credentials: private .env. No task app or driver packages were installed.")
    print("Connection examples: docs/CONNECTIONS.md. Stop with: python3 quickstart.py stop")


def report(script, name):
    result = compose("exec", "-T", "app", "python", script, capture=True)
    try:
        content = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SetupError("The app is not available. Run `python3 quickstart.py` first.") from error
    REPORTS.mkdir(mode=0o700, exist_ok=True)
    path = REPORTS / name
    path.write_text(json.dumps(content, indent=2) + "\n")
    if result.returncode or not content.get("ok"):
        raise SetupError(f"{script} did not pass. See {path.relative_to(ROOT)}; no app data was repaired.")
    return content


def verify():
    port = read_config()["APP_PORT"]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
        if json.load(response).get("application") != "documentdb-agent-kit-lean":
            raise SetupError("The published URL is not the expected lean-kit application.")
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as response:
        if not json.load(response).get("ok"):
            raise SetupError("The published app endpoint is not ready.")
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/tasks", timeout=10) as response:
        if not isinstance(json.load(response), list):
            raise SetupError("The published task API did not return its expected response.")
    e2e = report("e2e.py", "e2e-report.json")
    integrity = report("integrity.py", "integrity-report.json")
    print(f"Verified {len(e2e['checks'])} checks / {len(e2e['http'])} HTTP requests against real DocumentDB.")
    print(f"Running-app integrity: {integrity['checked']} documents checked; {integrity['coverage']} coverage.")
    for name, query in e2e["database"]["queries"].items():
        stats = query["summary"]
        print(f"Database {name}: returned={stats['nReturned']}, executionMs={stats['executionTimeMillis']}")
    print("Full evidence: .runtime/e2e-report.json and .runtime/integrity-report.json")


def main():
    parser = argparse.ArgumentParser(description="Start and verify the lean OSS DocumentDB app kit")
    parser.add_argument(
        "command", nargs="?",
        choices=["start", "database", "compatibility", "verify", "check", "stop"], default="start",
    )
    parser.add_argument("--app-port", type=int)
    parser.add_argument("--db-port", type=int)
    parser.add_argument("--features", help="Comma-separated requirements to probe; required for compatibility")
    args = parser.parse_args()
    if args.command == "compatibility" and not (
        args.features and any(part.strip() for part in args.features.split(","))
    ):
        parser.error("compatibility requires --features; see docs/COMPATIBILITY.md")
    if args.features is not None and args.command != "compatibility":
        parser.error("--features is only used by compatibility")
    for port in (args.app_port, args.db_port):
        if port is not None and not 1 <= port <= 65535:
            parser.error("Ports must be between 1 and 65535")
    try:
        architecture = preflight()
        if args.command in ("start", "database"):
            configure(args)
            if args.command == "database":
                start_database()
                return
            download_wheel("pymongo", "4.17.0", *PYMONGO[architecture])
            download_wheel("dnspython", "2.9.2", *DNS)
            result = compose("up", "--build", "--wait", "--wait-timeout", "600")
            if result.returncode:
                raise SetupError("Startup failed. Check registry access/resources; use --app-port or --db-port for port conflicts.")
            verify()
            print(f"Ready: http://127.0.0.1:{read_config()['APP_PORT']}")
            print("Local development only. Stop with: python3 quickstart.py stop")
        else:
            if not CONFIG.exists():
                raise SetupError("Run `python3 quickstart.py database` or the full quickstart first.")
            if args.command == "compatibility":
                content, code = database_probe(args.features)
                print(json.dumps(content, indent=2))
                raise SystemExit(code)
            elif args.command == "verify":
                verify()
            elif args.command == "check":
                content = report("integrity.py", "integrity-report.json")
                print(f"Integrity passed: {content['checked']} checked; {content['coverage']} coverage.")
            elif compose("down").returncode:
                raise SetupError("Could not stop the kit's Compose project.")
    except (SetupError, OSError, ValueError, KeyError, StopIteration, urllib.error.URLError) as error:
        if isinstance(error, SetupError):
            message = str(error)
        else:
            message = "Setup failed. Check network/proxy/CA trust and local Docker configuration; TLS verification was not disabled."
        parser.exit(2 if args.command == "compatibility" else 1, message + "\n")


if __name__ == "__main__":
    main()
