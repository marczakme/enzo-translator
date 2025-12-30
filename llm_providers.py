import os
from typing import Optional, List, Dict

from openai import OpenAI
import anthropic
import google.generativeai as genai


def _join_messages(messages: List[Dict[str, str]]) -> tuple[str, str]:
    """
    Returns (system_text, user_text) built from Chat-like messages.
    We keep it deterministic and provider-agnostic.
    """
    system_parts = []
    user_parts = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)
    return ("\n\n".join(system_parts).strip(), "\n\n".join(user_parts).strip())


def _clip(text: str, max_chars: int) -> str:
    """Hard clip to avoid provider BadRequest on very large prompts."""
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 200] + "\n\n[...truncated due to length...]\n"


def chat_llm(
    provider: str,
    messages: list,
    temperature: float = 0.2,
    model_hint: Optional[str] = None,
) -> str:
    """
    Unified LLM interface.
    provider: openai | claude | gemini
    messages: [{"role": "system"|"user", "content": "..."}]

    Notes:
    - For Anthropic we pass system separately (correct API usage).
    - We clip prompts to reduce BadRequest risk on huge glossary/context.
    """

    provider = provider.lower().strip()
    system_text, user_text = _join_messages(messages)

    # Safety clip: prevents BadRequest when glossary/context is massive
    # (You can tune these if needed.)
    system_text = _clip(system_text, 6000)
    user_text = _clip(user_text, 24000)

    # --------------------
    # OpenAI
    # --------------------
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak OPENAI_API_KEY w secrets/ENV.")

        client = OpenAI(api_key=api_key)

        # model_hint optional; fallback to a sane default
        model = model_hint or "gpt-4.1-mini"

        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_text} if system_text else {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": user_text},
            ],
        )
        return resp.choices[0].message.content.strip()

    # --------------------
    # Claude (Anthropic)
    # --------------------
    elif provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Brak ANTHROPIC_API_KEY w secrets/ENV.")

        client = anthropic.Anthropic(api_key=api_key)

        # Use stable alias by default to avoid “model not found” on dated IDs.
        model = model_hint or "claude-3-5-sonnet-latest"

        # Anthropic expects system separately
        resp = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=4096,
            system=system_text if system_text else None,
            messages=[{"role": "user", "content": user_text}],
        )
        return resp.content[0].text.strip()

    # --------------------
    # Gemini
    # --------------------
    elif provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak GEMINI_API_KEY w secrets/ENV.")

        genai.configure(api_key=api_key)

        model_name = model_hint or "gemini-1.5-pro"
        model = genai.GenerativeModel(model_name)

        # Gemini works fine with one prompt string
        prompt = (system_text + "\n\n" + user_text).strip() if system_text else user_text

        resp = model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return (resp.text or "").strip()

    else:
        raise ValueError(f"Nieznany provider LLM: {provider}")
