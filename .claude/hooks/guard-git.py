#!/usr/bin/env python3
"""Bash ツールで実行される git コマンドを検査する PreToolUse フック。

- main への push、タグの push、main での commit は拒否する（deny）
- develop への push はステージングへのデプロイになるため確認する（ask）
- それ以外は通常の権限判定に任せる（何も出力しない）
"""

import json
import shlex
import subprocess
import sys

PROTECTED = "main"
CONFIRM = "develop"
SEPARATORS = {";", "&&", "||", "|", "&", "\n"}
# git のグローバルオプションのうち、次のトークンを値として取るもの
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def current_branch() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def is_tag(name: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{name}"],
        capture_output=True,
    )
    return result.returncode == 0


def split_commands(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    commands: list[list[str]] = [[]]
    for token in lexer:
        if token in SEPARATORS:
            commands.append([])
        else:
            commands[-1].append(token)
    return [c for c in commands if c]


def git_subcommand(tokens: list[str]) -> tuple[str, list[str]] | None:
    """git の呼び出しなら (サブコマンド, 残りの引数) を返す。"""
    if not tokens or tokens[0].rsplit("/", 1)[-1] != "git":
        return None
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in GIT_OPTS_WITH_VALUE:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok, tokens[i + 1 :]
    return None


def push_destinations(args: list[str]) -> tuple[list[str], list[str]]:
    """push の宛先ブランチ名と、問題のあるフラグを返す。"""
    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]
    risky_flags = [f for f in flags if f in ("--tags", "--follow-tags", "--mirror", "--all")]
    refspecs = positional[1:]  # 先頭はリモート名
    if not refspecs:
        return [current_branch()], risky_flags
    dests = []
    for spec in refspecs:
        spec = spec.lstrip("+")
        src, _, dst = spec.partition(":")
        dest = dst or src
        if dest.startswith("refs/tags/") or (not dst and is_tag(src)):
            risky_flags.append(f"tag:{dest}")
            continue
        if dest == "HEAD":
            dest = current_branch()
        dests.append(dest.removeprefix("refs/heads/"))
    return dests, risky_flags


def decide(command: str) -> tuple[str, str] | None:
    try:
        commands = split_commands(command)
    except ValueError:
        return None
    ask_reason = None
    for tokens in commands:
        parsed = git_subcommand(tokens)
        if parsed is None:
            continue
        sub, args = parsed
        if sub == "commit" and current_branch() == PROTECTED:
            return "deny", f"{PROTECTED} ブランチでは commit しない。作業ブランチを作ってから commit すること。"
        if sub != "push":
            continue
        dests, risky = push_destinations(args)
        if risky:
            return "deny", f"タグや一括の push は本番デプロイにつながるため禁止（{', '.join(risky)}）。"
        if PROTECTED in dests:
            return "deny", f"{PROTECTED} への push は禁止。作業ブランチから PR を出すこと。"
        if CONFIRM in dests:
            ask_reason = f"{CONFIRM} への push はステージングへのデプロイになる。オーナーの指示があるか確認すること。"
    if ask_reason:
        return "ask", ask_reason
    return None


def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    result = decide(command)
    if result is None:
        return
    decision, reason = result
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
