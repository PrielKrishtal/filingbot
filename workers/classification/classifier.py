import logging

from groq import AsyncGroq
from pydantic import ValidationError

from core.config import settings
from core.logging_config import get_logger
from core.schemas.filing import ClassificationResult, InsiderFiling, InsiderHistory
from workers.classification.prompts import (
    SYSTEM_PROMPT,
    build_corrective_prompt,
    build_user_prompt,
)

base_logger = get_logger("classification")
client = AsyncGroq(api_key=settings.groq_api_key)
json_schema = ClassificationResult.model_json_schema()


async def _call_groq(messages: list) -> str:
    chat_completion = await client.chat.completions.create(
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ClassificationSchema",
                "schema": json_schema,
                "strict": True,
            },
        },
        model="llama-3.3-70b-versatile",
    )
    return chat_completion.choices[0].message.content


async def classify_filing(
    filing: InsiderFiling, history: InsiderHistory
) -> ClassificationResult:
    log = logging.LoggerAdapter(
        base_logger, extra={"correlation_id": filing.accession_number}
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(filing, history)},
    ]

    try:
        response_json = await _call_groq(messages)
        return ClassificationResult.model_validate_json(response_json)

    except ValidationError as e:
        log.warning("classification response failed validation, retrying")
        messages.append(
            {"role": "user", "content": build_corrective_prompt(response_json, str(e))}
        )

    try:
        response_json = await _call_groq(messages)
        return ClassificationResult.model_validate_json(response_json)

    except ValidationError:
        log.exception("classification failed after retry")
        raise
