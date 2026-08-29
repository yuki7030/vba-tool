# as-is 索引: <資産名>

> この文書群は **<観測日> 時点の観測結果**であり、合意された仕様ではない。
> 合意された仕様は `docs/spec/` にある。両者が矛盾する場合は `docs/spec/` を正とする。
> 陳腐化の確認は `docs/as-is/manifest.json` のハッシュと現在のコードを突き合わせる。

## この資産を触る前に

1. 改修対象がどの機能か分からない → 下の「機能一覧」
2. 触る関数の入出力・副作用を知りたい → [procedures.md](procedures.md)
3. 変更の波及範囲を知りたい → [dependencies.md](dependencies.md)
4. `Cells(i, 5)` の 5 が何か知りたい → [sheets.md](sheets.md)
5. **`【推測】` が付いた記述を根拠に改修判断をしてはならない。**
   確認が必要なら [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) を参照する。

## 機能一覧(解釈層)

| 機能 | 概要 | 主なモジュール | 詳細 |
|---|---|---|---|
| <機能名> | <1行> | <モジュール> | [features/<名>.md](features/<名>.md) |

## モジュール一覧(事実層)

| モジュール | パス | 行数 | Option Explicit | 機能 | 備考 |
|---|---|---|---|---|---|
| <名> | src/modules/... | 000 | 有/無 | <機能名 or 対象外> | |

`Option Explicit` が無いモジュールは、タイプミスが暗黙の `Variant` 変数になるため
改修時の危険度が高い。

## エントリポイント

| 種別 | 名称 | 起動元 |
|---|---|---|
| xlflow entry | <Module.Proc> | `xlflow.toml [project] entry` |
| ワークシート UDF | <関数名> | <シート名>!<範囲> の数式 |
| ブック/シートイベント | <Workbook_Open 等> | Excel |
| フォームイベント | <Form.Control_Event> | UserForm |
| 呼び出し元不明 | <Public プロシージャ名> | 不明(ボタン割り当ての可能性を否定できない) |

## リバース対象外

| モジュール | 除外理由 |
|---|---|
| Xlflow* | xlflow 提供の基盤モジュール。業務ロジックではない |

## 未解決・課題

- 人への確認待ち: [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)(<件数> 件)
- 移行課題・検証不能箇所: [MIGRATION-ISSUES.md](MIGRATION-ISSUES.md)(<件数> 件)
