import json
import os
import asyncio
import aiohttp
import argparse
from typing import Dict
from tqdm.asyncio import tqdm as tqdm_async

# --- 新增翻译功能部分 ---

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
MAX_CONCURRENT_REQUESTS = 10
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

async def translate_summary(session: aiohttp.ClientSession, summary: str, api_key: str) -> str:
    """
    提炼论文摘要
    """
    summary_prompt = """
        根据论文摘要，精确提炼以下五个要素并输出JSON格式：
        1. 研究任务（task） - 研究要解决的核心问题
        2. 研究动机（motivation） - 开展该研究的根本原因
        3. 研究方法（method） - 研究采用的技术路线
        4. 研究结果（result） - 实验发现或产出成果
        5. 研究结论（conclusion） - 研究得出的核心论断

        输出要求：
        - 一律输出中文，禁止输出英文
        - 严格保持JSON键名：task/motivation/method/result/conclusion
        - 无对应内容时留空字符串

        示例输入：
        "This paper systematically studies visual concept mining techniques to improve the controllability of text-to-image diffusion models. Due to the inherent limitations of text signals, it is difficult for models to capture specific concepts. We propose a four-quadrant classification method: concept learning, concept erasure, concept decomposition, and concept combination. Experiments show that this method can effectively analyze model behavior and provide a new perspective for enhancing controllability. This study confirms that visual concept mining is a key path to improving diffusion models."

        示例输出：
        {
            "task": "系统研究视觉概念挖掘技术以提升文本到图像扩散模型的可控性",
            "motivation": "文本信号的内在局限导致模型难以捕捉特定概念",
            "method": "提出四象限分类法：概念学习、概念擦除、概念分解与概念组合",
            "result": "实验表明该方法可有效解析模型行为，为增强生成可控性提供新视角",
            "conclusion": "视觉概念挖掘是改进扩散模型的关键路径"
        }
        """
    
    if not summary or not summary.strip():
        return "" # 如果文本为空则不翻译

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": MODEL_NAME,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": summary}
        ],
        "stream": False,
        "response_format": {'type': 'json_object'}
    }

    try:
        async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60) as response:
            if response.status == 200:
                result = await response.json()
                return json.loads(result['choices'][0]['message']['content'])
            else:
                error_text = await response.text()
                print(f"API请求错误: 状态码 {response.status}, 响应: {error_text}")
                return f"翻译失败: 状态码 {response.status}"
    except asyncio.TimeoutError:
        print("API请求超时")
        return "翻译失败: 请求超时"
    except Exception as e:
        print(f"翻译过程中发生未知错误: {e}")
        return f"翻译失败: {e}"
    

async def translate_title(session: aiohttp.ClientSession, title: str, api_key: str) -> str:
    """
    翻译论文题目
    """
    system_prompt = "将下面的论文题目翻译为中文，要求如下:1.确保原文意义一致；2.确保术语和定义准确，特别是对于领域的专有名词和术语；3. 采用简洁明确的表达方式，避免使用模糊或不必要的词汇、句子；4. 注意表达的准确性，确保句子结构正确；5. 只输出最终翻译结果，禁止多余解释"
    
    if not title or not title.strip():
        return "" # 如果文本为空则不翻译

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": MODEL_NAME,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title}
        ],
        "stream": False
    }

    try:
        async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60) as response:
            if response.status == 200:
                result = await response.json()
                return result['choices'][0]['message']['content']
            else:
                error_text = await response.text()
                print(f"API请求错误: 状态码 {response.status}, 响应: {error_text}")
                return f"翻译失败: 状态码 {response.status}"
    except asyncio.TimeoutError:
        print("API请求超时")
        return "翻译失败: 请求超时"
    except Exception as e:
        print(f"翻译过程中发生未知错误: {e}")
        return f"翻译失败: {e}"
    

async def translate_paper_record(session: aiohttp.ClientSession, paper_data: Dict, api_key: str, semaphore: asyncio.Semaphore) -> Dict:
    """
    为一个论文记录（字典）并发翻译标题和摘要。
    """
    async with semaphore:
        title_to_translate = paper_data.get("title", "")
        summary_to_translate = paper_data.get("summary", "")

        # 并发执行标题和摘要的翻译
        title_zh, summary_info = await asyncio.gather(
            translate_title(session, title_to_translate, api_key),
            translate_summary(session, summary_to_translate, api_key)
        )
        
        # 将翻译结果添加到原字典中
        paper_data['title_zh'] = title_zh
        paper_data['AI'] = summary_info
        return paper_data


async def translate_jsonl_file(input_filepath: str, output_filepath: str):
    """
    读取JSONL文件，并发翻译每一条记录，并写入新的JSONL文件。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 请设置环境变量 DEEPSEEK_API_KEY")
        return

    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            papers = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"错误: 输入文件未找到 {input_filepath}")
        return
    except json.JSONDecodeError as e:
        print(f"错误: 解析JSONL文件失败 {e}")
        return
        
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [translate_paper_record(session, paper, api_key, semaphore) for paper in papers]
        
        # 使用tqdm显示进度
        translated_papers = await tqdm_async.gather(*tasks, desc="正在翻译论文")

    # 写入到新的jsonl文件
    with open(output_filepath, 'w', encoding='utf-8') as f:
        for paper in translated_papers:
            f.write(json.dumps(paper, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to the jsonline file")
    args = parser.parse_args()
    original_jsonl_file = args.data
    print(f"\n准备翻译文件: {original_jsonl_file}")
    translated_jsonl_file = original_jsonl_file.replace('.jsonl', '_zh.jsonl')
    print(f"翻译后的文件将保存为: {translated_jsonl_file}")
    
    # 运行异步翻译流程
    asyncio.run(translate_jsonl_file(original_jsonl_file, translated_jsonl_file))
    
    print(f"\n翻译流程完成！")