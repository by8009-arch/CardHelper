#!/usr/bin/env python3
"""
CardHelper + Hermes + LM Studio 整合型 Telegram Bot
功能：
  1. 接收 Telegram 傳來的名片照片 (Photo / Image Document)，自動呼叫 CardHelper 進行 Apple Vision OCR
     (支援單張圖最多 4 張名片)、壓縮歸檔至 done/ (<1MB)、自動同步⭐重要名片至 macOS 聯絡人。
  2. 支援 Telegram 指令 (/start, /help, /search, /cards, /important) 與自然語言呼叫 CardHelper Skill。
  3. 採用 HTML 安全跳脫格式 (html.escape) 發送 Telegram 訊息，徹底避免 Email 底線 (_) 或特殊字元造成 Telegram 400 Bad Request。
"""

import asyncio
import html
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from telegram import Update
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

CARDHELPER_DIR = "/Users/arraymac/Desktop/project/CardHelper"
CARDHELPER_API = os.environ.get("CARDHELPER_API_URL", "http://127.0.0.1:8765")
LMSTUDIO_API = os.environ.get("LMSTUDIO_API_URL", "http://localhost:1234/v1/chat/completions")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "google/gemma-4-e4b")
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8895505472:AAGJiHmhkpH9LiDHLfhHKSBCDTRxaSX5V2o",
)

if CARDHELPER_DIR not in sys.path:
    sys.path.insert(0, CARDHELPER_DIR)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("CardHelperTelegramBot")

# 記錄每個 chat 最近一次處理或查詢到的名片 ID，方便使用者直接說「把這張標記為重要」
LAST_CARD_BY_CHAT = {}


def esc(val) -> str:
    return html.escape(str(val or ""))


def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


async def safe_reply_html(message, html_text: str):
    try:
        return await message.reply_text(html_text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"HTML reply fallback to plain text: {e}")
        return await message.reply_text(strip_html_tags(html_text))


async def safe_edit_html(status_msg, html_text: str):
    try:
        return await status_msg.edit_text(html_text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"HTML edit fallback to plain text: {e}")
        return await status_msg.edit_text(strip_html_tags(html_text))


def call_cardhelper_http(method: str, path: str, payload=None, timeout: int = 45):
    url = f"{CARDHELPER_API.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cardhelper_search(query: str = "", important_only: bool = False):
    # 直接使用最新 server.search_cards_query 確保複合關鍵字（如「麗臺科技侯剛平」）與即時檔案同步
    try:
        import server
        cards = server.search_cards_query(query or "", important_only=important_only)
        return {"ok": True, "query": query or "", "count": len(cards), "cards": cards}
    except Exception:
        params = urllib.parse.urlencode({
            "q": query or "",
            "important": "true" if important_only else "false",
        })
        return call_cardhelper_http("GET", f"/api/cards/search?{params}")


def cardhelper_ingest_file(file_path: str, notes: str = "", important: bool = False):
    payload = {
        "file_path": file_path,
        "notes": notes,
        "important": important,
        "conflict_policy": "update",
        "auto_extract": True,
    }
    try:
        return call_cardhelper_http("POST", "/api/hermes/ingest", payload, timeout=60)
    except Exception:
        import server
        return server.ingest_business_card_image(
            src_image_path=file_path,
            orig_filename=os.path.basename(file_path),
            notes=notes,
            important=important,
            conflict_policy="update",
            auto_extract=True,
        )


def cardhelper_set_important(card_id: str, important: bool = True):
    payload = {"id": card_id, "card_id": card_id, "important": important}
    try:
        return call_cardhelper_http("POST", "/api/cards/important", payload, timeout=30)
    except Exception:
        try:
            import server
            from datetime import datetime
            cards = server.load_cards()
            target_card = next((c for c in cards if c.get("id") == card_id), None)
            if not target_card:
                return {"ok": False, "error": "找不到該名片"}
            target_card["important"] = bool(important)
            target_card["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if important:
                contacts_ok, contacts_msg = server.sync_card_to_macos_contacts(target_card)
            else:
                contacts_ok, contacts_msg = server.remove_card_from_macos_contacts(target_card)
            server.save_cards(cards)
            return {
                "ok": True,
                "card": target_card,
                "contacts_synced": contacts_ok,
                "contacts_info": contacts_msg,
                "contacts_sync": {"ok": contacts_ok, "message": contacts_msg},
            }
        except Exception as e2:
            return {"ok": False, "error": str(e2)}


def format_card_summary_html(c: dict, idx: int = None) -> str:
    prefix = f"【名片 #{idx}】" if idx is not None else "📇 "
    star = "⭐ <b>[重要 / 已同步聯絡人]</b>" if c.get("important") else "☆ [一般]"
    name_str = esc(c.get("name") or "(未辨識姓名)")
    eng_str = esc(c.get("english_name") or "")
    # 若 name 已經包含 english_name，避免重複顯示
    if eng_str and eng_str.lower() in name_str.lower():
        title_line = f"{prefix}<b>{name_str}</b> {star}"
    else:
        title_line = f"{prefix}<b>{name_str}</b> {eng_str} {star}".strip()

    lines = [title_line]
    if c.get("company"):
        lines.append(f"🏢 公司：{esc(c['company'])}")
    if c.get("title"):
        lines.append(f"💼 職稱：{esc(c['title'])}")
    if c.get("mobile"):
        lines.append(f"📱 手機：<code>{esc(c['mobile'])}</code>")
    if c.get("phone"):
        lines.append(f"☎️ 電話：<code>{esc(c['phone'])}</code>")
    if c.get("fax"):
        lines.append(f"📠 傳真：<code>{esc(c['fax'])}</code>")
    if c.get("email"):
        lines.append(f"✉️ Email：<code>{esc(c['email'])}</code>")
    if c.get("tax_id"):
        lines.append(f"🔢 統編：<code>{esc(c['tax_id'])}</code>")
    if c.get("address"):
        lines.append(f"📍 地址：{esc(c['address'])}")
    if c.get("website"):
        lines.append(f"🌐 網站：{esc(c['website'])}")
    if c.get("notes"):
        lines.append(f"📝 備註：{esc(c['notes'])}")
    lines.append(f"🆔 ID：<code>{esc(c.get('id', ''))}</code>")
    return "\n".join(lines)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await asyncio.to_thread(cardhelper_search, "", False)
    total_cards = res.get("count", 0)
    imp_res = await asyncio.to_thread(cardhelper_search, "", True)
    imp_cards = imp_res.get("count", 0)

    msg = (
        "✅ <b>Hermes × CardHelper 名片助手已成功連線！</b>\n\n"
        f"📊 目前名片資料庫共有 <b>{total_cards}</b> 張名片（其中 ⭐ 重要名片 <b>{imp_cards}</b> 張）。\n\n"
        "📌 <b>你可以直接對我做以下操作：</b>\n"
        "1️⃣ <b>直接傳送名片照片</b>（支援單張照片內含 1～4 張名片）：\n"
        "   • 我會自動執行 Apple Vision OCR 辨識、壓縮歸檔至 <code>done/</code> (&lt;1MB)。\n"
        "   • 若照片說明文字加上「<code>重要</code>」，會自動同步進 Mac 的「聯絡人 (Contacts.app)」。\n"
        "2️⃣ <b>自然語言或指令查詢名片</b>：\n"
        "   • 例如：「<code>查侯剛平的電話</code>」、「<code>幫我查麗臺科技的所有聯絡人</code>」、「<code>列出重要名片</code>」\n"
        "   • 或輸入 <code>/search 關鍵字</code>、<code>/cards</code>\n"
        "3️⃣ <b>標記重要並加入 Mac 聯絡人</b>：\n"
        "   • 例如：「<code>把侯剛平標記為重要</code>」、「<code>把這張標記為重要</code>」\n"
        "   • 或輸入 <code>/important 姓名或ID</code>"
    )
    await safe_reply_html(update.message, msg)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip() if context.args else ""
    res = await asyncio.to_thread(cardhelper_search, query, False)
    cards = res.get("cards", [])
    if not cards:
        await safe_reply_html(update.message, f"🔍 找不到符合「<b>{esc(query)}</b>」的名片資料。")
        return
    LAST_CARD_BY_CHAT[update.effective_chat.id] = cards[0].get("id")
    blocks = [f"🔍 找到 <b>{len(cards)}</b> 張符合「<b>{esc(query or '全部')}</b>」的名片：\n"]
    for i, c in enumerate(cards[:10], start=1):
        blocks.append(format_card_summary_html(c, i))
    if len(cards) > 10:
        blocks.append(f"\n…（僅顯示前 10 筆，共 {len(cards)} 筆）")
    await safe_reply_html(update.message, "\n\n".join(blocks))


async def cards_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await asyncio.to_thread(cardhelper_search, "", False)
    cards = res.get("cards", [])
    if not cards:
        await safe_reply_html(update.message, "📭 目前資料庫中還沒有名片。")
        return
    LAST_CARD_BY_CHAT[update.effective_chat.id] = cards[0].get("id")
    blocks = [f"📚 目前共有 <b>{len(cards)}</b> 張名片（顯示最近 8 張）：\n"]
    for i, c in enumerate(cards[:8], start=1):
        blocks.append(format_card_summary_html(c, i))
    await safe_reply_html(update.message, "\n\n".join(blocks))


async def important_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = " ".join(context.args).strip() if context.args else ""
    chat_id = update.effective_chat.id
    card_id = None
    target_card = None

    if not target and chat_id in LAST_CARD_BY_CHAT:
        card_id = LAST_CARD_BY_CHAT[chat_id]
    elif target:
        res = await asyncio.to_thread(cardhelper_search, target, False)
        cards = res.get("cards", [])
        if cards:
            target_card = cards[0]
            card_id = target_card.get("id")
        else:
            card_id = target

    if not card_id:
        await safe_reply_html(
            update.message,
            "⚠️ 請提供要標記為重要的姓名或名片 ID，例如：<code>/important 侯剛平</code>",
        )
        return

    imp_res = await asyncio.to_thread(cardhelper_set_important, card_id, True)
    if imp_res.get("ok"):
        c = imp_res.get("card") or target_card or {}
        sync_msg = imp_res.get("contacts_sync", {}).get("message", "已同步至 macOS 聯絡人")
        await safe_reply_html(
            update.message,
            f"⭐ 已將 <b>{esc(c.get('name', card_id))}</b> 標記為重要！\n🔄 {esc(sync_msg)}\n\n{format_card_summary_html(c)}",
        )
    else:
        await safe_reply_html(update.message, f"❌ 標記失敗：{esc(imp_res.get('error', '未知錯誤'))}")



async def handle_photo_or_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = (update.message.caption or "").strip()
    is_important = any(k in caption.lower() for k in ["重要", "聯絡人", "important", "⭐", "star"])

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    status_msg = await update.message.reply_text(
        "⏳ 收到名片圖檔！正在透過 CardHelper (Apple Vision OCR) 進行多語系辨識與歸檔..."
    )

    suffix = ".jpg"
    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
    elif update.message.document:
        tg_file = await update.message.document.get_file()
        orig_name = update.message.document.file_name or f"telegram_card_{update.message.message_id}.jpg"
        _, ext = os.path.splitext(orig_name)
        if ext:
            suffix = ext
    else:
        await safe_edit_html(status_msg, "❌ 無法讀取圖片檔案。")
        return

    with tempfile.NamedTemporaryFile(prefix="tg_card_", suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await tg_file.download_to_drive(custom_path=tmp_path)
        res = await asyncio.to_thread(cardhelper_ingest_file, tmp_path, caption, is_important)
        if not res.get("ok"):
            await safe_edit_html(status_msg, f"❌ CardHelper 辨識失敗：{esc(res.get('error', '未知錯誤'))}")
            return

        # 同時相容舊欄位 (extracted/updated/replaced, card_count, done_filename) 與新欄位 (cards, detected_count, archived_image)
        cards = res.get("cards") or (
            res.get("extracted", []) + res.get("updated", []) + res.get("replaced", [])
        )
        detected_count = res.get("detected_count") or res.get("card_count") or len(cards)
        archived = res.get("archived_image") or res.get("done_filename") or ""
        if cards:
            LAST_CARD_BY_CHAT[chat_id] = cards[0].get("id")

        header = (
            f"✅ <b>CardHelper 辨識完成！</b>\n"
            f"📸 單檔偵測名片數：<b>{detected_count}</b> 張\n"
            f"🗂 壓縮歸檔：<code>done/{esc(archived)}</code>\n"
        )
        card_blocks = [format_card_summary_html(c, i + 1) for i, c in enumerate(cards)]
        footer = "\n💡 <i>提示：回覆「把這張標記為重要」即可自動加入 Mac 聯絡人 (Contacts.app)</i>"
        reply_text = header + "\n" + "\n\n".join(card_blocks) + "\n" + footer
        await safe_edit_html(status_msg, reply_text)
    except Exception as e:
        logger.exception("Error processing business card image")
        await safe_edit_html(status_msg, f"❌ 處理名片圖檔時發生錯誤：{esc(e)}")
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def detect_and_run_cardhelper_intent(user_text: str, chat_id: int):
    """
    針對自然語言指令自動判斷是否需要呼叫 CardHelper Skill，
    回傳 (handled_directly: bool, html_response: str)
    """
    text = user_text.strip()
    lower = text.lower()

    # 1. 檢查連線 / Skill 狀態
    if any(k in lower for k in ["cardhelper", "skill", "連上", "連線", "名片功能", "名片技能"]) and not any(
        k in lower for k in ["查", "找", "搜尋", "電話", "手機", "email", "地址", "統編", "誰"]
    ):
        res = cardhelper_search("", False)
        imp_res = cardhelper_search("", True)
        total = res.get("count", 0)
        imp = imp_res.get("count", 0)
        msg = (
            "✅ <b>已成功連接 Hermes <code>cardhelper</code> Skill 與本機 CardHelper 伺服器 (<code>127.0.0.1:8765</code>)！</b>\n\n"
            f"📇 目前名片資料庫：共 <b>{total}</b> 張名片（含 ⭐ 重要名片 <b>{imp}</b> 張）\n\n"
            "你可以直接：\n"
            "• 📷 <b>傳送名片照片給我</b>：自動 OCR 辨識（單張照片最多 4 張名片）並歸檔壓縮至 <code>done/</code>\n"
            "• 🔍 <b>直接問我</b>：「幫我查麗臺科技侯剛平的電話」、「幫我查麗臺科技的所有聯絡人」、「列出所有重要名片」\n"
            "• ⭐ <b>標記重要</b>：「把侯剛平標記為重要」（自動寫入 macOS 聯絡人 Contacts.app）"
        )
        return True, msg


    # 3. 把某人或剛剛那張名片標記為重要 / 加入聯絡人
    if any(k in text for k in ["標記為重要", "標記重要", "標定重要", "設為重要", "加入聯絡人", "加到聯絡人", "同步到聯絡人", "取消重要"]):
        turn_on = "取消" not in text
        cleaned = re.sub(
            r"(請|幫我|把|將|這張|剛剛那張|那張|名片|資料|的|標記為重要|標記重要|標定重要|設為重要|加入電腦聯絡人|加入聯絡人|加到聯絡人|同步到聯絡人|取消重要|標記|一下|吧|！|。|\s)+",
            "",
            text,
        )
        target_card = None
        card_id = None
        if cleaned:
            res = cardhelper_search(cleaned, False)
            if res.get("cards"):
                target_card = res["cards"][0]
                card_id = target_card.get("id")
        if not card_id and chat_id in LAST_CARD_BY_CHAT:
            card_id = LAST_CARD_BY_CHAT[chat_id]
        if not card_id:
            latest_res = cardhelper_search("", False)
            if latest_res.get("cards"):
                target_card = latest_res["cards"][0]
                card_id = target_card.get("id")

        if card_id:
            imp_res = cardhelper_set_important(card_id, turn_on)
            if imp_res.get("ok"):
                c = imp_res.get("card") or target_card or {}
                action_str = "⭐ 標記為重要並同步至 Mac 聯絡人" if turn_on else "☆ 已取消重要標記並從 Mac 聯絡人移除"
                return True, f"✅ <b>{action_str}</b>\n\n{format_card_summary_html(c)}"
            return True, f"❌ 操作失敗：{esc(imp_res.get('error', '未知錯誤'))}"

    # 3. 列出重要名片或全部名片
    if any(k in text for k in ["重要名片", "重要的名片"]):
        res = cardhelper_search("", True)
        cards = res.get("cards", [])
        if not cards:
            return True, "⭐ 目前還沒有標記為「重要」的名片。你可以說「<code>把侯剛平標記為重要</code>」來新增！"
        LAST_CARD_BY_CHAT[chat_id] = cards[0].get("id")
        blocks = [f"⭐ 目前共有 <b>{len(cards)}</b> 張重要名片（已同步至 Mac 聯絡人）：\n"]
        for i, c in enumerate(cards[:10], start=1):
            blocks.append(format_card_summary_html(c, i))
        return True, "\n\n".join(blocks)

    if any(k in text for k in ["所有名片", "全部名片", "有幾張名片", "名片列表", "列出名片"]):
        res = cardhelper_search("", False)
        cards = res.get("cards", [])
        if not cards:
            return True, "📭 目前名片資料庫是空的。"
        LAST_CARD_BY_CHAT[chat_id] = cards[0].get("id")
        blocks = [f"📚 目前資料庫共有 <b>{len(cards)}</b> 張名片（以下顯示前 8 張）：\n"]
        for i, c in enumerate(cards[:8], start=1):
            blocks.append(format_card_summary_html(c, i))
        return True, "\n\n".join(blocks)

    # 4. 關鍵字查詢名片（例如「幫我查麗臺科技的所有聯絡人」、「幫我查麗臺科技侯剛平的電話」、「查侯剛平的電話」、「查麗臺科技的電話」）
    card_related_keywords = ["名片", "電話", "手機", "傳真", "統編", "email", "信箱", "地址", "職稱", "公司", "聯絡方式", "聯絡人", "聯絡資訊"]
    search_verbs = ["查", "找", "搜尋", "搜索", "請問", "有沒有", "幫我看"]
    is_search_intent = any(k in lower for k in card_related_keywords) or any(v in text for v in search_verbs)

    if is_search_intent:
        kw = re.sub(
            r"(請|請問|幫我看一下|幫我看|幫我查詢|幫我查|幫我找|可以|一下|查詢|查看|查|搜尋|搜索|找一下|找|有沒有|所有的|所有|全部的|全部|的|名片|電話|手機|號碼|傳真|統編|統一編號|地址|職稱|公司|信箱|聯絡方式|聯絡資訊|聯絡人|是什麼|是多少|有哪些|有誰|嗎|呢|？|\?|!|！|。|cardhelper|skill|hermes)+",
            " ",
            text,
            flags=re.IGNORECASE,
        ).strip()

        candidates = [w for w in kw.split() if len(w) >= 2] if kw else []
        matched_cards = []
        if kw:
            res = cardhelper_search(kw, False)
            matched_cards = res.get("cards", [])
        if not matched_cards and candidates:
            for token in candidates:
                res = cardhelper_search(token, False)
                if res.get("cards"):
                    matched_cards = res["cards"]
                    break
        # 再用資料庫內每張名片的中文姓名、英文名、公司簡稱雙向比對使用者原句
        if not matched_cards:
            all_res = cardhelper_search("", False)
            for c in all_res.get("cards", []):
                c_name = (c.get("name") or "").strip()
                c_cjk_name = re.sub(r"[^\u4e00-\u9fff]", "", c_name)
                c_eng = (c.get("english_name") or "").strip()
                c_comp = (c.get("company") or "").strip()
                c_comp_short = re.sub(r"(股份有限公司|\(股\)公司|有限公司|公司|\(.*?\))", "", c_comp).strip()
                if (
                    (c_cjk_name and len(c_cjk_name) >= 2 and c_cjk_name in text)
                    or (c_name and len(c_name) >= 2 and c_name in text)
                    or (c_eng and len(c_eng) >= 3 and c_eng.lower() in lower)
                    or (c_comp_short and len(c_comp_short) >= 2 and c_comp_short in text)
                    or (c_comp and len(c_comp) >= 2 and c_comp[:4] in text)
                ):
                    matched_cards.append(c)

        if matched_cards:
            LAST_CARD_BY_CHAT[chat_id] = matched_cards[0].get("id")
            blocks = [f"🔍 從 <b>CardHelper</b> 為您找到 <b>{len(matched_cards)}</b> 筆名片資料：\n"]
            for i, c in enumerate(matched_cards[:8], start=1):
                blocks.append(format_card_summary_html(c, i))
            return True, "\n\n".join(blocks)
        elif kw:
            return True, f"🔍 在 CardHelper 名片資料庫中找不到符合「<b>{esc(kw)}</b>」的名片資料。"

    return False, ""


async def chat_with_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # 先檢查是否為 CardHelper Skill 相關指令，若是則直接執行並精準回傳
    handled, direct_reply = await asyncio.to_thread(detect_and_run_cardhelper_intent, user_text, chat_id)
    if handled:
        await safe_reply_html(update.message, direct_reply)
        return

    # 否則轉交 LM Studio 本地模型，並附上 CardHelper 摘要能力說明
    system_prompt = (
        "你是 Hermes Agent 與 CardHelper 名片管理助手的 Telegram AI 助理，請用繁體中文回答。\n"
        "你已經成功連接本機的 CardHelper 名片管理系統 (http://127.0.0.1:8765) 與 `cardhelper` Skill。\n"
        "當使用者想辨識名片時，請提示他直接把名片照片傳到這個 Telegram 對話視窗；\n"
        "當使用者想查詢名片或標記重要名片時，可以直接說出姓名或公司名稱（例如：查侯剛平的電話、把侯剛平標記為重要）。"
    )

    def _call_lmstudio():
        payload = json.dumps({
            "model": LMSTUDIO_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.7,
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            LMSTUDIO_API,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = await asyncio.to_thread(_call_lmstudio)
        if "error" in data:
            reply_text = f"LM Studio 錯誤：{data['error'].get('message', str(data['error']))}"
        else:
            msg = data["choices"][0]["message"]
            reply_text = msg.get("content") or msg.get("reasoning_content") or "（無回覆內容）"
    except Exception as e:
        reply_text = (
            f"💡 CardHelper 名片技能運作正常（可直接傳照片辨識或輸入 /search 關鍵字），"
            f"但連線至 LM Studio 聊天模型失敗：{e}"
        )

    await update.message.reply_text(reply_text)


def main():
    t_request = HTTPXRequest(
        connection_pool_size=16,
        read_timeout=60.0,
        write_timeout=60.0,
        connect_timeout=30.0,
        pool_timeout=30.0,
    )
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(t_request).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", start_cmd))
    application.add_handler(CommandHandler("search", search_cmd))
    application.add_handler(CommandHandler("card", search_cmd))
    application.add_handler(CommandHandler("cards", cards_cmd))
    application.add_handler(CommandHandler("list", cards_cmd))
    application.add_handler(CommandHandler("important", important_cmd))

    # 支援直接傳送照片或圖片檔案
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_or_image))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_with_agent))

    logger.info("CardHelper x Hermes Telegram Bot 正在運行...")
    while True:
        try:
            application.run_polling(drop_pending_updates=True, poll_interval=1.0)
            break
        except Exception as e:
            logger.warning("Polling encountered error: %s. Retrying in 3 seconds...", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
