import json
import os
import http.client
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        api_key    = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        base_url   = os.environ.get("ALPACA_BASE_URL", "https://api.alpaca.markets")

        if not api_key or not secret_key:
            self._send(500, {"error": "Alpaca credentials not configured"})
            return

        try:
            hostname = urllib.parse.urlparse(base_url).hostname
            hdrs = {
                "APCA-API-KEY-ID":     api_key,
                "APCA-API-SECRET-KEY": secret_key,
                "Accept":              "application/json",
            }

            conn = http.client.HTTPSConnection(hostname, timeout=10)
            conn.request("GET", "/v2/account", headers=hdrs)
            account = json.loads(conn.getresponse().read().decode())
            conn.close()

            conn = http.client.HTTPSConnection(hostname, timeout=10)
            conn.request("GET", "/v2/positions", headers=hdrs)
            positions = json.loads(conn.getresponse().read().decode())
            conn.close()

            STARTING_CASH = 50.00
            pv   = float(account.get("portfolio_value", 0))
            cash = float(account.get("cash", 0))

            holdings = []
            for p in (positions if isinstance(positions, list) else []):
                qty        = float(p.get("qty", 0))
                avg_cost   = float(p.get("avg_entry_price", 0))
                mkt_val    = float(p.get("market_value", 0))
                unreal_pl  = float(p.get("unrealized_pl", 0))
                cost_basis = avg_cost * qty
                holdings.append({
                    "ticker":            p.get("symbol"),
                    "qty":               round(qty, 6),
                    "avg_cost":          round(avg_cost, 4),
                    "current_price":     round(float(p.get("current_price", 0)), 4),
                    "market_value":      round(mkt_val, 2),
                    "unrealized_pl":     round(unreal_pl, 2),
                    "unrealized_pl_pct": round(unreal_pl / cost_basis * 100, 2) if cost_basis else 0.0,
                })

            self._send(200, {
                "portfolio_value":  round(pv, 2),
                "starting_capital": STARTING_CASH,
                "cash":             round(cash, 2),
                "total_return":     round((pv - STARTING_CASH) / STARTING_CASH * 100, 2),
                "holdings":         holdings,
                "last_updated":     datetime.utcnow().isoformat() + "Z",
                "source":           "alpaca-live",
            })

        except Exception as exc:
            self._send(500, {"error": str(exc)})

    def _send(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
