#!/usr/bin/env python3
"""
CardHelper CLI Bridge for Hermes Agent & External Automation
Usage examples:
  1. Ingest & OCR a business card image (auto-archive, compress < 1MB, optional important/notes):
     python3 cardhelper_cli.py ingest /path/to/card.jpg --notes "展覽認識" --important

  2. Search business cards:
     python3 cardhelper_cli.py search "統一證"
     python3 cardhelper_cli.py search "謝涵瑜" --important-only

  3. Toggle important status (syncs with macOS Contacts.app):
     python3 cardhelper_cli.py important <card_id> --on
     python3 cardhelper_cli.py important <card_id> --off
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error

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


def cmd_ingest(args):
    file_path = os.path.abspath(os.path.expanduser(args.file_path))
    if not os.path.exists(file_path):
        print(json.dumps({"ok": False, "error": f"找不到圖檔：{file_path}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    payload = {
        "file_path": file_path,
        "notes": args.notes or "",
        "important": bool(args.important),
        "conflict_policy": args.conflict_policy,
        "auto_extract": not args.queue_only,
    }
    try:
        res = call_http_json("POST", "/api/hermes/ingest", payload)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    except Exception:
        sys.path.insert(0, BASE_DIR)
        import server
        res = server.ingest_business_card_image(
            src_image_path=file_path,
            orig_filename=os.path.basename(file_path),
            notes=args.notes or "",
            important=bool(args.important),
            conflict_policy=args.conflict_policy,
            auto_extract=not args.queue_only,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_search(args):
    params = urllib.parse.urlencode({
        "q": args.query or "",
        "important": "true" if args.important_only else "false",
    })
    try:
        res = call_http_json("GET", f"/api/cards/search?{params}")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    except Exception:
        sys.path.insert(0, BASE_DIR)
        import server
        matches = server.search_cards_query(args.query or "", important_only=args.important_only)
        print(json.dumps({
            "ok": True,
            "query": args.query or "",
            "count": len(matches),
            "cards": matches,
        }, ensure_ascii=False, indent=2))


def cmd_important(args):
    is_imp = not args.off
    payload = {
        "id": args.card_id,
        "card_id": args.card_id,
        "important": is_imp,
    }
    try:
        res = call_http_json("POST", "/api/cards/important", payload)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"請確認 CardHelper 伺服器是否啟動，錯誤：{e}"}, ensure_ascii=False, indent=2))
        sys.exit(1)


def cmd_enrich(args):
    target = args.target
    card_id = target
    try:
        cards_res = call_http_json("GET", f"/api/cards/search?q={urllib.parse.quote(target)}")
        if cards_res.get("cards"):
            card_id = cards_res["cards"][0].get("id")
    except Exception:
        pass

    try:
        res = call_http_json("POST", f"/api/cards/{urllib.parse.quote(card_id)}/enrich")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    except Exception:
        sys.path.insert(0, BASE_DIR)
        import server
        import search_enricher
        cards = server.load_cards()
        target_card = next((c for c in cards if c.get("id") == card_id or target.lower() in (c.get("name") or "").lower()), None)
        if not target_card:
            print(json.dumps({"ok": False, "error": f"找不到名片：{target}"}, ensure_ascii=False, indent=2))
            sys.exit(1)
        enrich_res = search_enricher.enrich_card_data(target_card)
        target_card.update({
            "avatar_url": enrich_res.get("avatar_url") or target_card.get("avatar_url"),
            "social_profiles": enrich_res.get("social_profiles", []),
            "top_articles": enrich_res.get("top_articles", []),
            "company_insights": enrich_res.get("company_insights", {}),
        })
        server.save_cards(cards)
        print(json.dumps({"ok": True, "card": target_card, "enriched": enrich_res}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="CardHelper CLI for Hermes Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ingest = subparsers.add_parser("ingest", help="傳送名片圖檔至 CardHelper 進行自動 OCR 辨識與建檔")
    p_ingest.add_argument("file_path", help="名片圖檔路徑 (支援單張或同圖最多 4 張名片)")
    p_ingest.add_argument("--notes", default="", help="附加備註文字")
    p_ingest.add_argument("--important", action="store_true", help="標記為⭐重要並自動加入 macOS 聯絡人")
    p_ingest.add_argument("--conflict-policy", default="update", choices=["update", "overwrite", "both"], help="重複名片處理原則")
    p_ingest.add_argument("--queue-only", action="store_true", help="僅放入 img/ 待處理佇列，不立即執行 OCR")
    p_ingest.set_defaults(func=cmd_ingest)

    p_search = subparsers.add_parser("search", help="搜尋已建檔的名片資料")
    p_search.add_argument("query", nargs="?", default="", help="搜尋關鍵字 (姓名、公司、職稱、電話、Email、地址)")
    p_search.add_argument("--important-only", action="store_true", help="只列出 ⭐ 重要名片")
    p_search.set_defaults(func=cmd_search)

    p_imp = subparsers.add_parser("important", help="設定或取消名片的 ⭐ 重要狀態 (同步 macOS 聯絡人)")
    p_imp.add_argument("card_id", help="名片 ID")
    p_imp.add_argument("--on", action="store_true", help="標記為重要並同步至 macOS 聯絡人 (預設)")
    p_imp.add_argument("--off", action="store_true", help="取消重要標記並從 macOS 聯絡人移除")
    p_imp.set_defaults(func=cmd_important)

    p_enr = subparsers.add_parser("enrich", help="在網路上自動探索個人社群帳號、相片與前3篇熱門文章")
    p_enr.add_argument("target", help="名片 ID 或姓名")
    p_enr.set_defaults(func=cmd_enrich)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
