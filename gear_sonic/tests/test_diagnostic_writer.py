"""Exercise disk limits and stalled/failing storage on the control path."""

import json
from pathlib import Path
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

from gear_sonic.utils.diagnostic_writer import DiagnosticWriter


class DiagnosticWriterTest(unittest.TestCase):
    def test_rotated_trace_stays_bounded_and_latest_survives_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "actions.jsonl"
            latest = Path(directory) / "latest.json"
            writer = DiagnosticWriter(trace, latest_path=latest, max_bytes=256)
            for index in range(80):
                writer.submit({"index": index, "payload": "test" * 12})
            self.assertTrue(writer.close())
            self.assertIsNone(writer.error)
            files = list(Path(directory).glob("actions.jsonl*"))
            self.assertEqual(len(files), 2)
            self.assertLessEqual(sum(p.stat().st_size for p in files), 512)
            for path in files:
                for line in path.read_text().splitlines():
                    json.loads(line)
            self.assertEqual(json.loads(latest.read_text())["index"], 79)
            self.assertEqual(json.loads(trace.read_text().splitlines()[-1])["index"], 79)
            self.assertFalse(writer.submit({"index": 80}))

    def test_stalled_disk_does_not_block_producer_or_grow_backlog(self):
        entered, release = Event(), Event()
        original_write = DiagnosticWriter._write_record
        def stalled_write(writer, stream, line, record):
            entered.set()
            release.wait(3.)
            original_write(writer, stream, line, record)
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            with patch.object(DiagnosticWriter, "_write_record", stalled_write):
                writer = DiagnosticWriter(trace, queue_size=8)
                try:
                    writer.submit({"index": 0})
                    self.assertTrue(entered.wait(1.))
                    start = time.monotonic()
                    for index in range(1, 1001):
                        writer.submit({"index": index})
                    self.assertLess(time.monotonic() - start, .1)
                    self.assertEqual(writer.pending.qsize(), 8)
                    self.assertGreater(writer.dropped_records, 900)
                    self.assertFalse(writer.close(timeout=.01))
                finally:
                    release.set()
                    self.assertTrue(writer.close())
            self.assertEqual(json.loads(trace.read_text().splitlines()[-1])["index"], 1000)

    def test_storage_error_disables_only_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "file_not_directory"
            parent.write_text("occupied")
            writer = DiagnosticWriter(parent / "trace.jsonl")
            writer.submit({"event": "action"})
            self.assertTrue(writer.close())
            self.assertIsNotNone(writer.error)
            self.assertFalse(writer.submit({"event": "next action"}))


if __name__ == "__main__":
    unittest.main()
