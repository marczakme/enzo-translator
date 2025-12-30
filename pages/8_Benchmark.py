import os
from typing import Optional, List, Dict, Tuple

from openai import OpenAI
import anthropic
import google.generativeai as genai


def _join_messages(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    """
    Build (system_text, user_text) from chat-like messages.
    Ensures we never pass empty message content to Anthropic.
    """
    system_parts = []
    user_parts = []

    for m in messages:
        role = (m.get("role") or "").lower().strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue  # critical: avoid empty content -> Anthropic 400
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)

    system_text = "\n\n".join(system_parts).strip()
    user_text = "\n\n".join(user_parts).strip()

    if not user_text:
        # absolutely never call Anthropic with empty user content
        user_text = " "  # minimal non-empty; better than 400 crash

    return system_text, user_text


def _clip(text: str, max_chars: int) -> str:
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

    Claude notes:
    - system is passed via `system=...` (correct Anthropic API usage)
    - automatic model fallback to avoid 400 when a model isn't enabled for your key/account
    """

    provider = provider.lower().strip()
    system_text, user_text = _join_messages(messages)

    # Keep prompts bounded (helps with large glossary / long descriptions)
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
        model = model_hint or "gpt-4.1-mini"

        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_text or "You are helpful."},
                {"role": "user", "content": user_text},
            ],
        )
        return resp.choices[0].message.content.strip()

    # --------------------
    # Claude (Anthropic) with fallback
    # --------------------
    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Brak ANTHROPIC_API_KEY w secrets/ENV.")

        client = anthropic.Anthropic(api_key=api_key)

        # If user provided a model_hint, try it first. Otherwise use a robust fallback chain.
        # (Model availability varies by account/plan; this avoids hard failures.)
        fallback_models = []
        if model_hint:
            fallback_models.append(model_hint)

        # Env override if you want a fixed model without changing code
        env_model = os.environ.get("CLAUDE_MODEL")
        if env_model:
            fallback_models.insert(0, env_model)

        # Robust defaults (try modern aliases first, then dated IDs, then smaller model)
        fallback_models += [
            "claude-3-5-sonnet-latest",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-haiku-20240307",
        ]

        last_err = None
        for model in fallback_models:
            try:
                resp = client.messages.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=4096,
                    system=system_text if system_text else None,
                    messages=[{"role": "user", "content": user_text}],
                )
                return resp.content[0].text.strip()
            except anthropic.BadRequestError as e:
                # usually model not enabled, or request shape issue; try next model
                last_err = e
                continue

        # If we exhausted fallbacks, raise the last error (Streamlit will still redact, but at least we tried)
        raise last_err if last_err else RuntimeError("Claude call failed for unknown reasons.")

    # --------------------
    # Gemini
    # --------------------
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak GEMINI_API_KEY w secrets/ENV.")

        genai.configure(api_key=api_key)
        model_name = model_hint or "gemini-1.5-pro"
        model = genai.GenerativeModel(model_name)

        prompt = (system_text + "\n\n" + user_text).strip() if system_text else user_text
        resp = model.generate_content(prompt, generation_config={"temperature": temperature})
        return (resp.text or "").strip()

    raise ValueError(f"Nieznany provider LLM: {provider}")
