"""AI 分析模块 — 使用 OpenAI 兼容 API 对抓取的资讯进行智能分析。

支持任何 OpenAI 兼容的 LLM 服务：
- DeepSeek:  base_url=https://api.deepseek.com/v1
- 通义千问:   base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
- 豆包:      base_url=https://ark.cn-beijing.volces.com/api/v3
- Moonshot:  base_url=https://api.moonshot.cn/v1
- OpenAI:   base_url=https://api.openai.com/v1
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List

import httpx
from loguru import logger

from src.scrapers.base import BriefingSection


@dataclass
class AnalysisResult:
    summary: str = ""
    trends: List[str] = field(default_factory=list)
    must_read: str = ""
    must_read_reason: str = ""
    outlook: str = ""


SYSTEM_PROMPT = """你是一位资深 AI 行业分析师，每天为技术团队撰写晨间简报的「AI 编辑观点」栏目。

你的任务：基于今天抓取到的多个来源的资讯标题，输出一份简短、有洞察力的分析。

要求：
1. 「一句话总结」: 用 1 句话概括今天 AI 领域最值得关注的动态（≤50 字）
2. 「趋势洞察」: 提炼 3 条跨来源的关键趋势，每条 1 句话（≤40 字/条）
3. 「必读推荐」: 从所有标题中选 1 篇最值得深读的，给出标题和推荐理由（≤60 字）
4. 「今日展望」: 用 1 句话预判这些趋势对开发者/行业的影响（≤50 字）

请严格以 JSON 格式输出：
{
  "summary": "一句话总结",
  "trends": ["趋势1", "趋势2", "趋势3"],
  "must_read": "推荐文章的原始标题",
  "must_read_reason": "推荐理由",
  "outlook": "今日展望"
}

只输出 JSON，不要其他内容。"""


class AIAnalyzer:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _build_prompt(self, sections: List[BriefingSection]) -> str:
        lines = []
        for section in sections:
            for item in section.items[:3]:
                lines.append(f"[{section.source}] {item.title}")

        joined = "\n".join(lines)
        return (
            f"你是 AI 行业分析师。以下是今日 {len(sections)} 个来源的资讯标题：\n\n"
            f"{joined}\n\n"
            "请分析后严格输出以下 JSON（不要输出其他内容）：\n"
            "{\n"
            '  "summary": "一句话总结今日AI动态(≤50字)",\n'
            '  "trends": ["趋势1(≤40字)", "趋势2(≤40字)", "趋势3(≤40字)"],\n'
            '  "must_read": "最值得读的文章标题(从上面选)",\n'
            '  "must_read_reason": "推荐理由(≤60字)",\n'
            '  "outlook": "对开发者/行业的影响展望(≤50字)"\n'
            "}"
        )

    async def analyze(self, sections: List[BriefingSection]) -> AnalysisResult:
        prompt = self._build_prompt(sections)
        logger.debug(f"AI analysis prompt ({len(prompt)} chars)")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            raw_content = choice.get("message", {}).get("content")

            # 部分模型把推理过程放在 reasoning 字段
            if not raw_content:
                raw_content = choice.get("message", {}).get("reasoning")
            if not raw_content:
                finish = choice.get("finish_reason", "unknown")
                logger.warning(f"LLM returned empty content (finish_reason={finish}), retrying...")
                # 用更短的 prompt 重试一次
                retry_result = await self._retry_short(sections)
                if retry_result:
                    return retry_result
                return self._fallback_result()
            content = raw_content.strip()
            logger.debug(f"LLM raw response ({len(content)} chars): {content[:300]}")
            parsed = self._extract_json(content)
            result = AnalysisResult(
                summary=parsed.get("summary", ""),
                trends=parsed.get("trends", []),
                must_read=parsed.get("must_read", ""),
                must_read_reason=parsed.get("must_read_reason", ""),
                outlook=parsed.get("outlook", ""),
            )
            logger.success(f"AI analysis done: {result.summary[:40]}...")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error {e.response.status_code}: {e.response.text[:200]}")
            return self._fallback_result()
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"AI primary parse failed: {e}, retrying with short prompt...")
            try:
                retry_result = await self._retry_short(sections)
                if retry_result:
                    return retry_result
            except Exception:
                pass
            return self._fallback_result()
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_result()

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON，处理代码块、前后缀文本等情况。"""
        import re
        # 去掉 markdown 代码块
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if code_match:
            text = code_match.group(1).strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 提取第一个 {...} 块
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError("No valid JSON found", text, 0)

    async def _retry_short(self, sections: List[BriefingSection]) -> AnalysisResult | None:
        """用精简版 prompt 重试，适配小模型或免费 API。"""
        titles = []
        for s in sections:
            for item in s.items[:3]:
                titles.append(f"[{s.source}] {item.title}")
        joined = "\n".join(titles)

        short_prompt = (
            f"以下是今日 AI 资讯标题:\n{joined}\n\n"
            "请用 JSON 回答: "
            '{"summary":"一句话总结(≤50字)","trends":["趋势1","趋势2","趋势3"],'
            '"must_read":"最值得读的标题","must_read_reason":"推荐理由","outlook":"今日展望"}'
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": short_prompt}],
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0].get("message", {}).get("content", "")
                if not content:
                    return None
                content = content.strip()
                parsed = self._extract_json(content)
                result = AnalysisResult(
                    summary=parsed.get("summary", ""),
                    trends=parsed.get("trends", []),
                    must_read=parsed.get("must_read", ""),
                    must_read_reason=parsed.get("must_read_reason", ""),
                    outlook=parsed.get("outlook", ""),
                )
                logger.success(f"AI analysis done (retry): {result.summary[:40]}...")
                return result
        except Exception as e:
            logger.warning(f"AI retry also failed: {e}")
            return None

    @staticmethod
    def _fallback_result() -> AnalysisResult:
        return AnalysisResult(
            summary="AI 分析暂时不可用",
            trends=["请检查 LLM API 配置"],
            must_read="",
            must_read_reason="",
            outlook="",
        )
