#!/usr/bin/env python3
"""
CardHelper Search Enricher Module
三大核心功能升級：
  1. 嚴格相關性過濾：搜尋個人的社群帳號 (LinkedIn, Facebook, Instagram, X/Twitter, GitHub 等)。
     若經判斷與名片人員相關性不高（非本人、同名但職業/地區衝突、或純公司粉專），一律略過不放入。
  2. 嚴格相關性過濾：搜尋最具代表性 / 報導價值的文章。
     排除股票跳動流水帳、求職徵才與登記黃頁；若與本人或公司業務無直接高相關度，一律略過不放。
  3. 深掘公司網站、地址與地圖評論線索 (Company Insights & Map Clues)：
     若名片人員資訊有限，自動從公司官方網站 (About/Meta)、登記地址 (大樓/園區) 及 Google 地圖/大眾評論中萃取重要背景與評價線索。
  4. 搜尋並下載個人照片 (Avatar)，智慧正方形裁切並儲存於 avatars/ 目錄。
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


def normalize_cjk_spaces(text: str) -> str:
    """去除搜尋引擎在漢字之間插入的多餘空格，例如 '麗 臺 科 技' -> '麗臺科技'"""
    if not text:
        return ""
    # 去除相鄰漢字之間的空白
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[（(])", "", s)
    s = re.sub(r"(?<=[）)])\s+(?=[\u4e00-\u9fff])", "", s)
    return s.strip()


def clean_query_term(text: str) -> str:
    """清理多餘字元以利搜尋"""
    if not text:
        return ""
    # 移除括號內容
    s = re.sub(r"[\(（][^\)）]*[\)）]", " ", text)
    # 移除常見公司字尾
    s = re.sub(r"(股份有限公司|\(股\)公司|有限公司|株式會社|株式会社|有限会社|Co\.?,?\s*Ltd\.?|Inc\.?|Corp\.?)", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"[\\/:*?\"<>|\r\n/]+", " ", s)
    return normalize_cjk_spaces(" ".join(s.split()))


def extract_company_tokens(company_raw: str) -> list:
    """萃取公司名稱的代表性關鍵字（例如 '麗臺科技股份有限公司 (Leadtek Research Inc.)' -> ['麗臺科技', '麗臺', 'Leadtek']）"""
    tokens = []
    if not company_raw:
        return tokens

    # 1. 中文部分
    c_clean = clean_query_term(company_raw)
    if c_clean:
        tokens.append(c_clean)
        short_c = re.sub(r"(科技|電子|生醫|智能|工業|國際|證券|資訊|安全|技術|軟體|光電|通訊|設計)", "", c_clean).strip()
        if len(short_c) >= 2 and short_c not in tokens:
            tokens.append(short_c)

    # 2. 英文部分
    eng_matches = re.findall(r"([a-zA-Z0-9\s]{3,})", company_raw)
    for em in eng_matches:
        em_clean = re.sub(r"\b(Inc|Co|Ltd|Corp|Research|Holdings|Group|Electronics|Technology)\b", "", em, flags=re.IGNORECASE).strip()
        if len(em_clean) >= 3 and em_clean not in tokens:
            tokens.append(em_clean)

    return tokens


def search_web_text(query: str, max_results: int = 10) -> list:
    """綜合搜尋網頁文字結果（優先使用 ddgs，若失敗則使用 DuckDuckGo HTML 解析）"""
    results = []
    if HAS_DDGS:
        try:
            ddgs_client = DDGS()
            raw = ddgs_client.text(query, max_results=max_results)
            for r in (raw or []):
                href = r.get("href") or r.get("url") or ""
                title = normalize_cjk_spaces(r.get("title") or "")
                snippet = normalize_cjk_spaces(r.get("body") or r.get("snippet") or "")
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
                title = normalize_cjk_spaces(title_el.get_text(strip=True))
                snippet = normalize_cjk_spaces(snippet_el.get_text(strip=True) if snippet_el else "")
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
            if not u.endswith(".svg") and u not in image_urls:
                image_urls.append(u)
            if len(image_urls) >= max_results:
                break
    except Exception:
        pass
    return image_urls


# =========================================================================
# 1. 社群帳號嚴格過濾判斷 (Strict Social Profile Relevance)
# =========================================================================

def is_social_profile_relevant(url_raw: str, title: str, snippet: str, name: str, english_name: str, company: str, title_on_card: str = "") -> tuple:
    """
    嚴格檢驗此社群網址是否「真正屬於名片上的本人」：
    - 排除同名同姓但公司/職業/地區衝突的他國他人 (例如香港學生、新加坡醫學生等)。
    - 排除純公司官方粉專 (如 leadtektaiwan) 冒充個人帳號。
    回傳 (is_valid: bool, platform: str, username: str)
    """
    url = url_raw.split("?")[0].rstrip("/")
    lower_url = url.lower()
    combined_text = normalize_cjk_spaces(f"{title} {snippet} {url}".lower())

    platform = ""
    username = ""

    # 辨識平台
    if "linkedin.com/in/" in lower_url:
        platform = "LinkedIn"
        m = re.search(r"linkedin\.com/in/([^/?#]+)", url)
        username = urllib.parse.unquote(m.group(1).strip()) if m else ""
    elif "facebook.com/" in lower_url:
        if any(k in lower_url for k in ["/share", "/hashtag", "/watch", "/photo", "/groups", "/events", "/posts", "/pages"]):
            return False, "", ""
        platform = "Facebook"
        m = re.search(r"facebook\.com/([^/?#]+)", url)
        username = m.group(1).strip() if m else ""
    elif "instagram.com/" in lower_url:
        if any(k in lower_url for k in ["/p/", "/reel/", "/explore/", "/stories/", "/direct/"]):
            return False, "", ""
        platform = "Instagram"
        m = re.search(r"instagram\.com/([^/?#]+)", url)
        username = f"@{m.group(1).strip()}" if m else ""
    elif "x.com/" in lower_url or "twitter.com/" in lower_url:
        if any(k in lower_url for k in ["/status/", "/i/", "/intent/", "/hashtag/"]):
            return False, "", ""
        platform = "X (Twitter)"
        m = re.search(r"(?:x|twitter)\.com/([^/?#]+)", url)
        username = f"@{m.group(1).strip()}" if m else ""
    elif "github.com/" in lower_url:
        if any(k in lower_url for k in ["/topics", "/trending", "/pricing", "/features", "/organizations"]):
            return False, "", ""
        platform = "GitHub"
        m = re.search(r"github\.com/([^/?#]+)", url)
        raw_u = m.group(1).strip() if m else ""
        if "/" not in raw_u:
            username = raw_u
    elif "threads.net/@" in lower_url:
        platform = "Threads"
        m = re.search(r"threads\.net/@([^/?#]+)", url)
        username = f"@{m.group(1).strip()}" if m else ""

    if not platform or not username:
        return False, "", ""

    # 排除無效名稱或系統保留字
    if username.lower().lstrip("@") in ["profile.php", "home", "search", "about", "developer", "terms", "accounts", "explore", "login", "signup"]:
        return False, "", ""

    # 排除純公司粉專冒充個人 (例如 leadtektaiwan, horustech)
    comp_tokens = [t.lower() for t in extract_company_tokens(company)]
    u_lower = username.lower().lstrip("@")
    if comp_tokens and any(u_lower == t or u_lower.startswith(t + "taiwan") or u_lower.startswith(t + "official") for t in comp_tokens):
        return False, "", ""

    c_name = re.sub(r"[^\u4e00-\u9fff]", "", name.strip())
    c_eng = english_name.strip().lower()

    # 1. 檢驗姓名吻合度
    chinese_matched = False
    if len(c_name) >= 2 and c_name in combined_text:
        chinese_matched = True

    english_matched = False
    if c_eng:
        eng_parts = [p for p in re.split(r"[\s\-_.]+", c_eng) if len(p) >= 2]
        if len(eng_parts) >= 2:
            full_eng_compact = "".join(eng_parts)
            if c_eng in combined_text or full_eng_compact in combined_text.replace("-", "").replace("_", "").replace(".", ""):
                english_matched = True
            elif all(p in combined_text for p in eng_parts):
                english_matched = True
        elif len(eng_parts) == 1:
            single_eng = eng_parts[0]
            has_comp_in_text = any(t in combined_text for t in comp_tokens) if comp_tokens else False
            if single_eng in combined_text and (chinese_matched or has_comp_in_text):
                english_matched = True

    if not (chinese_matched or english_matched):
        return False, "", ""

    # 2. 嚴格防止同名同姓非本人（若名片有指定公司，社群中必須有公司/職稱/產業關聯線索）
    if comp_tokens:
        has_company_overlap = any(t in combined_text for t in comp_tokens)
        has_title_overlap = False
        if title_on_card:
            t_tokens = [tok for tok in re.split(r"[\s/]+", title_on_card) if len(tok) >= 2]
            has_title_overlap = any(tok.lower() in combined_text for tok in t_tokens)

        # 檢查是否有明顯衝突的地區或身分（如名片在台灣，但檔案是香港某大學學生、中醫師等）
        conflict_signals = ["曾就读于", "学生", "醫德網", "中醫師", "診所", "小學", "中學"]
        has_conflict = any(cs in combined_text for cs in conflict_signals)

        # 若同時具備中文與英文名 (如 Vincent Hou)，信任度極高；
        # 但若只有中文名 (如 林志恒)，且沒有任何公司/職稱線索，甚至有衝突身分，果斷略過！
        if not (has_company_overlap or has_title_overlap):
            if not english_matched:
                return False, "", ""
            if has_conflict:
                return False, "", ""

    return True, platform, username


def find_social_profiles(name: str, english_name: str = "", company: str = "", title_on_card: str = "") -> list:
    """
    搜尋該人員的個人社群帳號，並執行嚴格相關性過濾。
    若相關性不足則略過，不強求輸出。
    """
    profiles = []
    seen_platforms = set()
    seen_urls = set()

    c_name = name.strip()
    c_eng = english_name.strip()
    c_comp = clean_query_term(company)

    queries = []
    if c_eng and c_comp:
        queries.append(f'{c_eng} {c_comp} linkedin')
        queries.append(f'{c_eng} {c_comp}')
    if c_name and c_comp:
        queries.append(f'"{c_name}" "{c_comp}" linkedin')
        queries.append(f'"{c_name}" "{c_comp}"')
    if c_name:
        queries.append(f'"{c_name}" site:linkedin.com/in')

    for q in queries:
        items = search_web_text(q, max_results=5)
        for it in items:
            raw_url = it.get("url", "")
            title = it.get("title", "")
            snippet = it.get("snippet", "")
            is_valid, plat, uname = is_social_profile_relevant(raw_url, title, snippet, c_name, c_eng, c_comp, title_on_card)
            if is_valid and plat not in seen_platforms:
                clean_u = raw_url.split("?")[0].rstrip("/")
                if clean_u not in seen_urls:
                    seen_platforms.add(plat)
                    seen_urls.add(clean_u)
                    profiles.append({
                        "platform": plat,
                        "url": clean_u,
                        "username": uname
                    })
        if len(profiles) >= 3:
            break

    return profiles


# =========================================================================
# 2. 代表性文章嚴格篩選 (Strict Article Relevance)
# =========================================================================

def score_article_relevance(url: str, title: str, snippet: str, name: str, english_name: str, company: str, title_on_card: str = "") -> tuple:
    """
    評估文章是否具備高代表性與實質相關度：
    - 排除：股票跳動行情、求職徵才、商工登記、無關論壇、成人/農場網站。
    - 排除：同名但職業/專業完全不合者 (如中醫、策展人、演藝八卦)。
    - 計分：本人具名報導給予最高分，次為公司重要發表/展覽/獲獎/專訪。
    - 門檻：低於 60 分者判定為無關文章，回傳 False。
    """
    u_lower = url.lower()
    t_norm = normalize_cjk_spaces(title).lower()
    s_norm = normalize_cjk_spaces(snippet).lower()
    comb = f"{t_norm} {s_norm}"

    # 1. 網域黑名單 (徵才、黃頁、登記、行情跳動表)
    exclude_domains = [
        "104.com.tw", "1111.com.tw", "518.com.tw", "yes123.com.tw", "cakeresume.com",
        "twincn.com", "findcompany.com.tw", "opengovtw.com", "datagovtw.com", "gcis.nat.gov.tw",
        "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
        "goodjob.life", "interview.tw", "qollie.com", "art-mate.net", "edr.hk"
    ]
    if any(ex in u_lower for ex in exclude_domains):
        return False, 0, ""

    # 2. 標題關鍵詞排除 (無實質內容的純股票數字跳動流水帳)
    spam_phrases = ["即時行情", "成交量", "三大法人買賣超", "分點進出", "日k線", "盤後分析", "個股除權息", "股價走勢圖"]
    if any(sp in t_norm for sp in spam_phrases) and "專訪" not in comb and "發表" not in comb and "ai" not in comb:
        return False, 0, ""

    # 3. 排除明顯非商業/科技名片領域的衝突職業 (針對常見同名)
    unrelated_professions = ["中醫", "中醫師", "診所", "策展人", "藝術家", "演員", "歌手", "藝人", "編劇", "導演", "婦產科"]
    if any(bp in comb for bp in unrelated_professions):
        # 除非內文明顯包含名片公司
        if not any(t.lower() in comb for t in extract_company_tokens(company)):
            return False, 0, ""

    c_name = re.sub(r"[^\u4e00-\u9fff]", "", name.strip())
    c_eng = english_name.strip().lower()
    comp_tokens = [t.lower() for t in extract_company_tokens(company)]

    score = 0
    reason = []

    # 情況 A：文章提及名片人員本人
    person_hit = False
    if len(c_name) >= 2 and c_name.lower() in t_norm:
        score += 100
        person_hit = True
        reason.append("標題提及本人")
    elif len(c_name) >= 2 and c_name.lower() in s_norm:
        score += 75
        person_hit = True
        reason.append("內文提及本人")

    if c_eng and len(c_eng) >= 4 and c_eng in t_norm:
        score += 90
        person_hit = True
        reason.append("標題提及英文名")
    elif c_eng and len(c_eng) >= 4 and c_eng in s_norm:
        score += 65
        person_hit = True
        reason.append("內文提及英文名")

    # 若命中人名，但有公司名片時，須確認是否具備公司/職稱/產業相關性
    if person_hit and comp_tokens:
        has_comp = any(t in comb for t in comp_tokens)
        has_industry = any(ind in comb for ind in ["電子", "科技", "半導體", "產品", "軟體", "經理", "總裁", "執行長", "副總", "研發", "技術"])
        if not (has_comp or has_industry):
            # 僅是路人同名新聞（例如地方犯罪、同名演藝等），扣除分數
            score -= 50

    # 情況 B：文章與名片公司高度相關
    comp_in_title = any(t in t_norm for t in comp_tokens) if comp_tokens else False
    comp_in_snippet = any(t in s_norm for t in comp_tokens) if comp_tokens else False

    # 專業新聞情境字眼
    context_words = ["專訪", "發表", "營收", "新產品", "推出", "ai", "展覽", "computex", "技術", "董事長", "總經理", "合作", "併購", "獲獎", "佈局", "亮相", "首度"]
    has_news_context = any(w in comb for w in context_words)

    if comp_in_title:
        score += 60
        if has_news_context:
            score += 20
        reason.append("標題含公司名")
    elif comp_in_snippet and has_news_context:
        score += 50
        reason.append("內文含公司與要聞")

    # 篩選門檻：若總分未達 60 分，視為相關性不足，寧缺勿濫
    if score < 60:
        return False, score, ""

    return True, score, "、".join(reason)


def find_top_articles(name: str, english_name: str = "", company: str = "", title_on_card: str = "") -> list:
    """
    搜尋最具代表性 / 實質相關的新聞與文章。
    若相關性不高，寧缺勿濫，不強湊 3 篇。
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
    if c_eng and c_comp:
        queries.append(f'{c_eng} {c_comp}')
    if c_name:
        queries.append(f'"{c_name}" 專訪')
        queries.append(f'"{c_name}" 報導')
    if c_comp:
        queries.append(f'"{c_comp}" 新聞')
        queries.append(f'"{c_comp}" 專訪')
        queries.append(f'"{c_comp}" AI 發表')

    candidates = []

    for q in queries:
        raw_results = search_web_text(q, max_results=6)
        for r in raw_results:
            u = r.get("url", "")
            t = normalize_cjk_spaces(r.get("title", ""))
            s = normalize_cjk_spaces(r.get("snippet", ""))
            if not u or not t or u in seen_urls:
                continue

            parsed = urllib.parse.urlparse(u)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            is_rel, score, match_reason = score_article_relevance(u, t, s, c_name, c_eng, c_comp, title_on_card)
            if is_rel:
                seen_urls.add(u)
                candidates.append({
                    "score": score,
                    "title": t,
                    "url": u,
                    "domain": domain,
                    "snippet": s
                })

    # 依相關性分數降冪排序
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 網域去重（同一家媒體最多收錄 1 篇代表作）
    for c in candidates:
        dom = c["domain"]
        if dom in seen_domains:
            continue
        seen_domains.add(dom)

        # 簡化來源媒體標籤
        source_label = dom
        if "cna.com.tw" in dom:
            source_label = "中央社"
        elif "udn.com" in dom:
            source_label = "聯合新聞網"
        elif "ltn.com.tw" in dom:
            source_label = "自由時報"
        elif "chinatimes.com" in dom:
            source_label = "中時新聞網"
        elif "bnext.com.tw" in dom or "meet.bnext" in dom:
            source_label = "數位時代"
        elif "technews.tw" in dom:
            source_label = "科技新報 TechNews"
        elif "cool3c.com" in dom:
            source_label = "Cool3c"
        elif "inside.com.tw" in dom:
            source_label = "INSIDE 硬塞的"
        elif "ithome.com.tw" in dom:
            source_label = "iThome"
        elif "ctee.com.tw" in dom:
            source_label = "工商時報"
        elif "money.udn.com" in dom:
            source_label = "經濟日報"
        elif "aamataipei.com.tw" in dom:
            source_label = "AAMA 台北搖籃計畫"

        articles.append({
            "title": c["title"],
            "url": c["url"],
            "source": source_label,
            "snippet": c["snippet"]
        })
        if len(articles) >= 3:
            break

    return articles


# =========================================================================
# 3. 公司網站、地址與地圖評論線索 (Company Insights & Map Clues)
# =========================================================================

def mine_company_and_location_clues(card: dict) -> dict:
    """
    從公司官方網站、登記地址與 Google 地圖/大眾評論中萃取重要線索與背景：
    - 官網核心業務與簡介 (Official Website Info & Meta Description)
    - 登記地址、大樓名稱、科學園區線索 (Building, Tech Park, Transport)
    - 地圖評論、評分與整體公眾評價 (Google Maps Rating, Reviews, Sentiment)
    """
    company = (card.get("company") or "").strip()
    website = (card.get("website") or "").strip()
    address = (card.get("address") or "").strip()
    name = (card.get("name") or "").strip()

    c_comp = clean_query_term(company)
    if not c_comp and not website:
        return {}

    insights = {
        "summary": "",
        "website_clues": "",
        "location_clues": "",
        "review_clues": "",
        "clues_list": []
    }

    # A. 探索官方網站 (Website Clues)
    site_desc = ""
    if website:
        target_url = website if website.startswith("http") else f"https://{website}"
        try:
            req = urllib.request.Request(target_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=4) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")
            site_title = normalize_cjk_spaces(soup.title.string.strip() if soup.title else "")
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if desc_tag and desc_tag.get("content"):
                site_desc = normalize_cjk_spaces(desc_tag["content"].strip())
            elif site_title:
                site_desc = site_title
        except Exception:
            pass

    if not site_desc and c_comp:
        # Fallback 透過搜尋取得官網與簡介
        intro_results = search_web_text(f'"{c_comp}" 產品 OR 簡介', max_results=3)
        for it in intro_results:
            snip = it.get("snippet", "").strip()
            if snip and len(snip) > 20 and not any(k in snip for k in ["成人", "下載", "登入", "維基百科:首頁"]):
                site_desc = snip[:180]
                break

    if site_desc:
        insights["website_clues"] = site_desc[:180]
        insights["clues_list"].append(f"🌐 官網/業務：{site_desc[:120]}…")

    # B. 探索登記地址、大樓與園區線索 (Location & Park Clues)
    location_info = ""
    if address:
        clean_addr = normalize_cjk_spaces(re.sub(r"^[0-9\s\-〒]+", "", address).strip())
        building_match = re.search(r"((?:遠東|宏碁|科技|世紀|大同|中友|信義|國泰|金融|經貿|新光)[^\s號樓,，]+(?:大樓|園區|廣場|中心|大廈|館))", clean_addr)
        if building_match:
            location_info = f"位於 {building_match.group(1)}（{clean_addr}）"
        else:
            location_info = f"登記地址為 {clean_addr}"

    if c_comp and (not location_info or len(location_info) < 20):
        loc_res = search_web_text(f'"{c_comp}" 地址 園區', max_results=2)
        for it in loc_res:
            sn = it.get("snippet", "")
            m_park = re.search(r"((?:遠東世紀|內湖科技|汐止科學|南港軟體|新竹科學|竹科|台元科技)[^\s，。]+(?:園區|大樓|廣場)?)", sn)
            if m_park:
                location_info = f"位於 {m_park.group(1)}"
                break

    if location_info:
        insights["location_clues"] = location_info
        insights["clues_list"].append(f"📍 地標位置：{location_info}")

    # C. 探索地圖評價與大眾評論線索 (Map Reviews & Public Sentiment)
    review_info = ""
    if c_comp:
        rev_res = search_web_text(f'"{c_comp}" 評價', max_results=3)
        for it in rev_res:
            t = it.get("title", "")
            sn = it.get("snippet", "")
            comb = f"{t} {sn}"
            m_star = re.search(r"(\d\.\d)\s*(?:★|星|顆星|/5|\/ 5)", comb)
            m_rev_cnt = re.search(r"(\d+)\s*(?:則評論|篇評論|個評價|則心得)", comb)
            if m_star:
                star_val = m_star.group(1)
                cnt_str = f"（約 {m_rev_cnt.group(1)} 則評價）" if m_rev_cnt else ""
                review_info = f"大眾/地圖評價約 {star_val} ★ {cnt_str}"
                break
            elif "面試心得" in comb or "公司評價" in comb:
                m_stat = re.search(r"(整體評價為[^，。]+|面試難度[^，。]+|公司評價[^，。]+)", comb)
                if m_stat:
                    review_info = f"職場/社群評價：{m_stat.group(1)}"
                    break

    if review_info:
        insights["review_clues"] = review_info
        insights["clues_list"].append(f"⭐ 評分/評價：{review_info}")

    # 綜合總結
    summary_parts = []
    if insights["website_clues"]:
        summary_parts.append(insights["website_clues"][:60])
    if insights["location_clues"]:
        summary_parts.append(insights["location_clues"][:40])
    insights["summary"] = "；".join(summary_parts) if summary_parts else f"{c_comp} 背景線索已整理"

    return insights


# =========================================================================
# 4. 頭像照片搜尋與下載 (Avatar Search & Square Crop)
# =========================================================================

def find_and_save_avatar(name: str, english_name: str = "", company: str = "", card_id: str = "") -> dict:
    """
    搜尋個人照片，下載並存為 square JPEG 頭像 (avatars/<card_id>.jpg)。
    若無高可信度照片則不產生，避免拿風景或圖表充數。
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
        candidate_queries.append(f'"{c_name}" 經理 OR 總經理 OR 執行長 OR 代表')

    for q in candidate_queries:
        img_urls = search_web_images(q, max_results=6)
        for u in img_urls:
            try:
                req = urllib.request.Request(u, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                if len(data) < 3000:
                    continue
                im = Image.open(BytesIO(data))
                w, h = im.size
                if w < 120 or h < 120:
                    continue
                ratio = w / float(h)
                if ratio < 0.6 or ratio > 1.6:
                    continue

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


# =========================================================================
# 5. 主調用入口 (Master Enrichment Function)
# =========================================================================

def enrich_card_data(card: dict) -> dict:
    """
    智慧擴充名片資料：
      1. 個人社群帳號 (`social_profiles`)：嚴格相關性過濾，無關者略過。
      2. 代表性熱門文章 (`top_articles`)：排除股票流水帳與求職，無關者略過。
      3. 公司網站、地址與地圖評論線索 (`company_insights`)：若個人資訊少，深掘背景線索。
      4. 個人照片頭像 (`avatar_url`)：高可信度頭像下載與本地儲存。
    """
    c_id = str(card.get("id", "")).strip()
    c_name = str(card.get("name", "")).strip()
    c_eng = str(card.get("english_name", "")).strip()
    c_comp = str(card.get("company", "")).strip()
    c_title = str(card.get("title", "")).strip()

    # 1. 社群帳號 (嚴格過濾)
    socials = find_social_profiles(c_name, c_eng, c_comp, c_title)

    # 2. 代表性文章 (嚴格過濾)
    articles = find_top_articles(c_name, c_eng, c_comp, c_title)

    # 3. 公司、地址與地圖評論線索深掘
    insights = mine_company_and_location_clues(card)

    # 4. 個人照片
    avatar_res = find_and_save_avatar(c_name, c_eng, c_comp, c_id)

    return {
        "social_profiles": socials,
        "avatar_url": avatar_res.get("avatar_url", ""),
        "source_avatar_url": avatar_res.get("source_image_url", ""),
        "top_articles": articles,
        "company_insights": insights
    }


if __name__ == "__main__":
    import sys
    test_name = sys.argv[1] if len(sys.argv) > 1 else "侯剛平"
    test_comp = sys.argv[2] if len(sys.argv) > 2 else "麗臺科技股份有限公司 (Leadtek Research Inc.)"
    test_eng = sys.argv[3] if len(sys.argv) > 3 else "Vincent Hou"
    test_addr = sys.argv[4] if len(sys.argv) > 4 else "235603新北市中和區建一路166號18樓"
    test_web = sys.argv[5] if len(sys.argv) > 5 else "https://www.leadtek.com.tw"

    print(f"=== 測試嚴格擴充：{test_name} ({test_eng}) / {test_comp} ===")
    mock_card = {
        "id": "test_verification",
        "name": test_name,
        "english_name": test_eng,
        "company": test_comp,
        "address": test_addr,
        "website": test_web
    }
    res = enrich_card_data(mock_card)
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
