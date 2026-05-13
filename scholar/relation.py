"""Semantic Scholar 论文关系查询工具"""
import re

import fire
from scholar.utils import search_paper, fetch_relations, save_to_csv, safe_filename, print_results


ARXIV_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf|html|e-print)/)?"
    r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})"
    r"(?:v\d+)?(?:\.pdf)?/?$",
    re.IGNORECASE,
)


def parse_arxiv(value: str) -> str:
    text = value.strip().split("?", 1)[0].split("#", 1)[0]
    if text.lower().startswith("arxiv:"):
        text = text.split(":", 1)[1]

    match = ARXIV_RE.search(text)
    if not match:
        raise ValueError(f"无法解析 arXiv ID: {value}")
    return f"ARXIV:{match.group(1)}"


def main(
    title: str = "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning",
    arxiv: str = None,
    find: str = "reference",
    num_results: int = 10,
    fetch_limit: int = 10000,
    influential_only: bool = False,
    sort_by: str = "citation",  # citation | year | influential
    since_year: int = None,
    until_year: int = None,
    save_results: bool = False,
    save_path: str = None,
):
    """
    查询论文的引用或参考文献
    
    Args:
        title: 论文标题
        arxiv: arXiv ID 或 URL；提供时跳过标题搜索
        find: "reference" (参考文献) 或 "citation" (引用)
        num_results: 打印结果数量 (0 表示不打印)
        fetch_limit: 获取/存储结果数量上限
        influential_only: 是否只显示有影响力的论文
        sort_by: 排序方式 - citation(引用数) | year(年份) | influential(影响力)
        since_year: 从某年起 (含)
        until_year: 直到某年 (含)
        save_results: 是否保存为 CSV 文件
        save_path: 输出目录 (默认当前目录)
    """
    if find not in ("reference", "citation"):
        print("❌ find 参数必须是 'reference' 或 'citation'")
        return

    if arxiv:
        try:
            paper_id, info = parse_arxiv(arxiv), arxiv
        except ValueError as e:
            print(f"❌ {e}")
            return
    else:
        paper_id, info = search_paper(title)
        if not paper_id:
            return
    
    print(f"✅ 已锁定: {info}\n" + "-" * 50)
    
    relation_type = "references" if find == "reference" else "citations"
    data, paper_key = fetch_relations(
        paper_id, relation_type, sort_by, influential_only, since_year, until_year,
        fetch_limit=fetch_limit
    )
    
    # 打印结果
    if num_results > 0:
        print_results(data[:num_results], paper_key)
    
    # 保存 CSV
    if save_results:
        output_dir = save_path or "."
        save_to_csv(data, paper_key, f"{output_dir}/{relation_type}_{safe_filename(info)}.csv")


if __name__ == "__main__":
    fire.Fire(main)
