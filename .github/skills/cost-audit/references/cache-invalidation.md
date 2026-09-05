# キャッシュ破棄の照合表

cache miss / cache creation の高止まりを観測したとき、直前の操作をこの表と
照合して原因を特定する。

## 前提

キャッシュは**prefix の完全一致**で効く。ファイル単位・セグメント単位の
キャッシュは存在せず、prefix のどこか一箇所が変わると以降すべてが再計算になる。

リクエストは変化頻度の低い順に並んでいる。

| 層 | 内容 | 変わる契機 |
|---|---|---|
| system prompt | 中核指示、ツール定義、output style | ロード済みツール定義の変化、Claude Code のアップグレード |
| project context | CLAUDE.md、auto memory、スコープなし rules | セッション開始、`/clear`、`/compact` |
| 会話 | メッセージ、応答、ツール結果 | 毎ターン |

モデルと effort level はプロンプト本文ではないが、どちらもキャッシュキーの一部。

## 破棄する操作

| 操作 | 備考 |
|---|---|
| `/model` によるモデル切替 | 内容が同一でも全再処理。キャッシュがウォームな間は確認プロンプトが出る |
| `/effort` による effort 変更 | 同一モデルでも effort ごとに別キャッシュ |
| fast mode の初回 ON | 会話につき1回だけ。OFF→再 ON はキャッシュを保つ |
| MCP サーバーの接続・切断 | tool search で deferred なら影響なし。prefix にロードされる構成では破棄 |
| プラグインの有効・無効 | MCP サーバーを提供するプラグインのみ上記に準じる。skill/command/agent/hook/monitor/theme は破棄しない |
| ツール名そのものの deny ルール追加 | `Bash` `WebFetch` 等の裸のツール名、`Bash(*)`、`"*"`。`Bash(rm *)` のようなスコープ付きは影響なし |
| `/compact` | 設計上、会話層を作り直す |
| Claude Code のアップグレード | 再起動後の初回ターンが未キャッシュになる |

## 破棄しない操作

| 操作 | 備考 |
|---|---|
| リポジトリ内のファイル編集 | 差分は system-reminder として追記されるだけ |
| CLAUDE.md のセッション中編集 | ただし**変更も反映されない**。`/clear`・`/compact`・再起動まで待つ |
| output style の変更 | 同上。反映も次セッション |
| permission mode の切替 | `opusplan` を除く(下記) |
| skill / command の呼び出し | user message として末尾に追記される |
| `/recap` | 表示用サマリを追記するだけ |
| `/rewind` | すでにキャッシュ済みの prefix まで切り詰めるため再利用される |
| `/advisor` の ON/OFF | 定義が cache breakpoint の後ろにある |

## 診断時に見落としやすい原因

**予防規則(`opusplan` を使わない・親セッションのモデルを切り替えない)は
agent-workflow が持つ。** 実装中のセッションで読まれる必要があるため、
事後診断用の本ファイルには置かない。ここは観測後の照合にのみ使う。

### アップグレード後の resume

履歴が別の system prompt の後ろに来るため、全履歴がキャッシュヒットなしで
再処理される。長いセッションほど復帰1発目が最も高くなる。
`claude --version` が前回測定時と違うなら、その回の cache miss は
アップグレードで説明できる可能性が高く、他の原因を探す前に確認する。

### サブエージェントは親のキャッシュを読まない

独自の system prompt とツールセットで別の会話を始めるため、初回リクエストは
必ずコールド。TTL もサブスクリプションで5分固定。一方 fork は親の system prompt・
ツール・履歴を継承するので親のキャッシュを読む。委譲コストを評価するときは
この非対称を前提にする。

## TTL

| 環境 | 既定 | 変更 |
|---|---|---|
| Claude サブスクリプション | 1時間を自動要求 | usage credits に入ると5分へ自動低下。`ENABLE_PROMPT_CACHING_1H=1` で維持 |
| API キー / クラウドプロバイダ | 5分 | `ENABLE_PROMPT_CACHING_1H=1` でオプトイン |

`FORCE_PROMPT_CACHING_5M=1` で常に5分に固定できる。キャッシュ挙動を
デバッグするとき、または2つの TTL を比較するときに使う。
