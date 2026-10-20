"""Factories for the Angel One SDK objects.

The SDK (smartapi-python) configures logzero to print to the console and to write
logs/<date>/app.log, and it logs request headers and parameters on errors, which include the
API key, client code, PIN and JWT. Every SDK constructor re-enables that logging, so we silence
it immediately after each one.
"""

import logging


def silence_sdk_logging() -> None:
    import logzero

    for handler in list(logzero.logger.handlers):
        if isinstance(handler, logging.FileHandler):
            handler.close()  # logzero only detaches it, leaving logs/<date>/app.log locked on Windows
    logzero.logfile(None)
    logzero.loglevel(logging.CRITICAL + 10)


def smart_connect_factory(api_key: str):
    from SmartApi import SmartConnect

    smart = SmartConnect(api_key=api_key)
    silence_sdk_logging()
    return smart


def websocket_factory(auth_token: str, api_key: str, client_code: str, feed_token: str):
    """SmartWebSocketV2 with the SDK's own retry disabled: TickStream handles reconnects."""
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2

    ws = SmartWebSocketV2(auth_token, api_key, client_code, feed_token, max_retry_attempt=0)
    silence_sdk_logging()
    return ws
