# xlflow 概要と機能一覧

対象バージョン: **xlflow 0.20.0**(commit `0b05e64`, 2026-07-08 ビルド)
作成日: 2026-08-29 / 出典: 本リポジトリの `xlflow --help` 実出力、`xlflow.toml`、`.github/skills/xlflow/`

---

## 1. xlflow とは

**Excel VBA 開発を CLI とテキストソースだけで完結させるための開発フレームワーク**。
作者は harumiWeb、ライセンス MIT、Go / C# 製で PowerShell 非依存。

従来の VBA 開発は「VBE(Visual Basic Editor)を人間が開いて編集し、目視で実行し、
エラーはモーダルダイアログで止まる」という前提だった。この前提は
Git 管理・自動テスト・AI エージェントによる自律開発のいずれとも相性が悪い。

xlflow は Excel ブック(.xlsm)を **「ソースの置き場」ではなく「ビルド成果物」** として扱い、
真のソースを `src/` 配下のテキストファイル(.bas / .cls / .frm / YAML)に置く。
CLI が Excel COM 経由でブックへコードを流し込み(push)、実行し(run)、
テストし(test)、結果を **JSON で構造化して返す**。

### 従来手法との対比

| 論点 | VBE 手作業 / 自作 PowerShell | xlflow |
|---|---|---|
| ソースの正 | .xlsm の中(バイナリ) | `src/` のテキスト(Git 差分が読める) |
| 実行エラー | GUI ダイアログで停止 → 自動化が止まる | ダイアログを自動吸収し、種別・モジュール・行番号を JSON 返却 |
| MsgBox / InputBox | 人間の応答待ちでブロック | `XlflowUI` ラッパー + `--msgbox id=yes` で無人応答 |
| 実行速度 | 毎回 Excel を開閉 | セッションモードでブックを開いたまま反復 |
| テスト | 手動実行 / 自作フレームワーク | `xlflow test` に発見・フック・タグ・アサーションが内蔵 |
| UserForm | .frm バイナリ相当で差分不能 | YAML spec から生成(`form build`) |
| 文字コード | CP932 起因の文字化け | pull=UTF-8 / push=CP932 を自動変換 |
| 静的解析 | なし | `lint` / `analyze` / `fmt` を標準搭載 |

---

## 2. 全体像

```
  src/                     ← 真のソース(UTF-8, Git 管理)
    modules/*.bas
    classes/*.cls
    forms/specs/*.yaml     ← UserForm 定義(YAML)
    workbook/*.bas
  formulas/                ← ワークシート数式のスナップショット(JSONL)
  xlflow.toml              ← 唯一の設定ファイル
        │
        │  push  (UTF-8 → CP932 変換 + lint preflight)
        ▼
  build/vba-tool.xlsm      ← ビルド成果物(Excel ブック)
        │  run / test  (Excel COM 経由で実行)
        ▼
  JSON 出力(エラー種別 / 行番号 / debug ログ / UI イベント)
        │
        ▲  pull  (CP932 → UTF-8 変換)
```

Excel との接続は **セッション**という単位で管理される。
`session start` でブックを開いたままにし、以降の `push` / `run` / `test` は
`--session` を付けてその開きっぱなしのブックを再利用するため、反復が高速になる。

---

## 3. 機能一覧(カテゴリ別)

`xlflow --help` に現れる全 33 コマンドを機能カテゴリで整理したもの。

### 3.1 プロジェクト構築

| コマンド | 機能 |
|---|---|
| `xlflow new` | 新規プロジェクトとマクロブックを新しく作成 |
| `xlflow init <book.xlsm>` | **既存の .xlsm から** xlflow プロジェクトを起こす(移行の入口) |
| `xlflow skill install` | AI エージェント用のバンドル済みスキルを導入 |
| `xlflow module install` | `XlflowAssert` / `XlflowDebug` / `XlflowUI` 等のヘルパーモジュールを `src/` へ導入 |
| `xlflow runner install / status / remove` | 実行用の常駐ランナーモジュールをブックへ導入・確認・削除 |
| `xlflow doctor` | Excel COM / VBIDE アクセスの環境診断(トラストセンター設定漏れ等) |
| `xlflow update` | xlflow 本体の更新確認 |
| `xlflow version` | ビルド情報表示 |

### 3.2 ソースとブックの同期

| コマンド | 機能 |
|---|---|
| `xlflow push` | `src/` の VBA をブックへ取り込む。**lint が preflight として自動実行**され、違反があれば取り込み前に失敗する |
| `xlflow pull` | ブックから VBA を `src/` へ書き出す(`--formulas` で数式スナップショットも同時取得) |
| `xlflow status` | プロジェクト / ソース / ブック / セッションの状態を一覧 |
| `xlflow diff <before> <after>` | 2 つのブック、および書き出し済み VBA ソース同士を比較 |
| `xlflow pack --out <x.xlsm> --experimental` | ソースとテンプレートから .xlsm 成果物をビルド(**実験的機能**) |

`push` の主なフラグ:

| フラグ | 意味 |
|---|---|
| `--session` | 開いているセッションブックを再利用 |
| `--fast` | 開発向けの高速既定値を使う |
| `--no-save` | push 後にブックを保存しない(反復中の既定運用) |
| `--changed-only` | ソースに変化がなければブック更新をスキップ |
| `--backup always\|never` | push 前バックアップの方針(既定 `always`) |

### 3.3 セッション管理・実行

| コマンド | 機能 |
|---|---|
| `xlflow session start / status / stop` | ブックを開いたままにする開発セッションの開始・確認・終了 |
| `xlflow session attach` | 既に開いている Excel ブックへ後から接続 |
| `xlflow attach` | 現在アクティブなブック接続の確認 |
| `xlflow save` | セッション中のブックをディスクへ保存 |
| `xlflow run [macro]` | ブックのマクロを実行(マクロ省略時は `xlflow.toml` の `project.entry`) |
| `xlflow macros` | 実行可能マクロの一覧(`--runnable` で絞り込み) |
| `xlflow process list / cleanup` | ローカルの Excel プロセス一覧・強制終了(ゾンビ Excel の掃除) |
| `xlflow backup list` / `xlflow rollback` | push 時に自動取得されるバックアップの一覧・復元 |

`run` の主なフラグ:

| フラグ | 意味 |
|---|---|
| `--headless` | GUI 操作境界を事前に検出して拒否し、無人実行を保証する |
| `--interactive` | 逆に Excel を可視化して人間が操作する |
| `--diagnostic`(既定 on) | 実行前に VBA をコンパイルし、コンパイル診断を構造化して返す |
| `--arg string:hello` `--arg int:7` | 型付きのマクロ引数を渡す(`string` / `int` / `double` / `bool`) |
| `--msgbox` `--inputbox` `--filedialog` | ダイアログへの無人応答を与える(§4.3) |
| `--timeout 5m` | マクロの最大実行時間(既定 5 分)。超過をタイムアウトとして報告 |
| `--push` | 実行前に push を兼ねる |
| `--save` / `--no-save` / `--save-as <path>` | 実行後のブック保存方法 |
| `--gui-compile-errors` | 構造化診断ではなく、あえて GUI でエラーを出す(調査用) |

### 3.4 テスト

| コマンド | 機能 |
|---|---|
| `xlflow test` | ブック内 VBA テストの実行 |
| `xlflow test list` | ソースから発見されたテスト一覧 |
| `xlflow generate test <Module>` | フック雛形付きのテストモジュールを生成 |

絞り込みは `--filter <テスト名>`(完全一致)/ `--module <モジュール名>`(完全一致)/
`--tag <タグ>`(大小文字無視)で、組み合わせ可能。詳細は §4.2。

### 3.5 静的解析・整形

| コマンド | 機能 |
|---|---|
| `xlflow lint` | VBA ソースの静的解析。`push` の preflight としても走る |
| `xlflow analyze` | **実行時リスク**パターンの解析(例: `ActiveSheet` 依存 = VBA205) |
| `xlflow fmt [path...]` | .bas / .cls の整形 |
| `xlflow check` | `lint` + `analyze` + `doctor` を一括実行 |
| `xlflow inspect symbols` / `inspect calls` | ソース内のシンボル定義・呼び出し箇所の抽出 |
| `xlflow inspect-gui` | VBA の GUI 操作境界(無人実行を阻害する箇所)を報告 |
| `xlflow type db` | TypeLib 由来の型情報 DB を管理(補完・型解決の裏側) |
| `xlflow lsp` | VBA Language Server の起動。VSCode 拡張が補完・診断・定義ジャンプ・Rename・Test Explorer に使う |

`fmt` の主なフラグ: `--write`(書き戻し)/ `--check`(確認のみ)/ `--diff`(差分表示)/
`--stdin`、および `--line-numbers preserve|add|remove|renumber`(行番号の付与・除去。§4.4 のデバッグで使う)。

### 3.6 ブック状態の検査・操作

| コマンド | 機能 |
|---|---|
| `xlflow inspect workbook` | ブックのサマリ情報 |
| `xlflow inspect sheets` | シート一覧 |
| `xlflow inspect range --sheet <名前> --address <範囲>` | 範囲の値・状態 |
| `xlflow inspect cell` | 単一セル |
| `xlflow inspect used-range` | 軽量な UsedRange 取得 |
| `xlflow edit cell / range` | **ライブセッション**のセル・範囲を書き換える(テスト用データ投入等) |
| `xlflow edit rows / columns` | 行高・列幅の設定 |
| `xlflow export-image` | ワークシート範囲を画像として書き出し |

`inspect` は `--format text|json|markdown` を持つ。
注意: `inspect workbook / sheets / range / used-range / cell` は **保存済みファイル**を読む。
セッションに未保存の変更がある場合は先に `xlflow save` が必要。

### 3.7 UserForm(UaC: UserForm as Code)

| コマンド | 機能 |
|---|---|
| `xlflow list forms` | ブック内 UserForm と対応する .frm / .frx パスを列挙 |
| `xlflow inspect form <Name> --designer` | VBA を実行せず Designer を直接検査 |
| `xlflow inspect form <Name> --runtime` | 一時コピーブックで実際に初期化した状態を検査(`--initializer` 指定可) |
| `xlflow form snapshot <Name> --out <path.yaml>` | 既存フォームを YAML / JSON spec として書き出す |
| `xlflow form build <spec>` | spec からフォームを生成(`--overwrite` で置換) |
| `xlflow form new` | sidecar 方式の UserForm ソースを新規作成 |
| `xlflow form export-image <Name> --out <x.png>` | 実行時レンダリング結果を PNG 出力(見た目の検証) |
| `xlflow ui button` | ブック上のボタンコントロールを管理 |

詳細・spec スキーマは §4.5。

### 3.8 ワークシート数式のスナップショット

| コマンド | 機能 |
|---|---|
| `xlflow formulas pull` | 保存済みブックを OOXML として直接読み、数式を `formulas/` へ JSONL 出力 |
| `xlflow formulas inspect` | スナップショットを `--summary` / `--sheet` / `--cell` / `--range` の視点で参照 |

詳細は §4.6。

---

## 4. 中核機能の詳説

### 4.1 セッションモード(反復速度)

`session start` で Excel を起動しブックを開いたまま保持する。以降の
`push --session` / `run --session` / `test --session` は同じプロセス・同じブックを再利用するため、
コマンド毎の Excel 起動コスト(数秒規模)が消える。

```bash
xlflow session start --json
xlflow push --fast --session --no-save --json   # 反復中はここが最速形
xlflow test --session --json
# ... 編集 ...
xlflow push --fast --session --no-save --json
xlflow test --session --json
xlflow save --json
xlflow session stop --json
```

`--no-save` を付ける理由は、反復のたびにディスクへ書かないことでさらに速く、
かつ壊れた中間状態をブックに焼き付けないため。確定時に `save` する。

副次的な性質として、VBA の標準モジュールレベル変数は同一 Excel プロセス内の
`Application.Run` 間で保持される。テストのフック間で状態を共有できるのはこのため。

### 4.2 テストフレームワーク

**発見規則**: 標準モジュール内の `Public Sub`(または `Sub`)で、名前が `Test*` または `*_Test`
に一致し、**引数を取らない**もの。`Private Sub` と `Function` は無視される。
テストは通常のソースモジュールであり、専用ディレクトリは不要(本リポジトリは
`src/modules/Tests/` を推奨配置としている)。

**アサーション API**(`XlflowAssert`):

```vb
XlflowAssert.AssertEquals expected, actual, "メッセージ"
XlflowAssert.AssertNotEqual forbidden, actual, "メッセージ"
XlflowAssert.AssertTrue condition, "メッセージ"
XlflowAssert.AssertFalse condition, "メッセージ"
XlflowAssert.AssertIsNothing objectRef, "メッセージ"
XlflowAssert.AssertIsNotNothing objectRef, "メッセージ"
XlflowAssert.AssertFail "無条件失敗メッセージ"
XlflowAssert.AssertInconclusive "まだ実装されていない理由"
```

制約: `AssertEquals` / `AssertNotEqual` は **スカラー値のみ**。オブジェクトや配列は渡せず、
`Range.Value2` などスカラープロパティを比較する。

**ライフサイクルフック**: モジュール毎に `BeforeAll` / `AfterAll` / `BeforeEach` / `AfterEach`
(いずれも引数なし)を定義できる。失敗時の扱いは以下。

| フック | 失敗時 | `error.code` |
|---|---|---|
| `BeforeAll` | モジュール内の全テストが失敗扱い | `before_all_failed` |
| `AfterAll` | 成功/不確定だったテストも失敗へ上書き | `after_all_failed` |
| `BeforeEach` | そのテスト本体はスキップ(`AfterEach` は実行) | `before_each_failed` |
| `AfterEach` | そのテストが失敗扱い | `after_each_failed` |

**タグ**: テスト Sub の直上に `'@Tag("smoke")` 形式のコメントを置く。複数可。

**3 つの結果状態**: `passed` / `failed` / `inconclusive`。
`AssertInconclusive` による `inconclusive` は失敗にも成功にも数えないため、
「仕様は決まったが未実装」をコメントアウトせずに残せる。

JSON 出力は各テストについて `name` / `module` / `status` / `duration_ms` /
`error.{code,message,source,number}` を返す。

### 4.3 ヘッドレス UI(`XlflowUI`)

VBA の `MsgBox` / `InputBox` / ファイルダイアログは人間の応答を待ってブロックするため、
自動化の最大の障壁になる。xlflow は **同一のコードが対話実行と無人実行の両方で動く**
ラッパーを提供する。

提供される関数: `XlflowUI.MsgBox` / `InputBox` / `GetOpenFilename` /
`FileDialogOpen` / `GetSaveAsFilename` / `FolderPicker`。

```vb
decision = XlflowUI.MsgBox("confirm-save", "保存しますか?", vbYesNo + vbQuestion, "顧客")
customerName = XlflowUI.InputBox("customer-name", "顧客名", "顧客", "")
sourceFiles = XlflowUI.GetOpenFilename("source-files", MultiSelect:=True)
```

第 1 引数は **安定したダイアログ ID**。実行時に CLI から応答を注入する。

```bash
xlflow run Main.Run --headless --msgbox confirm-save=yes --inputbox customer-name=alice --json
xlflow run Main.Run --headless --filedialog get-open:source-files=C:\temp\a.txt --json
xlflow run Main.Run --headless --filedialog folder:export-dir=@cancel --ui-stream --json
```

- `--msgbox` の指定可能値: `yes` / `no` / `ok` / `cancel` / `abort` / `retry` / `ignore`
- `--filedialog` の kind: `get-open` / `file-open` / `save-as` / `folder`。`@cancel` でキャンセル表現。
  同じ `kind:id=` を繰り返すと複数選択の順序付き入力になる
- CLI 未指定時は VBA 側の `DefaultResponse` / `DefaultValue` にフォールバックする
- `--ui-stream` は解決過程を **stderr** へ実時間出力する(stdout の JSON を汚さない)。
  `InputBox` の値は既定で秘匿(`[redacted]`)される
- 人間が普通に Excel で開いた場合は素の `MsgBox` として振る舞うので、**利用者向けの挙動は変わらない**

生の `MsgBox` / `InputBox` 呼び出しは lint の `VB007` で検出される。

### 4.4 構造化されたエラー診断とデバッグ

xlflow の設計上の要は、**コンパイルエラー・実行時エラーの GUI ダイアログを自動で吸収し、
内容を JSON で返す**こと。返却されるのは `error.code` / `error.phase` / `error.message` /
`error.location`、および `debug.events`。

`Debug.Print` はターミナルへ届かないため、代わりに `XlflowDebug.Log` を使う。
これは `run` / `test` 実行時に stderr へストリームされ、JSON のトップレベル `debug` にも入る。

原因行が特定できない実行時エラーには、行番号 + `Erl` の併用が推奨手順:

```bash
xlflow fmt --line-numbers add --write      # 行番号を一時的に付与
xlflow push --fast --session --no-save --json
xlflow run <Macro> --headless --session --json
```

```vb
ErrHandler:
50  XlflowDebug.Log "Err.Number=" & CStr(Err.Number)
60  XlflowDebug.Log "Err.Description=" & Err.Description
70  XlflowDebug.Log "Erl=" & CStr(Erl)     ' ← 直前に実行された行番号
```

調査完了後は `xlflow fmt --line-numbers remove --write` で撤去する
(プロジェクトが意図的に行番号を保持する場合は `renumber` で正規化)。

`Erl` は行番号が無いと 0 を返すため、行番号は「`Erl` を意味あるものにするための道具」として
セットで使う。なお、コンパイルエラーではコードが実行されていないので `Erl` は無意味であり、
構造化コンパイル診断の location を直接読む。

### 4.5 UserForm as Code

UserForm は本来 `.frm` / `.frx` というレビュー困難な形式で保存されるが、
xlflow は **YAML / JSON の spec** を正とし、そこから Designer ベースのフォームを生成できる。

```yaml
schemaVersion: 1
kind: xlflow.userform
basis: designer
coordinateSystem: points
form:
  name: CustomerForm
  caption: Customer
controls:
  - id: frame_main
    name: FrameMain
    type: Frame
    progId: Forms.Frame.1
    left: 12
    top: 12
    width: 216
    height: 96
  - id: label_name
    parentId: frame_main     # ← 親子関係は id 参照で表現(フラット配列)
    name: LabelName
    type: Label
    left: 12
    top: 18
```

- `controls` はフラット配列。階層は `parentId`(大小文字区別)で表現し、
  兄弟順は `zIndex` で保つ。`id` の重複は自動補正せず検証エラーになる
- ビルド対応コントロール: `Label` / `TextBox` / `ComboBox` / `ListBox` /
  `CommandButton` / `CheckBox` / `OptionButton` / `Frame`
- **完全な往復変換は保証されない**。フォームの `width` / `height`、および
  設計時の `ComboBox` / `ListBox` の `list` / `selectedIndex` はベストエフォート扱い
- `--overwrite` は「export バックアップ → 削除 → 保存 → 再生成」で実装され、
  再生成に失敗した場合は元のフォームを復元してから失敗を返す
- `--overwrite --no-save` は不可(削除と再生成の間に Excel が保存を要求するため)

推奨ワークフロー: `list forms` → `inspect form --designer` → `pull` →
`form snapshot --out src/forms/specs/<Name>.yaml` → spec を編集 →
`form build <spec> --session --overwrite` → `inspect form` / `form export-image` で検証。

### 4.6 数式スナップショット

Excel の業務ロジックは VBA だけでなく **セルの数式**にも存在する。
`formulas pull` はこれを Git で追える形に落とす。

```
formulas/
  manifest.json                      # シート一覧とパース状況サマリ
  names.jsonl                        # 定義名(ブックスコープ / シートスコープ)
  sheets/001-Invoice.regions.jsonl   # 論理的な数式リージョン
```

重要な性質:

- **1 行 = 1 セルではなく、1 つの「同一パターンの数式が敷かれた領域」**。
  1000 セルにコピーされた数式は 1 行の差分として現れる
- `formula_r1c1`(正規化された R1C1 パターン)、`example_cell` / `example_formula`(代表セルの実際の式)、
  `count`、`refs`(参照先の推定範囲)、`depends_on_sheets`、`functions` を持つ
- `parse_status` は `ok` / `partial` / `failed`。**`partial` は失敗ではない** ——
  構造化参照・外部参照・3D 参照など正規化しきれない構文を、生の `formula` として安全に保持した状態
- Excel を起動せず OOXML を直接読むため、**未保存のセッション変更は反映されない**。
  先に `xlflow save` が必要

`formulas inspect --cell Invoice!E500` は、そのセルを含むリージョンを特定し、
可能ならその位置での A1 形式の式(例 `=D500*Config!$B$2`)まで展開して示す。

### 4.7 lint / analyze

`lint` はコーディング規約と危険パターンの静的検出で、**`push` の preflight としても走る**ため、
違反コードはブックへ入らない。`analyze` は実行時リスク(環境依存で壊れるパターン)を見る。

本リポジトリの `xlflow.toml` に記載のある診断 ID(全体の一部):

| ID | 内容 | 既定 |
|---|---|---|
| `VB001` 他 | `Option Explicit` 必須、`.Select` / `.Activate` 禁止、暗黙 Variant 検出など | 有効 |
| `VB006` | モジュールレベル public フィールド | 有効 |
| `VB007` | 生の `MsgBox` / `InputBox` / ファイルダイアログ呼び出し | 有効 |
| `VB018` | スコープシャドウイング | 無効(opt-in) |
| `VB020` | 未使用ローカル変数 | 有効 |
| `VB021` | 未使用 Private プロシージャ | 無効(opt-in) |
| `VB027` | `With` の曖昧参照 | 無効(opt-in) |
| `VBA205` | `ActiveSheet` 依存(analyze 側) | 有効 |

ルール単位の無効化は `xlflow.toml` の `[lint] disabled_rules` / `[analyze] disabled_rules` で行う。

### 4.8 安全機構

| 機構 | 内容 |
|---|---|
| 自動バックアップ | `push` は既定(`--backup always`)でブックを `.xlflow/backups/<timestamp>-push-<hash>/` へ退避 |
| ロールバック | `xlflow backup list` → `xlflow rollback` で復元 |
| push preflight | lint 違反、および UserForm spec 名 / `.frm` ベース名 / `Attribute VB_Name` の不一致で取り込みを中止 |
| プロセス掃除 | `xlflow process cleanup` で残留 Excel プロセスを終了 |
| フォーム再生成の巻き戻し | `form build --overwrite` 失敗時は一時 export から元フォームを復元 |
| 文字コード自動変換 | pull で UTF-8、push で CP932。ソースは常に UTF-8 のまま扱える |

---

## 5. 標準の開発ループ

本リポジトリ(`.github/skills/xlflow/SKILL.md`)で定めている手順。

```bash
# 1. セッション開始
xlflow session start

# 2. src/ 配下の .bas / .cls を編集(UTF-8 のまま)

# 3. ブックへ反映(lint 違反があればここで止まる)
xlflow push --fast --session --no-save --json

# 4. 実行 / 検証
xlflow run --session --json
xlflow test --session --json

# 5. 失敗したら JSON の Diagnostic(種別・モジュール・行番号・コード)を読んで自己修正 → 3 へ

# 6. 確定
xlflow save --json
xlflow session stop
```

新機能は TDD で進める:
テスト作成 → `xlflow test` で失敗確認 → 実装 → PASS → `xlflow lint` → `xlflow fmt . --write`。

---

## 6. 本リポジトリでの設定

`xlflow.toml` がプロジェクト直下にある唯一の設定ファイル。現在の設定:

| セクション | 主なキー | 現在値 | 意味 |
|---|---|---|---|
| `[project]` | `name` / `entry` | `vba-tool` / `Main.Run` | `xlflow run` のマクロ省略時の既定実行対象 |
| `[excel]` | `path` | `build/vba-tool.xlsm` | ビルド対象ブック |
| | `visible` | `false` | Excel ウィンドウ非表示 |
| | `display_alerts` | `false` | 上書き確認等のアラート抑制 |
| | `bridge` | `auto` | COM ブリッジ方式(`auto` / `dotnet`) |
| `[src]` | `modules` / `classes` / `forms` / `workbook` | `src/*` | ソースツリーの対応付け |
| `[vba]` | `folders` | `true` | Rubberduck 風 `@Folder("A.B")` 注釈を有効化 |
| | `folder_annotation` | `update` | push のたびにディレクトリ構成から注釈を書き換え |
| `[userform]` | `code_source` | `frm` | コードビハインドは `.frm` 内に保持(`sidecar` で分離可) |
| `[fmt]` | `operator_spacing` / `declaration_spacing` | `true` | 演算子・宣言まわりの空白正規化 |
| `[lint]` / `[analyze]` | `disabled_rules` | `[]`(無効化なし) | 全ルール有効 |

上表は「現在どうなっているか」だけを示す。**各キーを「いつ」「なぜ」直すかの判断基準、
導入手順、トラストセンター設定、スキルのリンク構造は
[docs/README-XLFLOW.md](README-XLFLOW.md) を正本とする**(ここには再掲しない)。

---

## 7. 前提・制約・リスク

**動作前提**

- Windows + デスクトップ版 Excel(COM 経由で操作するため)
- トラストセンター →「VBA プロジェクト オブジェクト モデルへのアクセスを信頼する」が **ON** 必須
- 未設定・不調時は `xlflow doctor --json` で診断できる

**機能上の制約**

- `inspect` の disk 系コマンドと `formulas pull` は **保存済みファイル**を読む。
  未保存のセッション状態は見えないため、先に `xlflow save` が必要
- `form build` は構造と一般的なプロパティの再現であり、**Designer の完全往復は保証しない**
- `xlflow pack`(純 Go でのブック生成)は `--experimental` 必須の実験的機能
- `AssertEquals` はスカラー限定。オブジェクト・配列は比較できない
- テストは引数なし `Public Sub` のみが対象

**プロジェクトリスク**(v0.x の破壊的変更・個人開発)の評価は
[docs/README-XLFLOW.md](README-XLFLOW.md) の「リスク」節を正本とする。

**運用上の注意**

- テストで外部ブックを開いたら必ず `Set wb = Nothing` で COM 参照を解放する。
  解放漏れはファイルロックとして残り、**別のテストの後片付けで初めて失敗する**
  (VBA エラー 70 / Permission denied はこのシグナル)
- テスト内で `ActiveSheet` / `Selection` / `ActiveWorkbook` に依存しない
- ダイアログ ID は業務上の判断を表す安定した名前にし、1 ID = 1 決定を守る

---

## 8. コマンド早見表

```bash
# 環境・プロジェクト
xlflow doctor --json                   # 環境診断
xlflow status                          # 状態確認
xlflow init excel_file/Book.xlsm --agent agents --with-skill

# 開発ループ
xlflow session start
xlflow push --fast --session --no-save --json
xlflow run --session --json
xlflow test --session --json
xlflow save --json && xlflow session stop

# テスト
xlflow test --filter Test_TotalPrice --session --json
xlflow test --module TestOrders --session --json
xlflow test --tag smoke --session --json
xlflow generate test TestOrders

# 品質
xlflow lint --json
xlflow analyze --json
xlflow fmt . --write
xlflow check                           # lint + analyze + doctor

# 検査
xlflow inspect range --sheet Invoice --address A1:D20 --json
xlflow inspect sheets --json
xlflow macros --runnable --json

# ダイアログ付き実行
xlflow run Main.Run --headless --msgbox confirm-save=yes --inputbox name=alice --ui-stream --json

# UserForm
xlflow list forms --session --json
xlflow form snapshot CustomerForm --out src/forms/specs/CustomerForm.yaml --session --json
xlflow form build src/forms/specs/CustomerForm.yaml --session --overwrite --json
xlflow form export-image CustomerForm --out tmp/form.png --session --json

# 数式
xlflow formulas pull --json
xlflow formulas inspect --summary --json
xlflow formulas inspect --cell Invoice!E500 --json

# 復旧
xlflow backup list
xlflow rollback
xlflow process cleanup
```

---

## 9. 関連ドキュメント

- 導入・セットアップ手順と `xlflow.toml` 設定リファレンス → [docs/README-XLFLOW.md](README-XLFLOW.md)
- 開発ループと安全規則(スキル本体) → [.github/skills/xlflow/SKILL.md](../.github/skills/xlflow/SKILL.md)
- テスト詳細 → [.github/skills/xlflow/references/testing.md](../.github/skills/xlflow/references/testing.md)
- デバッグ詳細 → [.github/skills/xlflow/references/debugging.md](../.github/skills/xlflow/references/debugging.md)
- ダイアログ詳細 → [.github/skills/xlflow/references/xlflow-ui.md](../.github/skills/xlflow/references/xlflow-ui.md)
- UserForm 詳細 → [.github/skills/xlflow/references/forms.md](../.github/skills/xlflow/references/forms.md)
- 数式スナップショット詳細 → [.github/skills/xlflow/references/formulas.md](../.github/skills/xlflow/references/formulas.md)
- VBA コーディング規約 → [.github/skills/vba-coding/SKILL.md](../.github/skills/vba-coding/SKILL.md)
