# VoltGoblin X Tracker

This project collects real-time data from the City of Edmonton micromobility API and provides a small web interface to visualize available e-scooters and e-bikes.

## Requirements

* Python 3.12 or newer
* Internet access to fetch the API and map tiles

No external Python packages are needed.

## Usage

```bash
python3 run.py
```

The server listens on `http://localhost:8000`. Open that address in a browser to see the map and the list of vehicles.

Data is stored in `data.db` (SQLite) and is updated roughly every minute.

## API Endpoints

* `/api/latest` – returns the most recent snapshot in JSON
* `/api/history?start=YYYY-MM-DDTHH:MM:SS&end=YYYY-MM-DDTHH:MM:SS` – returns historical records between the given UTC timestamps.

