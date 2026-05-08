#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCC 每日標案雷達
抓取近 3 天「電動機車」「機車租賃」「機車採購」相關最新標案
用 seen_tenders.json 去重，只回傳「新」標案
"""

import urllib.request, json, urllib.parse, time, os, sys
from datetime import datetime, timedelta

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE  = os.path.join(BASE_DIR, 'seen_tenders.json')

# 監測關鍵字 + 過濾規則
WATCH_KEYWORDS = ['電動機車', '機車']
MUST_CONTAIN   = ['電動機車', '機車租賃', '租賃機車', '機車出租',
                  '公務機車', '警用機車', '巡邏機車', '保林機車',
                  '採購機車', '機車採購', '機車購置', '機車汰換',
                  '電動二輪', '重型機車', '輕型機車', '打檔機車',
                  '打檔型', '無段變速', '機車2輛', '機車1輛',
                  '機車3輛', '機車4輛', '機車5輛', '機車6輛',
                  '機車2台', '機車1台', '機車3台', '機車4台',
                  '機車5台', '機車6台', '機車保險', '機車標售',
                  '機車汰舊', '報廢公務機車', '廢棄公務機車',
                  '機車責任保險', '機車維修', '機車保養']
EXCLUDE        = ['停車棚', '停車場', '停車格', '路面標線', '車棚',
                  '停車設施', '機車道', '停車彎', '停車位', '停車庫',
                  '柴電機車', '內燃機車', '軌道機車', '鐵路機車',
                  '機車練習場', '停車場設計', '機車停車']  # 台鐵柴電機車排除

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen), f, ensure_ascii=False)

def fetch_page(keyword, page=1):
    encoded = urllib.parse.quote(keyword)
    url = f"https://pcc-api.openfun.app/api/searchbytitle?query={encoded}&page={page}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))

def is_relevant(title):
    """判斷標案是否真正與機車採購/租賃有關"""
    if any(ex in title for ex in EXCLUDE):
        return False
    if any(mc in title for mc in MUST_CONTAIN):
        return True
    return False

def fetch_recent(days=3):
    """抓取近 N 天的新標案"""
    cutoff = int((datetime.now() - timedelta(days=days)).strftime('%Y%m%d'))
    results = {}

    for kw in WATCH_KEYWORDS:
        try:
            data = fetch_page(kw, 1)
        except Exception as e:
            print(f"  ⚠️ 抓取「{kw}」失敗: {e}")
            continue

        for r in data.get('records', []):
            d = r.get('date', 0)
            if d < cutoff:
                break  # 降序排列，可提前中止
            title = r.get('brief', {}).get('title', '')
            if not title or not is_relevant(title):
                continue
            key = r.get('filename', '')
            if key and key not in results:
                results[key] = {
                    'filename': key,
                    'date': str(d),
                    'title': title,
                    'type': r.get('brief', {}).get('type', ''),
                    'unit': r.get('unit_name', ''),
                    'job_number': r.get('job_number', ''),
                    'url': (lambda raw: f"https://openfunltd.github.io/pcc-viewer/tender.html?unit_id={raw.split('/')[3]}&job_number={r.get('job_number', '')}" if len(raw.split('/')) > 3 else f"https://openfunltd.github.io/pcc-viewer/")(r.get('url', '')),
                }
        time.sleep(0.3)

    return results

def run(days=3):
    seen      = load_seen()
    fetched   = fetch_recent(days)
    new_items = {k: v for k, v in fetched.items() if k not in seen}

    # 更新 seen（保留最近 1000 筆，避免無限增長）
    all_seen = seen | set(fetched.keys())
    if len(all_seen) > 1000:
        all_seen = set(list(all_seen)[-1000:])
    save_seen(all_seen)

    # 排序：日期降序
    sorted_new = sorted(new_items.values(), key=lambda x: -int(x['date']))

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_fetched': len(fetched),
        'new_count': len(sorted_new),
        'items': sorted_new
    }

if __name__ == '__main__':
    result = run(days=3)
    print(f"\n📡 PCC 標案雷達 — {result['generated_at']}")
    print(f"   掃描: {result['total_fetched']} 筆  ·  新增: {result['new_count']} 筆\n")
    for i, item in enumerate(result['items'], 1):
        d = item['date']
        dstr = f"{d[:4]}/{d[4:6]}/{d[6:]}"
        print(f"  {i:2d}. [{dstr}] {item['title']}")
        print(f"      {item['unit']}  ·  {item['type']}")
        print()

    # 輸出 JSON 供 HTML 讀取
    out_path = os.path.join(BASE_DIR, 'pcc_radar.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✓ 已輸出 pcc_radar.json")
