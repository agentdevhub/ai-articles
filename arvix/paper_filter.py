import arxiv
import argparse
import json
from datetime import datetime, timedelta
import time
from typing import List, Dict, Set


class ArxivLLMAgentFilter:
    def __init__(self):
        """
        初始化客户端和关键词。
        """
        self.client = arxiv.Client()
        # 更细化的 Agent/LLM 相关主题
        self.topic_keywords = {
            # 1. Agentic AI核心概念 (2025年最热门)
            'Agentic系统': [
                'Agentic AI', 'Agentic System', 'Autonomous Agents', 
                'Goal-Driven Agents', 'Self-Governing Agents',
                'Agent Orchestration', 'Agent Autonomy'
            ],
            
            # 2. 性能评估与基准测试 (更精准)
            '评估与基准': [
                'Agent Benchmark', 'Agentic Evaluation', 'Agent Performance',
                'Task-Oriented Evaluation', 'Agent Capability Assessment',
                'Real-World Agent Evaluation', 'Agent Reliability Metrics'
            ],
            
            # 3. 记忆与状态管理 (重新聚焦)
            '持久记忆系统': [
                'Persistent Memory', 'Agent Memory Architecture', 
                'Episodic Memory Agents', 'Memory Consolidation',
                'Stateful Agents', 'Context Persistence'
            ],
            '动态上下文': [
                'Dynamic Context', 'Context Switching', 'Adaptive Context',
                'Contextual Reasoning', 'Context-Aware Agents'
            ],
            
            # 4. 任务规划与执行 (核心热点)
            '任务分解与规划': [
                'Task Decomposition', 'Hierarchical Planning', 
                'Goal Decomposition', 'Task Orchestration',
                'Multi-Step Planning', 'Dynamic Task Planning'
            ],
            '工具调用与集成': [
                'Tool-Using Agents', 'Function Calling Agents',
                'API Orchestration', 'Tool Composition',
                'External Tool Integration', 'MCP Protocol'
            ],
            
            # 5. 多智能体系统 (更具体化)
            '多智能体协作': [
                'Multi-Agent Collaboration', 'Agent Coordination',
                'Collaborative Agents', 'Agent Communication Protocols',
                'Swarm Intelligence', 'Collective Intelligence'
            ],
            '智能体编排': [
                'Agent Orchestration', 'Agent Workflow', 
                'Multi-Agent Systems', 'Agent Ecosystem',
                'Agent Marketplace', 'Agent Mesh'
            ],
            
            # 6. 人机协作 (强调双向性)
            '人机协作': [
                'Human-AI Collaboration', 'Human-in-the-Loop Agents',
                'Bidirectional Human-AI', 'Collaborative Intelligence',
                'Human-Agent Teaming', 'Interactive Agents'
            ],
            '对话式智能体': [
                'Conversational Agents', 'Dialogue Agents',
                'Natural Language Agents', 'Chatbot Agents',
                'Voice Agents', 'Multimodal Interaction'
            ],
            
            # 7. 领域特化应用 (新增热点)
            '科学发现': [
                'Scientific Discovery Agents', 'Research Automation',
                'Hypothesis Generation', 'Literature Agents',
                'Experimental Design Agents'
            ],
            '代码生成与软件': [
                'Code Generation Agents', 'Software Development Agents',
                'Programming Assistants', 'Automated Coding',
                'Code Review Agents'
            ],
            
            # 8. 新兴技术方向
            '多模态智能体': [
                'Multimodal Agents', 'Vision-Language Agents',
                'Embodied Agents', 'Robotic Agents',
                'Sensory Agents'
            ],
            '可解释性与治理': [
                'Explainable Agents', 'Agent Governance',
                'Agent Safety', 'Transparent Agents',
                'Agent Alignment', 'Controllable Agents'
            ]
        }

        # 核心通用检索关键词 (更聚焦)
        self.core_keywords = [
            'Agentic AI', 'Autonomous Agents', 'AI Agents',
            'LLM Agents', 'Language Agents', 'Intelligent Agents',
            'Agent Framework', 'Agent System', 'Multi-Agent',
            'Tool-Using Agents', 'Reasoning Agents', 'Planning Agents'
        ]


    def build_search_query(self, topic_keywords: List[str], max_terms: int = 5) -> str:
        """
        构建arXiv搜索查询。
        """
        selected_keywords = topic_keywords[:max_terms]
        topic_query = ' OR '.join([f'"{keyword}"' for keyword in selected_keywords])
        core_query = ' OR '.join([f'"{keyword}"' for keyword in self.core_keywords[:5]])
        query = f'({core_query}) AND ({topic_query})'
        return query

    def search_papers(self, query: str, max_results: int = 50, start_date: datetime = None) -> List[arxiv.Result]:
        """
        根据查询字符串和日期搜索论文。
        """
        print(f"搜索查询: {query}")
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for result in self.client.results(search):
                if start_date and result.published.replace(tzinfo=None) < start_date:
                    continue
                papers.append(result)
                
            print(f"找到 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            print(f"搜索出错: {e}")
            return []

    def classify_paper(self, paper: arxiv.Result) -> Set[str]:
        """
        根据论文的标题和摘要进行分类。
        """
        text = (paper.title + " " + paper.summary).lower()
        topics = set()
        
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    topics.add(topic)
                    break
        return topics

    def extract_paper_info(self, paper: arxiv.Result, topics: Set[str]) -> Dict:
        
        """
        提取论文信息，为内部处理和最终的JSONL输出做准备。
        """
        return {
            # --- 用于最终JSONL输出的字段 ---
            'id': paper.entry_id.split('/')[-1],
            'pdf': paper.pdf_url,
            'abs': paper.entry_id,
            'authors': [author.name for author in paper.authors],
            'title': paper.title,
            'categories': paper.categories,
            'comment': paper.comment,
            'summary': paper.summary, # 保留换行符以匹配示例
            
            # --- 用于内部逻辑（排序、打印摘要）的字段 ---
            'published_date': paper.published.replace(tzinfo=None),
            'topics': ', '.join(topics) if topics else '其他'
        }

    def filter_and_collect(self, days_back: int = 7, max_per_topic: int = 10) -> List[Dict]:
        """
        主筛选函数，收集、分类并排序论文。
        """
        start_date = datetime.now() - timedelta(days=days_back)
        print(f"搜索 {start_date.strftime('%Y-%m-%d')} 以来的论文")
        
        all_papers = []
        processed_ids = set()
        
        for topic, keywords in self.topic_keywords.items():
            print(f"\n正在搜索主题: {topic}")
            query = self.build_search_query(keywords)
            papers = self.search_papers(query, max_per_topic, start_date)
            
            for paper in papers:
                # 使用entry_id来避免重复处理同一篇论文
                if paper.entry_id not in processed_ids:
                    topics = self.classify_paper(paper)
                    paper_info = self.extract_paper_info(paper, topics)
                    all_papers.append(paper_info)
                    processed_ids.add(paper.entry_id)
            
            time.sleep(1) # 避免API请求过于频繁
        
        if all_papers:
            # 按发布日期降序排序
            all_papers.sort(key=lambda p: p['published_date'], reverse=True)
            
            print(f"\n总共收集到 {len(all_papers)} 篇独特论文")
            
            # 显示各主题统计
            print("\n各主题论文数量:")
            topic_counts = {}
            for paper_info in all_papers:
                for topic_name in paper_info['topics'].split(', '):
                    topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
            
            for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {topic}: {count} 篇")
        
        return all_papers

    def save_results_to_jsonl(self, papers: List[Dict], filename: str = None):
        """
        将结果以JSONL格式保存到文件。
        """
        if not papers:
            print("没有找到相关论文，不创建文件。")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if filename is None:
            jsonl_file = f'llm_agent_papers_{timestamp}.jsonl'
        else:
            jsonl_file = filename
        
        try:
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for paper_info in papers:
                    # 构建符合要求的JSON对象
                    record = {
                        "id": paper_info['id'],
                        "pdf": paper_info['pdf'],
                        "abs": paper_info['abs'],
                        "authors": paper_info['authors'],
                        "title": paper_info['title'],
                        "categories": paper_info['categories'],
                        "comment": paper_info['comment'],
                        "summary": paper_info['summary']
                    }
                    # 将字典转换为JSON字符串并写入文件，后跟换行符
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"\n结果已保存到: {jsonl_file}")
            
        except IOError as e:
            print(f"写入文件时出错: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the jsonline file")
    args = parser.parse_args()
    # --- 搜索和收集论文 ---
    filter_agent = ArxivLLMAgentFilter()
    print("开始搜索LLM-based Agent相关论文...")
    results_list = filter_agent.filter_and_collect(days_back=7, max_per_topic=5)
    if results_list:
        # 保存原始结果
        filter_agent.save_results_to_jsonl(results_list, args.path)