"""Provider-independent failures used to bound retries and stop invalid credentials."""


class ProviderAuthError(RuntimeError):
    """Credentials/permissions require operator intervention; abort the batch."""


class ProviderRequestError(RuntimeError):
    """A permanent request error; do not retry the same call."""


class ProviderTransientError(RuntimeError):
    """A temporary service/network failure that may be retried."""
