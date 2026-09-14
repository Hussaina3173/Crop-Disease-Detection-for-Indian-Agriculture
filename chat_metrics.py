import json
import time
from pathlib import Path


class ChatMetrics:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, provider, latency, success):
        event = {'timestamp': time.time(), 'provider': provider, 'latency_seconds': latency, 'success': success}
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event) + '\n')

    def summary(self):
        if not self.path.exists():
            return {'total_queries': 0, 'successful_queries': 0, 'gemini_queries': 0, 'fallback_queries': 0, 'error_queries': 0, 'average_latency_seconds': 0}
        events = []
        for line in self.path.read_text(encoding='utf-8').splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        successful = [event for event in events if event.get('success')]
        latencies = [event.get('latency_seconds', 0) for event in events]
        return {
            'total_queries': len(events),
            'successful_queries': len(successful),
            'gemini_queries': sum(event.get('provider') == 'gemini' for event in events),
            'fallback_queries': sum(event.get('provider') == 'fallback' for event in events),
            'error_queries': sum(not event.get('success') for event in events),
            'average_latency_seconds': round(sum(latencies) / len(latencies), 3) if latencies else 0,
        }
