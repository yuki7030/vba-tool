"""xlflow LSP から VBA ソースの診断を取得する。

CLI の `xlflow lint` / `xlflow analyze` とは報告される診断が異なるため、
エディタが表示している警告を再現するにはこちらが必要になる。

使い方:
    python lsp_diagnostics.py <対象ファイル> [<対象ファイル> ...]

出力: 1 行 1 診断(`ファイル:行 [コード] メッセージ`)。診断が無ければ何も出さない。

注意: ここで得た診断をそのまま事実として書かないこと。誤検知の判定手順は
      references/extraction.md「CLI の診断だけでは足りない」を参照。
"""
import json
import os
import pathlib
import subprocess
import sys
import time

TIMEOUT_SEC = 25


def _send(proc, obj):
    body = json.dumps(obj).encode()
    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    proc.stdin.flush()


def _read(proc):
    header = b""
    while not header.endswith(b"\r\n\r\n"):
        chunk = proc.stdin and proc.stdout.read(1)
        if not chunk:
            return None
        header += chunk
    length = next(
        int(line.split(":")[1])
        for line in header.decode().split("\r\n")
        if line.lower().startswith("content-length")
    )
    return json.loads(proc.stdout.read(length))


def diagnostics_for(target):
    """target(パス)の診断リストを返す。1 ファイルにつき LSP を起動し直す。"""
    path = pathlib.Path(target)
    root = pathlib.Path(os.getcwd())
    uri = "file:///" + (root / path).as_posix()

    proc = subprocess.Popen(
        ["xlflow", "lsp", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"processId": None,
                                "rootUri": "file:///" + root.as_posix(),
                                "capabilities": {}}})
        _send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        _send(proc, {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                     "params": {"textDocument": {
                         "uri": uri, "languageId": "vba", "version": 1,
                         "text": path.read_text(encoding="utf-8")}}})

        deadline = time.time() + TIMEOUT_SEC
        while time.time() < deadline:
            message = _read(proc)
            if message is None:
                break
            if message.get("method") != "textDocument/publishDiagnostics":
                continue
            params = message["params"]
            # 別ファイルの診断が先に届くことがあるため、対象ファイルのものだけ拾う
            if params["uri"].lower().endswith(path.name.lower()):
                return params["diagnostics"]
        return []
    finally:
        proc.kill()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for target in sys.argv[1:]:
        for diag in diagnostics_for(target):
            line = diag["range"]["start"]["line"] + 1
            print("%s:%d [%s] %s" % (target, line, diag.get("code"), diag.get("message")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
