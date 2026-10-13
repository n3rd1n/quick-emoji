#!/usr/bin/env python3
"""Block private material from landing in this public repository.

CLI:
  scripts/scan-secrets.py --staged
  scripts/scan-secrets.py --push
  scripts/scan-secrets.py <path> ...

Cursor hook:
  scripts/scan-secrets.py --cursor-hook
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECRET_NAME_RE = re.compile(
    r"(?:^|/)"
    r"(?:"
    r"\.env(?:\..+)?$"
    r"|\.netrc$"
    r"|\.npmrc\.local$"
    r"|credentials\.json$"
    r"|secrets\.json$"
    r"|id_rsa$"
    r"|id_ed25519$"
    r"|id_ecdsa$"
    r"|id_dsa$"
    r"|\.p12$"
    r"|\.pfx$"
    r"|\.p8$"
    r"|\.pem$"
    r"|\.mobileprovision$"
    r"|\.keystore$"
    r"|\.jks$"
    r")",
    re.IGNORECASE,
)

CONTENT_PATTERNS = (
    ("npm token", re.compile(r"(?<![A-Za-z0-9_])npm_[A-Za-z0-9]{36}")),
    ("npmrc auth token", re.compile(r"_authToken\s*=\s*\S+")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("Stripe live key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{10,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
)

MCP_PUSH_TOOLS = {
    "create_or_update_file",
    "push_files",
    "create_repository",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def is_example_env(path: str) -> bool:
    name = Path(path).name.lower()
    return name in {".env.example", ".env.sample", ".env.template"}


def is_secret_filename(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if is_example_env(normalized):
        return False
    return bool(SECRET_NAME_RE.search(normalized))


def findings_in_text(text: str, source: str) -> list[str]:
    hits: list[str] = []
    if is_secret_filename(source):
        hits.append(f"{source}: blocked filename for a public repo")
    for label, pattern in CONTENT_PATTERNS:
        if pattern.search(text):
            hits.append(f"{source}: looks like a {label}")
    return hits


def scan_file(path: Path) -> list[str]:
    rel = str(path)
    try:
        rel = str(path.resolve().relative_to(ROOT))
    except ValueError:
        rel = str(path)
    if is_secret_filename(rel):
        return [f"{rel}: blocked filename for a public repo"]
    try:
        data = path.read_bytes()
    except OSError as exc:
        return [f"{rel}: cannot read ({exc})"]
    if b"\0" in data[:8192]:
        return []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return findings_in_text(text, rel)


def scan_staged() -> list[str]:
    names = [n for n in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if n]
    hits: list[str] = []
    for name in names:
        if is_secret_filename(name):
            hits.append(f"{name}: blocked filename for a public repo")
            continue
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "show", f":{name}"],
            capture_output=True,
            check=False,
        )
        if blob.returncode != 0 or b"\0" in blob.stdout[:8192]:
            continue
        text = blob.stdout.decode("utf-8", errors="replace")
        hits.extend(findings_in_text(text, name))
    return hits


def scan_push() -> list[str]:
    range_spec = "HEAD"
    try:
        upstream = git("rev-parse", "--abbrev-ref", "@{upstream}").strip()
        range_spec = f"{upstream}..HEAD"
    except RuntimeError:
        range_spec = git("hash-object", "-t", "tree", "/dev/null").strip() + "..HEAD"
    names = [n for n in git("diff", "--name-only", range_spec).splitlines() if n]
    hits: list[str] = []
    for name in names:
        path = ROOT / name
        if path.is_file():
            hits.extend(scan_file(path))
        elif is_secret_filename(name):
            hits.append(f"{name}: blocked filename for a public repo")
    return hits


def install_git_hooks() -> None:
    hooks_dir = ROOT / ".git" / "hooks"
    src_dir = ROOT / ".githooks"
    if not hooks_dir.is_dir() or not src_dir.is_dir():
        return
    for src in src_dir.iterdir():
        if not src.is_file() or src.name.startswith("."):
            continue
        dest = hooks_dir / src.name
        shutil.copyfile(src, dest)
        dest.chmod(dest.stat().st_mode | 0o111)


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")


def deny(user_message: str, agent_message: str | None = None) -> dict:
    body = {"permission": "deny", "user_message": user_message}
    if agent_message:
        body["agent_message"] = agent_message
    return body


def hits_message(hits: list[str]) -> str:
    preview = "\n".join(hits[:8])
    return (
        "Blocked: this is a public repo and the change looks like a secret.\n"
        f"{preview}"
    )


def outside_workspace(path: str, workspace_roots: list[str]) -> bool:
    resolved = str(Path(path).resolve())
    roots = workspace_roots or [str(ROOT)]
    for root in roots:
        prefix = str(Path(root).resolve())
        if resolved == prefix or resolved.startswith(prefix + os.sep):
            return False
    return True


def collect_strings(value: object) -> str:
    chunks: list[str] = []
    if isinstance(value, str):
        chunks.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            chunks.append(collect_strings(item))
    elif isinstance(value, list):
        for item in value:
            chunks.append(collect_strings(item))
    return "\n".join(chunk for chunk in chunks if chunk)


def handle_shell(command: str) -> dict:
    hits = findings_in_text(command, "<shell command>")
    if hits:
        return deny(hits_message(hits), hits_message(hits))

    is_git = re.search(r"(?:^|[;&|]\s*|\s)git(?:\s|$)", command) is not None
    is_gh = re.search(r"(?:^|[;&|]\s*|\s)gh(?:\s|$)", command) is not None
    if not is_git and not is_gh:
        return {"permission": "allow"}

    if re.search(r"--no-verify|--no-gpg-sign", command):
        msg = "Blocked: --no-verify / --no-gpg-sign would skip the secret scan."
        return deny(msg, msg)

    if re.search(r"\b(commit|push|publish)\b", command):
        staged_hits = scan_staged()
        if staged_hits:
            return deny(hits_message(staged_hits), hits_message(staged_hits))
        if re.search(r"\bpush\b|\bpublish\b", command):
            push_hits = scan_push()
            if push_hits:
                return deny(hits_message(push_hits), hits_message(push_hits))

    add_match = re.search(r"\bgit\b(?:\s+-C\s+\S+)?\s+add\s+(.+)$", command, re.DOTALL)
    if add_match:
        for token in add_match.group(1).split():
            if token.startswith("-"):
                continue
            if is_secret_filename(token):
                msg = f"Blocked: refusing to git add {token} in a public repo."
                return deny(msg, msg)

    return {"permission": "allow"}


def handle_read(data: dict) -> dict:
    path = data.get("file_path") or ""
    content = data.get("content") or ""
    if outside_workspace(path, data.get("workspace_roots") or []) and is_secret_filename(path):
        msg = f"Blocked: will not read {path} (secret-looking file outside this repo)."
        return deny(msg)
    if Path(path).name == ".npmrc" and outside_workspace(path, data.get("workspace_roots") or []):
        msg = f"Blocked: will not read {path} (user npmrc often contains tokens)."
        return deny(msg)
    hits = findings_in_text(content, path or "<read>")
    if hits:
        return deny(hits_message(hits))
    return {"permission": "allow"}


def handle_tool(data: dict) -> dict:
    tool_name = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input")
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {"_raw": tool_input}
    if not isinstance(tool_input, dict):
        tool_input = {}

    short_name = tool_name.split(":")[-1].strip()
    path = str(tool_input.get("path") or tool_input.get("file_path") or "")
    blob = collect_strings(tool_input)
    hits = findings_in_text(blob, path or tool_name or "<tool>")
    if hits and short_name in {"Write", "StrReplace", "Delete", *MCP_PUSH_TOOLS}:
        return deny(hits_message(hits), hits_message(hits))
    if short_name in MCP_PUSH_TOOLS:
        extra = findings_in_text(blob, f"MCP {short_name}")
        if extra:
            return deny(hits_message(extra), hits_message(extra))
    return {"permission": "allow"}


def handle_cursor_hook() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        emit(deny("Secret guard received invalid JSON.", "Secret guard received invalid JSON."))
        return 0

    event = data.get("hook_event_name") or ""
    try:
        if event == "sessionStart":
            install_git_hooks()
            emit(
                {
                    "additional_context": (
                        "This repository is public. Never commit or push secrets, tokens, "
                        "private keys, .env files, or user npmrc contents."
                    )
                }
            )
            return 0
        if event == "beforeShellExecution" or "command" in data and "tool_name" not in data:
            emit(handle_shell(str(data.get("command") or "")))
            return 0
        if event == "beforeReadFile" or "content" in data:
            emit(handle_read(data))
            return 0
        if event in {"preToolUse", "beforeMCPExecution"} or "tool_name" in data:
            emit(handle_tool(data))
            return 0
        emit({"permission": "allow"})
        return 0
    except Exception as exc:  # noqa: BLE001 — fail closed on guard bugs
        msg = f"Secret guard failed closed: {exc}"
        emit(deny(msg, msg))
        return 0


def main(argv: list[str]) -> int:
    if "--cursor-hook" in argv:
        return handle_cursor_hook()
    if "--install-git-hooks" in argv:
        install_git_hooks()
        return 0

    hits: list[str] = []
    if "--staged" in argv:
        hits.extend(scan_staged())
    elif "--push" in argv:
        hits.extend(scan_push())
    else:
        paths = [Path(arg) for arg in argv[1:] if not arg.startswith("-")]
        if not paths:
            sys.stderr.write("usage: scan-secrets.py --staged | --push | <path>...\n")
            return 2
        for path in paths:
            hits.extend(scan_file(path))

    if hits:
        sys.stderr.write(hits_message(hits) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
