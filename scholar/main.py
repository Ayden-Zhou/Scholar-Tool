"""
Scholar: Semantic Scholar 论文分析工具

Usage:
    scholar graph --title="Attention Is All You Need" --since_year=2020
    scholar relation --title="..." --find=citation --influential_only=False
"""
import fire
from scholar.relation import main as relation
from scholar.graph import main as graph
from scholar.kw_search import main as kw_search


class CLI:
    """
    Scholar: Semantic Scholar 论文分析工具
    
    Commands:
        search    使用关键词搜索论文 (Google Scholar)
        relation  查询论文的引用或参考文献 (Semantic Scholar)
        graph     生成论文关系图谱 (Semantic Scholar)
    
    Examples:
        scholar search "machine learning" --since_year=2020
        scholar graph --title="Attention Is All You Need"
        scholar relation --title="..." --find=citation
    """
    search = staticmethod(kw_search)
    relation = staticmethod(relation)
    graph = staticmethod(graph)


def cli():
    fire.Fire(CLI)


if __name__ == "__main__":
    cli()
