from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 10 * 60
IDEMPOTENCY_TTL_SECONDS = 10 * 60


class SupportTicketRateLimitError(RuntimeError):
    """The client has submitted too many tickets in the current window."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class IdempotencyConflictError(RuntimeError):
    """An idempotency key was reused for different request data."""


class IdempotencyInProgressError(RuntimeError):
    """Another request with the same idempotency key is still running."""


@dataclass
class IdempotencyEntry:
    fingerprint: str
    expires_at: float
    ticket_id: int | None = None


class SupportTicketRequestGuard:
    """Small in-memory guard suitable for this single-process diploma project."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._idempotency_entries: dict[tuple[str, str], IdempotencyEntry] = {}

    def begin(
        self,
        *,
        rate_limit_key: str,
        passport_id: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> int | None:
        """Reserve a request or return the ticket created by an earlier request."""

        now = monotonic()
        entry_key = (passport_id, idempotency_key)
        with self._lock:
            self._remove_expired_entries(now)
            entry = self._idempotency_entries.get(entry_key)
            if entry is not None:
                if entry.fingerprint != fingerprint:
                    raise IdempotencyConflictError
                if entry.ticket_id is None:
                    raise IdempotencyInProgressError
                return entry.ticket_id

            attempts = self._attempts[rate_limit_key]
            window_start = now - RATE_LIMIT_WINDOW_SECONDS
            while attempts and attempts[0] <= window_start:
                attempts.popleft()
            if len(attempts) >= RATE_LIMIT_ATTEMPTS:
                retry_after = max(1, int(attempts[0] + RATE_LIMIT_WINDOW_SECONDS - now) + 1)
                raise SupportTicketRateLimitError(retry_after)

            attempts.append(now)
            self._idempotency_entries[entry_key] = IdempotencyEntry(
                fingerprint=fingerprint,
                expires_at=now + IDEMPOTENCY_TTL_SECONDS,
            )
            return None

    def complete(
        self,
        *,
        passport_id: str,
        idempotency_key: str,
        ticket_id: int,
    ) -> None:
        """Save the successful result for later retries with the same key."""

        with self._lock:
            entry = self._idempotency_entries.get((passport_id, idempotency_key))
            if entry is not None:
                entry.ticket_id = ticket_id

    def abort(self, *, passport_id: str, idempotency_key: str) -> None:
        """Release a failed request so the same key can be retried safely."""

        with self._lock:
            self._idempotency_entries.pop((passport_id, idempotency_key), None)

    def clear(self) -> None:
        """Clear process-local state; primarily useful for isolated tests."""

        with self._lock:
            self._attempts.clear()
            self._idempotency_entries.clear()

    def _remove_expired_entries(self, now: float) -> None:
        expired = [
            key
            for key, entry in self._idempotency_entries.items()
            if entry.expires_at <= now
        ]
        for key in expired:
            del self._idempotency_entries[key]


support_ticket_guard = SupportTicketRequestGuard()
