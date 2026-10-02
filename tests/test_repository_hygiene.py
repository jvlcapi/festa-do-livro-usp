"""Guards for a public repository: no credentials committed, local secrets ignored."""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CREDENTIAL_PATTERNS = {
    "token do GitHub": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    "chave da Anthropic": re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    "chave da OpenAI": re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    "chave da AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "chave privada": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "token em URL": re.compile(r"[?&](access_?token|api_?key|apikey|token|signature)=[A-Za-z0-9\-_.]{12,}", re.I),
}


def tracked_text_files():
    listed = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return [ROOT / name for name in listed if not name.endswith(".pdf")]


def test_no_credentials_in_tracked_files():
    findings = []
    for path in tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    assert not findings, "Possíveis segredos no repositório:\n" + "\n".join(findings)


@pytest.mark.parametrize("path", [".env", ".env.local", "cache/27-festa-do-livro-da-usp/000-x.pdf"])
def test_local_secrets_and_caches_are_ignored(path):
    result = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT)
    assert result.returncode == 0, f"{path} deveria estar no .gitignore"
