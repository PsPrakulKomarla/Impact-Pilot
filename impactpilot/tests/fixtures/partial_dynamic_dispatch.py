"""A real static-analysis limitation: the runtime registry chooses the target."""

from importlib import import_module


def dispatch(event_name: str, payload: dict[str, str]) -> object:
    """The handler module and attribute are data, not a statically named call."""
    module_name, handler_name = RUNTIME_REGISTRY[event_name]
    handler = getattr(import_module(module_name), handler_name)
    return handler(payload)


RUNTIME_REGISTRY = {
    "payment.authorized": ("payment_handlers", "record_authorization"),
}
