"""
api/dashboard.py — Fifty Fund dashboard data endpoint
Returns trades, AI log, and performance history from Postgres.
"""
import json
import os
from http.server import BaseHTTPRequestHandler

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_PUBLIC_URL", "")
STARTING_CASH = 50.0


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cur = conn.cursor()

            cur.execute("SELECT * FROM ff_trades ORDER BY created_at DESC LIMIT 100")
            trades = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT * FROM ff_ai_log ORDER BY created_at DESC LIMIT 200")
            ai_log = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT * FROM ff_performance ORDER BY date ASC")
            performance = [dict(r) for r in cur.fetchall()]

            cur.close()
            conn.close()

            total_trades = len([t for t in trades if t["action"] in ("BUY", "SELL")])
            latest_pv = float(performance[-1]["portfolio_value"]) if performance else STARTING_CASH
            total_return = round((latest_pv - STARTING_CASH) / STARTING_CASH * 100, 2)

            # Serialize datetime/date objects
            for row in trades + ai_log + performance:
                for k, v in row.items():
                    if hasattr(v, "isoformat"):
                        row[k] = v.isoformat()

            body = json.dumps({
                "portfolio_value": latest_pv,
                "starting_capital": STARTING_CASH,
                "total_return": total_return,
                "total_trades": total_trades,
                "trades": trades,
                "ai_log": ai_log,
                "performance_history": performance,
            }, default=str).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
