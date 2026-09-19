"""
预约分诊服务
多轮对话，根据患者症状描述推荐挂号科室
"""
import json
import logging
import uuid
from typing import AsyncIterator, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.services.common.redis import redis_client
from app.services.common import llm_service, rag_service
from app.services.common.prompt_loader import load_prompt
from app.services.common.content_review import review_content
from app.schemas.client.triage import DepartmentRecommendation

logger = logging.getLogger("triage")

CONVERSATION_TTL = 3600  # 对话历史保留1小时
MAX_HISTORY_TURNS = 8  # 最多保留最近8轮对话（4对QA）


def _conversation_key(user_id: int, session_id: str) -> str:
    """构造对话历史Redis key"""
    return f"triage:conversation:{user_id}:{session_id}"


async def _load_conversation_history(user_id: int, session_id: str) -> List[dict]:
    """从Redis加载对话历史"""
    key = _conversation_key(user_id, session_id)
    messages_json = await redis_client.redis.lrange(key, 0, MAX_HISTORY_TURNS - 1)
    return [json.loads(msg) for msg in messages_json]


async def _save_conversation_turn(user_id: int, session_id: str, user_msg: str, ai_msg: str) -> None:
    """保存一轮对话到Redis"""
    key = _conversation_key(user_id, session_id)
    # 左推入用户消息和AI回复（LPUSH保证最新消息在前）
    await redis_client.redis.lpush(key, json.dumps({"role": "assistant", "content": ai_msg}, ensure_ascii=False))
    await redis_client.redis.lpush(key, json.dumps({"role": "user", "content": user_msg}, ensure_ascii=False))
    # 设置过期时间
    await redis_client.redis.expire(key, CONVERSATION_TTL)


async def _extract_department_names(ai_response: str) -> List[str]:
    """从AI回复中提取推荐的科室名称（基于常见科室白名单匹配）"""
    # 常见科室白名单（包含完整名称和简称）
    known_departments = [
        "心内科", "心血管内科", "心脏内科",
        "呼吸内科", "呼吸科",
        "消化内科", "消化科",
        "神经内科", "神经科",
        "内科", "普通内科",
        "外科", "普通外科", "普外科",
        "急诊科", "急诊",
        "骨科", "骨外科",
        "儿科", "儿童科",
        "妇产科", "妇科", "产科",
        "皮肤科", "皮肤性病科",
        "耳鼻喉科", "耳鼻咽喉科",
        "眼科",
        "口腔科", "牙科",
        "肾内科", "肾脏科",
        "内分泌科", "内分泌代谢科",
        "血液科", "血液内科",
        "风湿科", "风湿免疫科",
        "肿瘤科", "肿瘤内科", "肿瘤外科",
        "泌尿外科", "泌尿科",
        "胸外科", "心胸外科",
        "神经外科", "脑外科",
        "肝胆外科",
        "感染科", "传染科",
    ]

    # 先去除markdown格式符号
    clean_text = ai_response.replace("**", "")

    # 按长度倒序扫描，重叠位置长词优先（避免"外科"抢占"脊柱外科"的字符区间）
    # 记录每个匹配的文本位置，最终按在原文中出现的先后顺序排序，
    # 避免"内科/外科"这类短词遍历顺序靠前而挤占真正被推荐的科室名额
    claimed = [False] * len(clean_text)
    matches = []  # (start_index, dept_name)
    for dept in sorted(known_departments, key=len, reverse=True):
        start = 0
        while True:
            idx = clean_text.find(dept, start)
            if idx == -1:
                break
            span = range(idx, idx + len(dept))
            if not any(claimed[i] for i in span):
                for i in span:
                    claimed[i] = True
                matches.append((idx, dept))
            start = idx + 1

    matches.sort(key=lambda m: m[0])
    found = []
    for _, dept in matches:
        if dept not in found:
            found.append(dept)

    return found[:3]  # 最多返回3个科室


def _department_core(name: str) -> str:
    """去除科室通用后缀（内科/外科/科），提取核心专科词，用于模糊匹配（如"心内科"->"心"，"心血管内科"->"心血管"）"""
    for suffix in ["内科", "外科", "科"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


async def _match_departments(db: AsyncSession, dept_names: List[str]) -> List[DepartmentRecommendation]:
    """根据科室名称匹配数据库中的科室（核心专科词双向包含匹配）"""
    if not dept_names:
        return []

    all_departments = (await db.execute(select(Department))).scalars().all()

    recommendations = []
    matched_ids = set()
    for name in dept_names:
        core = _department_core(name)

        # core为空时（如"内科"、"外科"、"科"本身），改为全等匹配
        if not core:
            dept = next(
                (d for d in all_departments if d.id not in matched_ids and d.name == name),
                None,
            )
        else:
            dept = next(
                (
                    d for d in all_departments
                    if d.id not in matched_ids
                    and (
                        core in d.name
                        or (_department_core(d.name) and _department_core(d.name) in core)
                        or core in _department_core(d.name)
                    )
                ),
                None,
            )

        if dept:
            matched_ids.add(dept.id)
            recommendations.append(dept)

    # 置信度按「实际匹配成功的顺序」而非 AI 原始提取顺序赋值。
    # 否则前面的候选（如本院没有的肾内科）被丢弃后，
    # 唯一匹配上的科室会因原始索引靠后而只拿到 medium，显示为「可考虑」。
    levels = ["high", "medium", "low"]
    return [
        DepartmentRecommendation(
            department_id=dept.id,
            department_name=dept.name,
            confidence=levels[min(rank, len(levels) - 1)],
        )
        for rank, dept in enumerate(recommendations)
    ]


async def chat(
    db: AsyncSession,
    user_id: int,
    message: str,
    session_id: Optional[str] = None,
) -> Tuple[str, str, List[DepartmentRecommendation], int]:
    """
    处理分诊对话

    Args:
        db: 数据库会话
        user_id: 患者ID
        message: 用户输入症状描述
        session_id: 会话ID，首次可为空

    Returns:
        (session_id, ai_response, recommendations, turn_count)
    """
    # 生成或复用session_id
    if not session_id:
        session_id = str(uuid.uuid4())

    # 加载对话历史（Redis LRANGE 返回的是倒序，即最新消息在前，需翻转为正序）
    history = await _load_conversation_history(user_id, session_id)
    history.reverse()

    # RAG检索分诊指引
    chunks = await rag_service.search(
        db,
        query=message,
        top_k=3,
        source_type="分诊指引",
        agent_type="triage",
    )
    reference_chunks = [chunk.content for chunk in chunks]

    # 注入本院真实科室，约束 AI 只能推荐已开设的科室，
    # 避免推荐了患者根本挂不到的科室（如本院未开设的肾内科）
    departments = (await db.execute(select(Department).order_by(Department.id))).scalars().all()

    # 构造Prompt
    prompt = load_prompt(
        "triage_system",
        user_message=message,
        conversation_history=history,
        reference_chunks=reference_chunks,
        departments=departments,
    )

    # 调用LLM
    llm_result = await llm_service.call(db, prompt, agent_type="triage")
    ai_response = llm_result.content

    # 内容审核
    passed, reason = review_content(ai_response)
    if not passed:
        # 审核失败，返回降级文案
        logger.warning(f"Content review failed for user_id={user_id}, session_id={session_id}: {reason}")
        ai_response = "系统繁忙，请稍后重试或直接咨询导医台。"
        recommendations = []
    else:
        # 从AI回复中提取科室推荐
        dept_names = await _extract_department_names(ai_response)
        recommendations = await _match_departments(db, dept_names)

    # 保存对话历史
    await _save_conversation_turn(user_id, session_id, message, ai_response)

    # 计算轮次（历史消息数/2 + 当前轮）
    turn_count = len(history) // 2 + 1

    return session_id, ai_response, recommendations, turn_count


async def chat_stream(
    db: AsyncSession,
    user_id: int,
    message: str,
    session_id: Optional[str] = None,
) -> AsyncIterator[dict]:
    """流式处理分诊对话；先输出文本增量，完成后输出推荐科室等元数据。"""
    if not session_id:
        session_id = str(uuid.uuid4())

    history = await _load_conversation_history(user_id, session_id)
    history.reverse()

    chunks = await rag_service.search(
        db,
        query=message,
        top_k=3,
        source_type="分诊指引",
        agent_type="triage",
    )
    reference_chunks = [chunk.content for chunk in chunks]
    departments = (await db.execute(select(Department).order_by(Department.id))).scalars().all()
    prompt = load_prompt(
        "triage_system",
        user_message=message,
        conversation_history=history,
        reference_chunks=reference_chunks,
        departments=departments,
    )

    turn_count = len(history) // 2 + 1
    yield {"type": "start", "session_id": session_id, "turn_count": turn_count}

    response_parts: List[str] = []
    async for text_delta in llm_service.stream(db, prompt, agent_type="triage"):
        response_parts.append(text_delta)
        yield {"type": "delta", "content": text_delta}

    ai_response = "".join(response_parts)
    passed, reason = review_content(ai_response)
    if not passed:
        logger.warning(
            f"Content review failed for user_id={user_id}, session_id={session_id}: {reason}"
        )
        ai_response = "系统繁忙，请稍后重试或直接咨询导医台。"
        recommendations = []
        yield {"type": "replace", "content": ai_response}
    else:
        dept_names = await _extract_department_names(ai_response)
        recommendations = await _match_departments(db, dept_names)

    await _save_conversation_turn(user_id, session_id, message, ai_response)
    yield {
        "type": "done",
        "session_id": session_id,
        "turn_count": turn_count,
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
    }
