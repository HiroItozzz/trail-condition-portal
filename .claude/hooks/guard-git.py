#!/usr/bin/env python3
"""Bash ツールで実行される git コマンドを検査する PreToolUse フック。

- main への push、タグの push、main での commit は拒否する（deny）
- develop への push はステージングへのデプロイになるため確認する（ask）
- push かどうか・宛先ブランチが何かを解析できなかった場合も確認する（ask、fail-closed）
- それ以外は通常の権限判定に任せる（何も出力しない）
"""

import json
import re
import shlex
import subprocess
import sys

PROTECTED = "main"
CONFIRM = "develop"
# コマンドの区切りとして扱うトークン（改行は事前に ";" へ正規化してから見る）
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}
# git のグローバルオプションのうち、次のトークンを値として取るもの
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
# push のオプションのうち、次のトークンを値として取るもの（--opt=value の形は含まない）
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
# 単独で push 全体を危険にするフラグ
PUSH_RISKY_FLAGS = {"--tags", "--follow-tags", "--mirror", "--all"}
# 先頭から読み飛ばすコマンド（env 系のラッパー）
SKIP_WORDS = {"env", "command", "sudo", "time", "nohup", "exec"}
# 本番デプロイに使うタグの形式（例: v2026.09.27）
PROD_TAG_PATTERN = re.compile(r"^v\d{4}\.\d{2}\.\d{2}$")
NAME_ASSIGNMENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True,
        text=True,
    )


def current_branch(cwd: str) -> str:
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def is_branch(name: str, cwd: str) -> bool:
    return _run_git(["show-ref", "--verify", "--quiet", f"refs/heads/{name}"], cwd).returncode == 0


def is_tag(name: str, cwd: str) -> bool:
    return _run_git(["show-ref", "--verify", "--quiet", f"refs/tags/{name}"], cwd).returncode == 0


def _normalize_newlines(command: str) -> str:
    """クォートの外にある改行だけを ";" に置き換える（改行も区切りとして扱うため）。"""
    result: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in command:
        if quote == "'":
            result.append(ch)
            if ch == "'":
                quote = None
            continue
        if quote == '"':
            result.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quote = None
            continue
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue
        if ch == "'":
            quote = "'"
            result.append(ch)
            continue
        if ch == '"':
            quote = '"'
            result.append(ch)
            continue
        if ch == "\n":
            result.append(";")
            continue
        result.append(ch)
    return "".join(result)


def _tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    return list(lexer)


def _collapse_command_substitutions(tokens: list[str]) -> list[str]:
    """ "$(...)" をまとめて1トークンにし、中の git/push を誤検出しないようにする。"""
    result: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "$" and i + 1 < len(tokens) and tokens[i + 1] == "(":
            depth = 1
            j = i + 2
            while j < len(tokens) and depth > 0:
                if tokens[j] == "(":
                    depth += 1
                elif tokens[j] == ")":
                    depth -= 1
                j += 1
            result.append("$(...)")
            i = j
            continue
        result.append(tokens[i])
        i += 1
    return result


def _group_by_separator(tokens: list[str]) -> list[list[str]]:
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            groups.append([])
        else:
            groups[-1].append(token)
    return [g for g in groups if g]


def _strip_redirections(tokens: list[str]) -> list[str]:
    """リダイレクトのトークン（と、あればその対象・数字の fd）を取り除く。"""
    result: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if "<" in tok or ">" in tok:
            if result and result[-1].isdigit():
                result.pop()
            i += 2
            continue
        result.append(tok)
        i += 1
    return result


def _skip_leading(tokens: list[str]) -> list[str]:
    """先頭の NAME=value や env / sudo などのラッパーを読み飛ばす。"""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if NAME_ASSIGNMENT_PATTERN.match(tok) or tok in SKIP_WORDS:
            i += 1
            continue
        break
    return tokens[i:]


def build_simple_commands(command: str) -> list[list[str]]:
    """コマンド文字列を、区切りで分けたトークン列のリストにする（bash -c は再帰的に展開）。"""
    tokens = _tokenize(_normalize_newlines(command))
    tokens = _collapse_command_substitutions(tokens)
    result: list[list[str]] = []
    for group in _group_by_separator(tokens):
        group = _skip_leading(_strip_redirections(group))
        if len(group) >= 3 and group[0] in ("bash", "sh", "zsh") and group[1] == "-c":
            result.extend(build_simple_commands(group[2]))
        else:
            result.append(group)
    return result


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


def handle_checkout(args: list[str], effective_branch: str | None, created_branches: set[str]) -> str | None:
    """checkout / switch の後の実効ブランチを求める。"""
    if "--" in args:
        return effective_branch
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in ("-b", "-B", "-c", "-C"):
            if i + 1 < len(args):
                name = args[i + 1]
                created_branches.add(name)
                return name
            return effective_branch
        if not tok.startswith("-"):
            return tok
        i += 1
    return effective_branch


def parse_push_args(args: list[str]) -> tuple[list[str], list[str]]:
    """push の非オプション引数（リモート名 + refspec）と、危険なフラグを返す。"""
    positional: list[str] = []
    risky: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in PUSH_RISKY_FLAGS:
            risky.append(tok)
            i += 1
            continue
        if tok in PUSH_OPTS_WITH_VALUE:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        positional.append(tok)
        i += 1
    return positional, risky


def evaluate_refspec(spec: str, effective_branch: str, created_branches: set[str], cwd: str) -> tuple[str, str] | None:
    """1つの refspec を判定する。"""
    spec = spec.lstrip("+")
    has_colon = ":" in spec
    src, _, dst = spec.partition(":") if has_colon else (spec, "", "")
    if dst.startswith("refs/tags/") or (not has_colon and (src.startswith("refs/tags/") or is_tag(src, cwd))):
        return "deny", "タグの push は本番デプロイにつながるため禁止。作業ブランチの push だけにすること。"
    dest_name = (dst or src).removeprefix("refs/heads/")
    if dest_name in ("HEAD", "@"):
        dest_name = effective_branch
    if PROD_TAG_PATTERN.fullmatch(dest_name):
        return "deny", "本番タグの形式（vYYYY.MM.DD）への push は禁止。作業ブランチから PR を出すこと。"
    if dest_name == PROTECTED:
        return "deny", f"{PROTECTED} への push は禁止。作業ブランチから PR を出すこと。"
    if dest_name == CONFIRM:
        return "ask", f"{CONFIRM} への push はステージングへのデプロイになる。オーナーの指示があるか確認すること。"
    if not dst and src not in ("HEAD", "@") and src not in created_branches and not is_branch(src, cwd):
        return "ask", "push するものがブランチだと確かめられないため確認が必要。"
    return None


def handle_push(args: list[str], effective_branch: str, created_branches: set[str], cwd: str) -> tuple[str, str] | None:
    positional, risky = parse_push_args(args)
    if risky:
        return "deny", "タグや一括の push は本番デプロイにつながるため禁止。"
    refspecs = positional[1:]
    if not refspecs:
        dest_name = effective_branch
        if dest_name == PROTECTED:
            return "deny", f"{PROTECTED} への push は禁止。作業ブランチから PR を出すこと。"
        if dest_name == CONFIRM:
            return "ask", f"{CONFIRM} への push はステージングへのデプロイになる。オーナーの指示があるか確認すること。"
        return None
    if "tag" in refspecs:
        return "deny", "タグの push は本番デプロイにつながるため禁止。作業ブランチの push だけにすること。"
    decisions = [d for d in (evaluate_refspec(spec, effective_branch, created_branches, cwd) for spec in refspecs) if d]
    deny = next((d for d in decisions if d[0] == "deny"), None)
    if deny:
        return deny
    return next((d for d in decisions if d[0] == "ask"), None)


def decide(command: str, cwd: str) -> tuple[str, str] | None:
    commands = build_simple_commands(command)
    effective_branch: str | None = None
    created_branches: set[str] = set()
    decisions: list[tuple[str, str]] = []
    found_push = False
    for tokens in commands:
        parsed = git_subcommand(tokens)
        if parsed is None:
            continue
        sub, args = parsed
        if sub in ("checkout", "switch"):
            effective_branch = handle_checkout(args, effective_branch, created_branches)
        elif sub == "commit":
            eff = effective_branch if effective_branch is not None else current_branch(cwd)
            if eff == PROTECTED:
                decisions.append(
                    ("deny", f"{PROTECTED} ブランチでは commit しない。作業ブランチを作ってから commit すること。")
                )
        elif sub == "push":
            found_push = True
            eff = effective_branch if effective_branch is not None else current_branch(cwd)
            result = handle_push(args, eff, created_branches, cwd)
            if result:
                decisions.append(result)
    deny = next((d for d in decisions if d[0] == "deny"), None)
    if deny:
        return deny
    ask = next((d for d in decisions if d[0] == "ask"), None)
    if ask:
        return ask
    if not found_push and re.search(r"\bgit\b", command) and re.search(r"\bpush\b", command):
        return "ask", "git push の可能性がある書き方のため確認が必要。"
    return None


def main() -> None:
    # 解析に失敗したらどんな理由でも確認に倒す（fail-closed）。
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or "."
        result = decide(command, cwd)
    except Exception:
        result = "ask", "git コマンドを解析できなかったため確認が必要。"
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
