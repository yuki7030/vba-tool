---
name: doxyvb6
description: VBA(.bas/.cls/.frm)にDoxygenコメントを書く・APIリファレンスを生成する際に必ず使用。DoxyVB6フィルタが認識するマーカー(`'*`/`'!`/`'# Interface`)と生成手順を定義。
---

# DoxyVB6 による VBA Doxygen 生成

Doxygen は VBA を解析できない。[DoxyVB6](https://github.com/modern-vba/DoxyVB6) が
入力フィルタとして VBA を C# 相当の宣言へ変換し、Doxygen がそれを読む。
**フィルタが拾うのは専用マーカーで始まる行だけ**であり、素のコメントは捨てられる。

## マーカー

| 記法 | 変換先 | 用途 |
|---|---|---|
| `'*` | 直後メンバーの `///` | Sub / Function / Property / Enum / Type / Const / 変数のヘッダ |
| `'!` | モジュール自身の説明 | .bas/.cls/.frm 冒頭の概要 |
| `'# Interface` | クラスをインターフェース扱い | .cls のみ。行全体がこれ1つ |
| `'` | 破棄される | 実装内の「なぜ」コメント |

マーカーを間違えるとエラーにならず、**生成物からそのメンバーが静かに消える**。
メンバーに `'!` を付けた場合はモジュール説明側へ流れ込む。

## メンバーヘッダ

```vb
'* @brief   売上データを集計しシートへ出力する
'* @param   wsSrc  入力元ワークシート
'* @param   dtFrom 集計開始日
'* @return  出力した行数。異常時は -1
'* @details 日付範囲外の行は無視する
Public Function AggregateSales(ByVal wsSrc As Worksheet, ByVal dtFrom As Date) As Long
```

## モジュールヘッダ

`Attribute VB_Name` からモジュール名が取られる。エクスポート済み .bas/.cls には
必ず含まれるが、手書きファイルでは欠落しうる。

```vb
'! @brief 売上集計のドメインロジックを提供する
Attribute VB_Name = "SalesAggregator"
Option Explicit
```

## 生成対象と対象外

拾う: Function / Sub / Property / Enum / Type / Const / 変数の**宣言**。
拾わない: プロシージャの**内部コード**。ローカル変数にヘッダを書いても出力されない。

## 生成手順(未導入からのセットアップ)

1. Doxygen を PATH に通す。
2. 任意のツールフォルダに `GEN_DOC.BAT` と `gen_doc_main.ps1` を置く。
3. その下に `DoxyVB6/` を作り、`DoxyVB6.exe` と `Doxyfile` を置く。
4. `.bas`/`.cls` を含むフォルダの**親**がプロジェクトルートになる。
   そのフォルダと同じ階層に `GEN_DOC.BAT` へのショートカット `GEN_DOC.lnk` を作る。
   ショートカットの「作業フォルダー(Start in)」は**空欄**にする。
5. `GEN_DOC.lnk` を実行。`docs/api-reference/` と `docs/api-reference.zip` が出る。

`gen_doc_main.ps1` は Doxyfile テンプレートの `OUTPUT_DIRECTORY` / `INPUT` /
`INPUT_FILTER` / `PROJECT_NAME` を実行時に上書きする。Doxyfile を手で編集する前に
上書き対象かどうかを ps1 で確認する(手編集が無視される)。

## Property を書く / 既存 Property の出力が欠ける場合

インデックス付きプロパティ、`VB_UserMemId`、アクセサ群の並び順に固有の制約があり、
違反するとパースが失敗する。[references/property-rules.md](references/property-rules.md) を読む。
