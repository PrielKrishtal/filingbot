import sentry_sdk

from core.config import settings


def init_sentry(service_name: str) -> None:
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
    sentry_sdk.set_tag("service", service_name)
