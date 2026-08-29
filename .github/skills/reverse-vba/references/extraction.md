# 事実抽出の手順(フェーズ①)

ここで扱うのは**解釈を含まない事実**だけ。読み取れなかったものは空欄にせず
「取得不可」と理由を書く。推測はこのフェーズでは一切書かない。

## 1. コードからの抽出

| 抽出物 | 方法 |
|---|---|
| モジュール一覧 | `src/` 配下の `.bas` / `.cls` / `.frm` を列挙。パス・行数・`@Folder` 注釈 |
| 公開プロシージャ | `Public Sub` / `Public Function` / `Public Property` の宣言行。`Public` 省略時も既定は Public なので `Private` が付かない宣言は Public として扱う |
| 呼び出し関係 | プロシージャ名の出現箇所を全文検索し、宣言以外の出現を呼び出しとみなす |
| モジュールレベル変数 | `Public` / `Global` 宣言。モジュール間の暗黙の結合点になるため必ず記録 |
| 外部依存 | `CreateObject` / `Shell` / `Open` / `Kill` / `Name ` / ADO・Scripting などの参照 |
| 定数表 | `Const` 宣言。値は転記するが、分類の意味は書かない(それは解釈層) |

`Option Explicit` の有無はモジュール単位で記録する。無いモジュールは
タイプミスが暗黙の `Variant` 変数になるため、改修時の危険度が高い。

## 2. xlflow からの抽出

セッション開始後に実行する。

```bash
xlflow session start
xlflow lint --json                 # VB0xx: 静的規約違反
xlflow analyze --json              # VBA2xx: ランタイムリスク(例 VBA205 アクティブシート依存)
xlflow formulas pull --json        # シート数式のスナップショット
xlflow inspect range --sheet <名前> --address <範囲> --json
```

- `lint` / `analyze` の診断は**そのまま事実層の材料になる**。特に `analyze` の
  ランタイムリスク診断は、静的読解では見落としやすい結合(アクティブシート依存など)を
  拾うため必ず実行する。

### CLI の診断だけでは足りない

**`xlflow lint` / `analyze`(CLI)と `xlflow lsp`(エディタ)は報告する診断が違う。**
CLI が「指摘なし」でも、LSP は VB030 / VB036 などを報告することがある。
人はエディタで警告を見ているので、CLI だけを根拠に
「静的解析の指摘なし」と書くと**事実と食い違った as-is を作る**。

LSP 診断はヘッドレスでも取得できる。同梱スクリプトを使う:

```bash
python .github/skills/reverse-vba/scripts/lsp_diagnostics.py src/modules/**/*.bas
```

内部では `xlflow lsp --stdio` を起動し、`initialize` → `initialized` →
`textDocument/didOpen` を送って `textDocument/publishDiagnostics` を受け取る。
`xlflow lsp --check` は起動前提の検証だけで診断は返さないので使えない。

得られた診断は**そのまま事実として書かず、誤検知かどうかを判定する**。
判定材料:

- VBA の言語仕様(例: `Array()` は可変長引数なので「最大1引数」は誤り)
- 当該コードを通るテストが PASS しているか
- 同じ書き方の別モジュールで報告されないか(報告の有無が
  行継続の有無だけで変わるなら、規則ではなく実装上の限界)

誤検知と判断した場合も**コードは修正しない**。`MIGRATION-ISSUES.md` に
「対応不要(誤検知)」として根拠つきで記録する。エディタに警告が出続ける以上、
記録がないと後任が同じ調査を繰り返す。
- `formulas pull` の結果から、**ワークシート数式に埋め込まれた UDF 呼び出し**を抽出する。
  UDF はコード側からは呼び出し元が見えないため、これがないと「引数にどんな値が来るか」が
  永久に分からない。フェーズ③のテストケース選定の根拠にもなる。
- `inspect range` は**構造の把握にのみ使う**。シート名一覧、ヘッダ行(通常 1 行目)、
  名前定義を取る。データ本体は取り込まない。

### `formulas pull` が書き出す `formulas/` の扱い

`formulas pull` は**リポジトリ直下に `formulas/` を生成する**。したがって
フェーズ①は厳密には読み取り専用ではない。これは xlflow が Git 追跡を
意図した正規の成果物なので、**削除も `.gitignore` 追加もしない**。
as-is 成果物と一緒にコミットする。

ただし `names.jsonl` に出る `__XLFLOW_DEBUG_PIPE__` は pid とセッション ID を含み、
**セッションごとに値が変わる**。差分に現れても業務上の変更ではないので、
レビュー時に無視してよい旨を対象リポジトリに共有しておく。

数式が 0 件の資産では `formulas/` が実質空になる。その場合はコミットせず
削除してよい(空のスナップショットに追跡価値がないため)。

## 3. エントリポイントの特定

as-is を読むエージェントが最初に必要とする情報。次を漏れなく列挙する。

1. `xlflow.toml` の `[project] entry`
2. ワークシート数式から呼ばれる UDF(`formulas pull` の結果)
3. `ThisWorkbook` / `Sheet*` のイベントプロシージャ(`Workbook_Open` 等)
4. UserForm のイベントプロシージャ
5. どこからも呼ばれていない `Public` プロシージャ(ボタン割り当て・手動実行の可能性)

5 は「呼び出し元不明」として記録する。**削除候補と書いてはならない**
(ボタンから呼ばれている可能性を静的に否定できない)。

## 4. マジックナンバーの解決

`Cells(i, 5)` / `Columns(3)` のような列番号直書きを列挙し、`sheets.md` の
ヘッダ行と突き合わせて「5 列目 = <ヘッダ名>」を対応表にする。
突き合わせできたものは事実、対象シートが特定できないものは
`OPEN-QUESTIONS.md` へ回す(**どのシートか推測しない**)。

## 5. 純粋性の判定(フェーズ③の前提)

判定は**保守的に**行う。疑わしきは非純粋に倒す。誤って非純粋と判定しても
テストが1件減るだけだが、誤って純粋と判定すると xlflow セッションが壊れる。

対象プロシージャ本体、および**そこから呼ばれる全プロシージャ**に
次のいずれかが現れたら**非純粋**とする。

- UI: `MsgBox` / `InputBox` / `XlflowUI.` / `.Show`
- シート/ブック: `Range` / `Cells` / `Columns` / `Rows` / `Sheets` / `Worksheets` /
  `Workbooks` / `ActiveSheet` / `ActiveCell` / `Selection` / `ThisWorkbook`
- アプリケーション: `Application.`(`Application.Volatile` を含む)
- ファイル/外部: `Open` / `Close` / `Kill` / `Name ` / `Shell` / `CreateObject` / `GetObject`
- 状態: モジュールレベル変数への代入、`Static` 変数
- 非決定: `Now` / `Date` / `Time` / `Timer` / `Rnd` / `Environ`

呼び出し先を再帰的にたどれない場合(動的呼び出し `Application.Run` 等)も非純粋とする。

判定結果は `procedures.md` に「純粋 / 非純粋(理由)」で記録する。
非純粋のうちテストしたかったものは `MIGRATION-ISSUES.md` にも積み、
「なぜ検証できないか」を残す。

## 6. manifest.json の形式

**観測結果そのものは持たない。**「何をいつ観測したか」だけを持つ。
内容を重複して持つと、二重管理になって必ず食い違う。

```json
{
  "observedAt": "2026-08-29",
  "observedCommit": "<git rev-parse HEAD>",
  "targets": [
    { "path": "src/modules/Foo/Foo.bas", "sha256": "<hash>", "documents": ["docs/as-is/features/foo.md"] }
  ]
}
```

- `sha256` は対象ファイルの内容ハッシュ。
- `documents` は、そのファイルを根拠に書かれた as-is 文書。
  ハッシュが現在のコードと一致しなければ、その文書は古い可能性があると判定する。
- 陳腐化検知は「ハッシュを取り直して比較する」だけで済むよう、
  Markdown の表からパースする形にはしない。
