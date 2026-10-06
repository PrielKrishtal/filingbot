import logging

from groq import AsyncGroq
from pydantic import ValidationError

from core.config import settings
from core.logging_config import get_logger
from core.schemas.enums import (
    SignalStrength,
    TransactionClassification,
    TransactionCode,
)
from core.schemas.filing import ClassificationResult, InsiderFiling, InsiderHistory
from workers.classification.prompts import (
    SYSTEM_PROMPT,
    build_corrective_prompt,
    build_user_prompt,
)

base_logger = get_logger("classification")
client = AsyncGroq(api_key=settings.groq_api_key)
json_schema = ClassificationResult.model_json_schema()

# Grants and tax withholding skip the LLM - they happen to an insider, not by choice.
MECHANICAL_TRANSACTIONS = {
    TransactionCode.F: ClassificationResult(
        signal_strength=SignalStrength.NOISE,
        transaction_classification=TransactionClassification.tax_disposition,
        reasoning=(
            "Shares withheld automatically to cover taxes on a vesting grant "
            "- not a discretionary trade."
        ),
    ),
    TransactionCode.A: ClassificationResult(
        signal_strength=SignalStrength.NOISE,
        transaction_classification=TransactionClassification.other,
        reasoning="Company stock grant - shares received, not purchased.",
    ),
}


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
        model="openai/gpt-oss-120b",
    )

    usage = chat_completion.usage
    base_logger.info(
        "groq call complete",
        extra={
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    )

    return chat_completion.choices[0].message.content



async def classify_filing(
    filing: InsiderFiling, history: InsiderHistory
) -> ClassificationResult:
    log = logging.LoggerAdapter(
        base_logger, extra={"correlation_id": filing.accession_number}
    )

    # Skip the LLM for grants and tax withholding.
    rule_result = MECHANICAL_TRANSACTIONS.get(filing.transaction_code)
    if rule_result is not None:
        log.info("classified by rule, skipped LLM")
        return rule_result.model_copy()

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
