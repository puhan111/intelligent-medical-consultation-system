import hashlib
import logging
import time
from datetime import date
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI, OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.common.redis import redis_client
from app.models.llm_call_log import LLMCallLog
from app.exceptions.http_exceptions import BudgetExceededError, LLMServiceError, InputTooLongError

logger = logging.getLogger("llm_service")

# 此处限制的是拼装后的完整 prompt 长度（system 指令 + 对话历史 + RAG 检索结果 + 当前输入）
# 分诊 Agent 用户单轮输入已在 schema 层限制 500 字，完整 prompt 上限放宽到 3000 字以容纳多轮历史
# 报告解读 Agent 报告内容上限 5000 字
MAX_INPUT_LENGTH = {
    "triage": 3000,
    "report_interpret": 5000,
    # 追问 prompt 同时注入报告原文、既有解读、对话历史和 RAG 片段，上限放宽
    "report_followup": 8000,
}
DEFAULT_MAX_INPUT_LENGTH = 2000

# 分诊 30s，报告解读 60s
AGENT_TIMEOUT_SECONDS = {
    "triage": 30,
    "report_interpret": 60,
    "report_followup": 30,
}

# 各 Agent 类型的降级文案
FALLBACK_RESPONSES = {
    "triage": "系统繁忙，请稍后重试或直接咨询导医台。",
    "report_interpret": None,  # 报告解读走 interpretation_status=failed，不返回文案
    "report_followup": "系统繁忙，暂时无法回答。建议您携带报告咨询医生获得专业解读。仅供参考。",
}

_client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
_async_client = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


class LLMResult:
    def __init__(self, content: str, input_tokens: int, output_tokens: int, latency_ms: int):
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms


def _budget_key() -> str:
    """按天累加 token 消耗的 Redis key"""
    return f"llm:token_budget:{date.today().isoformat()}"


async def _check_budget() -> None:
    """成本熔断：达到每日预算 80% 记 WARNING，达到 100% 拒绝非核心请求"""
    used = await redis_client.get(_budget_key())
    used = int(used) if used else 0
    budget = settings.LLM_DAILY_TOKEN_BUDGET

    if used >= budget:
        raise BudgetExceededError(message="Daily LLM token budget exceeded, please try again tomorrow")

    if used >= budget * 0.8:
        logger.warning(f"LLM daily token usage at {used}/{budget} ({used / budget:.0%})")


async def _record_budget_usage(total_tokens: int) -> None:
    """累加当日 token 消耗（Redis 计数器，跨天自动重置靠 key 按日期命名）"""
    key = _budget_key()
    current = await redis_client.redis.incrby(key, total_tokens)
    if current == total_tokens:
        # 首次写入该 key，设置 48 小时过期兜底，避免长期堆积
        await redis_client.redis.expire(key, 48 * 3600)


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@retry(
    retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def _call_deepseek_sync(prompt: str, system_prompt: Optional[str], timeout: int) -> tuple:
    """同步调用 DeepSeek（OpenAI 兼容接口），tenacity 指数退避重试：1s -> 2s -> 4s，最多 3 次"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = _client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=messages,
        timeout=timeout,
    )
    content = response.choices[0].message.content
    return content, response.usage.prompt_tokens, response.usage.completion_tokens


async def call(
    db: AsyncSession,
    prompt: str,
    agent_type: str,
    system_prompt: Optional[str] = None
) -> LLMResult:
    """
    LLM 调用封装：成本熔断 -> 输入长度校验 -> 重试调用 -> 记录日志 -> 异常降级

    Args:
        db: 用于写入 llm_call_logs 的会话
        prompt: 用户 prompt
        agent_type: triage / report_interpret，决定超时阈值和降级文案
        system_prompt: 可选的 system prompt
    """
    max_length = MAX_INPUT_LENGTH.get(agent_type, DEFAULT_MAX_INPUT_LENGTH)
    if len(prompt) > max_length:
        raise InputTooLongError(message=f"Input exceeds maximum length of {max_length} characters")

    await _check_budget()

    timeout = AGENT_TIMEOUT_SECONDS.get(agent_type, settings.LLM_TIMEOUT_SECONDS)
    prompt_hash = _prompt_hash(prompt)
    start = time.monotonic()

    try:
        content, input_tokens, output_tokens = _call_deepseek_sync(prompt, system_prompt, timeout)
        latency_ms = int((time.monotonic() - start) * 1000)

        db.add(LLMCallLog(
            agent_type=agent_type,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status="success",
        ))
        await _record_budget_usage(input_tokens + output_tokens)

        return LLMResult(content=content, input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=latency_ms)

    except (APITimeoutError, APIConnectionError, RateLimitError) as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        status = "timeout" if isinstance(e, APITimeoutError) else "error"
        logger.error(f"LLM call failed for agent_type={agent_type} after retries: {e}", exc_info=True)

        db.add(LLMCallLog(
            agent_type=agent_type,
            prompt_hash=prompt_hash,
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            status=status,
            error_message=str(e),
        ))

        raise LLMServiceError(message=FALLBACK_RESPONSES.get(agent_type) or "LLM service unavailable") from e


async def stream(
    db: AsyncSession,
    prompt: str,
    agent_type: str,
    system_prompt: Optional[str] = None,
) -> AsyncIterator[str]:
    """流式调用 LLM，并在流结束后记录用量、延迟和调用状态。"""
    max_length = MAX_INPUT_LENGTH.get(agent_type, DEFAULT_MAX_INPUT_LENGTH)
    if len(prompt) > max_length:
        raise InputTooLongError(message=f"Input exceeds maximum length of {max_length} characters")

    await _check_budget()

    timeout = AGENT_TIMEOUT_SECONDS.get(agent_type, settings.LLM_TIMEOUT_SECONDS)
    prompt_hash = _prompt_hash(prompt)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    start = time.monotonic()
    input_tokens = 0
    output_tokens = 0

    try:
        response = await _async_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            timeout=timeout,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in response:
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens

            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        latency_ms = int((time.monotonic() - start) * 1000)
        db.add(LLMCallLog(
            agent_type=agent_type,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status="success",
        ))
        await _record_budget_usage(input_tokens + output_tokens)
        await db.commit()

    except (APITimeoutError, APIConnectionError, RateLimitError) as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        status = "timeout" if isinstance(e, APITimeoutError) else "error"
        logger.error(
            f"Streaming LLM call failed for agent_type={agent_type}: {e}",
            exc_info=True,
        )
        db.add(LLMCallLog(
            agent_type=agent_type,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=str(e),
        ))
        await db.commit()
        raise LLMServiceError(
            message=FALLBACK_RESPONSES.get(agent_type) or "LLM service unavailable"
        ) from e
