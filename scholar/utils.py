"""Semantic Scholar API 通用工具函数"""
import csv
import time
import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"


def request_with_retry(url, params=None, max_retries=10):
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


def sort_papers(papers, paper_key, strategy="citation"):
    """
    统一的论文排序逻辑 (多维排序，strategy 指定首要维度)
    默认优先级: citation > influential > year
    strategy: "citation" | "year" | "influential" (提升到第一位)
    """
    def key_fn(x):
        p = x.get(paper_key) or {}
        dims = {
            "citation": p.get("citationCount") or 0,
            "influential": bool(x.get("isInfluential")),
            "year": p.get("year") or 0,
        }
        # 默认顺序，将 strategy 提升到首位
        order = ["citation", "influential", "year"]
        if strategy in order:
            order.remove(strategy)
            order.insert(0, strategy)
        return tuple(dims[k] for k in order)
    
    papers.sort(key=key_fn, reverse=True)
    return papers


def fetch_relations(paper_id, relation_type, sort_by="citation", 
                     influential_only=False, since_year=None, until_year=None, 
                     num_results=None, fetch_limit=10000):
    """
    获取论文关系数据（citations 或 references）
    relation_type: "citations" | "references"
    sort_by: "citation" | "year" | "influential"
    influential_only: 是否只返回有影响力的论文
    since_year / until_year: 年份范围限制 (含边界)
    num_results: 返回结果上限 (None 表示不限制)
    fetch_limit: 从 API 获取的数据量上限 (默认 10000)
    """
    paper_key = "citingPaper" if relation_type == "citations" else "citedPaper"
    fields = f"isInfluential,{paper_key}.paperId,{paper_key}.title,{paper_key}.year,{paper_key}.citationCount"
    
    print(f"📥 获取 {relation_type}...")
    results, offset = [], 0
    
    while len(results) < fetch_limit:
        data = request_with_retry(
            f"{BASE_URL}/{paper_id}/{relation_type}",
            {"fields": fields, "offset": offset, "limit": 1000}
        )
        batch = data.get("data") if data else None
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
        print(f"   已获取 {len(results)} 条...")
        time.sleep(1)
    
    # 过滤 + 排序 (filter 在前可减少排序开销)
    def passes_filter(x):
        if influential_only and not x.get("isInfluential"):
            return False
        year = (x.get(paper_key) or {}).get("year")
        if since_year and (not year or year < since_year):
            return False
        if until_year and (not year or year > until_year):
            return False
        return True
    
    results = [x for x in results if passes_filter(x)]
    results = sort_papers(results, paper_key, strategy=sort_by)[:num_results]
    
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
