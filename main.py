"""Semantic Scholar 论文关系查询工具"""
import fire
from utils import search_paper, fetch_relations, save_to_csv, safe_filename, print_results


def main(
    title: str = "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning",
    find: str = "reference",
    save_csv: bool = False,
    num_results: int = 10,
    influential_only: bool = False,
    sort_by: str = "citation",  # citation | year | influential
):
    """
    查询论文的引用或参考文献
    
    Args:
        title: 论文标题
        find: "reference" (参考文献) 或 "citation" (引用)
        save_csv: 是否保存为 CSV 文件
        num_results: 打印结果数量 (0 表示不打印)
        influential_only: 是否只显示有影响力的论文
        sort_by: 排序方式 - citation(引用数) | year(年份) | influential(影响力)
    """
    if find not in ("reference", "citation"):
        print("❌ find 参数必须是 'reference' 或 'citation'")
        return

    paper_id, info = search_paper(title)
    if not paper_id:
        return
    
    print(f"✅ 已锁定: {info}\n" + "-" * 50)
    
    relation_type = "references" if find == "reference" else "citations"
    data, paper_key = fetch_relations(paper_id, relation_type, sort_by)
    
    # 过滤 influential
    if influential_only:
        data = [x for x in data if x.get("isInfluential")]
    
    # 打印结果
    if num_results > 0:
        print_results(data[:num_results], paper_key)
    
    # 保存 CSV
    if save_csv:
        save_to_csv(data, paper_key, f"results/{relation_type}_{safe_filename(title)}.csv")


if __name__ == "__main__":
    fire.Fire(main)
