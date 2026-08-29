---
name: reverse-vba
description: 既存VBA資産をリバースして現状仕様(as-is)とAIエージェント向けskill/instructionを生成する。VBAソースの解読・仕様起こし・引き継ぎ・レガシー資産の取り込み・「このVBAが何をしているか文書化したい」時に使用。
---

# VBA リバース(as-is 起こし)

既存 VBA 資産を読み解き、**現状の挙動(as-is)** と、以後その資産を改修する
AI エージェント向けの skill / instruction を生成する。

## 適用条件

- **対象リポジトリ上で実行する**。xlflow はリポジトリ単位で `xlflow.toml` と
  `.xlflow/` セッションを持つため、他リポジトリから外部参照して実行してはならない。
- 対象リポジトリは xlflow 導入済みで、`src/` 配下に実コードがあること。
- 本スキルを使うには、このスキルフォルダごと対象リポジトリの
  `.github/skills/reverse-vba/` へコピーする。

## 絶対規則(違反したら成果物を破棄する)

1. **対象の業務コードを修正しない。** 安全規則違反(`MsgBox` 直接呼び出し等)を
   見つけても自動修正しない。観測がコード改変になった瞬間、観測対象が変わる。
   違反は `MIGRATION-ISSUES.md` に記録して可視化するに留める。
   例外はフェーズ③の**既存テストの移設のみ**。
2. **as-is を `docs/spec/` に書かない。** as-is は観測結果であって合意ではない。
   `docs/spec/` に混ぜると既存挙動が「仕様」に昇格し、AGENTS.md の
   「仕様と既存挙動が矛盾する場合は仕様を正とする」が自己言及で無意味化する。
3. **推測を事実として書かない。** 推測には必ず `【推測】` を付け、同じ項目を
   `OPEN-QUESTIONS.md` にも積む。
4. **非純粋関数のテストを生成しない。** `MsgBox` を含む関数を実行すると
   モーダルダイアログで xlflow セッションが応答不能になる。
5. **シートのデータ本体を取り込まない。** 取り込むのは構造(シート名・ヘッダ行・
   名前定義)のみ。データは仕様ではなく、機微情報を `docs/` に永続化する事故になる。
6. **各フェーズの承認を得ずに次へ進まない。**

## 成果物

対象リポジトリの `docs/as-is/` に、**事実層**(`INDEX.md` / `procedures.md` /
`dependencies.md` / `sheets.md` / `manifest.json`)と**解釈層**(`features/*.md`)を
分けて置く。**両者を混ぜない。** 加えて `OPEN-QUESTIONS.md` /
`MIGRATION-ISSUES.md` / `CODEBASE-CONVENTIONS.md`、
`.github/skills/domain-<資産名>/SKILL.md`、`src/modules/Tests/` のテスト。
各ファイルの中身と雛形は [references/phases.md](references/phases.md)。

## 進め方

各フェーズの終わりで**必ず人の承認を得てから次へ進む**(絶対規則6)。

| フェーズ | やること | 承認材料 |
|---|---|---|
| ① 棚卸 | 機械抽出で事実層を作る | 機能グルーピング案(推測)・規模見積・対象外モジュール |
| ② 機能詳細 | 解釈層 `features/*.md` を**逐次**生成 | `OPEN-QUESTIONS.md` |
| ③ characterization test | 純粋関数だけをテスト化して実行 | 生成対象と件数(事前)/ 実行結果(事後) |
| ④ AI 向け成果物 | domain スキル・`CODEBASE-CONVENTIONS.md`・AGENTS.md へ1行 | 差分 |

**②は並列委譲しない。** 複数エージェントが並列に書くと、同じ業務用語に別々の訳語・
見出し構成・マーカー運用を当て、資産全体で規律が揃わなくなる。
**①は8ファイル以上の読み取りが必要なら explorer へ委譲してよい**
(解釈を含まないため、委譲しても一貫性は崩れない)。

## 手順の詳細

- ①②④ の手順・出力先の全体像 → [references/phases.md](references/phases.md)
- ① の事実抽出(xlflow / LSP 診断 / 純粋性判定 / manifest) →
  [references/extraction.md](references/extraction.md)
- ③ の対象選定・ケースの検算・既存テストの移設・命名制約 →
  [references/characterization-tests.md](references/characterization-tests.md)
- `【推測】` / `[検証済]` / 禁止する書き方 / 分量 →
  [references/writing-rules.md](references/writing-rules.md)

## 陳腐化の扱い

as-is は**取り込み時点のスナップショット**であり、改修に追従させない
(改修後の正本は `docs/spec/` 側に移る)。代わりに `manifest.json` が対象ファイルの
ハッシュと観測コミットを持ち、現在のコードとズレていれば「この記述は古い可能性がある」
と機械的に判定できる。

## 本スキルの範囲外

- **再実装・移植のための完全仕様(深度 C)**。本スキルの出力(全体マップ・機能詳細・
  テスト)を入力とする別スキルの領分。とりわけフェーズ③の characterization test は
  移植後の等価性判定基準になる。
- 対象コードのリファクタリング・バグ修正。

## 関連

- [.github/skills/xlflow/SKILL.md](../xlflow/SKILL.md) … xlflow の基本ループと安全規則
- [.github/skills/vba-coding/SKILL.md](../vba-coding/SKILL.md) … 生成テストのコメント規約
- [.github/skills/agent-workflow/SKILL.md](../agent-workflow/SKILL.md) … 委譲先の選定
