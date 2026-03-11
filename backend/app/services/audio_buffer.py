"""
audio_buffer.py — Thread-safe rolling audio buffer
------------------------------------------------
Stores the last N seconds of raw PCM audio at 16kHz, 16-bit mono.
The ListenerAgent reads overlapping 15-second windows every 10 seconds.
"""

import threading
import collections
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# At 16kHz, 16-bit (2 bytes/sample), mono:
#   1 second = 16000 samples × 2 bytes = 32 000 bytes
SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2  # 16-bit PCM
BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE  # 32 000


class AudioBuffer:
    """
    Rolling byte buffer that retains the last `max_seconds` of PCM audio.

    Thread-safe via a reentrant lock — audio arrives from the asyncio
    event-loop thread but the ListenerAgent may read from a thread-pool
    executor or the same event loop.
    """

    def __init__(self, max_seconds: int = 90):
        self._max_bytes = max_seconds * BYTES_PER_SECOND
        # deque gives O(1) appends and efficient slicing via bytes join
        self._buf: collections.deque[bytes] = collections.deque()
        self._total_bytes: int = 0
        self._lock = threading.RLock()
        logger.debug(
            f"[AudioBuffer] Created — capacity {max_seconds}s "
            f"({self._max_bytes:,} bytes)"
        )

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def push(self, chunk: bytes) -> None:
        """Append raw PCM bytes; trim oldest data if over capacity."""
        if not chunk:
            return
        with self._lock:
            self._buf.append(chunk)
            self._total_bytes += len(chunk)
            # Trim from the front until we're within capacity
            while self._total_bytes > self._max_bytes and self._buf:
                oldest = self._buf.popleft()
                self._total_bytes -= len(oldest)

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def get_window(self, seconds: float) -> bytes:
        """
        Return (up to) the last `seconds` of PCM data as a single bytes
        object, suitable for encoding and sending to Gemini Flash.

        Returns empty bytes if nothing has been captured yet.
        """
        if seconds <= 0:
            return b""
        wanted = int(seconds * BYTES_PER_SECOND)
        with self._lock:
            if self._total_bytes == 0:
                return b""
            all_data = b"".join(self._buf)
            return all_data[-wanted:] if len(all_data) >= wanted else all_data

    @property
    def duration_seconds(self) -> float:
        """How many seconds of audio are currently stored."""
        with self._lock:
            return self._total_bytes / BYTES_PER_SECOND

    def clear(self) -> None:
        """Discard all buffered audio."""
        with self._lock:
            self._buf.clear()
            self._total_bytes = 0
