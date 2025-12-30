import os
from openai import OpenAI
import anthropic
import google.generativeai as genai


def chat_llm(
    provider: str,
    messages: list,
    temperature: float = 0.2,
    model_hint: str | None = None,
) -> str:
    """
    Unified LLM interface.
    provider: openai | claude | gemini
    messages: [{"role": "system"|"user", "content": "..."}]
    """

    provider = provider.lower()

    # --------------------
    # OpenAI
    # --------------------
    if provider == "openai":
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        model = model_hint or "gpt-4.1-mini"

        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        return resp.choices[0].message.content.strip()

    # --------------------
    # Claude (Anthropic)
    # --------------------
    elif provider == "claude":
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        model = model_hint or "claude-3-5-sonnet-20240620"

        # Claude używa jednego promptu user → łączymy treść
        prompt = "\n\n".join([m["content"] for m in messages if m["role"] != "system"])

        resp = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    # --------------------
    # Gemini
    # --------------------
    elif provider == "gemini":
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel(model_hint or "gemini-1.5-pro")

        prompt = "\n\n".join([m["content"] for m in messages])
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return resp.text.strip()

    else:
        raise ValueError(f"Nieznany provider LLM: {provider}")
