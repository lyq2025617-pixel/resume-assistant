"""Agent: 根据候选人简历和目标岗位 JD 生成面试问题"""
import json
from anthropic import Anthropic


SYSTEM_PROMPT = """你是资深技术面试官。请根据候选人简历和目标岗位 JD，生成 8-10 个高概率面试问题。

要求：
1. 题目必须紧密围绕 JD 中的技术栈、业务场景和任职要求
2. 包含技术问题和行为面试问题（比例约 7:3）
3. 针对候选人简历中的经历深挖（STAR 追问）
4. 针对 JD 中的核心能力要求
5. 每个问题附带"考察点"说明
6. 为每道题提供 1-2 句"答题思路"，提示候选人应从哪些角度回答
7. 标注难度等级：easy（基础概念）/ medium（需要实战经验）/ hard（架构设计或深度原理）

输出 JSON 数组格式：
[
  {
    "question": "具体问题",
    "type": "技术/行为/产品/综合",
    "focus": "考察点说明",
    "difficulty": "easy/medium/hard",
    "hint": "1-2 句答题思路或回答方向提示"
  }
]

只输出 JSON 数组，不要其他内容。"""


def generate_questions(
    client: Anthropic,
    model: str,
    resume_data: dict,
    jd_text: str,
) -> list:
    """调用 AI 生成面试问题"""
    prompt = f"""候选人简历：
{json.dumps(resume_data, ensure_ascii=False, indent=2)}

目标岗位 JD：
{jd_text}

请生成面试问题。"""

    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    result = msg.content[0].text

    try:
        start = result.index("[")
        end = result.rindex("]") + 1
        return json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError):
        return [{"question": "生成失败", "type": "综合", "focus": result[:200]}]
