---
name: cardhelper
description: OCR business cards, search contacts, and sync to Contacts.
version: 1.0.0
author: Array, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [cardhelper, business-card, ocr, contacts, macos, productivity]
---

# CardHelper 名片管理助手 Skill (Hermes Agent 專用)

當使用者傳送名片圖片、要求辨識名片、查詢名片聯絡人，或要求將某張名片標記為「重要 / 加入聯絡人」時，請使用此 Skill 與本機的 **CardHelper** 服務（預設運行於 `http://127.0.0.1:8765`，專案路徑 `/Users/arraymac/Desktop/project/CardHelper`）進行溝通。

## When to Use
- 使用者傳送名片照片或圖片檔案，要求辨識、建檔或匯入名片。
- 使用者要求查詢、搜尋已建檔的名片聯絡人（姓名、公司、職稱、電話、手機、統編、Email、地址）。
- 使用者要求將某張名片標記為「⭐ 重要」並自動同步至 macOS 聯絡人 (`Contacts.app`)。

## 1. 傳送名片圖檔進行 OCR 辨識與建檔 (`ingest`)

當使用者在對話中附上名片照片（或提供圖檔路徑）時，請使用 `terminal` 工具執行以下 CLI 指令：

### 方式 A：透過 CLI 指令（最推薦，即使伺服器未啟動也會自動執行）
```bash
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py ingest "<圖片絕對路徑>" \
  --notes "<選填備註>" \
  --important   # 若使用者提到「重要」或「加入聯絡人」才加此參數
```

### 方式 B：透過 HTTP Multipart 上傳圖檔
```bash
curl -s -X POST "http://127.0.0.1:8765/api/hermes/ingest" \
  -F "file=@/path/to/business_card.jpg" \
  -F "important=false" \
  -F "notes=透過 Hermes Agent 匯入"
```

### 方式 C：透過 HTTP JSON 傳遞本機圖檔路徑
```bash
curl -s -X POST "http://127.0.0.1:8765/api/hermes/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/business_card.jpg",
    "important": false,
    "notes": "",
    "conflict_policy": "update"
  }'
```

### 回傳結果說明
- `detected_count`：該張照片中自動偵測並拆出的名片張數（最多支援同張圖內含 4 張名片）。
- `cards`：辨識並存入 `cards_db.json` 的名片結構化欄位（包含 `id`, `name`, `english_name`, `title`, `company`, `mobile`, `phone`, `fax`, `email`, `address`, `tax_id`, `important`, `archived_image`）。
- 收到回傳後，請以清晰易讀的表格或條列方式向使用者回報辨識出的姓名、職稱、公司、電話、手機、Email 與歸檔檔名。

---

## 2. 搜尋名片聯絡人 (`search`)

當使用者詢問「幫我找統一證謝經理的電話」、「查詢某公司的名片」或「列出所有重要名片」時：

```bash
# 關鍵字搜尋（可搜尋姓名、公司、職稱、電話、Email、地址、備註）
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py search "<關鍵字>"

# 只列出標記為 ⭐ 重要的名片
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py search "" --important-only
```

---

## 3. 標記名片為「⭐ 重要」並同步至 macOS 聯絡人 (`important`)

當使用者說「把這張名片標記為重要」或「把剛剛那張名片加到電腦聯絡人」時：

```bash
# 標記重要並寫入 macOS Contacts.app
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py important "<card_id>" --on

# 取消重要並從 macOS Contacts.app 移除
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py important "<card_id>" --off
```

---

## 4. 探索個人社群帳號、相片與熱門文章 (`enrich`)

當使用者說「探索某人的社群」、「找某人的照片」或「查某人或公司的代表性文章」時：

```bash
# 探索指定名片或人員的 LinkedIn/FB/IG、下載相片頭像與提取前 3 篇熱門文章
python3 /Users/arraymac/Desktop/project/CardHelper/cardhelper_cli.py enrich "<card_id 或 姓名>"
```

### HTTP API 呼叫方式：
```bash
curl -s -X POST "http://127.0.0.1:8765/api/cards/<card_id>/enrich"
```
