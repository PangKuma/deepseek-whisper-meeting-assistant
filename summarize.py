import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("❌ 错误：未找到 DEEPSEEK_API_KEY")

BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def summarize_one_file(txt_path, output_folder):
    """
    接收单个 txt 文件路径，生成 PM 视角的结构化纪要，返回 (生成的md路径, 结构化数据字典)。
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    filename = os.path.basename(txt_path)
    # 保持原文件名规则，避免重复生成
    md_filename = os.path.splitext(filename)[0] + "_纪要.md"
    output_path = os.path.join(output_folder, md_filename)

    # 1. 检查是否已存在
    if os.path.exists(output_path):
        print(f"⏩ [总结] 已存在，跳过: {md_filename}")
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            return output_path, extract_info(content, md_filename)
        except:
            return output_path, {"title": md_filename, "summary": "读取失败"}

    print(f"🧠 [DeepSeek] 正在分析决策逻辑: {filename} ...")
    
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        # 🌟 核心修改：Decision Keeper 专用 Prompt
        # 既保留了原来的标题结构（兼容旧逻辑），又在内部强制分层（实现新功能）
        system_prompt = """
        你是一名资深的会议纪要秘书。请根据会议转录文本，严格按照以下 Markdown 格式输出。
        
        【重要原则】
        1. 保持格式严格一致，不要修改标题层级（必须包含：📌 一句话摘要、👥 关键议题与讨论、✅ 决议与待办 (TODO)、💡 详细内容记录）。
        2. 在“决议与待办”章节，请务必将“决策”和“具体的待办任务”区分开，待办事项需明确负责人。

        格式模板：
        # 会议纪要：{自动生成能概括会议的标题}
        
        ## 📌 一句话摘要
        {这里写 50 字以内的摘要，包含会议的核心目的}

        ## 👥 关键议题与讨论
        - {议题1}：{核心观点/冲突点}
        - {议题2}：...

        ## ✅ 决议与待办 (TODO)
        **🚀 核心决议：**
        - [P0] {决议内容}
        - [P1] {决议内容}
        
        **📝 待办清单：**
        - [ ] @{负责人}：{具体动作} [截止时间]
        - [ ] @待定：{具体动作}

        ## 💡 详细内容记录
        {这里按时间或逻辑顺序记录详细的会议内容，作为备查，保留上下文}
        """

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下是会议逐字稿：\n\n{full_text}"},
            ],
            stream=False,
            temperature=0.2, # 降温，让提取更精准
            max_tokens=4000
        )

        summary = response.choices[0].message.content

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        
        print(f"✅ [总结] 决策纪要已生成: {output_path}")
        
        # 提取信息
        info = extract_info(summary, md_filename)
        return output_path, info

    except Exception as e:
        print(f"❌ [总结] 出错: {e}")
        return None, None

def extract_info(text, md_filename):
    """
    🌟 升级版提取函数：
    基于用户原有的结构提取信息，同时兼容新需求。
    """
    # 1. 提取标题 (匹配：# 会议纪要：xxx)
    title_match = re.search(r'# 会议纪要：(.*)', text)
    title = title_match.group(1).strip() if title_match else md_filename

    # 2. 提取摘要 (匹配：## 📌 一句话摘要 下面的内容)
    # 使用 (?=##) 前瞻断言，匹配到下一个 ## 标题之前的内容
    summary_match = re.search(r'## 📌 一句话摘要\s*\n\s*(.*?)(?=\n## |$)', text, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else "未提取到摘要内容"

    # 3. (新增能力) 提取决议与待办
    # 虽然你现在的 main.py 还没用到它，但我们先提取出来，为下一步 Dify/飞书 做好数据准备
    todo_match = re.search(r'## ✅ 决议与待办 \(TODO\)\s*\n\s*(.*?)(?=\n## |$)', text, re.DOTALL)
    todo_content = todo_match.group(1).strip() if todo_match else ""

    return {
        # --- 兼容旧代码 (你的 main.py 强依赖这些字段) ---
        "file_name": md_filename, 
        "title": title,
        "summary": summary,
        
        # --- 新能力 (Decision Keeper 核心数据) ---
        "todo_content": todo_content,
        "full_markdown": text # 把全文也带上，以后 Dify 知识库要用
    }