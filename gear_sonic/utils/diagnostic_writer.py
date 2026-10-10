"""Bounded diagnostic traces without disk I/O on control/physics threads."""

import json
from pathlib import Path
from queue import Empty, Full, Queue
import sys
from threading import Event, Lock, Thread
import time


class DiagnosticWriter:
    """Write JSONL on a worker, retaining one backup and optional latest JSON.

    Submission never waits for storage. If storage cannot keep up, discard the
    oldest pending records. Callers must not mutate a record after submitting it.
    These traces are diagnostics, not a lossless data collection interface.
    """

    def __init__(self, path, *, latest_path=None, max_bytes=32 * 1024 * 1024,
                 queue_size=128):
        if max_bytes < 1 or queue_size < 1:
            raise ValueError("Diagnostic size limits must be positive")
        self.path = Path(path)
        self.latest_path = Path(latest_path) if latest_path else None
        self.max_bytes = max_bytes
        self.pending = Queue(maxsize=queue_size)
        self.dropped_records = 0
        self.written_records = 0
        self.error = None
        self._closing = Event()
        self._submit_lock = Lock()
        self._thread = Thread(target=self._run, name="diagnostic-writer", daemon=True)
        self._thread.start()

    def submit(self, record):
        with self._submit_lock:
            if self._closing.is_set():
                return False
            try:
                self.pending.put_nowait(record)
            except Full:
                try:
                    self.pending.get_nowait()
                    self.dropped_records += 1
                except Empty:
                    pass
                self.pending.put_nowait(record)
            return True

    def close(self, timeout=2.):
        with self._submit_lock:
            self._closing.set()
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self):
        stream = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            size = self.path.stat().st_size if self.path.exists() else 0
            # A trace from an older unlimited logger must not become a huge
            # backup when this bounded writer takes over.
            if size > self.max_bytes:
                self.path.unlink()
                size = 0
            backup = self.path.with_name(self.path.name + ".1")
            if backup.exists() and backup.stat().st_size > self.max_bytes:
                backup.unlink()
            stream = self.path.open("ab")
            last_flush = time.monotonic()
            while not self._closing.is_set() or not self.pending.empty():
                try:
                    record = self.pending.get(timeout=.1)
                except Empty:
                    stream.flush()
                    continue
                line = (json.dumps(record) + "\n").encode("utf-8")
                if len(line) > self.max_bytes:
                    self.dropped_records += 1
                    continue
                if size + len(line) > self.max_bytes:
                    stream.close()
                    self.path.replace(backup)
                    stream = self.path.open("wb")
                    size = 0
                self._write_record(stream, line, record)
                size += len(line)
                self.written_records += 1
                if time.monotonic() - last_flush >= .5:
                    stream.flush()
                    last_flush = time.monotonic()
        except (OSError, TypeError, ValueError) as exc:
            self.error = str(exc)
            self._closing.set()
            print(f"[Diagnostics] Recording disabled for {self.path}: {exc}", file=sys.stderr)
        finally:
            if stream is not None:
                stream.close()

    def _write_record(self, stream, line, record):
        stream.write(line)
        if self.latest_path is not None:
            self.latest_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.latest_path.with_suffix(self.latest_path.suffix + ".tmp")
            temporary.write_text(json.dumps(record, indent=2))
            temporary.replace(self.latest_path)
