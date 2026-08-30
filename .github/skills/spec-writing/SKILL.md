---
name: spec-writing
description: ユーザ要求の調査・検討と仕様書(Markdown)の作成・更新。新機能追加、変更依頼、要件整理、「仕様を決めたい」「〜を作りたい」等、実装前の検討フェーズで必ず使用する。既存 as-is の正本化(昇格)もここで扱う。
---

# 仕様調査・仕様書作成

## 仕様の2層構造

| 層 | 置き場 | 性質 |
|---|---|---|
| 正本(FEAT) | `docs/spec/features/FEAT-<番号>-<slug>.md` | 機能の**現行仕様**。生きた文書。ここに書かれている内容は人間が承認済み |
| 変更要求(SPEC) | `docs/spec/changes/SPEC-<番号>-<slug>.md` | 承認済みの**変更提案**。承認後は凍結し編集しない |
| 起案中 | `docs/spec/changes/draft/` | 未承認。**これを根拠に実装に着手しない** |
| 索引 | `docs/spec/features/README.md` | 機械生成。手で編集しない |

`docs/spec/features/` だけを「正本」と呼ぶ。`docs/as-is/` は取り込み時点の
**観測記録**であって正本ではない(reverse-vba スキル参照)。

## 手順

1. 要求を分析し、不明点を箇条書きで質問(最大5件)。回答を得てから次へ。
2. `docs/spec/features/README.md` の**索引だけ**を読み、対象 FEAT を特定する
   (features/ を全文検索しない。FEAT が増えるほどトークンが線形に膨らむため)。
3. 対象 FEAT が無い場合:
   - `docs/as-is/features/` に該当があれば **先に昇格**する(下記「as-is からの昇格」)。
     変更前の正本が無いと手順6の「完成形」が書けず、結局 as-is を読み直すことになるため。
   - as-is も無ければ FEAT は作らず先へ進む。手順7の実装時に新規作成する。
4. 既存コードと対象 FEAT を調査し、影響範囲を特定。
5. `docs/spec/changes/_template.md` を複製し
   `docs/spec/changes/draft/SPEC-<連番>-<slug>.md` を作成。
6. 「7. 正本への反映内容」に**反映後の FEAT 該当節の完成形**を書く。
   書式は `### FEAT-<番号> § <FEAT側の節見出し>` + 本文。差分・方針で書かない
   (実装後は機械転記するだけにし、AI の解釈が入る余地を残さないため)。
7. ユーザに承認を求める。**承認前に実装を始めない。**
   承認されたら `git mv` で `draft/` から `docs/spec/changes/` へ移す。
   以降の実装〜正本反映は autonomous-dev スキルのフローに従う。

## as-is からの昇格(正本化)

`docs/as-is/features/*.md` を FEAT に昇格させる手順。全文通読はしない。

1. 対象 as-is 内の `【推測】` 箇所と、`docs/as-is/OPEN-QUESTIONS.md` の
   該当項目を**抜き出してユーザに提示**し、回答を得る。
2. 回答を反映した内容で `docs/spec/features/FEAT-<連番>-<slug>.md` を作成
   (`docs/spec/features/_template.md` を複製)。メタ表の `出典` に
   `as-is/features/<名前>.md@<observedCommit>` を記録する。
3. 「as-is/features/<名前>.md@<commit> を FEAT-nnn として昇格します」と提示し、
   **ユーザの一言承認を得る**。`【推測】` がゼロでも省略しない。
   マーカーの付け漏れ(推測を事実として書いた箇所)は原理的に自己検出できず、
   無確認で昇格させると未検証の記述が「承認済みの正本」に化けるため。
4. 昇格後も `docs/as-is/` は削除しない。元の `as-is/features/<名前>.md` の冒頭に
   「FEAT-nnn へ昇格済み(本文は取り込み時点のスナップショット)」と追記する。
5. `python scripts/check_spec_sync.py --scan . --regen-index` で索引を再生成する。

## 記述ルール

- 曖昧語(「適切に」「柔軟に」)禁止。入出力・境界値・異常系を具体化。
- FEAT には**現行仕様のみ**を書く。目的・背景・未決事項・改訂履歴は書かない
  (それらは SPEC 側にあり、二重管理すると片方が必ず古くなる)。
  変更の経緯はメタ表の `関連SPEC` から辿る。
- SPEC は決定事項と未決事項を明確に分離する。
- 1 FEAT = 1 機能 / 1 SPEC = 1 変更要求。長大化したら分割。
- FEAT 冒頭のメタ表は索引生成の入力。項目名と行の順序を変えない。

## 検査

FEAT・SPEC・索引の整合は機械検査で担保する(人手の確認に頼らない):

```
python scripts/check_spec_sync.py --scan .
python scripts/check_spec_sync.py --scan . --regen-index
```
