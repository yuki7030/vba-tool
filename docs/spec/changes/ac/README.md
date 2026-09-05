# 受け入れ基準(AC)の人手検証スクリプト

SPEC の「6. 受け入れ基準」で判定=**人手**とした AC の検証手順を置く。
書式検査は `python scripts/check_acceptance.py --scan .`(CI でも実行)。

## なぜ人手 AC を許すのか

VBA / Excel の領域には、帳票のレイアウト・UserForm の操作感など
**原理的に自動化できない AC** が必ずある。ここで自動を強制すると、
AI は「通るだけのテスト」を書く。それは未検証より質が悪い
(検証されたという誤った保証になる。`reverse-vba/references/writing-rules.md`
の `[検証済]` の扱いと同じ理由)。

人手 AC は**未検証として赤く残す**のが正しい状態であり、隠すべき欠陥ではない。

## ファイルの作り方

1. `.github/skills/diagnosing-bugs/templates/hitl-loop.template.sh` を複製する
2. `docs/spec/changes/ac/SPEC-<番号>-AC<番号>.sh` の名前で保存する
3. `step`(指示して Enter を待つ)と `capture`(質問して回答を変数へ)で手順を書く
4. SPEC の §6 の検証欄に `bash docs/spec/changes/ac/SPEC-nnn-ACn.sh` と書く

```bash
step "対象ブックを開き、[請求書出力] を実行してください。"
capture LAYOUT_OK "印刷プレビューで明細が1ページに収まっていますか? (y/n)"
```

## 誰がいつ実行するか

**自律実行(`/implement`)中は実行しない。** 実行すると人間が完了報告より前に
登場することになり、「人間の承認ゲートは仕様書の承認1箇所のみ」が崩れる。

自律実行は完了報告に `人手 n 件未検証(AC-2, AC-5)` と列挙するところまでを担う。
その後、人間が自分の判断で実行する。介入の引き金はシステムの要求ではなく
人間の判断である、という監督モデルを維持するため。

## 適用範囲

本検査は `scripts/check_acceptance.py` の `SINCE_SPEC` 以降の SPEC に適用する。
それより前の承認済み SPEC は対象外。凍結済みの承認物を検査通過のために
書き換えるのは、承認そのものの意味を消す操作だから
(同じ理由で autonomous-dev の停止条件に「§6 を書き換えない」を置いている)。

導入時に `SINCE_SPEC` を「現在の最大 SPEC 番号 + 1」へ書き換えること。
一時的な上書きは `--since-spec <番号>`。
