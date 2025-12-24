"""
graph_main.py: 基于 Semantic Scholar 的论文关系图谱生成器

实现逻辑：
1. 搜索与初始化：
   - 根据标题搜索种子论文，获取 ID 和基础信息。
   - 初始化有向图 (NetworkX)，用于存储引文网络。

2. 图谱构建 (BFS 策略)：
   - 采用广度优先搜索，从种子节点逐层向外扩展。
   - 支持三种模式：
     - references (溯源): 查找当前节点引用的论文 (箭头指向过去)。
     - citations (影响): 查找引用了当前节点的论文 (箭头指向未来/种子)。
     - all (混合): 每个节点同时向 references 和 citations 两个方向扩展。
       depth=2 时可发现 seed->ref->cite 和 seed->cite->ref 的混合路径，
       从而挖掘"共引"(Co-citation) 和"耦合"(Bibliographic Coupling) 关系。
   - 每一层处理：
     - 针对当前节点，通过 API 获取关联论文列表。
     - 由于 API 默认不排序，代码请求 limit=1000 条数据到本地。
     - 本地排序策略：优先 'isInfluential' (关键引用)，其次按 'citationCount' 降序。
     - 截取 Top N (width) 个节点作为下一层候选，加入队列。

3. 内部连线致密化 (Densification)：
   - 在 BFS 过程中，缓存每个节点的 references 列表。
   - BFS 结束后，遍历缓存，补全图中节点之间的所有引用关系。

4. 节点与边样式：
   - 节点颜色/大小随层级 (Layer) 递减：种子(红/大) -> Layer1(深蓝/中) -> Layer2(浅蓝/小)。
   - 边样式：关键引用显示为橙色粗线，普通引用为灰色细线。

5. 容错与限制：
   - 内置 API 限流处理 (429 Retry)。
   - 对 API 返回的空数据进行防御性检查，防止崩溃。
   - 通过 visited 集合避免环路和重复访问。

6. 输出：
   - 使用 Pyvis 生成交互式 HTML 文件，应用 Force Atlas 2 物理布局算法。
"""
import fire
import time
import math
import networkx as nx
from pyvis.network import Network
import webbrowser
import os
from typing import List

# 直接复用 utils.py 的基础工具
from scholar.utils import search_paper, request_with_retry, fetch_relations, BASE_URL, safe_filename


class PaperGraph:
    def __init__(self):
        self.G = nx.DiGraph()
        self.visited = set()
        self._cache = {}  # {(pid, relation_type): [(paper_info, is_influential), ...]}

    def add_node(self, paper_info, layer):
        """添加节点，根据层级设置颜色和大小"""
        if not paper_info:
            return False
            
        pid = paper_info.get('paperId')
        if not pid:
            return False
        
        if self.G.has_node(pid):
            return True
        
        title = paper_info.get('title', 'Unknown')
        year = paper_info.get('year', 'N/A')
        citations = paper_info.get('citationCount') or 0
        
        # Size 与引用量成正比 (对数缩放，避免过大)
        size = 10 + math.log10(max(citations, 1)) * 5
        
        # 颜色：默认灰色，种子节点蓝色轮廓，点击后变蓝
        color = {
            "background": "#aaaaaa",
            "border": "#0066ff" if layer == 0 else "#888888",
            "highlight": {"background": "#0066ff", "border": "#0044cc"},
        }
        border_width = 3 if layer == 0 else 1

        short_label = (title[:20] + '...') if len(title) > 20 else title
        tooltip = f"<b>{title}</b><br>Year: {year}<br>Citations: {citations}"

        self.G.add_node(pid, label=short_label, title=tooltip, 
                        color=color, size=size, borderWidth=border_width)
        return True

    def _get_relations(self, paper_id, relation_type, influential_only=True, 
                        since_year=None, until_year=None, fetch_limit=10000):
        """获取并缓存完整的 influential relations (references 或 citations)"""
        # 缓存键包含所有过滤参数，避免不同参数返回错误结果
        cache_key = (paper_id, relation_type, influential_only, since_year, until_year)
        if cache_key not in self._cache:
            items, key = fetch_relations(
                paper_id, relation_type, sort_by="citation", influential_only=influential_only,
                since_year=since_year, until_year=until_year, fetch_limit=fetch_limit
            )
            # 保留原始的 isInfluential 值
            self._cache[cache_key] = [(item.get(key), item.get("isInfluential", False)) for item in items]
        return self._cache[cache_key]

    def _add_edge(self, source, target, is_influential):
        """添加带样式的有向边"""
        if not self.G.has_node(source) or not self.G.has_node(target):
            return
        if self.G.has_edge(source, target):
            return
        edge_color = "#666666" if is_influential else "#dddddd"
        edge_width = 3 if is_influential else 1
        self.G.add_edge(source, target, color=edge_color, width=edge_width)

    def build(self, start_title, mode="references", depth=2, width=(4, 2),
               influential_only=True, since_year=None, until_year=None, fetch_limit=10000):
        """
        构建图谱核心逻辑 (BFS + 内部连线补全)
        :param width: 每层扩展的节点数。int 或 list/tuple (如 [4, 2] 表示第一层4个，第二层2个)
        """
        # 规范化 width 为列表，处理 int 输入
        widths = [width] if isinstance(width, int) else width
        
        # 1. 搜索种子文章
        root_id, root_info_str = search_paper(start_title)
        if not root_id:
            return
        
        print(f"🌟 种子节点: {root_info_str}")
        print(f"🕸️ 开始构建图谱 (深度: {depth}, 每层分支: {widths}, 模式: {mode})...")

        # 添加种子节点
        root_data = request_with_retry(f"{BASE_URL}/{root_id}", {"fields": "paperId,title,year,citationCount"})
        if not root_data:
            print("❌ 获取种子节点详情失败，请稍后重试")
            return

        self.add_node(root_data, layer=0)
        self.visited.add(root_id)

        # 2. BFS 遍历
        # mode="all" 时，每个节点同时向 references 和 citations 两个方向扩展
        # 这样 depth=2 可以发现 seed->ref->cite 和 seed->cite->ref 的混合路径
        directions = ["references", "citations"] if mode == "all" else [mode]
        queue = [(root_id, 0)]
        
        while queue:
            current_pid, current_depth = queue.pop(0)

            if current_depth >= depth:
                continue

            # 在当前节点，遍历所有需要探索的方向
            for m in directions:
                print(f"   🔎 [{m}][L{current_depth}->L{current_depth+1}] {current_pid[:8]}...")
                
                # 确定当前层的宽度 (如果层数超出列表长度，复用最后一个值)
                cur_width = widths[min(current_depth, len(widths) - 1)]

                # 从完整缓存中取前 cur_width 个
                items = [(info, inf) for info, inf in self._get_relations(
                    current_pid, m, influential_only=influential_only,
                    since_year=since_year, until_year=until_year, fetch_limit=fetch_limit
                )[:cur_width] if info]

                for p_info, is_influential in items:
                    if not p_info or not p_info.get('paperId'):
                        continue
                    target_id = p_info['paperId']

                    self.add_node(p_info, layer=current_depth + 1)
                    if m == "references":
                        self._add_edge(current_pid, target_id, is_influential)
                    else:
                        self._add_edge(target_id, current_pid, is_influential)

                    if target_id not in self.visited:
                        self.visited.add(target_id)
                        if current_depth + 1 < depth:
                            queue.append((target_id, current_depth + 1))
            
            time.sleep(0.5)

        # 3. 补全内部连线 (使用完整缓存，不限 width)
        print(f"🔗 补全内部连线...")
        nodes = set(self.G.nodes())
        for pid in nodes:
            for ref_info, is_influential in self._get_relations(
                pid, "references", influential_only=influential_only,
                since_year=since_year, until_year=until_year, fetch_limit=fetch_limit
            ):
                ref_id = ref_info.get('paperId') if ref_info else None
                if ref_id in nodes:
                    self._add_edge(pid, ref_id, is_influential)

        print(f"📊 图谱完成: {self.G.number_of_nodes()} 节点, {self.G.number_of_edges()} 边")

    def save(self, filename):
        """生成交互式 HTML"""
        if self.G.number_of_nodes() == 0:
            print("❌ 图为空")
            return

        print(f"🎨 正在绘制...")
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
        net.from_nx(self.G)
        net.force_atlas_2based(gravity=-50, spring_length=100, spring_strength=0.08)
        
        net.save_graph(filename)
        print(f"✅ 文件已生成: {filename}")
        try:
            webbrowser.open('file://' + os.path.realpath(filename))
        except:
            pass


def main(title: str = "Attention Is All You Need", 
        mode: str = "all", 
        depth: int = 2, 
        width: int | List[int] = [4, 2],
        influential_only: bool = True, 
        since_year: int = None, 
        until_year: int = None,
        fetch_limit: int = 10000,
        save_results: bool = True,
        save_path: str = None) -> None:
    """
    生成论文关系图谱
    
    Args:
        title: 论文标题
        mode: references (参考文献) | citations (引用) | all (双向)
        depth: 搜索深度 (建议 2)
        width: 每层分支数，int 或 list (如 [4, 2])
        influential_only: 是否只保留关键引用
        since_year: 筛选起始年份 (含)
        until_year: 筛选截止年份 (含)
        fetch_limit: API 获取数据上限
        save_results: 是否保存为 HTML 文件
        save_path: 输出目录 (默认当前目录)
    """
    g = PaperGraph()
    g.build(title, mode, depth, width, influential_only, since_year, until_year, fetch_limit)
    if save_results:
        output_dir = save_path or "."
        g.save(f"{output_dir}/graph_{mode}_{safe_filename(title)}.html")


if __name__ == "__main__":
    fire.Fire(main)
