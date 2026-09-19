import json
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True
)


def load_prompt(name: str, **variables: Any) -> str:
    """
    读取 app/prompts/{name}.md 并用 Jinja2 做变量替换

    Args:
        name: prompt 文件名（不含扩展名），如 "triage_system"
        variables: 注入模板的变量（如 RAG 检索结果、用户输入）
    """
    template = _jinja_env.get_template(f"{name}.md")
    return template.render(**variables)


def get_prompt_version(name: str) -> Dict[str, Any]:
    """读取 version.json 中指定 prompt 的版本信息"""
    version_file = PROMPTS_DIR / "version.json"
    with open(version_file, "r", encoding="utf-8") as f:
        versions = json.load(f)
    return versions.get(name, {})
