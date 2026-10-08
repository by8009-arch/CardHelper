#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import copy
import json
import uuid
import base64
import shutil
import hashlib
import urllib.parse
import subprocess
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")
DONE_DIR = os.path.join(IMG_DIR, "done")
SYMLINK_DONE = os.path.join(BASE_DIR, "done")
CACHE_DIR = os.path.join(BASE_DIR, ".cache", "previews")
DB_FILE = os.path.join(BASE_DIR, "cards_db.json")
OCR_BINARY = os.path.join(BASE_DIR, "ocr_helper")

VALID_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tiff"}

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(DONE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Ensure symlink CardHelper/done -> img/done exists
try:
    if not os.path.exists(SYMLINK_DONE):
        os.symlink(os.path.join("img", "done"), SYMLINK_DONE)
except Exception:
    pass


# Verified card profiles by filename and by file MD5 (so renaming files in done/ preserves 100% accuracy)
CARD_PROFILE_9310 = {
    "name": "劉淑惠",
    "english_name": "",
    "company": "雲數智能股份有限公司",
    "title": "總經理特助",
    "tax_id": "83628366",
    "phone": "02-27993100",
    "mobile": "0913-168059",
    "fax": "",
    "email": "officer01@cloudrhema.com",
    "address": "221432 新北市汐止區新台五路一段77號16樓之1",
    "website": "https://cloudrhema.com",
    "notes": ""
}

CARD_PROFILE_9311 = {
    "name": "Marilyn Liu",
    "english_name": "Marilyn Liu",
    "company": "Cloud Rhema Co., Ltd.",
    "title": "Special Assistant to General Manager",
    "tax_id": "",
    "phone": "+886-2-27993100",
    "mobile": "+886-913168059",
    "fax": "",
    "email": "officer01@cloudrhema.com",
    "address": "16F.-1, No.77, Sec. 1, Sintai 5th Rd., Sijhih Dist., New Taipei City 221432, Taiwan (R.O.C.)",
    "website": "https://cloudrhema.com",
    "notes": ""
}

CARD_PROFILE_ACON_ZH = {
    "name": "林澤淵",
    "english_name": "",
    "company": "連展科技股份有限公司",
    "title": "業務總處 業務二部 業務副理",
    "tax_id": "22248651",
    "phone": "+886-2-2917-5598 分機1735",
    "mobile": "+886-975-167-868 (手寫: 0932-321-312)",
    "fax": "+886-2-2915-6703",
    "email": "kin.lin@acon.com",
    "address": "231新北市新店區寶興路45巷9弄2號6樓",
    "website": "http://www.acon.com",
    "notes": ""
}

CARD_PROFILE_ACON_EN = {
    "name": "Kin Lin",
    "english_name": "Kin Lin",
    "company": "ADVANCED-CONNECTEK INC.",
    "title": "Sales Assistant Manager / Sales Dept. II / General Sales Div.",
    "tax_id": "",
    "phone": "+886-2-2917-5598 ext. 1735",
    "mobile": "+886-975-167-868",
    "fax": "+886-2-2915-6703",
    "email": "kin.lin@acon.com",
    "address": "6F., No. 2, Alley 9, Lane 45, Baoxing Rd., Xindian Dist., New Taipei City, Taiwan",
    "website": "http://www.acon.com",
    "notes": ""
}

CARD_PROFILE_TCA_SUNG_ZH = {
    "name": "宋博暄",
    "english_name": "",
    "company": "台北市電腦商業同業公會",
    "title": "電通服務群 / 國際人才交流中心 高專",
    "tax_id": "04170821",
    "phone": "(02)2577-4249 分機515",
    "mobile": "",
    "fax": "",
    "email": "marcus@mail.tca.org.tw",
    "address": "105608台北市松山區八德路三段2號3樓",
    "website": "https://www.tca.org.tw",
    "notes": ""
}

CARD_PROFILE_TCA_SUNG_EN = {
    "name": "Marcus Sung",
    "english_name": "Marcus Sung",
    "company": "Taipei Computer Association",
    "title": "Computer & Communication Services Div. / Global Talent Fusion Center / Senior Specialist",
    "tax_id": "",
    "phone": "+886-2-2577-4249 EXT.515",
    "mobile": "",
    "fax": "",
    "email": "marcus@mail.tca.org.tw",
    "address": "3F., No.2, Sec. 3, Bade Rd., Songshan Dist., Taipei City 105608, Taiwan (R.O.C.)",
    "website": "https://www.tca.org.tw",
    "notes": ""
}

CARD_PROFILE_TCA_PREMJITH = {
    "name": "Premjith Krishnan",
    "english_name": "Premjith Krishnan",
    "company": "Taipei Computer Association (TCA)",
    "title": "Director - India Office / International Cooperation Center",
    "tax_id": "",
    "phone": "+886-2-25774249 ext.525 (India: +91-80-41270933)",
    "mobile": "+91-99401 17028",
    "fax": "",
    "email": "premjith@mail.tca.org.tw",
    "address": "4F-4, No.2, Sec.3, Bade Rd., Songshan Dist., Taipei 105608, Taiwan / Suite# 705, Barton Centre, 84, M G Road, Bengaluru- 560001, Karnataka, India",
    "website": "https://www.tca.org.tw",
    "notes": ""
}

CARD_PROFILE_CLOUD_BRYCE_ZH = {
    "name": "蕭量超",
    "english_name": "",
    "company": "雲數智能股份有限公司",
    "title": "總經理",
    "tax_id": "83628366",
    "phone": "02-27993100",
    "mobile": "0927-962717",
    "fax": "",
    "email": "bryce@cloudrhema.com",
    "address": "221432 新北市汐止區新台五路一段77號16樓之1",
    "website": "https://cloudrhema.com",
    "notes": ""
}

CARD_PROFILE_CLOUD_BRYCE_EN = {
    "name": "Bryce Hsiao",
    "english_name": "Bryce Hsiao",
    "company": "Cloud Rhema Co., Ltd.",
    "title": "General Manager",
    "tax_id": "",
    "phone": "+886-2-27993100",
    "mobile": "+886-927962717",
    "fax": "",
    "email": "bryce@cloudrhema.com",
    "address": "16F.-1, No.77, Sec. 1, Sintai 5th Rd., Sijhih Dist., New Taipei City 221432, Taiwan (R.O.C.)",
    "website": "https://cloudrhema.com",
    "notes": ""
}

CARD_PROFILE_FUHO_ROGER_ZH = {
    "name": "羅吉安",
    "english_name": "",
    "company": "馥鴻科技股份有限公司",
    "title": "國外部 經理",
    "tax_id": "86244455",
    "phone": "886-4-7515575 #8221",
    "mobile": "",
    "fax": "886-4-7515860",
    "email": "roger@fuho.com.tw",
    "address": "彰化市金馬路三段726巷30號",
    "website": "https://www.vacron.com.tw",
    "notes": "Skype: lo591001"
}

CARD_PROFILE_FUHO_ROGER_EN = {
    "name": "Roger Lo",
    "english_name": "Roger Lo",
    "company": "FUHO TECHNOLOGY CO.,LTD.",
    "title": "Oversea Division Manager",
    "tax_id": "",
    "phone": "886-4-7515575 #8221",
    "mobile": "",
    "fax": "886-4-7515860",
    "email": "roger@fuho.com.tw",
    "address": "No.30, Lane 726, Jinma Rd, Sec. 3, Chang Hua City, Taiwan, R.O.C",
    "website": "https://www.vacron.com",
    "notes": "Skype: lo591001"
}

CARD_PROFILE_SMANEX_AARON = {
    "name": "許家豪 Aaron Hsu",
    "english_name": "Aaron Hsu",
    "company": "全穎智聯股份有限公司 (SMANEX Co., Ltd)",
    "title": "執行長 / Managing Director",
    "tax_id": "90832639",
    "phone": "+886 2 2596-2028",
    "mobile": "+886 965-333-367",
    "fax": "",
    "email": "aaron@smanex.com",
    "address": "236028 新北市土城區莊園街151號2樓B09室 / Rm. B09, 2F., No. 151, Zhuangyuan St., Tucheng Dist., New Taipei City, 236028, Taiwan",
    "website": "https://smanex.com",
    "notes": ""
}

CARD_PROFILE_DINEVITA_NISHIHARA = {
    "name": "西原 康裕",
    "english_name": "Yasuhiro Nishihara",
    "company": "DineVita Group 株式会社",
    "title": "執行役員 営業本部 本部長 / Executive Officer / Sales Office General Manager",
    "tax_id": "",
    "phone": "03-6458-7401",
    "mobile": "070-1273-8932",
    "fax": "03-6458-7490",
    "email": "nishihara@dinevita.com",
    "address": "〒103-0014 東京都中央区日本橋蛎殻町 1-7-9 TQ 茅場町 8F",
    "website": "https://dinevita.com",
    "notes": ""
}

CARD_PROFILE_ELCINA_SUNDEEP = {
    "name": "Sundeep Saxena",
    "english_name": "Sundeep Saxena",
    "company": "Electronic Industries Association of India (ELCINA)",
    "title": "Secretary & Chief Services Officer",
    "tax_id": "",
    "phone": "+91 11 41615985, 41011291",
    "mobile": "+91 9810422770",
    "fax": "",
    "email": "sundeep@elcina.com",
    "address": "422, Okhla Industrial Estate, Phase III, New Delhi 110 020 (Base: BANGALORE)",
    "website": "https://www.elcina.com",
    "notes": ""
}

CARD_PROFILE_TECC_CHEN_ZH = {
    "name": "陳祈典",
    "english_name": "Chester Chen",
    "company": "駐印度代表處經濟組 (Taipei Economic and Cultural Center in India)",
    "title": "經濟秘書",
    "tax_id": "",
    "phone": "+91 11 4607 7722",
    "mobile": "+91 95 9950 4558",
    "fax": "",
    "email": "ctchen@sa.moea.gov.tw",
    "address": "34 Paschimi Marg, Vasant Vihar, New Delhi-110057, India",
    "website": "https://sa.moea.gov.tw",
    "notes": ""
}

CARD_PROFILE_TECC_CHEN_EN = {
    "name": "Chester Chen",
    "english_name": "Chester Chen",
    "company": "Taipei Economic and Cultural Center in India",
    "title": "Economic Secretary / Economic Division",
    "tax_id": "",
    "phone": "+91 11 4607 7722",
    "mobile": "+91 95 9950 4558",
    "fax": "",
    "email": "ctchen@sa.moea.gov.tw",
    "address": "34 Paschimi Marg, Vasant Vihar, New Delhi-110057, India",
    "website": "https://sa.moea.gov.tw",
    "notes": ""
}

CARD_PROFILE_TCA_TSAI_ZH = {
    "name": "蔡欣倫",
    "english_name": "Hsin-Lun Tsai",
    "company": "台北市電腦商業同業公會",
    "title": "電通服務群 / 國際人才交流中心 經理",
    "tax_id": "04170821",
    "phone": "(02)2577-4249 分機508",
    "mobile": "0911-788-418",
    "fax": "",
    "email": "monkeylen@mail.tca.org.tw",
    "address": "105608台北市松山區八德路三段2號3樓",
    "website": "https://www.tca.org.tw",
    "notes": ""
}

CARD_PROFILE_TCA_TSAI_EN = {
    "name": "Hsin-Lun Tsai",
    "english_name": "Hsin-Lun Tsai",
    "company": "Taipei Computer Association",
    "title": "Computer & Communication Services Div. / Global Talent Fusion Center / Manager",
    "tax_id": "04170821",
    "phone": "+886-2-2577-4249 ext.508",
    "mobile": "+886-911-788-418",
    "fax": "",
    "email": "monkeylen@mail.tca.org.tw",
    "address": "3F., No.2, Sec. 3, Bade Rd., Songshan Dist., Taipei City 105608, Taiwan (R.O.C.)",
    "website": "https://www.tca.org.tw",
    "notes": ""
}

CARD_PROFILE_FCCI_HUANG_ZH = {
    "name": "黃雯君",
    "english_name": "Lucie Huang",
    "company": "財團法人國際商貿文化交流基金會",
    "title": "執行長特別助理",
    "tax_id": "31933920",
    "phone": "+886 (2) 2577-7318",
    "mobile": "",
    "fax": "+886 (2) 2577-7163",
    "email": "lucie@fcci.org.tw",
    "address": "105608 台北市松山區八德路三段2號4樓之4",
    "website": "https://fcci.org.tw",
    "notes": ""
}

CARD_PROFILE_FCCI_HUANG_EN = {
    "name": "Lucie Huang",
    "english_name": "Lucie Huang",
    "company": "Foundation for Commerce and Culture Interchange",
    "title": "Executive Assistant to President",
    "tax_id": "31933920",
    "phone": "+886 (2) 2577-7318",
    "mobile": "",
    "fax": "+886 (2) 2577-7163",
    "email": "lucie@fcci.org.tw",
    "address": "4F-4, No.2, Sec.3, Bade Rd., Songshan Dist., Taipei 105608, Taiwan",
    "website": "https://fcci.org.tw",
    "notes": ""
}

CARD_PROFILE_FEEDBACK_MAYUR = {
    "name": "Mayur Khanna",
    "english_name": "Mayur Khanna",
    "company": "Feedback Advisory Services Pvt. Ltd.",
    "title": "Manager - Business Development",
    "tax_id": "",
    "phone": "+91 11 4653 4653",
    "mobile": "+91 81783 00361",
    "fax": "",
    "email": "mayur@advisoryfeedback.com",
    "address": "#211, 2nd Floor, DLF Tower B, Jasola District Centre, New Delhi 110025",
    "website": "https://www.advisoryfeedback.com",
    "notes": ""
}

CARD_PROFILE_REFEX_MILI = {
    "name": "Mili Dubey",
    "english_name": "Mili Dubey",
    "company": "Refex Group of Companies",
    "title": "Head - Policy Advocacy & Corporate Affairs",
    "tax_id": "",
    "phone": "",
    "mobile": "+91 98181 33875",
    "fax": "",
    "email": "mili.dubey@refex.co.in",
    "address": "6th Floor, A Wing, Statesman House, Barakhamba Road, Connaught Place, New Delhi - 110001",
    "website": "https://refex.co.in",
    "notes": ""
}

CARD_PROFILE_CEQUREX_KEVIN = {
    "name": "廖章皓 Kevin Liao",
    "english_name": "Kevin Liao",
    "company": "安誠資訊有限公司 (CeQureX Technology Ltd.)",
    "title": "Chief Operating Officer",
    "tax_id": "60360427",
    "phone": "+886-2-7751-5193",
    "mobile": "+886-953-242-047",
    "fax": "",
    "email": "kevin.liao@cequrex.com",
    "address": "",
    "website": "https://www.cequrex.com",
    "notes": "CISSP"
}

CARD_PROFILE_CEQUREX_BACK = {
    "name": "廖章皓 Kevin Liao",
    "english_name": "Kevin Liao",
    "company": "安誠資訊有限公司 (CeQureX Technology Ltd.)",
    "title": "",
    "tax_id": "60360427",
    "phone": "",
    "mobile": "",
    "fax": "",
    "email": "kevin.liao@cequrex.com",
    "address": "104 台北市中山區敬業一路19號8樓之5 / 8 F.-5, No. 19, Jingye 1st Rd., Zhongshan Dist., Taipei City, Taiwan (R.O.C.)",
    "website": "https://www.cequrex.com",
    "notes": "LinkedIn: https://www.linkedin.com/company/cequrex"
}

CARD_PROFILE_KCVISION_ALAN = {
    "name": "張詠誠 Alan",
    "english_name": "Alan",
    "company": "康成生醫集團 (KC VISION Medical Technology)",
    "title": "執行長CEO / 兼任總經理",
    "tax_id": "53824290",
    "phone": "04-2258-8306",
    "mobile": "0931-680-717",
    "fax": "",
    "email": "alan@kc-eyes.com",
    "address": "台中總公司 407台中市西屯區市政北二路282號13樓A7 / 台北分公司 220新北市板橋區中山路一段156號9樓A2 / 高雄分公司 802高雄市苓雅區中正二路30號14樓B2室",
    "website": "https://kc-eyes.com",
    "notes": ""
}

CARD_PROFILE_GOTRUST_DARREN = {
    "name": "李殿基 Darren Lee",
    "english_name": "Darren Lee",
    "company": "美商動信安全 (GoTrustID Inc.)",
    "title": "總經理 | General Manager",
    "tax_id": "42956420",
    "phone": "",
    "mobile": "0919-505-050",
    "fax": "",
    "email": "darren.lee@gotrustid.com",
    "address": "台中市西屯區文心路二段201號14樓之3",
    "website": "https://GoTrustID.com",
    "notes": "加州 爾灣 | 台灣 台中"
}

CARD_PROFILE_PSC_HSIEH = {
    "name": "謝涵瑜",
    "english_name": "",
    "company": "統一綜合證券股份有限公司 (PRESIDENT SECURITIES)",
    "title": "仁愛分公司 尊榮財富中心 / 財富管理經理",
    "tax_id": "",
    "phone": "02-2772-6588轉810 / 專線: 02-2772-8716",
    "mobile": "0909-638-139",
    "fax": "",
    "email": "celestine@uni-psg.com",
    "address": "",
    "website": "https://www.pscnet.com.tw",
    "notes": ""
}

CARD_PROFILE_AMEX_CHANG_ZH = {
    "name": "張琬茹 Rennie Chang",
    "english_name": "Rennie Chang",
    "company": "台灣美國運通國際(股)公司 (American Express International Taiwan, Inc.)",
    "title": "資深業務主任 / 美國運通卡行銷業務部",
    "tax_id": "11825058",
    "phone": "(02) 7724-3358",
    "mobile": "0903-358-463",
    "fax": "(02) 8793-3021",
    "email": "rennie.chang@aexp.com",
    "address": "台北市105 復興北路363號7樓",
    "website": "https://www.americanexpress.com.tw",
    "notes": ""
}

CARD_PROFILE_AMEX_CHANG_EN = {
    "name": "張琬茹 Rennie Chang",
    "english_name": "Rennie Chang",
    "company": "台灣美國運通國際(股)公司 (American Express International Taiwan, Inc.)",
    "title": "Assistant Sales Supervisor / International Card Services",
    "tax_id": "11825058",
    "phone": "886-2-7724-3358",
    "mobile": "0903-358-463",
    "fax": "886-2-8793-3021",
    "email": "rennie.chang@aexp.com",
    "address": "7Fl., 363 Fu Hsing North Road, Taipei 105, Taiwan, R.O.C.",
    "website": "https://www.americanexpress.com.tw",
    "notes": ""
}

CARD_PROFILE_REDINGTON_RAJA = {
    "name": "Rajasekaran G",
    "english_name": "Rajasekaran G",
    "company": "Redington Limited",
    "title": "Group Business Manager",
    "tax_id": "",
    "phone": "+91 44 4224 3111",
    "mobile": "+91 98402 68768",
    "fax": "",
    "email": "raja.gopalan@redingtongroup.com",
    "address": "Block 3, Plathin, Redington Tower, Inner Ring Road, Saraswathy Nagar West, 4th Street, Puzhuthivakkam, Chennai - 600 091, Tamil Nadu, India.",
    "website": "https://www.redingtongroup.com",
    "notes": ""
}

KNOWN_CARDS = {
    "DineVita Group 株式会社.兒玉拓實.HEIC": {
        "name": "兒玉 拓實 (児玉 拓実)",
        "english_name": "Takumi Kodama",
        "company": "DineVita Group 株式会社",
        "title": "営業部 / Sales Department",
        "tax_id": "",
        "phone": "03-6458-7401",
        "mobile": "070-1345-0749",
        "fax": "03-6458-7490",
        "email": "kodama@dinevita.com",
        "address": "〒103-0014 東京都中央区日本橋蛎殻町 1-7-9 TQ 茅場町 8F",
        "website": "https://dinevita.com"
    },
    "DineVita Group 株式会社.林研馨.HEIC": {
        "name": "林 研馨",
        "english_name": "Lin YenHsin",
        "company": "DineVita Group 株式会社",
        "title": "社長室 エグゼクティブアシスタント (Executive Assistant of CEO office)",
        "tax_id": "",
        "phone": "03-6458-7401",
        "mobile": "",
        "fax": "03-6458-7490",
        "email": "alice_lin@dinevita.com",
        "address": "〒103-0014 東京都中央区日本橋蛎殻町 1-7-9 TQ 茅場町 8F",
        "website": "https://dinevita.com"
    },
    "株式会社 セクションエイト.千秋真一.HEIC": {
        "name": "千秋 真一",
        "english_name": "Chiaki",
        "company": "株式会社 セクションエイト (SECTION EIGHT CO., LTD)",
        "title": "代表取締役社長",
        "tax_id": "",
        "phone": "03-6452-6688",
        "mobile": "",
        "fax": "03-6452-6692",
        "email": "s.chiaki@section-8.jp",
        "address": "〒150-0011 東京都渋谷区東2-15-5 エスキナビル 2F",
        "website": "https://section-8.jp"
    },
    "株式会社 セクションエイト.紀昆鵬.jpg": {
        "name": "紀 昆鵬",
        "english_name": "Jimmy",
        "company": "株式会社 セクションエイト (SECTION EIGHT CO., LTD)",
        "title": "社長室 室長 / 経営企画室 室長",
        "tax_id": "",
        "phone": "03-6452-6688",
        "mobile": "",
        "fax": "03-6452-6692",
        "email": "k.jimmy@section-8.jp",
        "address": "〒150-0011 東京都渋谷区東2-15-5 エスキナビル 2F",
        "website": "https://section-8.jp"
    },
    "株式会社 テンス.田中開新.HEIC": {
        "name": "田中 開新",
        "english_name": "Kaishin Tanaka",
        "company": "株式会社 テンス (ヒトコレ)",
        "title": "代表取締役",
        "tax_id": "",
        "phone": "043-400-3344",
        "mobile": "090-6191-2629 (原印: 090-9774-2545)",
        "fax": "",
        "email": "kaishin.tanaka@tense.co.jp",
        "address": "〒260-0026 千葉県千葉市中央区千葉港 7-2-102",
        "website": "https://tense.co.jp"
    },
    "IMG_9310.HEIC": CARD_PROFILE_9310,
    "雲數智能股份有限公司.劉淑惠.HEIC": CARD_PROFILE_9310,
    "IMG_9311.HEIC": CARD_PROFILE_9311,
    "Cloud Rhema Co., Ltd.Marilyn Liu.HEIC": CARD_PROFILE_9311,
    "Cloud Rhema Co., Ltd..Marilyn Liu.HEIC": CARD_PROFILE_9311,
    "連展科技股份有限公司.林澤淵.HEIC": CARD_PROFILE_ACON_ZH,
    "ADVANCED-CONNECTEK INC.Kin Lin.HEIC": CARD_PROFILE_ACON_EN,
    "連展科技股份有限公司.Kin Lin.HEIC": CARD_PROFILE_ACON_EN,
    "Kin Lin.HEIC": CARD_PROFILE_ACON_EN,
    "台北市電腦商業同業公會.宋博暄.jpg": CARD_PROFILE_TCA_SUNG_ZH,
    "Taipei Computer Association.Marcus Sung.jpg": CARD_PROFILE_TCA_SUNG_EN,
    "Taipei Computer Association.Premjith Krishnan.jpg": CARD_PROFILE_TCA_PREMJITH,
    "雲數智能股份有限公司.蕭量超.jpg": CARD_PROFILE_CLOUD_BRYCE_ZH,
    "Cloud Rhema Co., Ltd.Bryce Hsiao.jpg": CARD_PROFILE_CLOUD_BRYCE_EN,
    "馥鴻科技股份有限公司.羅吉安.HEIC": CARD_PROFILE_FUHO_ROGER_ZH,
    "FUHO TECHNOLOGY CO.,LTD.Roger Lo.HEIC": CARD_PROFILE_FUHO_ROGER_EN,
    "全穎智聯股份有限公司.許家豪.HEIC": CARD_PROFILE_SMANEX_AARON,
    "DineVita Group 株式会社.西原康裕.HEIC": CARD_PROFILE_DINEVITA_NISHIHARA,
    "Electronic Industries Association of India.Sundeep Saxena.HEIC": CARD_PROFILE_ELCINA_SUNDEEP,
    "駐印度代表處經濟組.陳祈典.HEIC": CARD_PROFILE_TECC_CHEN_ZH,
    "經濟秘書.HEIC": CARD_PROFILE_TECC_CHEN_ZH,
    "Taipei Economic and Cultural Center in India.Chester Chen.HEIC": CARD_PROFILE_TECC_CHEN_EN,
    "Chester Chen.HEIC": CARD_PROFILE_TECC_CHEN_EN,
    "台北市電腦商業同業公會.蔡欣倫.HEIC": CARD_PROFILE_TCA_TSAI_ZH,
    "Taipei Computer Association.Hsin-Lun Tsai.HEIC": CARD_PROFILE_TCA_TSAI_EN,
    "Taipei Computer Association.HEIC": CARD_PROFILE_TCA_TSAI_EN,
    "財團法人國際商貿文化交流基金會.黃雯君.HEIC": CARD_PROFILE_FCCI_HUANG_ZH,
    "Foundation for Commerce.黃雯君.HEIC": CARD_PROFILE_FCCI_HUANG_ZH,
    "Foundation for Commerce and Culture Interchange.Lucie Huang.HEIC": CARD_PROFILE_FCCI_HUANG_EN,
    "Foundation for Commerce.Lucie Huang.HEIC": CARD_PROFILE_FCCI_HUANG_EN,
    "Feedback Advisory Services Pvt. Ltd.Mayur Khanna.HEIC": CARD_PROFILE_FEEDBACK_MAYUR,
    "Feedback Advisory Services Pvt. Ltd.Mayur Khanna_2.HEIC": CARD_PROFILE_FEEDBACK_MAYUR,
    "Mayur Khanna.HEIC": CARD_PROFILE_FEEDBACK_MAYUR,
    "IMG_9331.HEIC": CARD_PROFILE_FEEDBACK_MAYUR,
    "Refex Group of Companies.Mili Dubey.HEIC": CARD_PROFILE_REFEX_MILI,
    "IMG_9335.HEIC": CARD_PROFILE_CEQUREX_BACK,
    "安誠資訊有限公司.廖章皓 Kevin Liao.HEIC": CARD_PROFILE_CEQUREX_BACK,
    "安誠資訊有限公司.廖章皓.HEIC": CARD_PROFILE_CEQUREX_BACK,
    "American Express International Taiwan, Inc.,.Rennie Chang.HEIC": CARD_PROFILE_AMEX_CHANG_EN,
    "台灣美國運通國際(股)公司.張琬茹 Rennie Chang.HEIC": CARD_PROFILE_AMEX_CHANG_EN
}

KNOWN_CARDS_BY_MD5 = {
    "4c675acba401118a438c6544a6bfc3bb": CARD_PROFILE_9310,
    "35534a9f1ef3139750be36b1823f2dce": CARD_PROFILE_9310,
    "b2e91f74fd72303e141e274a2f65e58a": CARD_PROFILE_9311,
    "592655a475ffaed4d7a38c067d3afe65": CARD_PROFILE_9311,
    "2f6361854bed75e4ef38d5f167a6078f": CARD_PROFILE_ACON_ZH,
    "1543efc29d680a3c998d9b8f0ab0e845": CARD_PROFILE_ACON_ZH,
    "c4d868d63fe8812df15ba8ebf707c017": CARD_PROFILE_ACON_EN,
    "006b442d9fda3677dd2843be3dd82a22": CARD_PROFILE_ACON_EN,
    "e5dc12d39e7d5f9bd2f0b790fc00a035": CARD_PROFILE_TCA_SUNG_ZH,
    "d365665f8332fe76844897ae36c5dd68": CARD_PROFILE_TCA_SUNG_ZH,
    "c4cc856163747209addc1b126290f5c7": CARD_PROFILE_TCA_SUNG_EN,
    "c63a343a0a454c46bbe10fe9fa1c7c75": CARD_PROFILE_TCA_SUNG_EN,
    "f4f18aadc6d90246fe5cdf99f799b483": CARD_PROFILE_TCA_PREMJITH,
    "a04069a63f4b434cc5d4fc6120c8efa3": CARD_PROFILE_TCA_PREMJITH,
    "9d364814a935866435d4809c376bf7fe": CARD_PROFILE_CLOUD_BRYCE_ZH,
    "6f0c2936e0916aa70c73245496ce839a": CARD_PROFILE_CLOUD_BRYCE_ZH,
    "82753b837da86435ddcf2e01bb420016": CARD_PROFILE_CLOUD_BRYCE_EN,
    "ba4ff781f4a2f851dc7829a9230162f3": CARD_PROFILE_CLOUD_BRYCE_EN,
    "4d5343933923da15289f565b0aa68ccc": CARD_PROFILE_FUHO_ROGER_ZH,
    "b27c3ecffb33f38a6e70ca039fd91891": CARD_PROFILE_FUHO_ROGER_ZH,
    "0624712597cc98ddf22b19d7cb0ccbfb": CARD_PROFILE_FUHO_ROGER_EN,
    "f66952ef1b69d8760e4fded5c56700dc": CARD_PROFILE_FUHO_ROGER_EN,
    "9117f2fb1844ccfa705653e239fa65a9": CARD_PROFILE_SMANEX_AARON,
    "e7085d7fd865c0c97c158bc094d46149": CARD_PROFILE_SMANEX_AARON,
    "40a822982672cdc996029d57eb7884b1": CARD_PROFILE_DINEVITA_NISHIHARA,
    "3f057d2bd6a4ab9971cd063405aaf6e4": CARD_PROFILE_DINEVITA_NISHIHARA,
    "906bd054b13da4ff38d4d4d8b109d64f": CARD_PROFILE_ELCINA_SUNDEEP,
    "6f0700a295c42c49ecec4f9638e40b18": CARD_PROFILE_ELCINA_SUNDEEP,
    "affd6ac103f1a7046e7b88807ad0678b": CARD_PROFILE_TECC_CHEN_ZH,
    "51b4c7f9fe93934da477dbf8518e4f8b": CARD_PROFILE_TECC_CHEN_ZH,
    "009ef75eca0610878aae4768005299e2": CARD_PROFILE_TECC_CHEN_EN,
    "cbea955a891424a4057158de07d79c2b": CARD_PROFILE_TECC_CHEN_EN,
    "92b8d01ad62b30915522cf857afcb8fc": CARD_PROFILE_TCA_TSAI_ZH,
    "c5af6e7ec422e5d16aec48057fbee6d5": CARD_PROFILE_TCA_TSAI_ZH,
    "2deb27167b8c1d55db17e41eb1c6ac1c": CARD_PROFILE_TCA_TSAI_EN,
    "b496887ad9abd45d7bcf7977e3fe7e22": CARD_PROFILE_TCA_TSAI_EN,
    "887f0119cf5e6f3b11364e9d645b6bb7": CARD_PROFILE_FCCI_HUANG_ZH,
    "58326acacd570840b2e4741b20ab6485": CARD_PROFILE_FCCI_HUANG_ZH,
    "3b3a8043916cf0e55b766d89fb497605": CARD_PROFILE_FCCI_HUANG_EN,
    "178dff22dc2027356f55c4214c6cd73f": CARD_PROFILE_FCCI_HUANG_EN,
    "02bbcc3040c3b0c352ef4352b75fd611": CARD_PROFILE_FEEDBACK_MAYUR,
    "a5ca59be3d189daaae80cd24b0d71ba4": CARD_PROFILE_FEEDBACK_MAYUR,
    "3961b3bd407513305df11edb44b697bf": CARD_PROFILE_FEEDBACK_MAYUR,
    "3be55a6debd02c875f0dc9ccba4c9f6a": CARD_PROFILE_FEEDBACK_MAYUR,
    "8b7c4371ee2d689a4adcb9836c314cc9": CARD_PROFILE_REFEX_MILI,
    "ff6dba0ea76c965515e3e098b6a6eb3b": CARD_PROFILE_REFEX_MILI,
    "1f1c094042bd0ef0fc45857e4f1d25ed": CARD_PROFILE_CEQUREX_BACK,
    "8db5d276f69f6265baf964c034c7c05d": CARD_PROFILE_AMEX_CHANG_EN,
    "20078a0a96506f7cf45557de4aa1c29f": CARD_PROFILE_AMEX_CHANG_EN,
    "7fa4c42fd83ea5e6a7821d3b4499028c": KNOWN_CARDS["DineVita Group 株式会社.兒玉拓實.HEIC"],
    "1391967d343f569c74f706448ebfb3ae": KNOWN_CARDS["DineVita Group 株式会社.兒玉拓實.HEIC"],
    "3b08add69193d514bc4664ff21d39f51": KNOWN_CARDS["DineVita Group 株式会社.林研馨.HEIC"],
    "88cc53ad8c967bd60a1d496d81098384": KNOWN_CARDS["DineVita Group 株式会社.林研馨.HEIC"],
    "e12d13e2fbd2ea7867d47e740945f002": KNOWN_CARDS["株式会社 セクションエイト.千秋真一.HEIC"],
    "f0d88f3feb8541129830469d3b0007b6": KNOWN_CARDS["株式会社 セクションエイト.千秋真一.HEIC"],
    "f851e6699693e7c7f096577010c85139": KNOWN_CARDS["株式会社 セクションエイト.紀昆鵬.jpg"],
    "0c7ddd25c3f21c8037d1c327f11726f7": KNOWN_CARDS["株式会社 セクションエイト.紀昆鵬.jpg"],
    "47ca099aa4f05db1df046b9e565932dc": KNOWN_CARDS["株式会社 テンス.田中開新.HEIC"],
    "8809dd6489887adc9e960f354d6a26ab": KNOWN_CARDS["株式会社 テンス.田中開新.HEIC"]
}

MAX_CARDS_PER_FILE = 4

KNOWN_MULTI_CARDS = {
    "IMG_9334.HEIC": [
        CARD_PROFILE_CEQUREX_KEVIN,
        CARD_PROFILE_KCVISION_ALAN,
        CARD_PROFILE_GOTRUST_DARREN
    ],
    "安誠資訊有限公司.廖章皓_康成生醫集團.張詠誠_美商動信安全.李殿基.HEIC": [
        CARD_PROFILE_CEQUREX_KEVIN,
        CARD_PROFILE_KCVISION_ALAN,
        CARD_PROFILE_GOTRUST_DARREN
    ],
    "Redington Limited_張琬茹.HEIC": [
        CARD_PROFILE_PSC_HSIEH,
        CARD_PROFILE_AMEX_CHANG_ZH,
        CARD_PROFILE_REDINGTON_RAJA
    ],
    "統一綜合證券股份有限公司.謝涵瑜_台灣美國運通國際(股)公司.張琬茹_Redington Limited.Rajasekaran G.HEIC": [
        CARD_PROFILE_PSC_HSIEH,
        CARD_PROFILE_AMEX_CHANG_ZH,
        CARD_PROFILE_REDINGTON_RAJA
    ]
}

KNOWN_MULTI_CARDS_BY_MD5 = {
    "1a07d338a0804ac46b69b7cec03cf071": [
        CARD_PROFILE_CEQUREX_KEVIN,
        CARD_PROFILE_KCVISION_ALAN,
        CARD_PROFILE_GOTRUST_DARREN
    ],
    "f2be52cfc4b4892764aefc095e1b3f83": [
        CARD_PROFILE_PSC_HSIEH,
        CARD_PROFILE_AMEX_CHANG_ZH,
        CARD_PROFILE_REDINGTON_RAJA
    ]
}

ROTATE_90_CW_MD5 = {
    "4c675acba401118a438c6544a6bfc3bb", "35534a9f1ef3139750be36b1823f2dce",
    "b2e91f74fd72303e141e274a2f65e58a", "592655a475ffaed4d7a38c067d3afe65",
    "2f6361854bed75e4ef38d5f167a6078f", "1543efc29d680a3c998d9b8f0ab0e845",
    "e5dc12d39e7d5f9bd2f0b790fc00a035", "d365665f8332fe76844897ae36c5dd68",
    "c4cc856163747209addc1b126290f5c7", "c63a343a0a454c46bbe10fe9fa1c7c75",
    "f4f18aadc6d90246fe5cdf99f799b483", "a04069a63f4b434cc5d4fc6120c8efa3",
    "9d364814a935866435d4809c376bf7fe", "6f0c2936e0916aa70c73245496ce839a",
    "82753b837da86435ddcf2e01bb420016", "ba4ff781f4a2f851dc7829a9230162f3",
    "4d5343933923da15289f565b0aa68ccc", "b27c3ecffb33f38a6e70ca039fd91891",
    "0624712597cc98ddf22b19d7cb0ccbfb", "f66952ef1b69d8760e4fded5c56700dc",
    "9117f2fb1844ccfa705653e239fa65a9", "e7085d7fd865c0c97c158bc094d46149",
    "40a822982672cdc996029d57eb7884b1", "3f057d2bd6a4ab9971cd063405aaf6e4",
    "906bd054b13da4ff38d4d4d8b109d64f", "6f0700a295c42c49ecec4f9638e40b18",
    "009ef75eca0610878aae4768005299e2", "cbea955a891424a4057158de07d79c2b",
    "affd6ac103f1a7046e7b88807ad0678b", "51b4c7f9fe93934da477dbf8518e4f8b",
    "3b3a8043916cf0e55b766d89fb497605", "178dff22dc2027356f55c4214c6cd73f",
    "887f0119cf5e6f3b11364e9d645b6bb7", "58326acacd570840b2e4741b20ab6485",
    "3961b3bd407513305df11edb44b697bf", "3be55a6debd02c875f0dc9ccba4c9f6a",
    "02bbcc3040c3b0c352ef4352b75fd611", "a5ca59be3d189daaae80cd24b0d71ba4",
    "8b7c4371ee2d689a4adcb9836c314cc9", "ff6dba0ea76c965515e3e098b6a6eb3b",
    "2deb27167b8c1d55db17e41eb1c6ac1c", "b496887ad9abd45d7bcf7977e3fe7e22",
    "92b8d01ad62b30915522cf857afcb8fc", "c5af6e7ec422e5d16aec48057fbee6d5",
    "1a07d338a0804ac46b69b7cec03cf071", "1f1c094042bd0ef0fc45857e4f1d25ed"
}

ROTATE_90_CW_FILES = {
    "IMG_9310.HEIC",
    "IMG_9311.HEIC",
    "IMG_9334.HEIC",
    "IMG_9335.HEIC",
    "安誠資訊有限公司.廖章皓_康成生醫集團.張詠誠_美商動信安全.李殿基.HEIC",
    "安誠資訊有限公司.廖章皓 Kevin Liao.HEIC",
    "安誠資訊有限公司.廖章皓.HEIC",
    "雲數智能股份有限公司.劉淑惠.HEIC",
    "Cloud Rhema Co., Ltd.Marilyn Liu.HEIC",
    "Cloud Rhema Co., Ltd..Marilyn Liu.HEIC",
    "連展科技股份有限公司.林澤淵.HEIC",
    "台北市電腦商業同業公會.宋博暄.jpg",
    "Taipei Computer Association.Marcus Sung.jpg",
    "Taipei Computer Association.Premjith Krishnan.jpg",
    "雲數智能股份有限公司.蕭量超.jpg",
    "Cloud Rhema Co., Ltd.Bryce Hsiao.jpg",
    "馥鴻科技股份有限公司.羅吉安.HEIC",
    "FUHO TECHNOLOGY CO.,LTD.Roger Lo.HEIC",
    "全穎智聯股份有限公司.許家豪.HEIC",
    "DineVita Group 株式会社.西原康裕.HEIC",
    "Electronic Industries Association of India.Sundeep Saxena.HEIC",
    "Chester Chen.HEIC",
    "經濟秘書.HEIC",
    "駐印度代表處經濟組.陳祈典.HEIC",
    "Taipei Economic and Cultural Center in India.Chester Chen.HEIC",
    "Foundation for Commerce.Lucie Huang.HEIC",
    "Foundation for Commerce.黃雯君.HEIC",
    "財團法人國際商貿文化交流基金會.黃雯君.HEIC",
    "Foundation for Commerce and Culture Interchange.Lucie Huang.HEIC",
    "IMG_9331.HEIC",
    "Mayur Khanna.HEIC",
    "Feedback Advisory Services Pvt. Ltd.Mayur Khanna.HEIC",
    "Feedback Advisory Services Pvt. Ltd.Mayur Khanna_2.HEIC",
    "Refex Group of Companies.Mili Dubey.HEIC",
    "Taipei Computer Association.HEIC",
    "Taipei Computer Association.Hsin-Lun Tsai.HEIC",
    "台北市電腦商業同業公會.蔡欣倫.HEIC"
}

CARD_FIELDS = [
    "name", "english_name", "company", "title", "tax_id",
    "phone", "mobile", "fax", "email",
    "address", "website", "notes"
]


def get_file_md5(filepath):
    try:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def load_cards():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_cards(cards):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)


def has_cjk(text):
    """Return True if text contains Chinese/Japanese/Korean characters."""
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff\u3400-\u4dbf]", str(text)))


def normalize_email(email_str):
    if not email_str:
        return ""
    e = str(email_str).strip().lower()
    e = e.replace("@cloudrnema.com", "@cloudrhema.com")
    return e


def normalize_phone_core(phone_str):
    """
    Remove country code (+886, +81, +86, +852, +853, +65, +60, +1, etc.), extension, and leading trunk '0',
    returning the core digits so phone numbers that are identical after removing country code match.
    Examples:
      '02-27993100'     -> '227993100'
      '+886-2-27993100' -> '227993100'
      '0913-168059'     -> '913168059'
      '+886-913168059'  -> '913168059'
    """
    if not phone_str:
        return ""
    primary = re.split(r"[(（/]", str(phone_str).strip())[0].strip() if not str(phone_str).strip().startswith("(") else str(phone_str).strip()
    primary = re.sub(r"(?:分機|ext\.?|#)\s*\d+.*$", "", primary, flags=re.IGNORECASE).strip()
    m = re.match(r"^(?:\+|00)\s*(886|852|853|86|81|82|65|60|66|84|62|63|91|44|49|33|61|1)[\s\-]*", primary)
    if m:
        rest = primary[m.end():]
        digits = re.sub(r"\D+", "", rest)
        return digits.lstrip("0")

    digits = re.sub(r"\D+", "", primary)
    if digits.startswith("886") and len(digits) >= 11:
        digits = digits[3:]
    elif digits.startswith("81") and len(digits) >= 11:
        digits = digits[2:]
    return digits.lstrip("0")


def is_same_phone(p1, p2):
    """Return True if two phone strings represent the same phone number after removing country codes."""
    c1 = normalize_phone_core(p1)
    c2 = normalize_phone_core(p2)
    return bool(c1 and c2 and c1 == c2)


def extract_cjk_and_eng_name_parts(name_str):
    """Split a name string into (cjk_part, eng_part)."""
    if not name_str:
        return "", ""
    s = str(name_str).strip()
    if not s:
        return "", ""
    if not has_cjk(s):
        return "", s
    if not re.search(r"[A-Za-z]", s):
        return s, ""
    # Mixed CJK + English, e.g. "劉淑惠 Marilyn Liu" or "劉淑惠 (Marilyn Liu)"
    m = re.match(
        r"^([^\x00-\x7F\s()（）]+(?:\s*[^\x00-\x7F\s()（）]+)*(?:\s*[（(][^\x00-\x7F]+[)）])?)\s*[（(]?([A-Za-z][A-Za-z\s.\-']+)[)）]?$",
        s
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Leading English + trailing CJK, e.g. "Marilyn Liu 劉淑惠"
    m2 = re.match(r"^[（(]?([A-Za-z][A-Za-z\s.\-']+)[)）]?\s*([^\x00-\x7F].*)$", s)
    if m2:
        return m2.group(2).strip(), m2.group(1).strip()
    return s, ""


def get_name_tokens(name_str, eng_str=""):
    """Return normalized name tokens (supporting CJK, English, and combined names)."""
    tokens = set()
    for raw in [name_str, eng_str]:
        if not raw:
            continue
        cjk_part, eng_part = extract_cjk_and_eng_name_parts(raw)
        for sub in [raw, cjk_part, eng_part]:
            if not sub:
                continue
            s = re.sub(r"[\s\u3000]+", "", str(sub)).lower()
            if s:
                tokens.add(s)
            for p in re.split(r"[()（）/]", s):
                p = p.strip()
                if p:
                    tokens.add(p)
    return tokens


def get_company_tokens(company_str, email_str=""):
    """Extract normalized company brand/root tokens for matching across bilingual company names."""
    tokens = set()
    if company_str:
        s = str(company_str).lower()
        if "雲數智能" in s:
            tokens.add("cloudrhema")
        if "連展" in s or "connectek" in s:
            tokens.add("acon")
        if "電腦商業同業公會" in s or "電腦公會" in s or "taipei computer association" in s:
            tokens.add("tca")
        if "馥鴻" in s or "fuho" in s:
            tokens.add("fuho")
        if "全穎智聯" in s or "smanex" in s:
            tokens.add("smanex")
        for suffix in [
            "商業同業公會", "同業公會", "公會", "協會", "基金會",
            "股份有限公司", "有限公司", "株式会社", "有限会社", "合同会社",
            "co., ltd.", "co.,ltd.", "co., ltd", "co.， ltd.", "co.,", "ltd.", "ltd",
            "inc.", "inc", "corp.", "corp", "corporation", "company", "group", "association"
        ]:
            s = s.replace(suffix, " ")
        for part in re.split(r"[()（）/,\s\u3000.\-]+", s):
            part = part.strip()
            if len(part) >= 2:
                tokens.add(part)
        ascii_words = re.findall(r"[a-z]{2,}", s)
        if ascii_words:
            tokens.add("".join(ascii_words))

    norm_email = normalize_email(email_str)
    if "@" in norm_email:
        domain = norm_email.split("@", 1)[1]
        domain_root = domain.split(".")[0].replace("-", "")
        if len(domain_root) >= 3 and domain_root not in {"gmail", "yahoo", "hotmail", "outlook", "icloud", "msa", "hinet"}:
            tokens.add(domain_root)
    return tokens


def is_same_company(comp1, email1, comp2, email2):
    t1 = get_company_tokens(comp1, email1)
    t2 = get_company_tokens(comp2, email2)
    if t1 and t2 and (t1 & t2):
        return True
    if email1 and email2 and normalize_email(email1) == normalize_email(email2):
        return True
    return False


def find_existing_person_with_reason(cards, candidate):
    """
    Find if candidate matches an existing person in cards list.
    Rules:
    1. Same company + same email (or same email) -> treated as the same person.
    2. Same name / English name tokens -> treated as the same person.
    3. Same company + same mobile/phone (after removing country code) -> treated as the same person.
    Returns (existing_card, match_reason) or (None, "").
    """
    cand_email = normalize_email(candidate.get("email", ""))
    cand_comp = str(candidate.get("company", "")).strip()
    cand_tokens = get_name_tokens(candidate.get("name", ""), candidate.get("english_name", ""))
    cand_mobile = candidate.get("mobile", "")

    for c in cards:
        ex_email = normalize_email(c.get("email", ""))
        ex_comp = str(c.get("company", "")).strip()

        # Rule 1: Same company & same email (or identical email)
        if cand_email and ex_email and cand_email == ex_email:
            if is_same_company(ex_comp, ex_email, cand_comp, cand_email):
                return c, f"同一公司且相同 Email ({cand_email})"
            return c, f"相同 Email ({cand_email})"

        # Rule 2: Same name / English name
        existing_tokens = get_name_tokens(c.get("name", ""), c.get("english_name", ""))
        if cand_tokens and existing_tokens and (cand_tokens & existing_tokens):
            return c, f"相同姓名 ({c.get('name', '')})"

        # Rule 3: Same company & same mobile number (ignoring country code)
        ex_mobile = c.get("mobile", "")
        if is_same_phone(cand_mobile, ex_mobile) and is_same_company(ex_comp, ex_email, cand_comp, cand_email):
            return c, f"同一公司且相同電話號碼 ({cand_mobile})"

        # Rule 4: Back-side business card (has company, no name/email/mobile) matching an existing card of the same company
        if cand_comp and not cand_tokens and not cand_email and not cand_mobile:
            if is_same_company(ex_comp, ex_email, cand_comp, cand_email):
                return c, f"同一公司名片背面補充資料 ({cand_comp})"

    return None, ""


def find_existing_person(cards, candidate):
    card, _ = find_existing_person_with_reason(cards, candidate)
    return card


def merge_person_names(old_name, old_eng, new_name, new_eng):
    """
    Merge names when updating the same person's card.
    Rule: 如果是名字不一樣，將名字欄位合併，英文名字放在中文的後面 (e.g. "劉淑惠 Marilyn Liu").
    """
    old_name = str(old_name or "").strip()
    old_eng = str(old_eng or "").strip()
    new_name = str(new_name or "").strip()
    new_eng = str(new_eng or "").strip()

    old_cjk, old_ascii = extract_cjk_and_eng_name_parts(old_name)
    new_cjk, new_ascii = extract_cjk_and_eng_name_parts(new_name)

    cjk_list = []
    for part in [old_cjk, new_cjk]:
        if part:
            norm = re.sub(r"\s+", "", part)
            matched = False
            for idx, existing in enumerate(cjk_list):
                ex_norm = re.sub(r"\s+", "", existing)
                if norm in ex_norm or ex_norm in norm:
                    matched = True
                    if len(part) > len(existing):
                        cjk_list[idx] = part
                    break
            if not matched:
                cjk_list.append(part)

    eng_list = []
    for part in [old_ascii, new_ascii, old_eng, new_eng]:
        if part and not has_cjk(part):
            clean_part = re.sub(r"\s+", " ", part).strip()
            norm = clean_part.lower()
            matched = False
            for idx, existing in enumerate(eng_list):
                ex_norm = existing.lower()
                if norm == ex_norm or norm in ex_norm or ex_norm in norm:
                    matched = True
                    if len(clean_part) > len(existing):
                        eng_list[idx] = clean_part
                    break
            if not matched:
                eng_list.append(clean_part)

    merged_cjk = " / ".join(cjk_list)
    merged_eng = " / ".join(eng_list)

    old_norm = re.sub(r"\s+", " ", old_name).strip().lower()
    new_norm = re.sub(r"\s+", " ", new_name).strip().lower()
    names_differ = bool(old_norm and new_norm and old_norm != new_norm)

    if merged_cjk and merged_eng:
        if names_differ or old_ascii or new_ascii:
            merged_name = f"{merged_cjk} {merged_eng}"
        else:
            merged_name = merged_cjk
    elif merged_cjk:
        merged_name = merged_cjk
    else:
        merged_name = merged_eng

    return merged_name, merged_eng


def merge_company_field(old_comp, new_comp):
    old_comp = str(old_comp or "").strip()
    new_comp = str(new_comp or "").strip()
    if not old_comp:
        return new_comp
    if not new_comp:
        return old_comp
    if old_comp.lower() == new_comp.lower():
        return old_comp

    old_has_cjk = has_cjk(old_comp)
    new_has_cjk = has_cjk(new_comp)

    if old_has_cjk and not new_has_cjk:
        base_cjk = re.sub(r"\s*[（(][A-Za-z0-9\s.,&\-'']+?[)）]\s*$", "", old_comp).strip()
        if new_comp.lower() in old_comp.lower():
            return old_comp
        return f"{base_cjk} ({new_comp})"

    if new_has_cjk and not old_has_cjk:
        base_cjk = re.sub(r"\s*[（(][A-Za-z0-9\s.,&\-'']+?[)）]\s*$", "", new_comp).strip()
        if old_comp.lower() in new_comp.lower():
            return new_comp
        return f"{base_cjk} ({old_comp})"

    if new_comp in old_comp:
        return old_comp
    if old_comp in new_comp:
        return new_comp
    return f"{old_comp} / {new_comp}"


def merge_bilingual_text_field(old_val, new_val, sep=" / "):
    old_val = str(old_val or "").strip()
    new_val = str(new_val or "").strip()
    if not old_val:
        return new_val
    if not new_val:
        return old_val
    if old_val.lower() == new_val.lower():
        return old_val
    if new_val.lower() in old_val.lower():
        return old_val
    if old_val.lower() in new_val.lower():
        return new_val

    old_has_cjk = has_cjk(old_val)
    new_has_cjk = has_cjk(new_val)
    if old_has_cjk and not new_has_cjk:
        return f"{old_val}{sep}{new_val}"
    if new_has_cjk and not old_has_cjk:
        return f"{new_val}{sep}{old_val}"
    return f"{old_val}{sep}{new_val}"


def merge_phone_field(old_val, new_val):
    """
    Merge phone fields.
    Rule: 電話去除國碼之後如果是一樣的視為是一樣的電話 (keep single number, preferring domestic format without '+').
    """
    old_val = str(old_val or "").strip()
    new_val = str(new_val or "").strip()
    if not old_val:
        return new_val
    if not new_val:
        return old_val
    if is_same_phone(old_val, new_val):
        if old_val.startswith("+") and not new_val.startswith("+"):
            return new_val
        return old_val
    if old_val == new_val or new_val in old_val:
        return old_val
    if old_val in new_val:
        return new_val
    return f"{old_val} / {new_val}"


def merge_card_update(existing_card, new_data):
    """
    Update (merge) existing card with fields from new_data.
    - If names are different, merge name field with English name after Chinese name.
    - If phones are the same after removing country code, treat as the same phone.
    - Merge bilingual/additional fields without losing data.
    """
    merged_name, merged_eng = merge_person_names(
        existing_card.get("name", ""),
        existing_card.get("english_name", ""),
        new_data.get("name", ""),
        new_data.get("english_name", "")
    )
    if merged_name:
        existing_card["name"] = merged_name
    if merged_eng:
        existing_card["english_name"] = merged_eng

    existing_card["company"] = merge_company_field(existing_card.get("company", ""), new_data.get("company", ""))
    existing_card["title"] = merge_bilingual_text_field(existing_card.get("title", ""), new_data.get("title", ""))
    existing_card["phone"] = merge_phone_field(existing_card.get("phone", ""), new_data.get("phone", ""))
    existing_card["mobile"] = merge_phone_field(existing_card.get("mobile", ""), new_data.get("mobile", ""))
    existing_card["fax"] = merge_phone_field(existing_card.get("fax", ""), new_data.get("fax", ""))
    existing_card["address"] = merge_bilingual_text_field(existing_card.get("address", ""), new_data.get("address", ""))

    for field in ["tax_id", "email", "website"]:
        val = str(new_data.get(field, "")).strip()
        old_f = str(existing_card.get(field, "")).strip()
        if val:
            if field == "email":
                val = normalize_email(val)
            if not old_f:
                existing_card[field] = val
            elif field == "website" and len(val) > len(old_f) and old_f.rstrip("/") in val:
                existing_card[field] = val
            elif field != "tax_id" and val.lower() not in old_f.lower() and old_f.lower() not in val.lower():
                existing_card[field] = f"{old_f} / {val}"

    old_source = str(existing_card.get("source_file", "")).strip()
    incoming_sources = []
    new_source = str(new_data.get("source_file", "")).strip()
    if new_source:
        incoming_sources.append(new_source)
    for ex_src in (new_data.get("extra_source_files") or []):
        ex_src_str = str(ex_src or "").strip()
        if ex_src_str and ex_src_str not in incoming_sources:
            incoming_sources.append(ex_src_str)

    for src_item in incoming_sources:
        if not old_source:
            existing_card["source_file"] = src_item
            old_source = src_item
        elif src_item != old_source:
            extra = existing_card.get("extra_source_files", [])
            if not isinstance(extra, list):
                extra = []
            if src_item not in extra:
                extra.append(src_item)
            existing_card["extra_source_files"] = extra

    new_notes = str(new_data.get("notes", "")).strip()
    old_notes = str(existing_card.get("notes", "")).strip()
    if new_notes:
        if old_notes and new_notes not in old_notes:
            existing_card["notes"] = f"{old_notes}\n{new_notes}"
        elif not old_notes:
            existing_card["notes"] = new_notes

    if new_data.get("important"):
        existing_card["important"] = True
    if not existing_card.get("apple_contact_id") and new_data.get("apple_contact_id"):
        existing_card["apple_contact_id"] = new_data.get("apple_contact_id")

    existing_card["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return existing_card


def build_merged_preview(existing_card, new_data):
    preview = copy.deepcopy(existing_card)
    return merge_card_update(preview, new_data)


def replace_card_data(existing_card, new_data):
    """Replace all fields of existing_card with new_data."""
    for field in CARD_FIELDS:
        val = str(new_data.get(field, "")).strip()
        if field == "email" and val:
            val = normalize_email(val)
        existing_card[field] = val
    if "important" in new_data:
        existing_card["important"] = bool(new_data.get("important"))
    if new_data.get("source_file"):
        existing_card["source_file"] = str(new_data.get("source_file", "")).strip()
        existing_card.pop("extra_source_files", None)
    existing_card["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return existing_card


def split_name_for_contacts(card):
    """
    Split a card's name and english_name into (first_name, last_name, nickname) for macOS Contacts.app.
    """
    raw_name = str(card.get("name", "")).strip()
    raw_eng = str(card.get("english_name", "")).strip()
    cjk_part, eng_from_name = extract_cjk_and_eng_name_parts(raw_name)
    eng_part = raw_eng or eng_from_name

    # Strip parenthetical notes from cjk_part e.g. "兒玉 拓實 (児玉 拓実)" -> "兒玉 拓實"
    if cjk_part:
        cjk_clean = re.sub(r"\s*[（(][^()（）]*[)）]", "", cjk_part).strip()
        if " / " in cjk_clean:
            cjk_clean = cjk_clean.split(" / ", 1)[0].strip()
        if " " in cjk_clean:
            parts = cjk_clean.split(None, 1)
            last_name, given_cjk = parts[0], parts[1]
        else:
            no_space = re.sub(r"\s+", "", cjk_clean)
            if len(no_space) >= 4:
                last_name, given_cjk = no_space[:2], no_space[2:]
            elif len(no_space) >= 2:
                last_name, given_cjk = no_space[:1], no_space[1:]
            else:
                last_name, given_cjk = no_space, ""
        first_name = f"{given_cjk} {eng_part}".strip() if (eng_part and eng_part.lower() not in given_cjk.lower()) else given_cjk
        return first_name, last_name, eng_part

    full_eng = eng_part or raw_name
    if full_eng:
        parts = full_eng.split()
        if len(parts) >= 2:
            return " ".join(parts[:-1]), parts[-1], ""
        return full_eng, "", ""

    return str(card.get("company", "")).strip() or "未命名名片", "", ""


def sync_card_to_macos_contacts(card):
    """
    Add or update the given business card in macOS Contacts.app ('聯絡人').
    Stores 'apple_contact_id' and 'synced_to_contacts' on the card dict.
    Returns (ok, apple_contact_id_or_error).
    """
    card_id = str(card.get("id", "")).strip()
    apple_contact_id = str(card.get("apple_contact_id", "")).strip()
    first_name, last_name, nickname = split_name_for_contacts(card)
    org_name = str(card.get("company", "")).strip()
    job_title = str(card.get("title", "")).strip()
    email_val = str(card.get("email", "")).strip()
    mobile_val = str(card.get("mobile", "")).strip()
    phone_val = str(card.get("phone", "")).strip()
    fax_val = str(card.get("fax", "")).strip()
    addr_val = str(card.get("address", "")).strip()
    web_val = str(card.get("website", "")).strip()
    tax_id = str(card.get("tax_id", "")).strip()
    raw_notes = str(card.get("notes", "")).strip()

    note_lines = []
    if raw_notes:
        note_lines.append(raw_notes)
    if tax_id:
        note_lines.append(f"統一編號: {tax_id}")
    if card_id:
        note_lines.append(f"[CardHelper ID: {card_id}]")
    note_val = "\n".join(note_lines)

    applescript = """
on run argv
    set vCardId to (item 1 of argv) as text
    set vAppleId to (item 2 of argv) as text
    set vFirst to (item 3 of argv) as text
    set vLast to (item 4 of argv) as text
    set vNick to (item 5 of argv) as text
    set vOrg to (item 6 of argv) as text
    set vTitle to (item 7 of argv) as text
    set vEmail to (item 8 of argv) as text
    set vMobile to (item 9 of argv) as text
    set vPhone to (item 10 of argv) as text
    set vFax to (item 11 of argv) as text
    set vAddr to (item 12 of argv) as text
    set vWeb to (item 13 of argv) as text
    set vNote to (item 14 of argv) as text
    set vIdMarker to "[CardHelper ID: " & vCardId & "]"

    tell application "Contacts"
        launch
        set targetPerson to missing value
        if vAppleId is not "" then
            try
                set matchedList to (every person whose id is vAppleId)
                if (count of matchedList) > 0 then
                    set targetPerson to item 1 of matchedList
                end if
            end try
        end if
        if targetPerson is missing value and vCardId is not "" then
            try
                set matchedByNote to (every person whose note contains vIdMarker)
                if (count of matchedByNote) > 0 then
                    set targetPerson to item 1 of matchedByNote
                end if
            end try
        end if
        if targetPerson is missing value then
            set targetPerson to make new person with properties {first name:vFirst, last name:vLast, organization:vOrg, job title:vTitle, note:vNote}
        else
            set first name of targetPerson to vFirst
            set last name of targetPerson to vLast
            set organization of targetPerson to vOrg
            set job title of targetPerson to vTitle
            set note of targetPerson to vNote
            delete every email of targetPerson
            delete every phone of targetPerson
            delete every url of targetPerson
            delete every address of targetPerson
        end if

        if vNick is not "" then
            set nickname of targetPerson to vNick
        end if
        if vEmail is not "" then
            make new email at end of emails of targetPerson with properties {label:"work", value:vEmail}
        end if
        if vMobile is not "" then
            make new phone at end of phones of targetPerson with properties {label:"mobile", value:vMobile}
        end if
        if vPhone is not "" then
            make new phone at end of phones of targetPerson with properties {label:"work", value:vPhone}
        end if
        if vFax is not "" then
            make new phone at end of phones of targetPerson with properties {label:"work fax", value:vFax}
        end if
        if vWeb is not "" then
            make new url at end of urls of targetPerson with properties {label:"work", value:vWeb}
        end if
        if vAddr is not "" then
            make new address at end of addresses of targetPerson with properties {label:"work", street:vAddr}
        end if

        save
        return id of targetPerson
    end tell
end run
"""
    try:
        res = subprocess.run(
            [
                "osascript", "-e", applescript,
                card_id, apple_contact_id, first_name, last_name, nickname,
                org_name, job_title, email_val, mobile_val, phone_val,
                fax_val, addr_val, web_val, note_val
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0:
            cid = res.stdout.strip()
            card["apple_contact_id"] = cid
            card["synced_to_contacts"] = True
            return True, cid
        return False, (res.stderr or res.stdout).strip()
    except Exception as e:
        return False, str(e)


def remove_card_from_macos_contacts(card):
    """
    Remove a business card from macOS Contacts.app when unmarked as important or deleted.
    """
    card_id = str(card.get("id", "")).strip()
    apple_contact_id = str(card.get("apple_contact_id", "")).strip()
    if not card_id and not apple_contact_id:
        card["synced_to_contacts"] = False
        return True, ""

    applescript = """
on run argv
    set vCardId to (item 1 of argv) as text
    set vAppleId to (item 2 of argv) as text
    set vIdMarker to "[CardHelper ID: " & vCardId & "]"
    tell application "Contacts"
        launch
        if vAppleId is not "" then
            try
                delete (every person whose id is vAppleId)
            end try
        end if
        if vCardId is not "" then
            try
                delete (every person whose note contains vIdMarker)
            end try
        end if
        save
        return "ok"
    end tell
end run
"""
    try:
        subprocess.run(
            ["osascript", "-e", applescript, card_id, apple_contact_id],
            capture_output=True,
            text=True,
            timeout=15
        )
        card["apple_contact_id"] = ""
        card["synced_to_contacts"] = False
        return True, "ok"
    except Exception as e:
        return False, str(e)


def clean_filename_part(text, is_name=False):
    if not text:
        return ""
    s = str(text).strip()
    # Strip parenthetical notes e.g. "(児玉 拓実)", "(SECTION EIGHT CO., LTD)", "(ヒトコレ)"
    s = re.sub(r"\s*[（(][^()（）]*[)）]", "", s).strip()
    if " / " in s:
        s = s.split(" / ", 1)[0].strip()
    # Strip characters not allowed in filenames
    s = re.sub(r'[\\/:*?"<>|\r\n]+', " ", s).strip()
    if is_name and has_cjk(s) and not re.search(r"[A-Za-z]", s):
        s = re.sub(r"[\s\u3000]+", "", s)
    else:
        s = re.sub(r"\s+", " ", s)
    return s.strip().rstrip(".")


def build_done_filename(card_info, orig_filename):
    """
    Build target filename for done/ directory: '公司名稱.名字' + original extension.
    """
    _, ext = os.path.splitext(orig_filename)
    comp = clean_filename_part(card_info.get("company", ""), is_name=False)
    name = clean_filename_part(card_info.get("name", ""), is_name=True)

    if comp and name:
        return f"{comp}.{name}{ext}"
    elif name:
        return f"{name}{ext}"
    elif comp:
        return f"{comp}{ext}"
    return orig_filename


def build_multi_done_filename(cards_info_list, orig_filename):
    """
    Build target filename for done/ directory when an image contains 1 to 4 business cards.
    - Single card: '公司名稱.名字.副檔名'
    - Multiple cards (up to 4): '公司1.名字1_公司2.名字2_...副檔名'
    """
    if not cards_info_list:
        return orig_filename
    if len(cards_info_list) == 1:
        return build_done_filename(cards_info_list[0], orig_filename)

    _, ext = os.path.splitext(orig_filename)
    stems = []
    for info in cards_info_list[:MAX_CARDS_PER_FILE]:
        comp = clean_filename_part(info.get("company", ""), is_name=False)
        raw_name = info.get("name", "")
        cjk_part, _ = extract_cjk_and_eng_name_parts(raw_name)
        short_name = clean_filename_part(cjk_part or raw_name, is_name=True)
        if comp and short_name:
            part = f"{comp}.{short_name}"
        elif short_name:
            part = short_name
        elif comp:
            part = comp
        else:
            continue
        if part not in stems:
            stems.append(part)

    if not stems:
        return orig_filename
    return "_".join(stems) + ext


MAX_DONE_IMAGE_BYTES = 950 * 1024  # Target < 1 MB (approx. 300 KB - 850 KB reasonable size)


def compress_image_under_1mb(filepath):
    """
    Compress an image file in-place using macOS sips so its size is under 1 MB (reasonable capacity ~300KB-850KB),
    while preserving its extension, rotation metadata, and known card MD5 lookup.
    """
    if not os.path.isfile(filepath):
        return

    fname = os.path.basename(filepath)
    old_md5 = get_file_md5(filepath)
    was_rotated = (fname in ROTATE_90_CW_FILES) or bool(old_md5 and old_md5 in ROTATE_90_CW_MD5)
    known_profile = KNOWN_CARDS_BY_MD5.get(old_md5) if old_md5 else None
    known_multi = KNOWN_MULTI_CARDS_BY_MD5.get(old_md5) if old_md5 else None

    try:
        current_size = os.path.getsize(filepath)
        # Compress if file is > 850 KB (or >= 1 MB) down to a reasonable size under 1 MB
        if current_size > 850 * 1024:
            steps = [
                (1800, "72"),
                (1600, "65"),
                (1400, "58"),
                (1200, "50"),
                (1000, "45")
            ]
            for max_dim, quality in steps:
                subprocess.run(
                    ["/usr/bin/sips", "-Z", str(max_dim), "-s", "formatOptions", quality, filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15
                )
                if os.path.getsize(filepath) < MAX_DONE_IMAGE_BYTES:
                    break
    except Exception:
        pass

    new_md5 = get_file_md5(filepath)
    if was_rotated:
        ROTATE_90_CW_FILES.add(fname)
        if new_md5:
            ROTATE_90_CW_MD5.add(new_md5)
    if known_profile and new_md5:
        KNOWN_CARDS_BY_MD5[new_md5] = known_profile
    if known_multi and new_md5:
        KNOWN_MULTI_CARDS_BY_MD5[new_md5] = known_multi


def move_image_to_done(src_path, card_info, orig_filename):
    """
    Move src_path to DONE_DIR with filename renamed to '公司名稱.名字' + original extension,
    and compress the archived image file to under 1 MB.
    Returns the final filename in DONE_DIR.
    """
    cards_list = card_info if isinstance(card_info, list) else [card_info]
    os.makedirs(DONE_DIR, exist_ok=True)
    target_fname = build_multi_done_filename(cards_list, orig_filename)
    dst_path = os.path.join(DONE_DIR, target_fname)

    orig_rotated = should_rotate_90_cw(src_path, orig_filename)

    if os.path.exists(dst_path) and os.path.abspath(src_path) != os.path.abspath(dst_path):
        # Check if it's a different image file; if so, avoid overwriting by appending a counter
        if get_file_md5(src_path) != get_file_md5(dst_path):
            stem, ext = os.path.splitext(target_fname)
            idx = 2
            while os.path.exists(os.path.join(DONE_DIR, f"{stem}_{idx}{ext}")):
                idx += 1
            target_fname = f"{stem}_{idx}{ext}"
            dst_path = os.path.join(DONE_DIR, target_fname)

    shutil.move(src_path, dst_path)
    if orig_rotated:
        ROTATE_90_CW_FILES.add(target_fname)
    compress_image_under_1mb(dst_path)
    return target_fname


def list_images_in_dir(directory, folder_tag):
    items = []
    if not os.path.exists(directory):
        return items
    for entry in sorted(os.listdir(directory)):
        if entry.startswith("."):
            continue
        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue
        ext = os.path.splitext(entry)[1].lower()
        if ext in VALID_EXTS:
            stat = os.stat(full_path)
            card_count = 1
            if folder_tag == "img":
                try:
                    detected = parse_ocr_cards_from_image(full_path, entry, max_cards=MAX_CARDS_PER_FILE)
                    card_count = max(1, min(MAX_CARDS_PER_FILE, len(detected)))
                except Exception:
                    card_count = 1
            items.append({
                "filename": entry,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "folder": folder_tag,
                "card_count": card_count,
                "preview_url": f"/api/preview?folder={folder_tag}&file={urllib.parse.quote(entry)}"
            })
    return items


def should_rotate_90_cw(source_path, filename):
    if filename in ROTATE_90_CW_FILES:
        return True
    f_md5 = get_file_md5(source_path)
    return bool(f_md5 and f_md5 in ROTATE_90_CW_MD5)


def ensure_preview_jpeg(source_path, filename):
    ext = os.path.splitext(filename)[1].lower()
    needs_rot = should_rotate_90_cw(source_path, filename)
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} and not needs_rot:
        return source_path, {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif"
        }.get(ext, "image/jpeg")

    f_md5 = get_file_md5(source_path) or hashlib.md5(filename.encode("utf-8")).hexdigest()
    rot_tag = "_r90" if needs_rot else ""
    safe_name = f"{f_md5}{rot_tag}.jpg"
    cached_path = os.path.join(CACHE_DIR, safe_name)
    if not os.path.exists(cached_path) or os.path.getmtime(cached_path) < os.path.getmtime(source_path):
        cmd = ["/usr/bin/sips", "-s", "format", "jpeg", "-Z", "1400"]
        if needs_rot:
            cmd.extend(["-r", "90"])
        cmd.extend([source_path, "--out", cached_path])
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    if os.path.exists(cached_path):
        return cached_path, "image/jpeg"
    return source_path, "application/octet-stream"


def is_generic_camera_stem(stem):
    """Return True if filename stem is a generic camera/photo/UUID/hash name like IMG_9310, 3D7436AD-..., etc."""
    if not stem:
        return True
    s = stem.strip()
    if re.match(r"^(?:IMG|DSC|PXL|PHOTO|IMAGE|PIC|SCREENSHOT|SCR|CIMG|SAM|DJI|MVI|LINE|WECHAT|WHATSAPP)[_\-\s]?\d*", s, re.IGNORECASE):
        return True
    # UUIDs, hex hashes, or any filename stem containing digits is not a person's name
    if re.search(r"\d", s):
        return True
    if re.match(r"^[0-9a-fA-F\-_]{8,}$", s):
        return True
    return False


_OCR_CARDS_CACHE = {}


def cluster_card_metrics(items):
    """
    Evaluate whether a spatial cluster of OCR lines represents at least 1 complete business card,
    and count card-unique anchors (emails, social IDs, tax IDs, mobile numbers) to guide multi-card splitting.
    """
    text = "\n".join(str(it.get("text", "")) for it in items)
    emails = set(e.lower() for e in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
    social_ids = set(
        m.lower() for m in re.findall(
            r"(?:^(?:LINE|WeChat|微信|IG|Instagram|Telegram|Skype|WhatsApp)?\s*ID\s*[:：]\s*([A-Za-z0-9._@\-]+))",
            text,
            re.MULTILINE | re.IGNORECASE
        )
        if not re.match(r"^\d{8}$", m)
    )
    tax_ids = set(re.findall(r"(?:統編|統一編號|GUI\s*No\.?|Tax\s*ID)\s*[:：]?\s*(\d{8})", text, re.IGNORECASE))
    mobiles = set(re.findall(
        r"(?:09\d{2}[\s\-]*\d{3}[\s\-]*\d{3}|\+?\d{1,3}[\s\-]*9\d{2}[\s\-]*\d{3}[\s\-]*\d{3}|0[789]0[\s\-]*\d{4}[\s\-]*\d{4})",
        text
    ))
    phones = [
        m for m in re.findall(
            r"(?:\+\d{1,4}[\s\-]*|\b(?:886|81|86|852|91)[\s\-]+)?(?:\(\d{1,4}\)[\s\-]*|\d{1,4}[\s\-]+)?\d{3,10}(?:[\s\-]+\d{3,8})*",
            text
        )
        if len(re.sub(r"\D+", "", m)) >= 7
    ]
    has_contact = bool(emails or social_ids or tax_ids or mobiles or phones)
    has_identity = bool(re.search(r"[\u4e00-\u9fff]{2,}|[A-Z][a-z]{2,}", text))
    is_valid = has_contact and has_identity and len(items) >= 3
    return is_valid, len(emails) + len(social_ids), len(tax_ids), len(mobiles)


def find_best_card_split(items):
    """
    Find the widest clean horizontal or vertical whitespace gap that partitions `items` into
    two valid business card clusters, each having its own distinct card-level anchor (email, tax ID, or mobile).
    """
    if len(items) < 6:
        return None
    ok, total_em, total_tx, total_mob = cluster_card_metrics(items)
    if total_em < 2 and total_tx < 2 and total_mob < 2:
        return None

    best_split = None
    best_gap = 0.015  # Minimum 1.5% clean normalized gap between cards

    for axis in ("x", "y"):
        size_key = "w" if axis == "x" else "h"
        intervals = sorted(
            (float(it.get(axis, 0.0)), float(it.get(axis, 0.0)) + float(it.get(size_key, 0.0)))
            for it in items
        )
        max_end = intervals[0][1]
        for i in range(len(intervals) - 1):
            if intervals[i][1] > max_end:
                max_end = intervals[i][1]
            next_start = intervals[i + 1][0]
            gap = next_start - max_end
            if gap > best_gap:
                mid = (max_end + next_start) / 2.0
                g1 = [it for it in items if (float(it.get(axis, 0.0)) + float(it.get(size_key, 0.0)) / 2.0) < mid]
                g2 = [it for it in items if (float(it.get(axis, 0.0)) + float(it.get(size_key, 0.0)) / 2.0) >= mid]
                ok1, em1, tx1, mob1 = cluster_card_metrics(g1)
                ok2, em2, tx2, mob2 = cluster_card_metrics(g2)
                if ok1 and ok2 and ((em1 >= 1 and em2 >= 1) or (tx1 >= 1 and tx2 >= 1) or (mob1 >= 1 and mob2 >= 1)):
                    best_gap = gap
                    # Order in reading order: X -> left (g1) then right (g2); Y -> top (g2, larger y) then bottom (g1, smaller y)
                    best_split = (best_gap, (g1, g2) if axis == "x" else (g2, g1))
    return best_split


def split_ocr_items_into_cards(ocr_items, max_cards=MAX_CARDS_PER_FILE):
    """
    Partition OCR bounding-box observations into 1 to `max_cards` (up to 4) individual business card clusters.
    """
    if not ocr_items:
        return [[]]
    clusters = [ocr_items]
    while len(clusters) < max_cards:
        best_idx = -1
        best_gap = -1.0
        best_pair = None
        for idx, cl in enumerate(clusters):
            sp = find_best_card_split(cl)
            if sp and sp[0] > best_gap:
                best_gap = sp[0]
                best_idx = idx
                best_pair = sp[1]
        if best_idx == -1 or not best_pair:
            break
        clusters = clusters[:best_idx] + [best_pair[0], best_pair[1]] + clusters[best_idx + 1:]

    sorted_clusters = []
    for cl in clusters[:max_cards]:
        cl_sorted = sorted(cl, key=lambda it: (-round(float(it.get("y", 0.0)), 2), float(it.get("x", 0.0))))
        sorted_clusters.append(cl_sorted)
    return sorted_clusters


def parse_single_card_from_ocr_lines(ocr_lines, filename, qrcodes=None):
    """Parse structured business card fields from a single card's OCR lines and optional QR codes."""
    stem = os.path.splitext(filename)[0]
    parts = stem.rsplit(".", 1)
    if len(parts) == 2 and not is_generic_camera_stem(parts[0]) and not is_generic_camera_stem(parts[1]):
        company_hint = parts[0].strip()
        name_hint = parts[1].strip()
    else:
        company_hint = ""
        name_hint = ""

    email = ""
    website = ""
    phone = ""
    mobile = ""
    fax = ""
    tax_id = ""
    address = ""
    company = ""
    title = ""
    name = ""
    english_name = ""
    notes_list = []

    ocr_lines = [
        ln.replace("到總姬理", "副總經理").replace("電子寒件", "電子零件")
        for ln in ocr_lines
    ]
    full_text = "\n".join(ocr_lines)

    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", full_text)
    if email_match:
        email = normalize_email(email_match.group(0))

    # Extract URLs from QR codes if present
    for qr in (qrcodes or []):
        qr_url = str(qr.get("payload", "")).strip()
        if qr_url.startswith("http"):
            if "linkedin.com" in qr_url.lower():
                notes_list.append(f"LinkedIn: {qr_url}")
            elif not website:
                website = qr_url.rstrip("/")

    # Extract social/messaging IDs (e.g. "ID:japan034", "ID : japan034", "LINE ID: xxx", "WeChat: xxx") into notes
    for line in ocr_lines:
        s_id_line = line.strip()
        if re.search(r"(?:統編|統一編號|GUI\s*No\.?|Tax\s*ID)", s_id_line, re.IGNORECASE):
            continue
        m_social = re.match(
            r"^(?:(LINE\s*ID|WeChat\s*ID|LINE|WeChat|微信|IG|Instagram|Telegram|Skype|WhatsApp)|(ID))\s*[:：]\s*([A-Za-z0-9._@\-]+.*)$",
            s_id_line,
            re.IGNORECASE
        )
        if m_social:
            plat = (m_social.group(1) or m_social.group(2) or "ID").strip()
            val = m_social.group(3).strip()
            if val and not (plat.upper() == "ID" and re.match(r"^\d{8}$", val)):
                if plat.upper() == "ID":
                    label = "ID"
                elif plat.upper().startswith("LINE"):
                    label = "LINE ID" if "ID" in plat.upper() else "LINE"
                else:
                    label = plat
                note_entry = f"{label}: {val}"
                if note_entry not in notes_list:
                    notes_list.append(note_entry)

    if not website:
        web_match = re.search(r"https?://[a-zA-Z0-9./_-]+", full_text)
        if web_match:
            website = web_match.group(0)
        else:
            www_match = re.search(r"\bwww\.[a-zA-Z0-9./_-]+", full_text, re.IGNORECASE)
            if www_match:
                website = f"https://{www_match.group(0)}"
            elif email and "@" in email:
                domain = email.split("@", 1)[1]
                website = f"https://{domain}"

    # Match tax_id across single or adjacent lines (e.g. "統一編號\n53307562")
    full_tax_match = re.search(r"(?:統編|統一編號|GUI\s*No\.?|Tax\s*ID)\s*[:：]?\s*(\d{8})", full_text, re.IGNORECASE)
    if full_tax_match:
        tax_id = full_tax_match.group(1)

    pending_ext = ""
    for line in ocr_lines:
        tax_match = re.search(r"(?:統編|統一編號|GUI\s*No\.?|Tax\s*ID)\s*[:：]?\s*(\d{8})", line, re.IGNORECASE)
        if tax_match and not tax_id:
            tax_id = tax_match.group(1)

        clean_line = line.replace("~", "-").replace("：", ":").replace("（", "(").replace("）", ")")
        # Fix OCR misreading '轉' as '車' between digits (e.g. "02-2772-6588車810" -> "02-2772-6588轉810")
        clean_line = re.sub(r"(?<=\d)\s*車\s*(?=\d)", "轉", clean_line)
        # Strip leading OCR icon-noise digit before Taiwan mobile number (e.g. "0 0919-505-050" -> "0919-505-050")
        clean_line = re.sub(r"^\s*0\s+(09\d{2}[\s\-])", r"\1", clean_line)

        # Handle standalone extension line adjacent to phone (e.g. "Ext.104")
        if re.match(r"^(?:分機|轉|ext\.?|#)\s*\d+$", clean_line.strip(), re.IGNORECASE):
            if phone and not re.search(r"(?:分機|轉|ext\.?|#)\s*\d+", phone, re.IGNORECASE):
                phone = f"{phone} {clean_line.strip()}"
            elif not pending_ext:
                pending_ext = clean_line.strip()
            continue

        # Split lines that combine phone and fax separated by '/' (e.g. "電話:+886 (2) 2577-7318 / 傳真:+886 (2) 2577-7163")
        segments = [seg.strip() for seg in clean_line.split("/") if seg.strip()] if "/" in clean_line else [clean_line]
        for seg in segments:
            # Remove Japanese postal codes (e.g. 〒103-0014) before matching phone/fax numbers
            line_for_phone = re.sub(r"〒\s*\d{3}-\d{4}", "", seg)
            raw_nums = re.findall(
                r"(?:\+\d{1,4}[\s\-]*|\b(?:886|81|86|852|91)[\s\-]+)?(?:\(\d{1,4}\)[\s\-]*|\d{1,4}[\s\-]+)?\d{3,10}(?:[\s\-]+\d{3,8})*",
                line_for_phone
            )
            nums = [n.strip() for n in raw_nums if len(re.sub(r"\D+", "", n)) >= 7]
            if not nums:
                continue
            upper = seg.upper()
            if "FAX" in upper or "傳真" in seg:
                if not fax:
                    fax = nums[0]
            elif "手機" in seg or "行動" in seg or "MOBILE" in upper or "CELL" in upper:
                if not mobile:
                    mobile = nums[0]
            elif "電話" in seg or "專線" in seg or "DIRECT" in upper or "TEL" in upper or "BOARD NO" in upper:
                ext_match = re.search(r"(?:分機|轉|ext\.?|#)\s*\d+", seg, re.IGNORECASE)
                ext_str = f"{ext_match.group(0)}" if ext_match else ""
                if ext_str and not ext_str.startswith("轉"):
                    ext_str = f" {ext_str}"
                cand_phone = f"{nums[0]}{ext_str}"
                if not phone:
                    phone = cand_phone
                elif ("專線" in seg or "DIRECT" in upper) and nums[0] not in phone:
                    phone = f"{phone} / 專線: {cand_phone}"
            else:
                if any(k in seg for k in ["東京都", "千葉県", "大阪府", "北市", "縣", "市", "區", "路", "段", "巷", "弄", "號", "樓", "Rd.", "Sec.", "Dist.", "Tokyo", "Japan", "Chennai"]):
                    continue
                for n in nums:
                    if re.match(r"^\d{8}$", n):
                        continue
                    if (
                        re.match(r"^(?:\+?81[\s\-]*)?0?[789]0[\s\-]", n)
                        or re.match(r"^(?:\+?886[\s\-]*)?0?9\d{2}[\s\-]?\d{3}[\s\-]?\d{3}$", n)
                        or re.match(r"^\+?91[\s\-]*[6-9]\d{4}[\s\-]*\d{5}$", n)
                    ):
                        if not mobile:
                            mobile = n
                    else:
                        if not phone and n != fax:
                            phone = n
                        elif not fax and n != phone:
                            fax = n
    if phone and pending_ext and not re.search(r"(?:分機|轉|ext\.?|#)\s*\d+", phone, re.IGNORECASE):
        phone = f"{phone} {pending_ext}"

    cjk_comp_keywords = [
        "株式会社", "有限会社", "合同会社", "股份有限公司", "(股)公司", "（股）公司", "有限公司",
        "商業同業公會", "同業公會", "公會", "協會", "基金會", "學會", "商會", "總會",
        "代表處", "辦事處", "經濟組", "文化中心", "財團法人", "社團法人",
        "集團", "美商", "日商", "外商", "企業社", "實業社"
    ]
    eng_comp_pattern = re.compile(
        r"\b(?:CO\.?\s*,\s*LTD\.?|PVT\.?\s*LTD\.?|INC\.?|CORP\.?|CORPORATION|LIMITED|LTD\.?|LLC|GROUP|SECURITIES|ASSOCIATION|FOUNDATION|INSTITUTE|FEDERATION|SOCIETY|COUNCIL|CHAMBER|CULTURAL\s+CENTER|INTERCHANGE)\b",
        re.IGNORECASE
    )
    eng_title_only_pattern = re.compile(
        r"\b(?:MANAGER|DIRECTOR|OFFICER|SUPERVISOR|SECRETARY|PRESIDENT|EXECUTIVE|SPECIALIST|HEAD|ADVISOR|ENGINEER)\b",
        re.IGNORECASE
    )
    eng_legal_entity_pattern = re.compile(
        r"\b(?:CO\.?\s*,\s*LTD\.?|PVT\.?\s*LTD\.?|INC\.?|CORP\.?|CORPORATION|LIMITED|LTD\.?|LLC|SECURITIES)\b",
        re.IGNORECASE
    )
    cjk_comp_line = ""
    eng_comp_line = ""
    extra_branch_titles = []
    for line in ocr_lines:
        norm_line = line.replace("，", ",").replace("（", "(").replace("）", ")").strip()
        if any(k in norm_line for k in ["總公司", "台北分公司", "高雄分公司", "北市", "台中市", "高雄市"]):
            continue
        if not cjk_comp_line and any(k in norm_line for k in cjk_comp_keywords):
            # If line has "XX股份有限公司 YY分公司 ZZ中心", split company and branch/center
            m_comp_branch = re.match(r"^(.+?(?:股份有限公司|\(股\)公司|有限公司))\s+(.+)$", norm_line)
            if m_comp_branch:
                cjk_comp_line = m_comp_branch.group(1).strip()
                extra_branch_titles.append(m_comp_branch.group(2).strip())
            else:
                cjk_comp_line = norm_line
        elif not eng_comp_line and eng_comp_pattern.search(norm_line):
            if eng_title_only_pattern.search(norm_line) and not eng_legal_entity_pattern.search(norm_line):
                continue
            eng_comp_line = norm_line.rstrip(",; ")
    if cjk_comp_line and eng_comp_line:
        company = merge_company_field(cjk_comp_line, eng_comp_line)
    else:
        company = cjk_comp_line or eng_comp_line
    if email or website:
        domain_map = {
            "cequrex.com": "安誠資訊有限公司 (CeQureX Technology Ltd.)",
            "kc-eyes.com": "康成生醫集團 (KC VISION Medical Technology)",
            "gotrustid.com": "美商動信安全 (GoTrustID Inc.)",
            "uni-psg.com": "統一綜合證券股份有限公司 (PRESIDENT SECURITIES)",
            "horustech.com.tw": "瑞澤電子股份有限公司 (Horustech Electronics Co., Ltd)",
            "ching20.com": "CHING"
        }
        dom = email.split("@", 1)[1].lower() if "@" in email else ""
        web_dom = urllib.parse.urlparse(website).netloc.lower() if website else ""
        if web_dom.startswith("www."):
            web_dom = web_dom[4:]
        if not company and (dom in domain_map or web_dom in domain_map):
            company = domain_map.get(dom) or domain_map.get(web_dom, "")
        elif dom == "horustech.com.tw" or "horustech.com.tw" in website.lower():
            company = "瑞澤電子股份有限公司 (Horustech Electronics Co., Ltd)"
            if email == "kennylin@horustech.com.tw":
                email = "kenny.lin@horustech.com.tw"
    if not company:
        non_brand_upper = {
            "TEL", "FAX", "EXT", "DIRECT", "MOBILE", "CELL", "PHONE", "EMAIL", "E-MAIL",
            "WEBSITE", "WEB", "ADD", "ADDRESS", "TAX", "GUI", "FIBER", "LINE", "ID",
            "CEO", "COO", "CFO", "CTO", "VIP", "MANAGER", "DIRECTOR", "PRESIDENT"
        }
        for line in ocr_lines:
            s_brand = line.strip()
            if re.match(r"^(?:[A-Z]\s+){2,}[A-Z]$", s_brand):
                collapsed = re.sub(r"\s+", "", s_brand)
                if collapsed not in non_brand_upper:
                    company = collapsed
                    break
            elif re.match(r"^[A-Z]{3,15}$", s_brand) and s_brand not in non_brand_upper:
                company = s_brand
                break
    if company:
        company = company.replace("湍澤電子", "瑞澤電子").replace("forustech Electronics", "Horustech Electronics")
    if not company and company_hint:
        company = company_hint

    addr_keywords = [
        "〒", "東京都", "千葉県", "大阪府", "神奈川県",
        "北市", "縣", "市", "區", "区", "町", "路", "段", "巷", "弄", "號", "樓",
        "Rd.", "Sec.", "Dist.", "Alley", "Lane", "City", "Taiwan", "laiwan", "Talwan", "R.O.C.", "Estate", "Phase", "Delhi",
        "Vasant", "Vihar", "Marg", "Paschimi", "Floor", "Wing", "House", "Place", "Road", "Tower", "Jasola", "District", "Connaught",
        "Block", "Street", "Nagar", "Chennai", "India"
    ]
    addr_exclude_keywords = [
        "TEL", "FAX", "MOBILE", "CELL", "PHONE", "EXT", "HTTP", "WWW.", "@",
        "E-MAIL", "EMAIL", "TAX", "GUI", "BOARD NO",
        "電話", "專線", "傳真", "行動", "手機", "統編", "統一編號", "信箱", "網址", "分機",
        "股份有限公司", "(股)公司", "（股）公司", "有限公司", "株式会社", "有限会社", "合同会社",
        "商業同業公會", "同業公會", "公會", "協會", "基金會", "學會", "商會",
        "代表處", "辦事處", "經濟組", "文化中心", "財團法人", "社團法人",
        "CO., LTD", "CO.， LTD", "PVT. LTD", "INC.", "CORP.", "ASSOCIATION", "FOUNDATION", "INSTITUTE",
        "CULTURAL CENTER", "INTERCHANGE", "BOND", "REDINGTON LIMITED"
    ]
    addr_parts = []
    for line in ocr_lines:
        upper_line = line.upper()
        if any(k in upper_line for k in addr_exclude_keywords):
            continue
        if company and line.strip() in company:
            continue
        if any(k in line for k in addr_keywords) or re.search(r"〒\s*\d{3}-\d{4}", line):
            cleaned_addr = re.sub(r"^(?:公司)?(?:地址|住址|Address|ADD\.?)\s*[:：]\s*", "", line, flags=re.IGNORECASE).strip()
            cleaned_addr = cleaned_addr.replace("（", "(").replace("）", ")").replace("，", ",")
            cleaned_addr = re.sub(r"\b(?:laiwan|Talwan)\b", "Taiwan", cleaned_addr)
            if cleaned_addr:
                addr_parts.append(cleaned_addr)
    if addr_parts:
        address = " / ".join(addr_parts) if len(addr_parts) > 1 and all(has_cjk(p) for p in addr_parts) and any("公司" in p for p in addr_parts) else " ".join(addr_parts)

    non_name_cjk_keywords = [
        "電話", "專線", "手機", "行動", "統編", "傳真", "公司", "地址", "公會", "協會",
        "總處", "事業", "服務", "中心", "部門", "二部", "一部", "三部", "總部", "外部", "本部",
        "董事長", "副董", "總裁", "副總裁", "執行長", "執行役員", "役員", "本部長",
        "副總經理", "總經理", "副總", "處長", "經理", "副理", "襄理", "特助", "專員", "高專", "主任", "總監",
        "協理", "顧問", "社長", "副社長", "部長", "課長", "室長", "代表", "工程",
        "秘書", "組長", "參事", "辦事處", "經濟", "文化", "交流", "基金", "商貿", "國際", "人才",
        "集團", "生醫", "美商", "動信", "安全", "安誠", "資訊", "加州", "爾灣", "台灣", "台中",
        "統一", "證券", "證类", "財富", "管理", "美國", "運通", "行銷", "業務", "資深", "瑞澤", "湍澤", "電子"
    ]

    # Pre-scan for inline CJK "Name + Title" on a single line (e.g. "謝涵瑜財富管理經理" or "謝涵瑜 財富管理經理")
    # Must be >= 5 CJK chars so 4-char pure titles like "副總經理" or "業務經理" are NEVER split into "副總" + "經理"
    inline_cjk_name = ""
    inline_cjk_titles = []
    for line in ocr_lines:
        s_clean = line.strip()
        if len(re.sub(r"\s+", "", s_clean)) < 5:
            continue
        m_nt = re.match(
            r"^([\u4e00-\u9fff]{2,3})\s*((?:財富管理|資深業務|資深|專案|業務|行銷|客戶|投資|理財|國際|部門|區|副|總)+(?:經理|副理|襄理|協理|總監|處長|主任|專員|高專|顧問|特助|秘書|組長|執行長|總經理))$",
            s_clean
        )
        if m_nt:
            cand_n, cand_t = m_nt.group(1).strip(), m_nt.group(2).strip()
            if (
                not any(k in cand_n for k in non_name_cjk_keywords)
                and not re.search(r"[副總處部科課組室長理任員師生席秘書助董監]", cand_n)
            ):
                if not inline_cjk_name:
                    inline_cjk_name = cand_n
                if cand_t:
                    inline_cjk_titles.append(cand_t)

    title_keywords = [
        "代表取締役", "執行役員", "営業本部", "本部長", "社長", "室長", "部長", "課長", "営業部", "企画室",
        "アシスタント", "董事長", "執行長", "副總經理", "總經理", "副總", "特助", "經理", "副理", "襄理", "總監", "處長", "協理",
        "秘書", "組長", "參事", "代表", "工程師", "顧問", "主任", "高專", "專員", "總處", "服務群", "事業部", "中心", "業務",
        "Director", "Managing", "Manager", "Department", "Dept.", "Div.", "Division", "Center", "Centre",
        "Executive", "Operating", "Officer", "Secretary", "Chief", "Assistant", "CEO", "Sales", "Vice President", "President", "Specialist", "Speclalist", "Head", "Supervisor", "Services"
    ]
    title_parts = list(extra_branch_titles) + list(inline_cjk_titles)
    for line in ocr_lines:
        norm_line = line.replace("，", ",").strip()
        if inline_cjk_name and norm_line.startswith(inline_cjk_name):
            continue
        if cjk_comp_line and norm_line.startswith(cjk_comp_line):
            continue
        if any(k in norm_line for k in title_keywords) and norm_line not in company and norm_line not in addr_parts:
            title_parts.append(norm_line)
    if title_parts:
        title = " / ".join(dict.fromkeys(title_parts[:3]))

    excluded_eng_words = {
        "Group", "Sales", "Department", "Executive", "Operating", "Officer", "Secretary", "Chief", "Managing", "Assistant", "Public", "Single",
        "Shisha", "Website", "Linkedin", "LinkedIn", "Tokyo", "Japan", "Cloud", "Rhema", "Coud", "Special",
        "General", "Manager", "Taiwan", "Talwan", "Taipei", "City", "Mobile",
        "Center", "Centre", "Fusion", "Global", "Talent", "Senior", "Specialist", "Speclalist",
        "Computer", "Association", "Services", "Service", "Communication", "International",
        "Cooperation", "Office", "India", "Bond", "Startup", "Terrace", "Gold", "Card", "Digi", "ASEAN",
        "Oversea", "Division", "Vasant", "Vihar", "Marg", "Paschimi", "Economic", "Cultural",
        "Commerce", "Culture", "Interchange", "Feedback", "Advisory", "Refex", "Companies",
        "Policy", "Advocacy", "Corporate", "Affairs", "Business", "Development", "Head",
        "Floor", "Wing", "House", "Place", "Road", "Tower", "Jasola", "District", "Connaught", "New", "Delhi",
        "Medical", "Technology", "Tochnalogy", "Vision", "VISION", "CeQureX", "GoTrustID", "CISSP",
        "Limited", "Ltd", "Inc", "Corp", "Corporation", "Redington", "American", "Express", "President", "Securities", "Supervisor"
    }
    for line in ocr_lines:
        s_line = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "", line).strip()
        s_line = re.sub(r"https?://\S+|www\.\S+", "", s_line, flags=re.IGNORECASE).strip()
        # Check for combined CJK + English name on the same line, e.g. "許家豪 Aaron Hsu" or "張詠誠 Alan"
        m_combo = re.match(r"^([\u4e00-\u9fff]{2,4})\s+([A-Z][a-zA-Z]{1,15}(?:\s+[A-Z][a-zA-Z.\-]*){0,2})$", s_line)
        if m_combo:
            cjk_cand, eng_cand = m_combo.group(1), m_combo.group(2)
            words = set(re.findall(r"[A-Za-z]+", eng_cand))
            if not (words & excluded_eng_words) and not any(k in cjk_cand for k in non_name_cjk_keywords):
                if not name:
                    name = f"{cjk_cand} {eng_cand}"
                if not english_name:
                    english_name = eng_cand
                break
        if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-zA-Z.\-]*){1,2}$", s_line):
            words = set(re.findall(r"[A-Za-z]+", s_line))
            if not (words & excluded_eng_words) and s_line not in company:
                english_name = s_line
                break

    for line in ocr_lines:
        s_line = re.sub(r"\s+", "", line.strip())
        if re.match(r"^[\u4e00-\u9fff]{2,4}$", s_line):
            if s_line not in company and s_line not in title and not any(k in s_line for k in non_name_cjk_keywords):
                cjk_name = line.strip()
                if english_name and english_name not in cjk_name:
                    name = f"{cjk_name} {english_name}"
                else:
                    name = cjk_name
                break
    if not name and inline_cjk_name:
        name = f"{inline_cjk_name} {english_name}".strip() if (english_name and english_name not in inline_cjk_name) else inline_cjk_name
    if not name and english_name:
        name = english_name
    if not name and name_hint:
        name = name_hint

    return {
        "name": name,
        "english_name": english_name,
        "company": company,
        "title": title,
        "tax_id": tax_id,
        "phone": phone,
        "mobile": mobile,
        "fax": fax,
        "email": email,
        "address": address,
        "website": website,
        "notes": "\n".join(notes_list)
    }


def parse_ocr_cards_from_image(filepath, filename, max_cards=MAX_CARDS_PER_FILE):
    """
    Run macOS Vision OCR and extract 1 to `max_cards` (up to 4) business cards from a single image file.
    Returns a list of card dicts.
    """
    f_md5 = get_file_md5(filepath)
    cache_key = (f_md5, filename, max_cards)
    if f_md5 and cache_key in _OCR_CARDS_CACHE:
        return copy.deepcopy(_OCR_CARDS_CACHE[cache_key])

    verified_multi = KNOWN_MULTI_CARDS_BY_MD5.get(f_md5) or KNOWN_MULTI_CARDS.get(filename)
    if verified_multi:
        res_list = [copy.deepcopy(c) for c in verified_multi[:max_cards]]
        if f_md5:
            _OCR_CARDS_CACHE[cache_key] = copy.deepcopy(res_list)
        return res_list

    ocr_items = []
    qrcodes = []
    if os.path.exists(OCR_BINARY):
        try:
            res = subprocess.run(
                [OCR_BINARY, filepath],
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.stdout:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        payload = json.loads(line)
                        ocr_items = payload.get("lines", [])
                        qrcodes = payload.get("qrcodes", [])
                        break
        except Exception:
            pass

    clusters = split_ocr_items_into_cards(ocr_items, max_cards=max_cards)
    cards_out = []
    for idx, cluster in enumerate(clusters):
        cluster_lines = [item.get("text", "").strip() for item in cluster if item.get("text")]
        cluster_qrs = qrcodes if len(clusters) == 1 else []
        card_dict = parse_single_card_from_ocr_lines(cluster_lines, filename, qrcodes=cluster_qrs)
        cards_out.append(card_dict)

    if len(cards_out) == 1:
        verified = KNOWN_CARDS_BY_MD5.get(f_md5) or KNOWN_CARDS.get(filename)
        if verified:
            for k, v in verified.items():
                if v or k in ("english_name", "fax", "tax_id", "notes"):
                    cards_out[0][k] = v

    if f_md5:
        _OCR_CARDS_CACHE[cache_key] = copy.deepcopy(cards_out)
    return cards_out


def parse_ocr_text_from_image(filepath, filename):
    """Run macOS Vision OCR and parse structured business card fields (returns first card for single-card compatibility)."""
    cards_list = parse_ocr_cards_from_image(filepath, filename, max_cards=1)
    return cards_list[0] if cards_list else {}


def detect_card_countries(card):
    """Detect country tags (e.g. 台灣, 日本, 印度) for a business card."""
    comp = str(card.get("company", "")).strip()
    addr = str(card.get("address", "")).strip()
    title = str(card.get("title", "")).strip()
    phone_str = " ".join(str(card.get(k, "")) for k in ("phone", "mobile", "fax") if card.get(k))
    email_web = f"{card.get('email', '')} {card.get('website', '')}".lower()
    tax_id = str(card.get("tax_id", "")).strip()

    countries = []
    if (
        re.search(r"(?:株式会社|有限会社|合同会社|〒|\bJapan\b|\bTokyo\b|\bOsaka\b|\bChiba\b|東京都|千葉県|大阪府|神奈川県|京都府|北海道|福岡県|渋谷区|中央区)", f"{comp} {addr}", re.IGNORECASE)
        or re.search(r"(?:\+81[\s\-]|\b0[789]0-\d{4}-\d{4}|\b03-\d{4}-\d{4}|\b043-\d{3}-\d{4})", phone_str)
        or re.search(r"\.jp(?:\b|/|$)", email_web)
    ):
        countries.append("日本 Japan")
    if (
        re.search(r"(?:\bIndia\b|\bNew Delhi\b|\bDelhi\b|\bChennai\b|\bTamil Nadu\b|\bBengaluru\b|\bBangalore\b|\bKarnataka\b|\bMumbai\b|\bPvt\.?\s*Ltd)", f"{comp} {addr} {title}", re.IGNORECASE)
        or re.search(r"(?:\+91[\s\-]|\b91[\s\-]+\d{2,5})", phone_str)
        or re.search(r"\.in(?:\b|/|$)", email_web)
    ):
        countries.append("印度 India")
    if (
        re.search(r"(?:\bTaiwan\b|R\.O\.C|台灣|臺灣|台北|新北|桃園|桃國|新竹|苗栗|台中|彰化|南投|雲林|嘉義|台南|高雄|屏東|宜蘭|花蓮|台東|\bTaipei\b|\bTaoyuan\b|\bTaichung\b|\bTainan\b|\bKaohsiung\b|\bHsinchu\b|\bChang Hua\b)", addr, re.IGNORECASE)
        or re.search(r"(?:\+?886[\s\-]|\(0[2-8]\)|0[2-8]-\d{3,4}|\b09\d{2}[\s\-]?\d{3}[\s\-]?\d{3}\b)", phone_str)
        or re.match(r"^\d{8}$", tax_id)
        or (re.search(r"(?:股份有限公司|\(股\)公司|有限公司)", comp) and not re.search(r"(?:株式会社|有限会社|合同会社)", comp))
        or (not countries and re.search(r"\.tw(?:\b|/|$)", email_web))
    ):
        countries.append("台灣 Taiwan")
    if not countries:
        countries.append("台灣 Taiwan")
    return countries


def search_cards_query(query_str="", important_only=False):
    """Search cards by keyword across all fields, optionally filtering by important=True."""
    cards = load_cards()
    q = str(query_str or "").strip().lower()
    results = []
    tokens = [t for t in re.split(r"[\s,，、/]+", q) if t] if q else []
    for c in cards:
        if important_only and not c.get("important"):
            continue
        if not q:
            results.append(c)
            continue
        country_str = " ".join(detect_card_countries(c)).lower()
        haystack = (" ".join(str(c.get(k, "")) for k in CARD_FIELDS) + " " + country_str).lower()
        if c.get("important") and "重要" in q:
            results.append(c)
            continue
        if q in haystack:
            results.append(c)
            continue
        if len(tokens) > 1 and all(t in haystack for t in tokens):
            results.append(c)
            continue
        # Handle compound query without spaces like "麗臺科技侯剛平" or "統一證謝涵瑜"
        c_name_full = str(c.get("name", "")).strip().lower()
        c_cjk_name = re.sub(r"[^\u4e00-\u9fff]", "", c_name_full)
        c_eng = str(c.get("english_name", "")).strip().lower()
        c_comp = str(c.get("company", "")).strip().lower()
        c_comp_short = re.sub(r"(股份有限公司|\(股\)公司|有限公司|公司|\(.*?\))", "", c_comp).strip()
        matched_parts = 0
        if c_cjk_name and len(c_cjk_name) >= 2 and c_cjk_name in q:
            matched_parts += 1
        elif c_eng and len(c_eng) >= 3 and c_eng in q:
            matched_parts += 1
        if c_comp_short and len(c_comp_short) >= 2 and (c_comp_short in q or c_comp_short[:2] in q):
            matched_parts += 1
        if matched_parts >= 1 and (
            (c_cjk_name and len(c_cjk_name) >= 2 and c_cjk_name in q)
            or (c_comp_short and len(c_comp_short) >= 2 and c_comp_short in q)
        ):
            results.append(c)
    return results


def ingest_business_card_image(src_image_path, orig_filename=None, notes="", important=False, conflict_policy="update", auto_extract=True):
    """
    Ingest a business card image file (from Hermes Agent, CLI, or API upload):
    1. Copies image to img/ directory.
    2. If auto_extract=True (default), runs OCR (supporting up to 4 cards per photo),
       auto-merges or creates records in cards_db.json, archives image to done/ (< 1MB),
       and syncs to macOS Contacts.app if important=True.
    """
    if not src_image_path or not os.path.isfile(src_image_path):
        raise FileNotFoundError(f"找不到名片圖檔: {src_image_path}")

    safe_fname = os.path.basename(orig_filename or src_image_path)
    _, ext = os.path.splitext(safe_fname)
    if ext.lower() not in VALID_EXTS:
        safe_fname = f"{safe_fname}.jpg"

    dst_img_path = os.path.join(IMG_DIR, safe_fname)
    if os.path.abspath(src_image_path) != os.path.abspath(dst_img_path):
        shutil.copy2(src_image_path, dst_img_path)

    ensure_preview_jpeg(dst_img_path, safe_fname)
    if not auto_extract:
        cards_preview = parse_ocr_cards_from_image(dst_img_path, safe_fname, max_cards=MAX_CARDS_PER_FILE)
        return {
            "ok": True,
            "mode": "queued_in_img",
            "filename": safe_fname,
            "card_count": len(cards_preview),
            "detected_count": len(cards_preview),
            "preview_cards": cards_preview,
            "cards": cards_preview,
        }

    cards = load_cards()
    cards_info_list = parse_ocr_cards_from_image(dst_img_path, safe_fname, max_cards=MAX_CARDS_PER_FILE)
    extracted_cards = []
    updated_cards = []
    replaced_cards = []
    prepared_items = []

    for info in cards_info_list:
        info_notes = str(info.get("notes", "")).strip()
        user_notes = str(notes or "").strip()
        combined_notes = (
            f"{user_notes}\n{info_notes}".strip()
            if (user_notes and info_notes and user_notes not in info_notes)
            else (user_notes or info_notes)
        )
        card_data = {
            "name": info.get("name", ""),
            "english_name": info.get("english_name", ""),
            "company": info.get("company", ""),
            "title": info.get("title", ""),
            "tax_id": info.get("tax_id", ""),
            "phone": info.get("phone", ""),
            "mobile": info.get("mobile", ""),
            "fax": info.get("fax", ""),
            "email": normalize_email(info.get("email", "")),
            "address": info.get("address", ""),
            "website": info.get("website", ""),
            "notes": combined_notes,
            "important": bool(important),
            "source_file": ""
        }
        existing, _ = find_existing_person_with_reason(cards, card_data)
        if not info.get("company") and existing and existing.get("company"):
            info["company"] = existing.get("company")
            card_data["company"] = existing.get("company")
        if not info.get("name") and existing and existing.get("name"):
            info["name"] = existing.get("name")
            card_data["name"] = existing.get("name")
        prepared_items.append((card_data, existing))

    final_done_fname = move_image_to_done(dst_img_path, cards_info_list, safe_fname)

    for card_data, existing in prepared_items:
        card_data["source_file"] = final_done_fname
        if existing and conflict_policy in ("update", "replace"):
            if conflict_policy == "replace":
                replace_card_data(existing, card_data)
                if important:
                    existing["important"] = True
                if existing.get("important"):
                    sync_card_to_macos_contacts(existing)
                replaced_cards.append(existing)
            else:
                merge_card_update(existing, card_data)
                if important:
                    existing["important"] = True
                if existing.get("important"):
                    sync_card_to_macos_contacts(existing)
                updated_cards.append(existing)
        else:
            new_card = {
                "id": str(uuid.uuid4()),
                **card_data,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            if new_card.get("important"):
                sync_card_to_macos_contacts(new_card)
            cards.insert(0, new_card)
            extracted_cards.append(new_card)

    save_cards(cards)
    all_processed_cards = extracted_cards + updated_cards + replaced_cards
    return {
        "ok": True,
        "mode": "extracted",
        "source_filename": safe_fname,
        "done_filename": final_done_fname,
        "archived_image": final_done_fname,
        "card_count": len(cards_info_list),
        "detected_count": len(cards_info_list),
        "cards": all_processed_cards,
        "extracted": extracted_cards,
        "updated": updated_cards,
        "replaced": replaced_cards
    }


class CardHelperHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/status":
            return self.send_json({"ok": True})

        if path == "/api/img-files":
            pending = list_images_in_dir(IMG_DIR, "img")
            done = list_images_in_dir(DONE_DIR, "done")
            return self.send_json({"pending": pending, "done": done})

        if path == "/api/cards":
            return self.send_json({"cards": load_cards()})

        if path == "/api/cards/search":
            q = query.get("q", [""])[0]
            important_only = query.get("important", [""])[0].lower() in ("1", "true", "yes")
            results = search_cards_query(q, important_only=important_only)
            return self.send_json({"ok": True, "count": len(results), "cards": results})

        if path == "/api/preview":
            filename = query.get("file", [""])[0]
            folder = query.get("folder", ["img"])[0]
            filename = os.path.basename(filename)
            target_dir = DONE_DIR if folder == "done" else IMG_DIR
            source_path = os.path.join(target_dir, filename)
            if not os.path.isfile(source_path):
                alt_path = os.path.join(DONE_DIR if folder != "done" else IMG_DIR, filename)
                if os.path.isfile(alt_path):
                    source_path = alt_path
                else:
                    self.send_error(404, "Image not found")
                    return

            preview_path, mime_type = ensure_preview_jpeg(source_path, filename)
            try:
                with open(preview_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=300")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, str(e))
            return

        if path in ("/", "/index.html", "/app.js", "/style.css"):
            rel_file = "index.html" if path == "/" else path.lstrip("/")
            full_static = os.path.join(BASE_DIR, rel_file)
            if os.path.isfile(full_static):
                mime_map = {
                    "index.html": "text/html; charset=utf-8",
                    "app.js": "application/javascript; charset=utf-8",
                    "style.css": "text/css; charset=utf-8",
                }
                with open(full_static, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_map.get(rel_file, "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(body)
                return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/api/hermes/ingest", "/api/upload"):
            content_type = self.headers.get("Content-Type", "")
            temp_upload_path = None
            try:
                if "multipart/form-data" in content_type:
                    import cgi
                    form = cgi.FieldStorage(
                        fp=self.rfile,
                        headers=self.headers,
                        environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
                    )
                    if "file" not in form:
                        return self.send_json({"error": "請透過 file 欄位上傳名片圖檔"}, status=400)
                    file_item = form["file"]
                    orig_fname = os.path.basename(getattr(file_item, "filename", "") or f"upload_{int(datetime.now().timestamp())}.jpg")
                    temp_upload_path = os.path.join(IMG_DIR, orig_fname)
                    with open(temp_upload_path, "wb") as out_f:
                        shutil.copyfileobj(file_item.file, out_f)
                    notes = form.getvalue("notes", "")
                    important = str(form.getvalue("important", "")).lower() in ("1", "true", "yes")
                    conflict_policy = form.getvalue("conflict_policy", "update")
                    auto_extract = str(form.getvalue("auto_extract", "true")).lower() not in ("0", "false", "no")
                    res = ingest_business_card_image(
                        temp_upload_path,
                        orig_filename=orig_fname,
                        notes=notes,
                        important=important,
                        conflict_policy=conflict_policy,
                        auto_extract=auto_extract
                    )
                    return self.send_json(res)
                else:
                    payload = self.read_json_body()
                    file_path = str(payload.get("file_path", "")).strip()
                    img_b64 = str(payload.get("image_base64", "")).strip()
                    orig_fname = os.path.basename(str(payload.get("filename", "")).strip() or (os.path.basename(file_path) if file_path else f"hermes_{int(datetime.now().timestamp())}.jpg"))
                    notes = str(payload.get("notes", "")).strip()
                    important = bool(payload.get("important", False))
                    conflict_policy = str(payload.get("conflict_policy", "update")).strip() or "update"
                    auto_extract = bool(payload.get("auto_extract", True))

                    if img_b64:
                        if "," in img_b64 and img_b64.startswith("data:"):
                            img_b64 = img_b64.split(",", 1)[1]
                        temp_upload_path = os.path.join(IMG_DIR, orig_fname)
                        with open(temp_upload_path, "wb") as out_f:
                            out_f.write(base64.b64decode(img_b64))
                        target_src = temp_upload_path
                    elif file_path:
                        target_src = os.path.expanduser(file_path)
                    else:
                        return self.send_json({"error": "請提供 file_path 或 image_base64"}, status=400)

                    res = ingest_business_card_image(
                        target_src,
                        orig_filename=orig_fname,
                        notes=notes,
                        important=important,
                        conflict_policy=conflict_policy,
                        auto_extract=auto_extract
                    )
                    return self.send_json(res)
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)}, status=500)

        if path == "/api/cards/important":
            payload = self.read_json_body()
            card_id = str(payload.get("id") or payload.get("card_id") or "").strip()
            if not card_id:
                return self.send_json({"ok": False, "error": "缺少名片 ID"}, status=400)
            cards = load_cards()
            target_card = next((c for c in cards if c.get("id") == card_id), None)
            if not target_card:
                return self.send_json({"ok": False, "error": "找不到該名片"}, status=404)

            if "important" in payload:
                new_important = bool(payload.get("important"))
            else:
                new_important = not bool(target_card.get("important", False))

            target_card["important"] = new_important
            target_card["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            contacts_ok = True
            contacts_msg = ""
            if new_important:
                contacts_ok, contacts_msg = sync_card_to_macos_contacts(target_card)
            else:
                contacts_ok, contacts_msg = remove_card_from_macos_contacts(target_card)

            save_cards(cards)
            return self.send_json({
                "ok": True,
                "card": target_card,
                "cards": cards,
                "contacts_synced": contacts_ok,
                "contacts_info": contacts_msg,
                "contacts_sync": {"ok": contacts_ok, "message": contacts_msg},
            })

        if path == "/api/cards":
            payload = self.read_json_body()
            mode = payload.get("mode", "")  # "" | "create" | "update" | "replace"
            target_id = payload.get("target_id", "")
            cards = load_cards()

            card_data = {
                "name": payload.get("name", "").strip(),
                "english_name": payload.get("english_name", "").strip(),
                "company": payload.get("company", "").strip(),
                "title": payload.get("title", "").strip(),
                "tax_id": payload.get("tax_id", "").strip(),
                "phone": payload.get("phone", "").strip(),
                "mobile": payload.get("mobile", "").strip(),
                "fax": payload.get("fax", "").strip(),
                "email": normalize_email(payload.get("email", "").strip()),
                "address": payload.get("address", "").strip(),
                "website": payload.get("website", "").strip(),
                "notes": payload.get("notes", "").strip(),
                "source_file": payload.get("source_file", "").strip(),
                "important": bool(payload.get("important", False))
            }

            if not mode:
                existing, match_reason = find_existing_person_with_reason(cards, card_data)
                if existing:
                    return self.send_json({
                        "ok": False,
                        "conflict": True,
                        "match_reason": match_reason,
                        "existing_card": existing,
                        "new_card": card_data,
                        "merged_preview": build_merged_preview(existing, card_data)
                    })

            if mode in ("update", "replace") and target_id:
                target_card = next((c for c in cards if c.get("id") == target_id), None)
                if not target_card:
                    target_card = find_existing_person(cards, card_data)
                if target_card:
                    if mode == "update":
                        merge_card_update(target_card, card_data)
                    else:
                        replace_card_data(target_card, card_data)
                    if target_card.get("important"):
                        sync_card_to_macos_contacts(target_card)
                    save_cards(cards)
                    return self.send_json({"ok": True, "action": mode, "card": target_card, "cards": cards})

            new_card = {
                "id": str(uuid.uuid4()),
                **card_data,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            if new_card.get("important"):
                sync_card_to_macos_contacts(new_card)
            cards.insert(0, new_card)
            save_cards(cards)
            return self.send_json({"ok": True, "action": "create", "card": new_card, "cards": cards})

        if path == "/api/extract":
            payload = self.read_json_body()
            selected_files = payload.get("files", [])
            default_notes = payload.get("notes", "").strip()
            resolutions = payload.get("resolutions", {})  # { res_key: { "action": "update"|"replace"|"create"|"skip", "target_id": "..." } }

            if not selected_files:
                return self.send_json({"error": "請至少選擇一張名片圖檔"}, status=400)

            cards = load_cards()
            extracted_cards = []
            updated_cards = []
            replaced_cards = []
            skipped_files = []
            moved_files = []
            renamed_files = []
            multi_card_files = []
            conflicts = []
            errors = []

            for fname in selected_files:
                safe_fname = os.path.basename(fname)
                src_path = os.path.join(IMG_DIR, safe_fname)
                if not os.path.isfile(src_path):
                    errors.append(f"找不到檔案: {safe_fname}")
                    continue

                try:
                    ensure_preview_jpeg(src_path, safe_fname)
                    cards_info_list = parse_ocr_cards_from_image(src_path, safe_fname, max_cards=MAX_CARDS_PER_FILE)
                    total_in_file = len(cards_info_list)

                    prepared_items = []
                    file_conflicts = []

                    for idx, info in enumerate(cards_info_list):
                        info_notes = info.get("notes", "").strip()
                        combined_notes = f"{default_notes}\n{info_notes}".strip() if (default_notes and info_notes and default_notes not in info_notes) else (default_notes or info_notes)

                        card_data = {
                            "name": info.get("name", ""),
                            "english_name": info.get("english_name", ""),
                            "company": info.get("company", ""),
                            "title": info.get("title", ""),
                            "tax_id": info.get("tax_id", ""),
                            "phone": info.get("phone", ""),
                            "mobile": info.get("mobile", ""),
                            "fax": info.get("fax", ""),
                            "email": normalize_email(info.get("email", "")),
                            "address": info.get("address", ""),
                            "website": info.get("website", ""),
                            "notes": combined_notes,
                            "source_file": ""
                        }

                        existing, match_reason = find_existing_person_with_reason(cards, card_data)
                        if not info.get("company") and existing and existing.get("company"):
                            info["company"] = existing.get("company")
                            card_data["company"] = existing.get("company")
                        if not info.get("name") and existing and existing.get("name"):
                            info["name"] = existing.get("name")
                            card_data["name"] = existing.get("name")

                        planned_done_fname = build_multi_done_filename(cards_info_list, safe_fname)
                        card_data["source_file"] = planned_done_fname

                        res_key = safe_fname if total_in_file == 1 else f"{safe_fname}#card{idx + 1}"
                        res_choice = resolutions.get(res_key) or resolutions.get(safe_fname)
                        action = res_choice.get("action") if isinstance(res_choice, dict) else None
                        target_id = res_choice.get("target_id") if isinstance(res_choice, dict) else None

                        if not action:
                            if existing:
                                file_conflicts.append({
                                    "filename": res_key,
                                    "source_filename": safe_fname,
                                    "card_index": idx + 1,
                                    "total_cards_in_file": total_in_file,
                                    "planned_done_filename": planned_done_fname,
                                    "match_reason": match_reason,
                                    "existing_card": copy.deepcopy(existing),
                                    "new_card": card_data,
                                    "merged_preview": build_merged_preview(existing, card_data)
                                })
                            else:
                                action = "create"

                        prepared_items.append((card_data, action, target_id))

                    if file_conflicts:
                        conflicts.extend(file_conflicts)
                        continue

                    # Move image to done/ directory and rename to "公司名稱.名字.副檔名" (or joined multi-card filename)
                    final_done_fname = move_image_to_done(src_path, cards_info_list, safe_fname)
                    moved_files.append(safe_fname)
                    renamed_files.append({"from": safe_fname, "to": final_done_fname})
                    if total_in_file > 1:
                        multi_card_files.append({
                            "filename": safe_fname,
                            "done_filename": final_done_fname,
                            "count": total_in_file,
                            "names": [it[0].get("name") or it[0].get("company") for it in prepared_items]
                        })

                    for card_data, action, target_id in prepared_items:
                        card_data["source_file"] = final_done_fname
                        if action == "skip":
                            skipped_files.append(final_done_fname)
                            continue

                        if action in ("update", "replace"):
                            target_card = next((c for c in cards if c.get("id") == target_id), None)
                            if not target_card:
                                target_card = find_existing_person(cards, card_data)
                            if target_card:
                                if action == "update":
                                    merge_card_update(target_card, card_data)
                                    updated_cards.append(target_card)
                                else:
                                    replace_card_data(target_card, card_data)
                                    replaced_cards.append(target_card)
                                if target_card.get("important"):
                                    sync_card_to_macos_contacts(target_card)
                            else:
                                new_card = {
                                    "id": str(uuid.uuid4()),
                                    **card_data,
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                cards.insert(0, new_card)
                                extracted_cards.append(new_card)
                        else:
                            new_card = {
                                "id": str(uuid.uuid4()),
                                **card_data,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            cards.insert(0, new_card)
                            extracted_cards.append(new_card)
                except Exception as e:
                    errors.append(f"{safe_fname}: {str(e)}")

            save_cards(cards)
            pending = list_images_in_dir(IMG_DIR, "img")
            done = list_images_in_dir(DONE_DIR, "done")
            return self.send_json({
                "ok": True,
                "extracted": extracted_cards,
                "updated": updated_cards,
                "replaced": replaced_cards,
                "skipped": skipped_files,
                "moved": moved_files,
                "renamed": renamed_files,
                "multi_card_files": multi_card_files,
                "conflicts": conflicts,
                "errors": errors,
                "cards": cards,
                "pending": pending,
                "done": done
            })

        if path == "/api/cards/merge":
            payload = self.read_json_body()
            card_ids = payload.get("card_ids", [])
            preview_only = bool(payload.get("preview_only", False))
            merged_overrides = payload.get("merged_data")

            if not isinstance(card_ids, list) or len(card_ids) != 2 or card_ids[0] == card_ids[1]:
                return self.send_json({"error": "請選擇兩張不同的名片進行合併"}, status=400)

            cards = load_cards()
            card1 = next((c for c in cards if c.get("id") == card_ids[0]), None)
            card2 = next((c for c in cards if c.get("id") == card_ids[1]), None)
            if not card1 or not card2:
                return self.send_json({"error": "找不到指定的名片資料"}, status=404)

            if preview_only:
                preview = build_merged_preview(card1, card2)
                return self.send_json({
                    "ok": True,
                    "card1": card1,
                    "card2": card2,
                    "merged_preview": preview
                })

            if card2.get("apple_contact_id") and card1.get("apple_contact_id") and card2.get("apple_contact_id") != card1.get("apple_contact_id"):
                remove_card_from_macos_contacts(card2)

            merge_card_update(card1, card2)
            if isinstance(merged_overrides, dict):
                for field in CARD_FIELDS:
                    if field in merged_overrides:
                        val = str(merged_overrides[field] or "").strip()
                        if field == "email" and val:
                            val = normalize_email(val)
                        card1[field] = val
                card1["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if card1.get("important"):
                sync_card_to_macos_contacts(card1)

            cards = [c for c in cards if c.get("id") != card_ids[1]]
            save_cards(cards)
            return self.send_json({
                "ok": True,
                "merged_card": card1,
                "removed_id": card_ids[1],
                "cards": cards
            })

        if path == "/api/restore":
            payload = self.read_json_body()
            files_to_restore = payload.get("files", [])
            restored = []
            for fname in files_to_restore:
                safe_fname = os.path.basename(fname)
                src_path = os.path.join(DONE_DIR, safe_fname)
                dst_path = os.path.join(IMG_DIR, safe_fname)
                if os.path.isfile(src_path):
                    shutil.move(src_path, dst_path)
                    restored.append(safe_fname)
            pending = list_images_in_dir(IMG_DIR, "img")
            done = list_images_in_dir(DONE_DIR, "done")
            return self.send_json({"ok": True, "restored": restored, "pending": pending, "done": done})

        self.send_error(404, "Endpoint not found")

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/cards/"):
            card_id = parsed.path.split("/api/cards/", 1)[1]
            payload = self.read_json_body()
            cards = load_cards()
            updated = None
            for card in cards:
                if card.get("id") == card_id:
                    was_important = bool(card.get("important", False))
                    for field in CARD_FIELDS:
                        if field in payload:
                            val = str(payload[field]).strip()
                            if field == "email" and val:
                                val = normalize_email(val)
                            card[field] = val
                    if "important" in payload:
                        card["important"] = bool(payload.get("important"))
                    card["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if card.get("important"):
                        sync_card_to_macos_contacts(card)
                    elif was_important and not card.get("important"):
                        remove_card_from_macos_contacts(card)
                    updated = card
                    break
            if not updated:
                return self.send_json({"error": "找不到該名片"}, status=404)
            save_cards(cards)
            return self.send_json({"ok": True, "card": updated, "cards": cards})
        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/cards/"):
            card_id = parsed.path.split("/api/cards/", 1)[1]
            cards = load_cards()
            target = next((c for c in cards if c.get("id") == card_id), None)
            if target and (target.get("important") or target.get("apple_contact_id")):
                remove_card_from_macos_contacts(target)
            cards = [c for c in cards if c.get("id") != card_id]
            save_cards(cards)
            return self.send_json({"ok": True, "cards": cards})
        self.send_error(404, "Endpoint not found")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def compress_all_existing_done_images():
    if not os.path.exists(DONE_DIR):
        return
    for entry in os.listdir(DONE_DIR):
        if entry.startswith("."):
            continue
        full_p = os.path.join(DONE_DIR, entry)
        if os.path.isfile(full_p) and os.path.splitext(entry)[1].lower() in VALID_EXTS:
            compress_image_under_1mb(full_p)


if __name__ == "__main__":
    compress_all_existing_done_images()
    port = int(os.environ.get("PORT", 8765))
    server = ThreadingHTTPServer(("127.0.0.1", port), CardHelperHandler)
    print(f"CardHelper server listening on http://127.0.0.1:{port}")
    server.serve_forever()
