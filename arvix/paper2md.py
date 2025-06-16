import json
import argparse
from collections import defaultdict

def render_to_markdown(jsonl_path, output_path):
    """将JSONL文件批量渲染为带分类目录的Markdown格式"""
    # 第一阶段：读取所有数据并统计分类
    all_papers = []
    category_counter = defaultdict(int)
    category_rank = {"cs.AI": 1, "cs.CL": 2, "cs.HC": 3}  # 自定义分类排序
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            try:
                paper = json.loads(line)
                # 获取主分类（第一个分类）
                main_cate = paper["categories"][0] if paper["categories"] else "Uncategorized"
                
                # 添加全局序号
                paper["global_idx"] = idx
                all_papers.append(paper)
                
                # 分类计数
                category_counter[main_cate] += 1
                
            except (KeyError, json.JSONDecodeError) as e:
                print(f"处理第{idx}条数据时出错: {str(e)}")
    
    # 第二阶段：生成目录和内容
    with open(output_path, 'w', encoding='utf-8') as f_out:
        # 生成分类目录
        f_out.write("<div id='toc'></div>\n\n")
        f_out.write("# 论文分类目录\n\n")
        
        # 按自定义顺序排序分类
        sorted_categories = sorted(
            category_counter.keys(),
            key=lambda x: (category_rank.get(x, 100), x)  # 未定义分类排在后面
        )
        
        # 写入目录
        for cate in sorted_categories:
            count = category_counter[cate]
            f_out.write(f"- **[{cate}](#{cate.replace('.', '')})** ({count}篇)\n")
        f_out.write("\n---\n\n")
        
        # 按分类分组论文
        papers_by_category = defaultdict(list)
        for paper in all_papers:
            main_cate = paper["categories"][0] if paper["categories"] else "Uncategorized"
            papers_by_category[main_cate].append(paper)
        
        # 按分类写入内容
        for cate in sorted_categories:
            if cate not in papers_by_category:
                continue
                
            # 分类标题
            f_out.write(f"## {cate} <a id='{cate.replace('.', '')}'></a>\n\n")
            f_out.write(f"*本分类共有 {category_counter[cate]} 篇论文*\n\n")
            
            # 写入该分类下的所有论文
            for paper in papers_by_category[cate]:
                # 准备模板变量
                variables = {
                    "idx": paper["global_idx"],
                    "title": paper.get("title_zh", paper["title"]),
                    "url": paper["abs"],
                    "authors": ", ".join(paper["authors"]),
                    "cate": cate,
                    "tldr": paper["AI"]["task"],
                    "motivation": paper["AI"]["motivation"],
                    "method": paper["AI"]["method"],
                    "result": paper["AI"]["result"],
                    "conclusion": paper["AI"]["conclusion"],
                    "summary": paper["summary"].replace("\n", " ")
                }
                
                # 渲染单个论文模板
                md_template = f"""
### [{variables['idx']}] [{variables['title']}]({variables['url']})
*{variables['authors']}*

Main category: {variables['cate']}

TL;DR: {variables['tldr']}

<details>
  <summary>Details</summary>
Motivation: {variables['motivation']}

Method: {variables['method']}

Result: {variables['result']}

Conclusion: {variables['conclusion']}

Abstract: {variables['summary']}
</details>

"""
                f_out.write(md_template)
            
            # 添加返回目录链接
            f_out.write(f"[返回目录](#toc)\n\n---\n\n")
            

# --- 主程序入口 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to the jsonline file")
    args = parser.parse_args()
    original_jsonl_file = args.data
    md_file = original_jsonl_file.replace('_zh.jsonl', '.md')
    render_to_markdown(original_jsonl_file, md_file)