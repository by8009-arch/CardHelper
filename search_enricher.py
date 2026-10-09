#!/usr/bin/env python3
"""
CardHelper Search Enricher Module
功能：
  1. 在網路上搜尋個人的社群帳號 (LinkedIn, Facebook, Instagram, X/Twitter, GitHub 等)。
  2. 搜尋並下載一張個人的相片 (Avatar / Headshot)，儲存於 avatars/ 目錄並記錄於名片。
  3. 搜尋網路上 3 篇關於此人或此公司點閱率最高 / 最具代表性的新聞與報導文章。
"""

import os
import re
import urllib.parse
import urllib.request
from io import BytesIO
from bs4 import BeautifulSoup
from PIL import Image

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AVATARS_DIR = os.path.join(BASE_DIR, "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def clean_query_term(text: str) -> str:
    """清理多餘字元以利搜尋"""
    if not text:
        return ""
    # 移除括號內容
    s = re.sub(r"[\(（][^\)）]*[\)）]", " ", text)
    # 移除常見公司字尾
    s = re.sub(r"(股份有限公司|\(股\)公司|有限公司|株式會社|株式会社|有限会社|Co\.?,?\s*Ltd\.?|Inc\.?|Corp\.?)", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"[\\/:*?\"<>|\r\n/]+", " ", s)
    return " ".join(s.split()).strip()


def search_web_text(query: str, max_results: int = 10) -> list:
    """綜合搜尋網頁文字結果（優先使用 ddgs，若失敗則使用 DuckDuckGo HTML 解析）"""
    results = []
    if HAS_DDGS:
        try:
            ddgs_client = DDGS()
            raw = ddgs_client.text(query, max_results=max_results)
            for r in (raw or []):
                href = r.get("href") or r.get("url") or ""
                title = r.get("title") or ""
                snippet = r.get("body") or r.get("snippet") or ""
                if href and title:
                    results.append({"title": title, "url": href, "snippet": snippet})
            if results:
                return results
        except Exception:
            pass

    # Fallback: DuckDuckGo HTML
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")
        for r in soup.select(".result"):
            title_el = r.select_one(".result__title a")
            snippet_el = r.select_one(".result__snippet")
            if title_el:
                href = title_el.get("href", "")
                if "uddg=" in href:
                    href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                title = title_el.get_text(strip=True)
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append({"title": title, "url": href, "snippet": snippet})
    except Exception:
        pass

    return results


def search_web_images(query: str, max_results: int = 15) -> list:
    """搜尋圖片直接連結（使用 Bing Image 網頁擷取）"""
    image_urls = []
    try:
        url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        murls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", html)
        for u in murls:
            # 排除明顯廣告或 SVG
            if not u.endswith(".svg") and u not in image_urls:
                image_urls.append(u)
            if len(image_urls) >= max_results:
                break
    except Exception:
        pass
    return image_urls


def find_social_profiles(name: str, english_name: str = "", company: str = "") -> list:
    """
    搜尋該人員的社群帳號 (LinkedIn, Facebook, Instagram, X/Twitter, GitHub 等)。
    返回格式：[ {"platform": "LinkedIn", "url": "...", "username": "..."}, ... ]
    """
    profiles = []
    seen_platforms = set()
    seen_urls = set()

    c_name = name.strip()
    c_eng = english_name.strip()
    c_comp = clean_query_term(company)

    # 組合搜尋關鍵字
    queries = []
    if c_name and c_comp:
        queries.append(f'"{c_name}" "{c_comp}" linkedin')
        queries.append(f'"{c_name}" "{c_comp}" facebook')
        queries.append(f'"{c_name}" "{c_comp}" instagram')
    if c_eng and c_comp:
        queries.append(f'"{c_eng}" "{c_comp}" linkedin')
    if c_name:
        queries.append(f'"{c_name}" site:linkedin.com/in')
        queries.append(f'"{c_name}" site:facebook.com')

    def parse_profile(url_raw: str, title: str):
        url = url_raw.split("?")[0].rstrip("/")
        if url in seen_urls:
            return
        lower_url = url.lower()

        # LinkedIn
        if "linkedin.com/in/" in lower_url:
            if "LinkedIn" not in seen_platforms:
                m = re.search(r"linkedin\.com/in/([^/?#]+)", url)
                uname = m.group(1).strip() if m else ""
                if uname and re.match(r"^[a-zA-Z0-9.\-_%]{2,}$", uname):
                    seen_platforms.add("LinkedIn")
                    seen_urls.add(url)
                    profiles.append({"platform": "LinkedIn", "url": url, "username": urllib.parse.unquote(uname)})

        # Facebook (排除 share, hashtag, watch 等)
        elif "facebook.com/" in lower_url and not any(k in lower_url for k in ["/share", "/hashtag", "/watch", "/photo", "/groups", "/events"]):
            if "Facebook" not in seen_platforms:
                m = re.search(r"facebook\.com/([^/?#]+)", url)
                uname = m.group(1).strip() if m else ""
                if uname and uname.lower() not in ["profile.php", "home", "search"] and re.match(r"^[a-zA-Z0-9.\-_]{2,}$", uname):
                    seen_platforms.add("Facebook")
                    seen_urls.add(url)
                    profiles.append({"platform": "Facebook", "url": url, "username": uname})

        # Instagram (排除 /p/, /explore/, /stories/)
        elif "instagram.com/" in lower_url and not any(k in lower_url for k in ["/p/", "/reel/", "/explore/", "/stories/"]):
            if "Instagram" not in seen_platforms:
                m = re.search(r"instagram\.com/([^/?#]+)", url)
                uname = m.group(1).strip() if m else ""
                if uname and uname.lower() not in ["about", "developer", "terms", "accounts"] and re.match(r"^[a-zA-Z0-9._]{2,}$", uname):
                    seen_platforms.add("Instagram")
                    seen_urls.add(url)
                    profiles.append({"platform": "Instagram", "url": url, "username": f"@{uname}"})

        # X / Twitter
        elif ("x.com/" in lower_url or "twitter.com/" in lower_url) and not any(k in lower_url for k in ["/status/", "/i/", "/intent/"]):
            if "X" not in seen_platforms:
                m = re.search(r"(?:x|twitter)\.com/([^/?#]+)", url)
                uname = m.group(1).strip() if m else ""
                if uname and uname.lower() not in ["home", "explore", "messages"] and re.match(r"^[a-zA-Z0-9_]{2,}$", uname):
                    seen_platforms.add("X (Twitter)")
                    seen_urls.add(url)
                    profiles.append({"platform": "X (Twitter)", "url": url, "username": f"@{uname}"})

        # GitHub
        elif "github.com/" in lower_url and not any(k in lower_url for k in ["/topics", "/trending", "/pricing"]):
            if "GitHub" not in seen_platforms:
                m = re.search(r"github\.com/([^/?#]+)", url)
                uname = m.group(1).strip() if m else ""
                if uname and "/" not in uname and re.match(r"^[a-zA-Z0-9\-_]{2,}$", uname):
                    seen_platforms.add("GitHub")
                    seen_urls.add(url)
                    profiles.append({"platform": "GitHub", "url": url, "username": uname})

    for q in queries:
        items = search_web_text(q, max_results=6)
        for it in items:
            parse_profile(it.get("url", ""), it.get("title", ""))
        if len(profiles) >= 4:
            break

    return profiles


def find_and_save_avatar(name: str, english_name: str = "", company: str = "", card_id: str = "") -> dict:
    """
    搜尋個人照片，下載並存為 square JPEG 頭像 (avatars/<card_id>.jpg)。
    返回格式：{ "avatar_url": "/api/avatar?id=...", "source_image_url": "..." } 或 {}
    """
    if not card_id:
        return {}

    c_name = name.strip()
    c_eng = english_name.strip()
    c_comp = clean_query_term(company)

    candidate_queries = []
    if c_name and c_comp:
        candidate_queries.append(f'"{c_name}" "{c_comp}"')
    if c_eng and c_comp:
        candidate_queries.append(f'"{c_eng}" "{c_comp}"')
    if c_name:
        candidate_queries.append(f'"{c_name}"')

    for q in candidate_queries:
        img_urls = search_web_images(q, max_results=8)
        for u in img_urls:
            try:
                req = urllib.request.Request(u, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = resp.read()
                if len(data) < 2048:
                    continue
                im = Image.open(BytesIO(data))
                w, h = im.size
                # 排除太小或太極端的長寬比（例如長條橫幅或超長截圖）
                if w < 100 or h < 100:
                    continue
                ratio = w / float(h)
                if ratio < 0.45 or ratio > 2.2:
                    continue

                # 轉換為 RGB 並裁切為置中正方形
                im = im.convert("RGB")
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                cropped = im.crop((left, top, left + min_dim, top + min_dim))
                cropped = cropped.resize((400, 400), Image.Resampling.LANCZOS)

                out_filename = f"{card_id}.jpg"
                out_path = os.path.join(AVATARS_DIR, out_filename)
                cropped.save(out_path, format="JPEG", quality=88)

                return {
                    "avatar_url": f"/api/avatar?id={card_id}",
                    "source_image_url": u
                }
            except Exception:
                continue

    return {}


def find_top_articles(name: str, english_name: str = "", company: str = "") -> list:
    """
    搜尋網路上 3 篇關於此人或此公司點閱率最高 / 最具代表性的文章。
    返回格式：[ {"title": "...", "url": "...", "source": "...", "snippet": "..."}, ... ]
    """
    articles = []
    seen_urls = set()
    seen_domains = set()

    c_name = name.strip()
    c_eng = english_name.strip()
    c_comp = clean_query_term(company)

    queries = []
    if c_name and c_comp:
        queries.append(f'"{c_name}" "{c_comp}"')
    if c_comp:
        queries.append(f'"{c_comp}" 新聞 專訪 OR 報導')
        queries.append(f'"{c_comp}" 科技 營收 OR 發表')
    if c_name:
        queries.append(f'"{c_name}" 專訪 OR 報導')

    # 排除常見黃頁、求職、商工登記、單純社群目錄網址
    exclude_domains = {
        "findcompany.com.tw", "twincn.com", "opengovtw.com", "datagovtw.com",
        "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "google.com", "yahoo.com"
    }

    for q in queries:
        raw_results = search_web_text(q, max_results=8)
        for r in raw_results:
            u = r.get("url", "")
            if not u or u in seen_urls:
                continue
            parsed = urllib.parse.urlparse(u)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            if any(ex in domain for ex in exclude_domains):
                continue
            if domain in seen_domains:
                continue

            title = r.get("title", "").strip()
            snippet = r.get("snippet", "").strip()
            if not title:
                continue

            # 簡化來源網站名稱
            source_label = domain
            if "cna.com.tw" in domain:
                source_label = "中央社"
            elif "udn.com" in domain:
                source_label = "聯合新聞網"
            elif "ltn.com.tw" in domain:
                source_label = "自由時報"
            elif "chinatimes.com" in domain:
                source_label = "中時新聞網"
            elif "bnext.com.tw" in domain or "meet.bnext" in domain:
                source_label = "數位時代"
            elif "technews.tw" in domain:
                source_label = "科技新報 TechNews"
            elif "cool3c.com" in domain:
                source_label = "Cool3c"
            elif "inside.com.tw" in domain:
                source_label = "INSIDE 硬塞的"
            elif "ithome.com.tw" in domain:
                source_label = "iThome"
            elif "ctee.com.tw" in domain:
                source_label = "工商時報"
            elif "money.udn.com" in domain:
                source_label = "經濟日報"

            seen_urls.add(u)
            seen_domains.add(domain)
            articles.append({
                "title": title,
                "url": u,
                "source": source_label,
                "snippet": snippet
            })

            if len(articles) >= 3:
                return articles

    return articles[:3]


def enrich_card_data(card: dict) -> dict:
    """
    一鍵擴充名片資料：
      1. 搜尋個人社群帳號 (`social_profiles`)
      2. 搜尋並儲存個人相片 (`avatar_url`)
      3. 搜尋 3 篇熱門報導文章 (`top_articles`)
    """
    c_id = str(card.get("id", "")).strip()
    c_name = str(card.get("name", "")).strip()
    c_eng = str(card.get("english_name", "")).strip()
    c_comp = str(card.get("company", "")).strip()

    # 1. 社群帳號
    socials = find_social_profiles(c_name, c_eng, c_comp)

    # 2. 個人照片
    avatar_res = find_and_save_avatar(c_name, c_eng, c_comp, c_id)

    # 3. 熱門文章
    articles = find_top_articles(c_name, c_eng, c_comp)

    return {
        "social_profiles": socials,
        "avatar_url": avatar_res.get("avatar_url", ""),
        "source_avatar_url": avatar_res.get("source_image_url", ""),
        "top_articles": articles
    }


if __name__ == "__main__":
    import sys
    test_name = sys.argv[1] if len(sys.argv) > 1 else "侯剛平"
    test_comp = sys.argv[2] if len(sys.argv) > 2 else "麗臺科技"
    test_eng = sys.argv[3] if len(sys.argv) > 3 else "Vincent Hou"
    print(f"=== 測試搜尋擴充：{test_name} ({test_eng}) / {test_comp} ===")
    mock_card = {
        "id": "test_preview",
        "name": test_name,
        "english_name": test_eng,
        "company": test_comp
    }
    res = enrich_card_data(mock_card)
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
