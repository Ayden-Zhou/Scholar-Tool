"""使用关键词搜索论文 (基于 sortgs)"""
import subprocess
import fire


def main(
    keyword: str,
    num_results: int = 10,
    fetch_limit: int = 100,
    sort_by: str = "cit/year",  # Citations | cit/year
    since_year: int = None,
    until_year: int = None,
    save_results: bool = False,
    save_path: str = None,
):
    """
    使用关键词搜索 Google Scholar 论文
    
    Args:
        keyword: 搜索关键词 (精确匹配用单引号: "'exact phrase'")
        num_results: 打印结果数量
        fetch_limit: 获取/存储结果数量上限
        sort_by: 排序方式 - Citations | cit/year
        since_year: 筛选起始年份
        until_year: 筛选截止年份
        save_results: 是否保存为 CSV
        save_path: 输出目录 (默认当前目录)
    
    Requires:
        pip install sortgs
    """
    cmd = ["sortgs", keyword, "--nresults", str(fetch_limit), "--sortby", sort_by]
    
    if since_year:
        cmd.extend(["--startyear", str(since_year)])
    if until_year:
        cmd.extend(["--endyear", str(until_year)])
    if save_results:
        cmd.extend(["--csvpath", save_path or "."])
    else:
        cmd.append("--notsavecsv")
    
    print(f"🔎 搜索: {keyword} (获取 {fetch_limit} 条, 打印 {num_results} 条)")
    
    # 捕获 sortgs 输出，只打印前 num_results 行（+2 为表头和分隔线）
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    for line in lines[:num_results + 2]:  # 表头 + 分隔线 + 数据行
        print(line)
    if len(lines) > num_results + 2:
        print(f"... (共 {len(lines) - 2} 条结果，已显示前 {num_results} 条)")


if __name__ == "__main__":
    fire.Fire(main)
