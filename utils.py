"""Semantic Scholar API 通用工具函数"""
import csv
import time
import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"


def request_with_retry(url, params=None, max_retries=5):
    """带重试机制的 GET 请求，自动处理 429 限流"""
    for i in range(max_retries):
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = (i + 1) * 3
                print(f"⚠️ 限流中，等待 {wait}s...")
                time.sleep(wait)
                continue
            return None
        except requests.RequestException as e:
            print(f"请求异常: {e}")
            return None
    print("❌ 重试次数耗尽")
    return None


def search_paper(title):
    """通过标题搜索论文，返回 (paper_id, info) 或 (None, None)"""
    print(f"🔎 搜索: '{title}'")
    data = request_with_retry(
        f"{BASE_URL}/search",
        {"query": title, "limit": 1, "fields": "paperId,title,year"}
    )
    if data and data.get("data"):
        p = data["data"][0]
        return p["paperId"], f"{p['title']} ({p.get('year', 'N/A')})"
    print("❌ 未找到")
    return None, None


def fetch_relations(paper_id, relation_type, sort_by="citation"):
    """
    获取论文关系数据（citations 或 references）
    relation_type: "citations" | "references"
    sort_by: "citation" | "year" | "influential"
    """
    paper_key = "citingPaper" if relation_type == "citations" else "citedPaper"
    fields = f"isInfluential,{paper_key}.title,{paper_key}.year,{paper_key}.citationCount"
    
    print(f"📥 获取 {relation_type}...")
    results, offset = [], 0
    
    while True:
        data = request_with_retry(
            f"{BASE_URL}/{paper_id}/{relation_type}",
            {"fields": fields, "offset": offset, "limit": 1000}
        )
        if not data or "data" not in data:
            break
        batch = data["data"]
        results.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
        print(f"   已获取 {len(results)} 条...")
        time.sleep(1)
    
    # 排序
    sort_keys = {
        "citation": lambda x: (x.get(paper_key) or {}).get("citationCount") or 0,
        "year": lambda x: (x.get(paper_key) or {}).get("year") or 0,
        "influential": lambda x: (x.get("isInfluential", False), (x.get(paper_key) or {}).get("citationCount") or 0),
    }
    results.sort(key=sort_keys.get(sort_by, sort_keys["citation"]), reverse=True)
    
    print(f"📊 共 {len(results)} 条")
    return results, paper_key


def save_to_csv(data, paper_key, output_path):
    """保存结果到 CSV"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["isInfluential", "citationCount", "year", "title"])
        writer.writeheader()
        for item in data:
            p = item.get(paper_key) or {}
            writer.writerow({
                "isInfluential": bool(item.get("isInfluential")),
                "citationCount": p.get("citationCount") or 0,
                "year": p.get("year", "N/A"),
                "title": p.get("title", "Unknown")
            })
    print(f"✅ 已保存到 {output_path}")



def safe_filename(title):
    """生成安全的文件名"""
    return "".join(c if c.isalnum() or c in " -_" else "" for c in title).replace(" ", "_")


def print_results(data, paper_key):
    """打印结果表格"""
    if not data:
        print("无结果")
        return
    
    print(f"\n{'#':<4} {'Year':<6} {'Citations':<10} {'Inf':<4} Title")
    print("-" * 80)
    for i, item in enumerate(data, 1):
        p = item.get(paper_key) or {}
        inf = "✓" if item.get("isInfluential") else ""
        print(f"{i:<4} {p.get('year', 'N/A'):<6} {p.get('citationCount') or 0:<10} {inf:<4} {(p.get('title') or 'Unknown')[:50]}")
