#!/usr/bin/env python3
"""
ResearchMind dev CLI.

Usage:
    python dev.py <service> <command>
    python dev.py <command>              # targets all services

Services:  backend  frontend  all (default)
Commands:  start  stop  restart  status  logs

Examples:
    python dev.py start                  # start backend + frontend
    python dev.py backend start          # start backend only
    python dev.py frontend restart       # restart frontend only
    python dev.py status                 # status of all services
    python dev.py backend logs           # tail backend logs
"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

SERVICES: dict[str, dict] = {
    "backend": {
        "dir":   ROOT / "backend",
        "port":  8001,
        "exe":   "backend/.venv/bin/uvicorn",
        "cmd":   ["app.main:app", "--reload", "--port", "8001"],
        "color": "\033[34m",   # blue
        "setup": "cd backend && uv venv && uv pip install -r requirements.txt",
    },
    "frontend": {
        "dir":   ROOT / "frontend",
        "port":  8501,
        "exe":   "frontend/.venv/bin/streamlit",
        "cmd":   ["run", "app.py", "--server.port", "8501"],
        "color": "\033[32m",   # green
        "setup": "cd frontend && uv venv && uv pip install -r requirements.txt",
    },
    "frontend2": {
        "dir":   ROOT / "frontend2",
        "port":  3000,
        "exe":   "frontend2/node_modules/.bin/next",
        "cmd":   ["dev", "--port", "3000"],
        "color": "\033[33m",   # yellow
        "setup": "cd frontend2 && npm install",
    },
}

_BOLD  = "\033[1m"
_DIM   = "\033[2m"
_RED   = "\033[31m"
_CYAN  = "\033[36m"
_RESET = "\033[0m"


# ── Port / process helpers ────────────────────────────────────────────────────

def _pids_on_port(port: int) -> list[int]:
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
        return [int(p) for p in out.strip().split() if p]
    except subprocess.CalledProcessError:
        return []


def _kill_port(port: int) -> None:
    for pid in _pids_on_port(port):
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"  {_DIM}killed PID {pid} on :{port}{_RESET}")
        except ProcessLookupError:
            pass
    if _pids_on_port(port):
        time.sleep(0.6)


def _spawn(svc: dict) -> subprocess.Popen:
    exe = ROOT / svc["exe"]
    if not exe.exists():
        _die(f"Executable not found: {exe}\nRun:  {svc['setup']}")
    return subprocess.Popen(
        [str(exe)] + svc["cmd"],
        cwd=str(svc["dir"]),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stream(proc: subprocess.Popen, label: str, color: str) -> None:
    for line in proc.stdout:
        sys.stdout.write(f"{color}[{label}]{_RESET} {line}")
        sys.stdout.flush()


def _die(msg: str) -> None:
    print(f"{_RED}✗  {msg}{_RESET}")
    sys.exit(1)


# ── Per-service commands ──────────────────────────────────────────────────────

def svc_start(names: list[str]) -> None:
    for name in names:
        svc = SERVICES[name]
        print(f"{_BOLD}Killing :{svc['port']}…{_RESET}")
        _kill_port(svc["port"])
        print(f"{_BOLD}Starting {name} (:{svc['port']})…{_RESET}")

    procs: list[tuple[str, subprocess.Popen]] = []
    for name in names:
        proc = _spawn(SERVICES[name])
        procs.append((name, proc))
        threading.Thread(
            target=_stream,
            args=(proc, name, SERVICES[name]["color"]),
            daemon=True,
        ).start()

    print(f"\n{_CYAN}{_BOLD}Running{_RESET}")
    for name, _ in procs:
        svc = SERVICES[name]
        label = "http://localhost:" + str(svc["port"])
        print(f"  {svc['color']}{name:<10}{_RESET} → {_BOLD}{label}{_RESET}")
    print(f"\n{_DIM}Ctrl-C to stop{_RESET}\n")

    try:
        procs[0][1].wait()
    except KeyboardInterrupt:
        print(f"\n{_BOLD}Shutting down…{_RESET}")
        for _, proc in procs:
            proc.terminate()
        for _, proc in procs:
            proc.wait()
        print("Done.")


def svc_stop(names: list[str]) -> None:
    for name in names:
        port = SERVICES[name]["port"]
        pids = _pids_on_port(port)
        if pids:
            _kill_port(port)
            print(f"  Stopped {name} (:{port})")
        else:
            print(f"  {name} (:{port}) was not running")


def svc_restart(names: list[str]) -> None:
    svc_stop(names)
    time.sleep(0.4)
    svc_start(names)


def svc_status(names: list[str]) -> None:
    print(f"{_BOLD}Status{_RESET}")
    for name in names:
        svc  = SERVICES[name]
        pids = _pids_on_port(svc["port"])
        if pids:
            pid_str = ", ".join(map(str, pids))
            print(f"  \033[32m●{_RESET} {name:<10} :{svc['port']}  {_DIM}PID {pid_str}{_RESET}")
        else:
            print(f"  {_RED}○{_RESET} {name:<10} :{svc['port']}  {_DIM}not running{_RESET}")


def svc_logs(names: list[str]) -> None:
    """Re-attach to running processes isn't possible; show last lines from log files if any."""
    print(f"{_DIM}Tip: logs stream live when you use 'start'. "
          f"For a running process, use:  lsof -p <PID>{_RESET}")
    svc_status(names)


# ── Dispatch ──────────────────────────────────────────────────────────────────

_CMD_FNS = {
    "start":   svc_start,
    "stop":    svc_stop,
    "restart": svc_restart,
    "status":  svc_status,
    "logs":    svc_logs,
}

_HELP = """\
{bold}Usage:{reset}  python dev.py [service] <command>

{bold}Services{reset} (optional, default = all):
  backend    FastAPI on :8001
  frontend   Streamlit on :8501
  all        Both (default when omitted)

{bold}Commands{reset}:
  start      Kill port(s), spawn server(s), stream logs
  stop       Kill server(s)
  restart    stop + start
  status     Show running PIDs per service
  logs       Show status (live logs only available via start)

{bold}Examples{reset}:
  python dev.py start                  start both
  python dev.py backend start          start backend only
  python dev.py frontend restart       restart frontend only
  python dev.py all status             status of all services
  python dev.py stop                   stop both
""".format(bold=_BOLD, reset=_RESET)


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(_HELP)
        sys.exit(0)

    # Determine service(s) and command
    if args[0] in SERVICES:
        names   = [args[0]]
        cmd_arg = args[1] if len(args) > 1 else None
    elif args[0] == "all":
        names   = list(SERVICES)
        cmd_arg = args[1] if len(args) > 1 else None
    elif args[0] in _CMD_FNS:
        names   = list(SERVICES)
        cmd_arg = args[0]
    else:
        print(f"{_RED}Unknown service or command: {args[0]!r}{_RESET}\n")
        print(_HELP)
        sys.exit(1)

    if cmd_arg is None:
        print(f"{_RED}No command given.{_RESET}\n")
        print(_HELP)
        sys.exit(1)

    if cmd_arg not in _CMD_FNS:
        print(f"{_RED}Unknown command: {cmd_arg!r}{_RESET}\n")
        print(_HELP)
        sys.exit(1)

    _CMD_FNS[cmd_arg](names)


if __name__ == "__main__":
    main()
