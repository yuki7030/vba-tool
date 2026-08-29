# 各フェーズの手順と成果物

フェーズ③(characterization test)だけは
[characterization-tests.md](characterization-tests.md) に分離してある。

## 出力先(対象リポジトリ内)

```
docs/as-is/
├── INDEX.md                 索引。モジュール一覧・エントリポイント・読み進め方
├── procedures.md            公開プロシージャ一覧・純粋性判定・検証状態
├── dependencies.md          呼び出し関係・外部依存
├── sheets.md                シート構造(シート名・ヘッダ行・名前定義)
├── features/<機能名>.md      機能単位の詳細(解釈層)
├── OPEN-QUESTIONS.md        人への確認質問リスト
├── MIGRATION-ISSUES.md      移行課題リスト(規約違反・検証不能箇所)
├── CODEBASE-CONVENTIONS.md  資産固有の規約・地雷(AGENTS.md から参照される)
└── manifest.json            対象ファイルパス・ハッシュ・観測コミット
.github/skills/domain-<資産名>/SKILL.md
src/modules/Tests/<Module>Tests.bas    既存テストと同名になる場合は <Module>CharTests.bas
```

`INDEX.md` / `procedures.md` / `dependencies.md` / `sheets.md` / `manifest.json` が
**事実層**、`features/*.md` が**解釈層**。両者を混ぜない。
雛形は `templates/` 配下(`as-is-index.md` / `as-is-procedures.md` /
`as-is-dependencies.md` / `as-is-sheets.md` / `as-is-feature.md` /
`open-questions.md` / `migration-issues.md` / `codebase-conventions.md` /
`domain-skill.md`)。

## フェーズ①: 棚卸(事実層の生成)

抽出手順の詳細は [extraction.md](extraction.md)。

1. `xlflow session start` でセッションを開始する。
2. 事実を機械的に抽出する(`xlflow lint` / `analyze` / `formulas pull` /
   `inspect range`、`scripts/lsp_diagnostics.py` による LSP 診断、`src/` の静的読解)。
   **8ファイル以上の読み取りが必要なら explorer サブエージェントへ委譲する。**
   このフェーズは解釈を含まないため、委譲しても一貫性は崩れない。
3. `INDEX.md` / `procedures.md` / `dependencies.md` / `sheets.md` /
   `manifest.json` をテンプレートから生成する。
4. 規約違反・検証不能箇所を `MIGRATION-ISSUES.md` に記録する。
5. 次を人に提示して**承認を得る**:
   - 機能グルーピング案(どのモジュール群を1機能とみなすか。これは推測である)
   - 規模見積(機能数・純粋関数の数・想定される features ファイル数)
   - リバース対象外にするモジュール(`Xlflow*` 基盤モジュール等)

## フェーズ②: 機能詳細(解釈層の生成)

1. 承認されたグルーピングに従い、`features/<機能名>.md` を**逐次**生成する。
   **並列委譲しない。** 複数エージェントが並列に書くと、同じ業務用語に別々の訳語・
   別々の見出し構成・別々のマーカー運用を当て、資産全体で規律が揃わなくなる。
2. コードから読み取れない意図・業務的理由は `【推測】` を付けて記述し、
   **同じ項目を `OPEN-QUESTIONS.md` にも積む**。
3. 1機能あたり150行以内を目安にする(超えるなら機能の切り方が粗い)。
   記述規約は [writing-rules.md](writing-rules.md)。
4. `OPEN-QUESTIONS.md` を添えて**承認を得る**。

## フェーズ④: AI 向け成果物の生成

1. `.github/skills/domain-<資産名>/SKILL.md` を**1本だけ**生成する
   (雛形: `templates/domain-skill.md`)。機能単位に増やさない。
   description のトリガ語が重複して起動が不安定になる。
   役割は「この資産を触るなら `docs/as-is/INDEX.md` を読め」という導線に限る。
2. `docs/as-is/CODEBASE-CONVENTIONS.md` に資産固有の規約・地雷を書く。
   AGENTS.md から常時参照されるため **60行以内**。詳細は as-is 文書へ委譲する。
3. 対象リポジトリの AGENTS.md「プロジェクト知識」節に**参照1行のみ**追加する。
   本文を直接書き足さない(常時コンテキストに載るため他の重要指示が埋もれ、
   差分が大きいと既存指示の破壊をレビューで見逃す)。

   ```
   - 既存資産の現状挙動・固有の地雷 → docs/as-is/CODEBASE-CONVENTIONS.md
   ```

   AGENTS.md の差分が1行を超えたら、それは規則違反なので戻す。
4. 差分を提示して**承認を得る**。
5. `xlflow save --json` → `xlflow session stop`。
