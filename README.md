# Scholar Tool

[English](#english) | [中文](#中文)

---

## English

A command-line tool for academic paper analysis using Semantic Scholar API.

### Features

- **search** - Search papers on Google Scholar by keywords
- **relation** - Query citations and references of a paper
- **graph** - Generate interactive citation network visualization

### Installation

```bash
pip install git+https://github.com/Ayden-Zhou/Scholar-Tool.git
```

### Usage

```bash
# Search papers by keyword
scholar search "machine learning" --num_results=10

# Query references of a paper
scholar relation --title="Attention Is All You Need" --find=reference

# Generate citation graph
scholar graph --title="Attention Is All You Need" --depth=2
```

### Acknowledgements

This project uses the following open-source libraries:

- [sortgs](https://github.com/WittmannF/sort-google-scholar) by Fernando Wittmann - MIT License  
  Used for Google Scholar search functionality.

---

## 中文

基于 Semantic Scholar API 的论文分析命令行工具。

### 功能

- **search** - 使用关键词搜索 Google Scholar 论文
- **relation** - 查询论文的引用和参考文献
- **graph** - 生成交互式引文网络可视化图

### 安装

```bash
pip install git+https://github.com/Ayden-Zhou/Scholar-Tool.git
```

### 使用示例

```bash
# 关键词搜索论文
scholar search "machine learning" --num_results=10

# 查询论文的参考文献
scholar relation --title="Attention Is All You Need" --find=reference

# 生成引文图谱
scholar graph --title="Attention Is All You Need" --depth=2
```

### 致谢

本项目使用了以下开源库：

- [sortgs](https://github.com/WittmannF/sort-google-scholar) by Fernando Wittmann - MIT License  
  用于 Google Scholar 搜索功能。

---

## License

MIT License

