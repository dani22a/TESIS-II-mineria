"""Optional LLM layer. Only used when an API key env var is set; it never sees images or ids."""
import json

from .config import llm_provider

SYSTEM = ("You answer questions about aggregated tuberculosis-screening statistics. Use ONLY the JSON "
          "facts provided. If the facts do not answer the question, say so. Never give clinical "
          "diagnoses. Mention DEMO MODE when is_demo is true.")


def answer_with_llm(question: str, facts: dict) -> str | None:
    provider = llm_provider()
    if provider is None:
        return None
    try:
        from langchain_core.prompts import ChatPromptTemplate

        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            model = ChatAnthropic(model="claude-haiku-4-5", temperature=0)
        else:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM), ("human", "Facts: {facts}\n\nQuestion: {q}")])
        return (prompt | model).invoke({"facts": json.dumps(facts), "q": question}).content
    except Exception:  # missing package, network or key error: fall back to the template
        return None
