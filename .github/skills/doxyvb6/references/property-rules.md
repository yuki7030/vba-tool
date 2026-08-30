# DoxyVB6 の Property 変換規則

DoxyVB6 は Property Get/Let/Set を C# 相当の宣言へ変換する。
通常のクラスモジュールと `'# Interface` 付きモジュールで規則は同一。

## 変換される形

| VB の形 | 生成される C# 相当 |
|---|---|
| インデックス引数なし | 通常のプロパティ |
| インデックス引数あり + `Attribute <Name>.VB_UserMemId = 0` | インデクサ |
| インデックス引数あり(UserMemId なし)の Get | 戻り値を返すメソッド |
| インデックス引数あり(UserMemId なし)の Let/Set | 代入値を引数に取る `void` メソッド |

`VB_UserMemId = 0` があってもインデックス引数が無い場合はインデクサにならず、
通常のプロパティとして出力される(VB の既定メンバー呼び出しは表現されない)。

省略可能なインデックス引数とその既定値は、Doxygen が受け付ける限り保持される。

## アクセサ群の規則

- 同一プロパティの Get / Let / Set は**連続**して並べる。間に別メンバーを挟むとパース失敗。
- メンバーコメント(`'*`)は**群の先頭アクセサにのみ**書く。2つ目以降に書くとパース失敗。
- Get / Let / Set のインデックス署名を揃える。setter の代入値引数は署名に含まない。
- Get があれば、プロパティ型は Get の戻り値型から決まる。
- Let と Set で代入値の型が異なってよいのは、Get が存在する場合のみ。
- `Attribute <Name>.VB_UserMemId` の `<Name>` が群のプロパティ名と食い違うとパース失敗。

## パース失敗の条件(まとめ)

- アクセサ間のインデックス署名の不一致
- Let と Set のインデックス署名の不一致
- Get が無い Let / Set のみの組(代表型を決められない)
- 同一プロパティのアクセサが非連続
- 2つ目以降のアクセサにメンバーコメントがある
- 群内の `VB_UserMemId` のメンバー名不一致

## 自動生成される @note

元のアクセサにコメントが無くても出力されるため、
`EXTRACT_ALL = NO`(コメント必須設定)でもインデックス付きプロパティは消えない。

```csharp
/// @note Converted from the VB default indexed property <Name>.
/// @note Converted from a VB indexed property getter.
/// @note Converted from a VB indexed property setter.
```
