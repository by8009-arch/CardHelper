#!/usr/bin/env python3
"""
CardHelper MCP (Model Context Protocol) Stdio Server for Hermes Agent
Allows Hermes Agent (or Claude Desktop / Cursor / MCP clients) to directly invoke:
  - cardhelper_ingest_image: Send a business card image file to CardHelper for OCR, archiving (<1MB), and optional macOS Contacts sync
  - cardhelper_search_cards: Search saved business cards by name, company, title, phone, email, or notes
  - cardhelper_set_important: Mark/unmark a business card as Important and sync with macOS Contacts.app
"""

import json
import os
import sys
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_API_BASE = os.environ.get("CARDHELPER_API_URL", "http://127.0.0.1:8765")


def call_http_json(method, path, payload=None, timeout=45):
    url = f"{DEFAULT_API_BASE.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


TOOLS = [
    {
        "name": "cardhelper_ingest_image",
        "description": "傳送名片照片圖檔給 CardHelper 進行 Apple Vision OCR 多語系辨識（單張照片支援 1~4 張名片）、自動壓縮歸檔至 done/ (<1MB)、寫入名片資料庫，並可選擇標記為重要以自動加入 macOS 聯絡人 (Contacts.app)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "名片圖檔的本機絕對路徑 (例如 /path/to/card.jpg)"
                },
                "notes": {
                    "type": "string",
                    "description": "選填的備註資訊（例如認識場合、客戶需求）"
                },
                "important": {
                    "type": "boolean",
                    "description": "是否標記為⭐重要名片（若為 true 會自動同步至 macOS 聯絡人 Contacts.app）"
                },
                "conflict_policy": {
                    "type": "string",
                    "enum": ["update", "overwrite", "both"],
                    "description": "遇到同名同公司名片時的合併策略，預設為 update（智慧合併空白欄位）"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "cardhelper_search_cards",
        "description": "搜尋 CardHelper 名片資料庫中的聯絡人（可依姓名、英文名、公司、職稱、電話、Email、地址或備註搜尋）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜尋關鍵字（留空則列出全部名片）"
                },
                "important_only": {
                    "type": "boolean",
                    "description": "是否只篩選標記為⭐重要的名片"
                }
            }
        }
    },
    {
        "name": "cardhelper_set_important",
        "description": "將指定名片標記為⭐重要（自動加入 macOS 聯絡人）或取消重要標記（從 macOS 聯絡人移除）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "名片的唯一 ID"
                },
                "important": {
                    "type": "boolean",
                    "description": "true 為標記重要並加入聯絡人；false 為取消重要並移除聯絡人"
                }
            },
            "required": ["card_id", "important"]
        }
    }
]


def handle_tool_call(name, arguments):
    arguments = arguments or {}
    if name == "cardhelper_ingest_image":
        file_path = os.path.abspath(os.path.expanduser(arguments.get("file_path", "")))
        if not os.path.exists(file_path):
            return {"ok": False, "error": f"找不到名片圖檔：{file_path}"}
        payload = {
            "file_path": file_path,
            "notes": arguments.get("notes", ""),
            "important": bool(arguments.get("important", False)),
            "conflict_policy": arguments.get("conflict_policy", "update"),
            "auto_extract": True,
        }
        try:
            return call_http_json("POST", "/api/hermes/ingest", payload)
        except Exception:
            sys.path.insert(0, BASE_DIR)
            import server
            return server.ingest_business_card_image(
                src_image_path=file_path,
                orig_filename=os.path.basename(file_path),
                notes=payload["notes"],
                important=payload["important"],
                conflict_policy=payload["conflict_policy"],
                auto_extract=True,
            )

    elif name == "cardhelper_search_cards":
        query = arguments.get("query", "")
        important_only = bool(arguments.get("important_only", False))
        params = urllib.parse.urlencode({
            "q": query,
            "important": "true" if important_only else "false",
        })
        try:
            return call_http_json("GET", f"/api/cards/search?{params}")
        except Exception:
            sys.path.insert(0, BASE_DIR)
            import server
            matches = server.search_cards_query(query, important_only=important_only)
            return {"ok": True, "query": query, "count": len(matches), "cards": matches}

    elif name == "cardhelper_set_important":
        cid = arguments.get("card_id", "") or arguments.get("id", "")
        payload = {
            "id": cid,
            "card_id": cid,
            "important": bool(arguments.get("important", True)),
        }
        return call_http_json("POST", "/api/cards/important", payload)

    return {"ok": False, "error": f"未知的工具名稱：{name}"}


def send_response(msg):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cardhelper-mcp", "version": "1.0.0"}
                }
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            })
        elif method == "tools/call":
            params = req.get("params") or {}
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}
            try:
                result_data = handle_tool_call(tool_name, tool_args)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_data, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Error: {e}"}]
                    }
                })
        elif req_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            })


if __name__ == "__main__":
    main()
