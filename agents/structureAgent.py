"""Agent: 将 PDF 解析后的原始文本映射为结构化简历 JSON"""
import json
from anthropic import Anthropic


SYSTEM_PROMPT = """你是一位简历数据结构化专家。请将用户提供的简历原始文本解析为结构化 JSON。

输入文本是一份简历，可能包含以下信息：
- 个人信息（姓名、电话、邮箱、籍贯、政治面貌）
- 教育背景（学校、专业、类型、入学时间、排名、GPA、均分）
- 技能标签
- 实习经历（公司、部门、岗位、时间、地点、经历详情按 STAR 法则提取）
- 项目经历（名称、类型、角色、状态、详情）
- 产品案例（名称、角色、详情）
- 竞赛奖项（名称、级别、奖项、角色、日期、详情）
- 论文发表（标题、类型、角色、状态）
- 软件著作权（名称、角色、登记号）
- 奖学金与荣誉
- 学生组织领导力
- 志愿服务（时长、荣誉）
- 自我评价

要求：
1. 从文本中提取所有能找到上述信息
2. 找不到的字段留空字符串或空数组，不要编造
3. 实习经历和项目经历尽量按 STAR 法则拆分（情境、任务、行动、结果）
4. 保持语言与原文一致，不做改写
5. 严格按照以下 JSON 格式输出：

{
  "personal_info": {"name":"","phone":"","email":"","location":"","political":"","signature":""},
  "education": {"graduate":{"school":"","major":"","type":"","start":""},"undergraduate":{"school":"","major":"","type":"","start":"","rank":"","gpa":"","score":""}},
  "skills": [""],
  "internship": {"company":"","department":"","position":"","period":"","location":"","achievements":[{"title":"","situation":"","task":"","action":"","result":""}]},
  "product_cases": [{"name":"","role":"","items":[{"title":"","content":""}]}],
  "projects": [{"name":"","type":"","role":"","status":"","items":[""]}],
  "competitions": [{"name":"","level":"","award":"","role":"","date":"","descriptions":[]}],
  "publications": [{"title":"","type":"","role":"","status":""}],
  "software_copyrights": [{"name":"","role":"","registration":""}],
  "awards": [""],
  "leadership": [""],
  "volunteer": {"hours":"","award":""},
  "self_evaluation": [""]
}

只输出 JSON，不要其他内容。"""


def parse_to_resume_data(
    client: Anthropic,
    model: str,
    raw_text: str,
) -> dict:
    """调用 AI 将原始简历文本解析为结构化数据"""
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        temperature=0.3,
    )
    result = msg.content[0].text

    try:
        start = result.index("{")
        end = result.rindex("}") + 1
        return json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"error": "AI 解析失败", "raw": result[:500]}
