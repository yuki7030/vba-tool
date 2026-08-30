---
name: Explore
description: >-
  Fast read-only codebase exploration (overrides the built-in Explore
  to pin a lightweight model instead of inheriting the session model).
tools: Read, Grep, Glob, Bash
model: sonnet
effort: medium
color: cyan
background: true
---

# Explore (model-pinned override) — 本プロジェクトでは既定で有効

## 挙動
このリポジトリの `.claude/agents/` に配置されているため、Claude Code は
組み込み `Explore` をこの定義で自動的に上書きする(追加のコピー作業は不要)。
v2.1.198 以降、組み込み Explore はメイン会話のモデルを継承するため、
メインが Opus のセッションでは Explore も Opus で走り、長考による
無音・コスト増の一因になる。この定義で Sonnet に固定する。

## コスト(公式ドキュメント明記の副作用・上書き中は常時発生)
組み込み Explore/Plan だけが CLAUDE.md と git status の読み込みを
スキップする最適化を持つ。同名カスタム定義で上書きしている間は:
- Explore 呼び出しごとに CLAUDE.md 全量 + git status が入力トークンに乗る
- 組み込みのチューニング済みプロンプト(thoroughness レベル対応)を失う

## 無効化したい場合
このファイルを削除すれば組み込み Explore の挙動に戻る。CLAUDE.md が
大きいプロジェクトでは、削除して CLAUDE.md の委譲規則で explorer
(本ハーネス)への委譲を促す方が副作用がない可能性がある。

役割: 高速な読み取り専用のコードベース探索。
結果は構造化サマリ(path:line + 判定)で返し、raw dump は返さない。
