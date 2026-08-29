---
name: domain-<資産名>
description: <資産名>(<現場での呼び名・略語をすべて列挙>)の実装・修正・調査・質問時に必ず使用。現状挙動(as-is)の参照先と、参照時の注意を示す。
---

# <資産名> ガイド

<!--
  用途が近いテンプレートが2種ある。取り違えないこと:
    - 本テンプレート          … 既存VBA資産の as-is(docs/as-is/)への導線。reverse-vba が生成
    - .github/skills/_domain-template/ … 業務領域の知識(docs/domain/)への導線。手動で複製
  どちらも `.github/skills/domain-<名前>/SKILL.md` を作るため、同じ資産・領域に
  両方置いてはならない(description のトリガ語が衝突してスキル選択が不安定になる)。

  reverse-vba スキルが生成する。**資産全体で1本だけ**作る。
  機能単位に増やしてはならない。同じ業務用語が複数スキルの description に
  重複して載ると、スキル選択が不安定になる(全部起動する / どれも起動しない)。
  「どの機能を見るべきか」の振り分けは docs/as-is/INDEX.md が担う。
-->

## 必読

1. [docs/as-is/INDEX.md](../../../docs/as-is/INDEX.md) … 機能一覧・モジュール一覧・エントリポイント
2. [docs/as-is/CODEBASE-CONVENTIONS.md](../../../docs/as-is/CODEBASE-CONVENTIONS.md) … 固有の規約と地雷
3. [docs/glossary.md](../../../docs/glossary.md) … 用語(不明語は推測禁止)

## この資産を触るときの要点

<!-- 5行以内。毎回必ず意識させたい最重要事項だけ。詳細は上記へ委譲 -->

- `docs/as-is/` は **<観測日> 時点の観測結果**であり、合意された仕様ではない。
  `docs/spec/` と矛盾する場合は `docs/spec/` を正とする。
- **`【推測】` が付いた記述を根拠に改修判断をしてはならない。**
- <この資産で最も壊しやすい箇所を1行>

## 作業手順

1. 改修対象の機能を `docs/as-is/INDEX.md` の機能一覧から特定する。
2. 該当する `docs/as-is/features/<機能名>.md` を読む。
3. 波及範囲を `docs/as-is/dependencies.md` で確認する。
4. VBA の実装・テストは [xlflow スキル](../xlflow/SKILL.md) の手順に従う。
