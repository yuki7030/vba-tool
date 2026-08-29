# <資産名> 固有の規約と地雷

> AGENTS.md から参照される。**常時コンテキストに載るため 60 行以内に抑える。**
> 詳細は `docs/as-is/` の各文書へリンクで委譲し、ここには書き写さない。

## この資産を触る前に必ず読む

- [docs/as-is/INDEX.md](as-is/INDEX.md) … どのモジュールが何をしているか

## 絶対規則

1. `docs/as-is/` の記述のうち **`【推測】` が付いたものを根拠に改修判断をしてはならない。**
   確認が必要なら [OPEN-QUESTIONS.md](as-is/OPEN-QUESTIONS.md) に積むか、人に聞く。
2. `docs/as-is/` は <観測日> 時点のスナップショットであり、合意された仕様ではない。
   `docs/spec/` と矛盾する場合は `docs/spec/` を正とする。
3. 記述が古い可能性は `docs/as-is/manifest.json` のハッシュで確認する。

## 既存コードの流儀(観測されたもの、推奨ではない)

<既存コードが実際に採っている書き方。新規実装は AGENTS.md / vba-coding の規約に従うが、
既存コードを読むときの前提として必要なものだけ書く>

- エラー処理: <実際の流儀>
- 命名: <実際の流儀。規約と食い違う場合はその旨>
- シート参照: <名前指定 / CodeName / インデックスのどれが主流か>

## 触るときに壊しやすい箇所

| 箇所 | 何をすると壊れるか | 詳細 |
|---|---|---|
| <Module> | <例: シート名を変えると壊れる> | [dependencies.md](as-is/dependencies.md) |

## 未解消の課題

- [MIGRATION-ISSUES.md](as-is/MIGRATION-ISSUES.md)(<件数> 件)
- [OPEN-QUESTIONS.md](as-is/OPEN-QUESTIONS.md)(<件数> 件)
