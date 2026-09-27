#!/usr/bin/env python3
"""guard-git.py の単体テスト。

pytest ではなく `python3 .claude/hooks/test_guard_git.py` で実行する。
一時ディレクトリに git リポジトリを作り、フックを subprocess で呼んで判定を確かめる。
実際の push は行わない（フックに JSON を渡して判定を見るだけ）。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK_PATH = Path(__file__).parent / "guard-git.py"


def run_git(args: list[str], cwd: str) -> None:
    subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True)


def setup_repo(repo_dir: str) -> None:
    run_git(["init", "-b", "main"], repo_dir)
    run_git(["config", "user.email", "test@example.com"], repo_dir)
    run_git(["config", "user.name", "test"], repo_dir)
    run_git(["commit", "--allow-empty", "-m", "init"], repo_dir)
    run_git(["branch", "feat/a"], repo_dir)
    run_git(["tag", "v9"], repo_dir)


def call_hook(command: str | None, cwd: str, raw_stdin: str | None = None) -> tuple[int, str]:
    """フックを呼び出し、(終了コード, 標準出力) を返す。"""
    if raw_stdin is not None:
        stdin_data = raw_stdin
    else:
        stdin_data = json.dumps({"tool_input": {"command": command}, "cwd": cwd})
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=stdin_data,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def decision_of(command: str, cwd: str, raw_stdin: str | None = None) -> str | None:
    returncode, stdout = call_hook(command, cwd, raw_stdin)
    if returncode != 0:
        return f"error(exit={returncode}): {stdout}"
    if not stdout:
        return None
    data = json.loads(stdout)
    return data["hookSpecificOutput"]["permissionDecision"]


def main() -> None:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as repo_dir:
        setup_repo(repo_dir)

        # ブランチに依存しないケース（main にいる状態で確認する）
        run_git(["checkout", "main"], repo_dir)

        deny_always = [
            "git push origin main",
            "git push origin HEAD:main",
            "git push origin @:main",
            "git push origin +main",
            "git push origin --delete main",
            "git push --tags",
            "git push origin refs/tags/v1",
            "git push origin v9",
            "git push origin tag v9",
            "git push origin HEAD:v2026.09.27",
            "git tag v2026.01.01 && git push origin v2026.01.01",
            'bash -c "git push origin main"',
            "GIT_TRACE=1 git push origin main",
            "env git push origin main",
            "(git push origin main)",
            "echo hi\ngit push origin main",
        ]
        for command in deny_always:
            actual = decision_of(command, repo_dir)
            if actual != "deny":
                failures.append(f"deny を期待: {command!r} -> {actual!r}")

        ask_always = [
            "git push origin develop",
            "git push -f origin feat/a:develop",
            "echo $(git push origin main)",
            "x=main; git push origin $x",
            "git -c alias.p=push p origin main",
            "git push origin nosuchbranch",
        ]
        for command in ask_always:
            actual = decision_of(command, repo_dir)
            if actual != "ask":
                failures.append(f"ask を期待: {command!r} -> {actual!r}")

        # 閉じていない引用符
        actual = decision_of("git push origin 'main", repo_dir)
        if actual != "ask":
            failures.append(f"ask を期待（引用符が閉じていない）-> {actual!r}")

        # stdin が JSON でない場合
        returncode, stdout = call_hook(None, repo_dir, raw_stdin="not json")
        if returncode != 0 or not stdout:
            failures.append(f"ask を期待（JSON でない stdin）-> exit={returncode} stdout={stdout!r}")
        else:
            data = json.loads(stdout)
            if data["hookSpecificOutput"]["permissionDecision"] != "ask":
                failures.append(f"ask を期待（JSON でない stdin）-> {stdout!r}")

        silent_always = [
            "ls",
            "echo 'git status'",
            "git status",
        ]
        for command in silent_always:
            actual = decision_of(command, repo_dir)
            if actual is not None:
                failures.append(f"何も出力しないことを期待: {command!r} -> {actual!r}")

        # feat/a にいるときのケース
        run_git(["checkout", "feat/a"], repo_dir)

        deny_on_feat_a = [
            "git switch main && git push",
            "git checkout main && git commit -m x",
        ]
        for command in deny_on_feat_a:
            actual = decision_of(command, repo_dir)
            if actual != "deny":
                failures.append(f"deny を期待（feat/a）: {command!r} -> {actual!r}")

        silent_on_feat_a = [
            "git push -u origin feat/a",
            "git push origin feat/a 2>&1",
            "git push -o ci.skip origin feat/a",
            "git push origin HEAD",
        ]
        for command in silent_on_feat_a:
            actual = decision_of(command, repo_dir)
            if actual is not None:
                failures.append(f"何も出力しないことを期待（feat/a）: {command!r} -> {actual!r}")

        # main にいるときのケース
        run_git(["checkout", "main"], repo_dir)

        actual = decision_of("git checkout -b feat/new && git commit -m x", repo_dir)
        if actual is not None:
            failures.append(f"何も出力しないことを期待（main で新規ブランチに commit）-> {actual!r}")

    if failures:
        print(f"failed: {len(failures)} 件")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("ok: すべて成功")


if __name__ == "__main__":
    main()
