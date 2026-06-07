"""Agent: 根据 JD 优化简历内容（STAR 法则）"""
import json
from anthropic import Anthropic


SYSTEM_PROMPT = """你是资深简历顾问和产品经理面试官。请根据用户提供的 JD，对其简历内容进行针对性优化。

要求：
1. 提取 JD 中的核心关键词和能力要求
2. 用 STAR 法则重写实习经历和项目经历，突出与 JD 匹配的能力
   - S/T：先交代场景、目标或任务背景
   - A：再说明采取了什么动作
   - R：最后写结果，优先量化结果、效率提升、业务影响
3. 量化产出要有数据支撑，不要空泛描述
4. 保留真实信息，不要虚构
5. 严禁使用 AI 腔调词汇（赋能、深度、链路、抓手、闭环、颗粒度、底层逻辑）
6. 使用自然、真实、专业的中文表达
7. 输出 JSON 格式，结构与输入的简历数据一致，只修改需要定制的部分

只输出 JSON，不要其他内容。"""


def optimize_resume(
    client: Anthropic,
    model: str,
    resume_data: dict,
    jd_text: str,
) -> dict:
    """调用 AI 根据 JD 优化简历内容"""
    prompt = f"""以下是候选人基础信息：
{json.dumps(resume_data, ensure_ascii=False, indent=2)}

以下是目标岗位 JD：
{jd_text}

请根据 JD 定制简历，输出 JSON 格式。"""

    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    result = msg.content[0].text

    try:
        start = result.index("{")
        end = result.rindex("}") + 1
        return json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"error": "AI 响应解析失败", "raw": result[:500]}
