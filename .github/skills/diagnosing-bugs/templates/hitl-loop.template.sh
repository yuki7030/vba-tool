#!/usr/bin/env bash
# 人手介在(HITL)の再現ループ。
# このファイルをコピーし、下の手順を書き換えて実行する。
# 実行するのはエージェント、指示に従うのはユーザー(自分の端末に表示される)。
#
# 使い方:
#   bash hitl-loop.template.sh
#
# ヘルパは2つ:
#   step "<指示>"              → 指示を表示し、Enter を待つ
#   capture VAR "<質問>"       → 質問を表示し、回答を VAR に読み込む
#
# 最後に採取値が KEY=VALUE で出力され、エージェントがそれを読む。
#
# capture は値を端末に表示し、それをエージェントが読む。よって観測結果は
# capture で採り、サインインやブックを開くといった操作は step に置く。
set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [終わったら Enter] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- ここから書き換える -------------------------------------------------

step "対象のブックを Excel で開き、[売上入力] シートを表示してください。"

capture ERRORED "[集計] ボタンを押してください。エラーは出ましたか? (y/n)"

capture ERROR_MSG "エラーメッセージを貼り付けてください(無ければ none):"

# --- ここまで書き換える -------------------------------------------------

printf '\n--- 採取値 ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
