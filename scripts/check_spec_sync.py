#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正本(docs/spec/features/)と変更要求(docs/spec/changes/)の同期検査・索引生成。

この設計は「FEAT に書かれている内容は人間が承認済み」という不変条件の上に乗る。
転記漏れが1回でも起きると code-review の突合基準が静かに壊れるため、
完了報告ではなく機械検査で担保する(最終防衛線をモデルの判断に置かない)。

  ERROR: 承認済み SPEC の「正本への反映内容」が対象 FEAT に転記されていない
  ERROR: 参照先の FEAT ファイル / 節が存在しない
  ERROR: features/README.md の索引が FEAT のメタ表と一致しない
終了コード: ERROR があれば 1(CI検知用)。指摘なしは 0。

使い方:
  python scripts/check_spec_sync.py --scan .                # 検査(CI / autonomous-dev)
  python scripts/check_spec_sync.py --scan . --regen-index  # 索引を再生成
  python scripts/check_spec_sync.py --self-test             # 回帰テスト

既知の制約: 承認済み SPEC は「実装 → 正本反映」まで完了してからコミットする前提。
承認直後の未反映状態でコミットすると本検査は ERROR になる(承認〜反映は
autonomous-dev の1ランで完結する運用のため、通常この窓は発生しない)。
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

FEAT_DIR = "docs/spec/features"
CHANGES_DIR = "docs/spec/changes"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
FEAT_FILE_RE = re.compile(r"^FEAT-(\d+)-[\w\-]+\.md$")
SPEC_FILE_RE = re.compile(r"^SPEC-(\d+)-[\w\-]+\.md$")
FEAT_H1_RE = re.compile(r"^#\s+FEAT-(\d+):\s*(.+?)\s*$")
# 「### FEAT-001 § 2. 処理」— 反映先の FEAT と節を一意に指す
REFLECT_RE = re.compile(r"^FEAT-(\d+)\s*§\s*(.+?)\s*$")
REFLECT_SECTION = "正本への反映内容"
META_KEYS = ("対象", "対象モジュール", "関連SPEC", "出典")

INDEX_HEADER = """# 機能仕様(正本)索引

<!-- このファイルは scripts/check_spec_sync.py が FEAT-*.md のメタ表から生成する。
     手で編集しない(次回の生成で上書きされる)。
     再生成: python scripts/check_spec_sync.py --scan . --regen-index -->

変更要求を検討するときは、まずこの索引だけを読んで対象 FEAT を特定する
(features/ を全文検索しない)。該当が無い場合の手順は
.github/skills/spec-writing/SKILL.md を参照。
"""


def norm(text: str) -> str:
    """比較用の正規化。空白の揺れとHTMLコメントで検査が落ちないようにする。"""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"\s+", " ", text).strip()


def section_body(lines: list[str], match) -> list[str] | None:
    """見出しが match(title) を満たす節の本文を、同レベル以上の見出しの手前まで返す。"""
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if not (m and match(m.group(2))):
            continue
        level, body = len(m.group(1)), []
        for nxt in lines[i + 1:]:
            m2 = HEADING_RE.match(nxt)
            if m2 and len(m2.group(1)) <= level:
                break
            body.append(nxt)
        return body
    return None


def parse_meta(lines: list[str]) -> dict[str, str]:
    """冒頭のメタ表(| 項目 | 内容 |)を読む。索引生成の入力。"""
    meta: dict[str, str] = {}
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] in META_KEYS:
            meta[cells[0]] = cells[1]
    return meta


def load_feats(root: Path) -> dict[str, dict]:
    """FEAT-*.md を番号キーで読み込む(_template.md / README.md は対象外)。"""
    feats: dict[str, dict] = {}
    d = root / FEAT_DIR
    if not d.is_dir():
        return feats
    for p in sorted(d.iterdir()):
        m = FEAT_FILE_RE.match(p.name)
        if not m:
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        h1 = next((FEAT_H1_RE.match(x) for x in lines if FEAT_H1_RE.match(x)), None)
        feats[m.group(1)] = {
            "path": p,
            "name": p.name,
            "title": h1.group(2) if h1 else "",
            "lines": lines,
            "meta": parse_meta(lines),
        }
    return feats


def build_index(feats: dict[str, dict]) -> str:
    if not feats:
        return INDEX_HEADER + "\n_登録された FEAT はまだありません。_\n"
    rows = ["| FEAT | 機能名 | 対象 | 対象モジュール |", "|---|---|---|---|"]
    for num in sorted(feats):
        f = feats[num]
        rows.append(f"| [FEAT-{num}]({f['name']}) | {f['title']} | "
                    f"{f['meta'].get('対象', '')} | {f['meta'].get('対象モジュール', '')} |")
    return INDEX_HEADER + "\n" + "\n".join(rows) + "\n"


def check(root: Path) -> list[tuple[str, str]]:
    """(ファイル, 指摘) の一覧を返す。空なら同期している。"""
    findings: list[tuple[str, str]] = []
    feats = load_feats(root)

    # 1) 索引が FEAT のメタ表と一致するか(索引は手書きせず生成物として扱う)
    index_path = root / FEAT_DIR / "README.md"
    expected = build_index(feats)
    actual = index_path.read_text(encoding="utf-8", errors="replace") if index_path.exists() else ""
    if norm(actual) != norm(expected):
        findings.append((f"{FEAT_DIR}/README.md",
                         "索引が FEAT と一致しない。--regen-index で再生成する"))

    # 2) 承認済み SPEC の反映内容が FEAT に転記されているか(draft/ は未承認なので対象外)
    changes = root / CHANGES_DIR
    if not changes.is_dir():
        return findings
    for p in sorted(changes.iterdir()):
        if not SPEC_FILE_RE.match(p.name):
            continue
        rel = f"{CHANGES_DIR}/{p.name}"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        body = section_body(lines, lambda t: REFLECT_SECTION in t)
        if body is None:
            findings.append((rel, f"「{REFLECT_SECTION}」節が無い"))
            continue
        blocks = 0
        for i, line in enumerate(body):
            m = HEADING_RE.match(line)
            if not m:
                continue
            r = REFLECT_RE.match(m.group(2))
            if not r:
                continue
            blocks += 1
            num, sec = r.group(1), r.group(2)
            level = len(m.group(1))
            content: list[str] = []
            for nxt in body[i + 1:]:
                m2 = HEADING_RE.match(nxt)
                if m2 and len(m2.group(1)) <= level:
                    break
                content.append(nxt)
            want = norm("\n".join(content))
            if not want:
                findings.append((rel, f"FEAT-{num} § {sec} の反映内容が空"))
                continue
            if num not in feats:
                findings.append((rel, f"参照先の FEAT-{num} が {FEAT_DIR}/ に無い"))
                continue
            target = section_body(feats[num]["lines"], lambda t, s=sec: norm(t) == norm(s))
            if target is None:
                findings.append((rel, f"FEAT-{num} に節「{sec}」が無い"))
                continue
            if want not in norm("\n".join(target)):
                findings.append((rel, f"FEAT-{num} § {sec} が未転記(正本と不一致)"))
        if blocks == 0:
            findings.append((rel, f"「{REFLECT_SECTION}」節に反映先(### FEAT-nnn § 節名)が無い"))
    return findings


SELF_TEST_FEAT = """# FEAT-001: サンプル機能

| 項目 | 内容 |
|---|---|
| 対象 | VBA |
| 対象モジュール | Sample.bas |
| 関連SPEC | SPEC-001 |
| 出典 | SPEC-001 |

## 1. 入力
なし

## 2. 処理
値を2倍して返す。負値は0を返す。

## 3. 出力
Long
"""

SELF_TEST_SPEC = """# SPEC-001: 負値の扱いを追加

| 項目 | 内容 |
|---|---|
| 対象FEAT | FEAT-001 |
| 対象 | VBA |
| 起案日 | 2026-08-30 |

## 7. 正本への反映内容

### FEAT-001 § 2. 処理
値を2倍して返す。負値は0を返す。
"""


def self_test() -> int:
    """検査が「通るべきケース」と「落ちるべきケース」を区別できることを確認する。"""
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / FEAT_DIR).mkdir(parents=True)
        (root / CHANGES_DIR / "draft").mkdir(parents=True)
        feat = root / FEAT_DIR / "FEAT-001-sample.md"
        spec = root / CHANGES_DIR / "SPEC-001-negative.md"
        feat.write_text(SELF_TEST_FEAT, encoding="utf-8")
        spec.write_text(SELF_TEST_SPEC, encoding="utf-8")
        (root / FEAT_DIR / "README.md").write_text(
            build_index(load_feats(root)), encoding="utf-8")

        if check(root):
            failures.append(f"同期済みなのに指摘が出た: {check(root)}")

        # 転記漏れ: FEAT 側だけ古いままにする
        feat.write_text(SELF_TEST_FEAT.replace("値を2倍して返す。負値は0を返す。",
                                               "値を2倍して返す。"), encoding="utf-8")
        if not any("未転記" in m for _, m in check(root)):
            failures.append("転記漏れを検出できなかった")
        feat.write_text(SELF_TEST_FEAT, encoding="utf-8")

        # 索引の陳腐化
        (root / FEAT_DIR / "README.md").write_text(INDEX_HEADER, encoding="utf-8")
        if not any("索引" in m for _, m in check(root)):
            failures.append("索引の不一致を検出できなかった")
        (root / FEAT_DIR / "README.md").write_text(
            build_index(load_feats(root)), encoding="utf-8")

        # 未承認(draft/)は検査対象外
        (root / CHANGES_DIR / "draft" / "SPEC-009-wip.md").write_text(
            "# SPEC-009: 起案中\n", encoding="utf-8")
        if check(root):
            failures.append("draft/ を検査対象にしてしまった")

        # 参照先の FEAT が無い
        spec.write_text(SELF_TEST_SPEC.replace("FEAT-001 §", "FEAT-777 §"), encoding="utf-8")
        if not any("FEAT-777" in m for _, m in check(root)):
            failures.append("存在しない FEAT 参照を検出できなかった")

    for f in failures:
        print(f"[FAIL] {f}")
    print("self-test: " + ("FAILED" if failures else "OK"))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", default=".")
    ap.add_argument("--regen-index", action="store_true", help="索引を再生成して終了")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    root = Path(args.scan).resolve()
    if not (root / FEAT_DIR).is_dir():
        print(f"{FEAT_DIR}/ が無いため検査をスキップ")
        return 0

    if args.regen_index:
        path = root / FEAT_DIR / "README.md"
        path.write_text(build_index(load_feats(root)), encoding="utf-8")
        print(f"索引を再生成: {FEAT_DIR}/README.md")
        return 0

    findings = check(root)
    print(f"仕様同期検査: 指摘 {len(findings)} 件")
    for f, msg in findings:
        print(f"[ERROR] {f}: {msg}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
