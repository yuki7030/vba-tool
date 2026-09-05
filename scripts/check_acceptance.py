#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""変更要求(docs/spec/changes/)の「6. 受け入れ基準」節の機械検査。

この設計は「完了報告の各主張は検証可能でなければならない」という要請に乗る。
AC が散文のままだと完了報告が AI の自己申告になり、照合先が存在しないため、
書式・判定・検証手段の3点を機械で担保する(最終防衛線をモデルの判断に置かない)。

  ERROR: §6 が無い / AC 行が無い / ID 形式違反・重複
  ERROR: 判定列が「自動」「人手」以外 / 検証欄が空
  ERROR: 自動 AC の検証コマンドが allowlist 外 / シェルメタ文字を含む
  ERROR: 人手 AC の検証先が docs/spec/changes/ac/ 配下に実在しない
  WARN : 内容欄の曖昧語 / 人手 AC が過半数
終了コード: ERROR があれば 1(CI検知用)。WARN のみ・指摘なしは 0。

★このスクリプトは検証コマンドを実行しない(subprocess を呼ばない)。★
理由: SPEC は外部要求から起案されうるため、表のセルから読んだ文字列を
本スクリプトが実行すると、プロンプトインジェクション経由の任意コード実行
経路になる。加えて .claude/settings.json の PreToolUse
(scripts/block_dangerous_bash.py)を迂回してしまう。
実行はエージェントが Bash ツール経由で行い、必ず既存の PreToolUse を通す。
本スクリプトの役割は「実行してよい形になっているか」の検査に限定する。
将来この制約を外す改修を入れないこと。

使い方:
  python scripts/check_acceptance.py --scan .                       # 検査(CI / autonomous-dev)
  python scripts/check_acceptance.py --scan docs/spec/changes/SPEC-012-foo.md
  python scripts/check_acceptance.py --scan . --since-spec 12       # 適用下限を上書き
  python scripts/check_acceptance.py --self-test                    # 回帰テスト

既知の制約:
- 表のセル内に `|` を含めると列分割が壊れる(コードスパン内でも同じ)。
  検証コマンドにパイプは allowlist・メタ文字検査の両方で弾かれるため実害は無い。
- draft/ 配下は起案途中なので ERROR をすべて WARN に降格する(着手禁止領域のため)。
- 全角記号(`；` 等)は検出しない。シェルの区切り文字ではないため実害が無く、
  そのコマンドは実行時に素直に失敗する(安全側)。
- allowlist は接頭辞一致のため、E5(接頭辞)・E6(メタ文字)・E6(親ディレクトリ参照)の
  3点を必ず対で維持すること。どれか1つを外すと迂回できる。
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

try:
    # 見出し解釈は check_spec_sync.py を単一の真実源とする。
    # 複製すると §6/§7 で節の切り出し規則が分岐し、audit_instructions.py の
    # 重複行検出にも掛かるため import で共有する。
    from check_spec_sync import HEADING_RE, SPEC_FILE_RE, section_body
except ImportError as e:  # pragma: no cover - 環境不備を握りつぶさない
    sys.stderr.write(
        "ERROR: check_spec_sync.py を import できません "
        "(同じ scripts/ ディレクトリに置いてください): %s\n" % e
    )
    raise

CHANGES_DIR = "docs/spec/changes"
AC_DIR = "docs/spec/changes/ac"
SECTION = "受け入れ基準"

VERDICT_AUTO = "自動"
VERDICT_MANUAL = "人手"
VERDICTS = (VERDICT_AUTO, VERDICT_MANUAL)

# 本機能の適用下限。導入時に「現在の最大SPEC番号 + 1」へ書き換える。
# 凍結済みの承認済み SPEC を検査通過のために書き換えるのは承認の意味を消すため、
# 既存分は遡って ERROR にしない(docs/spec/changes/ac/README.md 参照)。
SINCE_SPEC = 0

# 自動 AC の検証コマンドに許す接頭辞。増やす前に「その系統が
# block_dangerous_bash.py の検査を通る形か」を確認すること。
ALLOW_PREFIXES = (
    "xlflow test",
    "xlflow lint",
    "dotnet test",
    "python scripts/",
    "bash docs/spec/changes/ac/",
)

# 接頭辞一致だけでは `xlflow test x; rm -rf ~` を通してしまうため必ず対で使う。
META_CHARS = re.compile(r"[;|&`$><\n\r]|\$\(")

# 接頭辞一致は `python scripts/../../../evil.py` を通してしまうため対で使う。
PARENT_REF = re.compile(r"(^|[\s/\\])\.\.([\s/\\]|$)")

AC_ID_RE = re.compile(r"^AC-(\d+)$")
SEP_CELL_RE = re.compile(r"^:?-{2,}:?$")
PLACEHOLDER_RE = re.compile(r"<[^>]*>")
CODE_SPAN_RE = re.compile(r"^`(.*)`$")
AC_PATH_RE = re.compile(r"(docs/spec/changes/ac/[^\s`\"']+)")

VAGUE_WORDS = ("適切に", "柔軟に", "必要に応じて", "正しく")


class Finding:
    """1件の指摘。fail-loud のため ID を必ず持たせる。"""

    def __init__(self, severity: str, path: str, line: int, code: str, msg: str):
        self.severity = severity
        self.path = path
        self.line = line
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "%-5s %s:%d: [%s] %s" % (
            self.severity, self.path, self.line, self.code, self.msg
        )


def section_start(lines: list[str], match) -> int | None:
    """match(title) を満たす見出しの行インデックスを返す。

    section_body は本文だけを返し行番号を持たないため、指摘に絶対行番号を
    付けるためだけにここで見出し位置を引く。
    """
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and match(m.group(2)):
            return i
    return None


def split_row(line: str) -> list[str] | None:
    """Markdown 表の1行をセル配列にする。表行でなければ None。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEP_CELL_RE.match(c or "-") for c in cells)


def unwrap(cell: str) -> str:
    """コードスパンの backtick を外す。"""
    m = CODE_SPAN_RE.match(cell.strip())
    return m.group(1).strip() if m else cell.strip()


def is_empty_cell(cell: str) -> bool:
    """空欄、またはテンプレートのプレースホルダのみなら真。"""
    s = PLACEHOLDER_RE.sub("", unwrap(cell)).strip()
    return s == ""


def mask_comments(body: list[str]) -> list[str]:
    """HTMLコメント内の行を空行に置き換える(行番号を保つため削除しない)。

    テンプレートの説明コメントに表の例を書くと AC 行として拾ってしまうため。
    """
    out, in_comment = [], False
    for line in body:
        s = line
        if in_comment:
            if "-->" in s:
                in_comment = False
                s = s.split("-->", 1)[1]
            else:
                out.append("")
                continue
        while "<!--" in s:
            head, rest = s.split("<!--", 1)
            if "-->" in rest:
                s = head + rest.split("-->", 1)[1]
            else:
                s = head
                in_comment = True
                break
        out.append(s)
    return out


def parse_rows(body: list[str], offset: int) -> list[tuple[int, list[str]]]:
    """§6 本文から AC 行(ヘッダ・区切り行を除く)を (絶対行番号, セル) で返す。"""
    rows: list[tuple[int, list[str]]] = []
    raw: list[tuple[int, list[str]]] = []
    for i, line in enumerate(mask_comments(body)):
        cells = split_row(line)
        if cells is None:
            continue
        # 末尾の空セル(`| a | b | c | d ||` 等)は列数判定から落とす
        while len(cells) > 4 and cells[-1] == "":
            cells.pop()
        raw.append((offset + i + 1, cells))

    for idx, (lineno, cells) in enumerate(raw):
        if is_separator(cells):
            continue
        # 区切り行の直前はヘッダ行
        if idx + 1 < len(raw) and is_separator(raw[idx + 1][1]):
            continue
        rows.append((lineno, cells))
    return rows


def check_spec(path: Path, root: Path, since: int) -> list[Finding]:
    """SPEC 1本を検査する。draft 配下は ERROR を WARN に降格する。"""
    try:
        # Path.is_relative_to は 3.9+。リポジトリの前提は 3.8+ なので使わない。
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    is_draft = "/draft/" in "/" + rel

    def E(line: int, code: str, msg: str) -> Finding:
        return Finding("WARN" if is_draft else "ERROR", rel, line, code, msg)

    def W(line: int, code: str, msg: str) -> Finding:
        return Finding("WARN", rel, line, code, msg)

    m = SPEC_FILE_RE.match(path.name)
    if m and int(m.group(1)) < since:
        return []  # 適用下限より前の SPEC は対象外(凍結済みのため遡及しない)

    out: list[Finding] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    start = section_start(lines, lambda t: SECTION in t)
    body = section_body(lines, lambda t: SECTION in t)
    if start is None or body is None:
        return [E(1, "E1", "「%s」節がありません" % SECTION)]

    rows = parse_rows(body, start)
    if not rows:
        return [E(start + 1, "E1", "「%s」節に AC の表がありません" % SECTION)]

    seen: dict[str, int] = {}
    manual = 0
    for lineno, cells in rows:
        if len(cells) != 4:
            out.append(E(lineno, "E1", "列は4つ(AC/内容/検証/判定)です: %d列"
                         % len(cells)))
            continue
        ac_id, content, verify, verdict = cells[0], cells[1], cells[2], cells[3]

        # --- E2: ID 形式・重複
        if not AC_ID_RE.match(ac_id):
            out.append(E(lineno, "E2", "AC-ID が AC-<数字> 形式ではありません: %r" % ac_id))
        elif ac_id in seen:
            out.append(E(lineno, "E2", "AC-ID が重複しています: %s (既出 %d行目)"
                         % (ac_id, seen[ac_id])))
        else:
            seen[ac_id] = lineno

        # --- W1: 曖昧語
        for w in VAGUE_WORDS:
            if w in content:
                out.append(W(lineno, "W1", "内容に曖昧語「%s」があります。"
                                           "検証可能な表現へ具体化してください" % w))

        # --- E3: 判定
        if verdict not in VERDICTS:
            out.append(E(lineno, "E3", "判定は「%s」か「%s」です: %r"
                         % (VERDICT_AUTO, VERDICT_MANUAL, verdict)))
            continue
        if verdict == VERDICT_MANUAL:
            manual += 1

        # --- E4: 検証欄が空
        if is_empty_cell(verify):
            out.append(E(lineno, "E4", "検証欄が空です。手段の無い AC は"
                                       "要求が曖昧である兆候です"))
            continue
        cmd = unwrap(verify)

        if verdict == VERDICT_AUTO:
            # --- E6: メタ文字(E5 と必ず対で使う。接頭辞一致だけでは迂回できる)
            if META_CHARS.search(cmd):
                out.append(E(lineno, "E6", "検証コマンドにシェルメタ文字が"
                                           "含まれています: %r" % cmd))
                continue
            if PARENT_REF.search(cmd):
                out.append(E(lineno, "E6", "検証コマンドに親ディレクトリ参照(..)が"
                                           "含まれています(allowlist の迂回): %r" % cmd))
                continue
            # --- E5: allowlist
            if not any(cmd.startswith(p) for p in ALLOW_PREFIXES):
                out.append(E(lineno, "E5", "検証コマンドが allowlist 外です"
                                           "(許可: %s): %r"
                             % (" / ".join(ALLOW_PREFIXES), cmd)))
        else:
            # --- E7: 人手 AC の検証先が実在するか
            pm = AC_PATH_RE.search(cmd)
            if PARENT_REF.search(cmd):
                out.append(E(lineno, "E7", "検証スクリプトのパスに親ディレクトリ"
                                           "参照(..)が含まれています: %r" % cmd))
            elif not pm:
                out.append(E(lineno, "E7", "人手 AC の検証欄は %s/ 配下の"
                                           "スクリプトを指してください: %r"
                             % (AC_DIR, cmd)))
            elif not (root / pm.group(1)).is_file():
                out.append(E(lineno, "E7", "検証スクリプトが存在しません: %s"
                             % pm.group(1)))

    # --- W2: 人手が過半数
    total = len(seen)
    if total and manual * 2 > total:
        out.append(W(start + 1, "W2", "人手 AC が過半数です(%d/%d)。"
                                      "自動化の投資先を検討してください" % (manual, total)))
    return out


def iter_specs(target: Path, root: Path):
    """検査対象の SPEC ファイルを列挙する(_template.md は除外)。"""
    if target.is_file():
        if target.name != "_template.md":
            yield target
        return
    d = root / CHANGES_DIR
    if not d.is_dir():
        return
    for p in sorted(d.rglob("*.md")):
        if p.name == "_template.md" or p.name == "README.md":
            continue
        if not SPEC_FILE_RE.match(p.name):
            continue
        yield p


def run_scan(target: str, since: int) -> int:
    t = Path(target).resolve()
    root = t if t.is_dir() else _find_root(t)
    findings: list[Finding] = []
    for p in iter_specs(t, root):
        findings.extend(check_spec(p, root, since))

    for f in findings:
        print(f)
    errors = sum(1 for f in findings if f.severity == "ERROR")
    warns = len(findings) - errors
    print("受け入れ基準検査: ERROR %d / WARN %d" % (errors, warns))
    return 1 if errors else 0


def _find_root(file_path: Path) -> Path:
    """ファイル指定時、docs/spec/changes を遡ってリポジトリルートを推定する。"""
    for parent in file_path.parents:
        if (parent / CHANGES_DIR).is_dir():
            return parent
    return file_path.parent


# ---------------------------------------------------------------- 回帰テスト
_HEAD = "# SPEC-%s: テスト\n\n## 1. 目的・背景\nテスト用。\n\n"


def _spec(body: str, num: str = "900") -> str:
    return (_HEAD % num) + body


_TABLE_HEAD = "## 6. 受け入れ基準\n\n| AC | 内容 | 検証 | 判定 |\n|---|---|---|---|\n"


def _self_test() -> int:
    cases: list[tuple[str, str, str, str]] = [
        # (名前, ファイル名, 本文, 期待する指摘コード or "")
        ("E1 節が無い", "SPEC-900-a.md",
         _spec("## 7. 正本への反映内容\n本文\n"), "E1"),
        ("E1 表が無い", "SPEC-901-a.md",
         _spec("## 6. 受け入れ基準\n\n散文で書いてある。\n"), "E1"),
        ("E2 ID形式", "SPEC-902-a.md",
         _spec(_TABLE_HEAD + "| 1 | 空文字で失敗する | `xlflow test --name T` | 自動 |\n"), "E2"),
        ("E2 重複", "SPEC-903-a.md",
         _spec(_TABLE_HEAD
               + "| AC-1 | 空文字で失敗する | `xlflow test --name T` | 自動 |\n"
               + "| AC-1 | 別の話 | `dotnet test` | 自動 |\n"), "E2"),
        ("E3 判定不正", "SPEC-904-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `xlflow test --name T` | 半自動 |\n"), "E3"),
        ("E3 判定空", "SPEC-905-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `xlflow test --name T` |  |\n"), "E3"),
        ("E4 検証空", "SPEC-906-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する |  | 自動 |\n"), "E4"),
        ("E4 プレースホルダ", "SPEC-907-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `<コマンド>` | 自動 |\n"), "E4"),
        ("E5 allowlist外", "SPEC-908-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `curl http://x` | 自動 |\n"), "E5"),
        ("E6 メタ文字迂回", "SPEC-909-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `xlflow test --name T && rm -rf ~` | 自動 |\n"), "E6"),
        ("E7 ac配下でない", "SPEC-910-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 帳票が崩れない | `目視で確認する` | 人手 |\n"), "E7"),
        ("E7 ファイル不在", "SPEC-911-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 帳票が崩れない | `bash docs/spec/changes/ac/nope.sh` | 人手 |\n"), "E7"),
        ("W1 曖昧語", "SPEC-912-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 適切に丸められる | `dotnet test` | 自動 |\n"), "W1"),
        ("正常(自動)", "SPEC-913-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で ERR を返す | `xlflow test --name T` | 自動 |\n"), ""),
        ("正常(人手あり)", "SPEC-914-a.md",
         _spec(_TABLE_HEAD
               + "| AC-1 | 空文字で ERR を返す | `xlflow test --name T` | 自動 |\n"
               + "| AC-2 | 帳票が崩れない | `bash docs/spec/changes/ac/ok.sh` | 人手 |\n"), ""),
        ("E6 パストラバーサル", "SPEC-916-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `python scripts/../../../evil.py` | 自動 |\n"), "E6"),
        ("E7 パストラバーサル", "SPEC-917-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 帳票が崩れない | `bash docs/spec/changes/ac/../../../../evil.sh` | 人手 |\n"), "E7"),
        ("E1 5列目に混入", "SPEC-918-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 空文字で失敗する | `dotnet test` | 自動 | rm -rf ~ |\n"), "E1"),
        ("コメント内の表を拾わない", "SPEC-919-a.md",
         _spec("## 6. 受け入れ基準\n\n<!--\n| AC-9 | 例 | `curl http://x` | 自動 |\n-->\n\n| AC | 内容 | 検証 | 判定 |\n|---|---|---|---|\n| AC-1 | 空文字で ERR を返す | `dotnet test` | 自動 |\n"), ""),
        ("W2 人手過半数", "SPEC-915-a.md",
         _spec(_TABLE_HEAD + "| AC-1 | 帳票が崩れない | `bash docs/spec/changes/ac/ok.sh` | 人手 |\n"), "W2"),
    ]

    failed = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / CHANGES_DIR).mkdir(parents=True)
        (root / "docs/spec/changes/draft").mkdir(parents=True)
        (root / AC_DIR).mkdir(parents=True)
        (root / AC_DIR / "ok.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

        for name, fname, text, expect in cases:
            p = root / CHANGES_DIR / fname
            p.write_text(text, encoding="utf-8")
            fs = check_spec(p, root, 0)
            codes = {f.code for f in fs}
            if expect:
                ok = expect in codes
            else:
                ok = not any(f.severity == "ERROR" for f in fs) and not codes & {"W1", "W2"}
            if not ok:
                failed += 1
                print("[NG] %s: 期待 %r / 実際 %s" % (name, expect or "指摘なし", sorted(codes)))
            else:
                print("[ok] %s" % name)

        # draft 降格
        d = root / "docs/spec/changes/draft/SPEC-920-a.md"
        d.write_text(_spec("## 7. 正本への反映内容\n本文\n", "920"), encoding="utf-8")
        fs = check_spec(d, root, 0)
        if any(f.severity == "ERROR" for f in fs) or not fs:
            failed += 1
            print("[NG] draft 降格: ERROR が残っています %s" % [str(f) for f in fs])
        else:
            print("[ok] draft 降格")

        # _template.md 除外
        tpl = root / CHANGES_DIR / "_template.md"
        tpl.write_text(_spec(_TABLE_HEAD + "| AC-1 | <内容> | `<コマンド>` | 自動 |\n"), encoding="utf-8")
        if any(p.name == "_template.md" for p in iter_specs(root, root)):
            failed += 1
            print("[NG] _template.md が対象に含まれています")
        else:
            print("[ok] _template.md 除外")

        # 適用下限(--since-spec)
        old = root / CHANGES_DIR / "SPEC-005-old.md"
        old.write_text(_spec("## 7. 正本への反映内容\n本文\n", "005"), encoding="utf-8")
        if check_spec(old, root, 10):
            failed += 1
            print("[NG] 適用下限より前の SPEC が検査されています")
        else:
            print("[ok] 適用下限")

        # コマンドを一切実行していないことの静的確認。
        # needle を実行時に連結して作るのは、この検査自身のリテラルに
        # 反応して常に落ちるのを避けるため(自己参照の回避)。
        src = Path(__file__).read_text(encoding="utf-8")
        needles = ["import sub" + "process", "from sub" + "process",
                   "os." + "system", "os." + "popen", "sub" + "process.run"]
        hit = [n for n in needles if n in src]
        if hit:
            failed += 1
            print("[NG] 外部コマンド実行の痕跡があります(設計違反): %s" % hit)
        else:
            print("[ok] 外部コマンド実行なし")

    print("\n自己テスト: %s (失敗 %d)" % ("PASS" if failed == 0 else "FAIL", failed))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="受け入れ基準(SPEC §6)の機械検査")
    ap.add_argument("--scan", metavar="PATH", help="リポジトリルートまたは SPEC ファイル")
    ap.add_argument("--since-spec", type=int, default=SINCE_SPEC,
                    help="この番号未満の SPEC を対象外にする(既定 %d)" % SINCE_SPEC)
    ap.add_argument("--self-test", action="store_true", help="回帰テストを実行")
    a = ap.parse_args()

    if a.self_test:
        return _self_test()
    if not a.scan:
        ap.print_help()
        return 2
    return run_scan(a.scan, a.since_spec)


if __name__ == "__main__":
    sys.exit(main())
