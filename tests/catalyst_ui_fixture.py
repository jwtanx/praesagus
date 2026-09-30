"""Synthetic UI review server; never loads project datasets or providers.

Run: python3 tests/catalyst_ui_fixture.py
Then: cd frontend && VITE_API_BASE_URL=http://localhost:8015 npm run dev -- --port 5179
Review http://localhost:5179/financial and http://localhost:8015/mobile.
Ticker EMPTY returns no rows, FAIL returns a 503, SLOW delays three seconds.
"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.catalyst_services import get_catalysts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5179', 'http://127.0.0.1:5179'], allow_headers=['*'])
base = tempfile.TemporaryDirectory(prefix='catalyst-ui-fixture-')
now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
rows = [{'source_id': f'news-{i:03}', 'ticker': 'AAPL', 'title': f'Frozen disclosure {i + 1} · synthetic fixture',
         'source_name': 'Fixture provider', 'published_at': '2026-10-01T10:00:00+02:00',
         'first_seen_at': '2026-10-01T08:05:00Z', 'ingest_ts': '2026-10-01T08:06:00Z',
         'link': 'https://example.org/source'} for i in range(52)]
Path(base.name, 'news.json').write_text(json.dumps(rows))
Path(base.name, 'calendar.json').write_text(json.dumps({'records': [
    {'source_id': 'macro-1', 'event_date': '2026-10-02', 'title': 'Upcoming global release · synthetic fixture',
     'event_type': 'macro', 'estimated': True, 'metadata': {'source_url': 'https://example.org/calendar'}},
    None,
]}))
Path(base.name, 'filings.json').write_text('{malformed fixture')


@app.get('/api/v1/financial/catalysts')
async def catalysts(ticker=None, event_type=None, limit: int = 50, offset: int = 0):
    if ticker == 'FAIL':
        raise HTTPException(503, 'Synthetic read failure')
    if ticker == 'SLOW':
        await asyncio.sleep(3)
        ticker = None
    return get_catalysts(ticker=ticker, event_type=event_type, limit=limit, offset=offset, now=now, data_dir=base.name)


@app.get('/api/v1/financial/{dataset}')
def empty_panels(dataset: str):
    return {'records': [], 'count': 0, 'counts': {}}


@app.get('/mobile', response_class=HTMLResponse)
def mobile():
    return '<html><meta name="viewport" content="width=device-width, initial-scale=1"><body style="margin:0;background:#ddd"><iframe title="Mobile Financial page at 390 pixels" src="http://localhost:5179/financial" style="width:390px;height:844px;border:0"></iframe></body></html>'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8015)
