import json
import sqlite3
import threading
import time
import urllib.request
import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse

API_URL = 'https://data.edmonton.ca/resource/q9ny-crw9.json'
DB_PATH = 'data.db'
FETCH_INTERVAL = 60  # seconds


def init_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_ts TEXT,
            company TEXT,
            vehicle_type TEXT,
            lat REAL,
            lon REAL,
            battery_level INTEGER,
            status TEXT,
            last_updated TEXT
        )"""
    )
    conn.commit()
    conn.close()


class DataFetcher(threading.Thread):
    def __init__(self, db_path, interval=60):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                with urllib.request.urlopen(API_URL) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    self.save_data(data)
            except Exception as e:
                print('Fetch error:', e)
            time.sleep(self.interval)

    def save_data(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        fetch_ts = datetime.datetime.utcnow().isoformat()
        for entry in data:
            c.execute(
                'INSERT INTO vehicles (fetch_ts, company, vehicle_type, lat, lon, battery_level, status, last_updated) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    fetch_ts,
                    entry.get('company'),
                    entry.get('vehicle_type'),
                    float(entry.get('lat')) if entry.get('lat') is not None else None,
                    float(entry.get('lon')) if entry.get('lon') is not None else None,
                    int(entry.get('battery_level')) if entry.get('battery_level') is not None else None,
                    entry.get('status'),
                    entry.get('last_updated'),
                ),
            )
        conn.commit()
        conn.close()

    def stop(self):
        self._stop_event.set()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, db_path=None, **kwargs):
        self.db_path = db_path
        super().__init__(*args, directory='.', **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/latest'):
            self.handle_latest()
        elif self.path.startswith('/api/history'):
            self.handle_history()
        else:
            super().do_GET()

    def handle_latest(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            'SELECT company, vehicle_type, lat, lon, battery_level, status, last_updated '
            'FROM vehicles ORDER BY fetch_ts DESC'
        )
        rows = c.fetchall()
        conn.close()
        data = [
            {
                'company': r[0],
                'vehicle_type': r[1],
                'lat': r[2],
                'lon': r[3],
                'battery_level': r[4],
                'status': r[5],
                'last_updated': r[6],
            }
            for r in rows
        ]
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def handle_history(self):
        query = urllib.parse.urlsplit(self.path).query
        params = urllib.parse.parse_qs(query)
        start = params.get('start', [None])[0]
        end = params.get('end', [None])[0]
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if start and end:
            c.execute(
                'SELECT fetch_ts, company, vehicle_type, lat, lon, battery_level, status, last_updated '
                'FROM vehicles WHERE fetch_ts BETWEEN ? AND ? ORDER BY fetch_ts',
                (start, end),
            )
        else:
            c.execute(
                'SELECT fetch_ts, company, vehicle_type, lat, lon, battery_level, status, last_updated '
                'FROM vehicles ORDER BY fetch_ts'
            )
        rows = c.fetchall()
        conn.close()
        data = [
            {
                'fetch_ts': r[0],
                'company': r[1],
                'vehicle_type': r[2],
                'lat': r[3],
                'lon': r[4],
                'battery_level': r[5],
                'status': r[6],
                'last_updated': r[7],
            }
            for r in rows
        ]
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


def main():
    init_db(DB_PATH)
    fetcher = DataFetcher(DB_PATH, FETCH_INTERVAL)
    fetcher.start()

    server_address = ('', 8000)
    handler = lambda *args, **kwargs: Handler(*args, db_path=DB_PATH, **kwargs)
    httpd = HTTPServer(server_address, handler)
    print('Serving on http://localhost:8000')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        fetcher.stop()
        httpd.server_close()


if __name__ == '__main__':
    main()
