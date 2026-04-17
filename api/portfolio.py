"""
api/portfolio.py — Vercel serverless function
Proxies live portfolio data from Alpaca to the dashboard.
Deploy to Vercel — secret keys stay safe in Vercel env vars.
"""

import json
import os
import http.client
import urllib.parse
from datetime import datetime

def handler(request):
    """Vercel Python serverless handler."""

    # ── CORS headers — allow fiftyfund.ai to call this ──────────────────────
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    if request.method == "OPTIONS":
        return Response("", 200, headers)

    api_key    = os.environ.get("ALPACA_API_KEY", "")
    secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
    base_url   = os.environ.get("ALPACA_BASE_URL", "https://api.alpaca.markets")

    if not api_key or not secret_key:
        return Response(
            json.dumps({"error": "Alpaca credentials not configured"}),
            500, headers
        )

    try:
        # Parse hostname from base_url
        parsed   = urllib.parse.urlparse(base_url)
        hostname = parsed.hostname  # e.g. "api.alpaca.markets"

        alpaca_headers = {
            "APCA-API-KEY-ID":     api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Accept":              "application/json",
        }

        # ── Fetch account ────────────────────────────────────────────────────
        conn = http.client.HTTPSConnection(hostname, timeout=10)
        conn.request("GET", "/v2/account", headers=alpaca_headers)
        resp    = conn.getresponse()
        account = json.loads(resp.read().decode())
        conn.close()

        # ── Fetch positions ──────────────────────────────────────────────────
        conn = http.client.HTTPSConnection(hostname, timeout=10)
        conn.request("GET", "/v2/positions", headers=alpaca_headers)
        resp      = conn.getresponse()
        positions = json.loads(resp.read().decode())
        conn.close()

        # ── Build response ───────────────────────────────────────────────────
        STARTING_CASH = 50.00
        pv   = float(account.get("portfolio_value", 0))
        cash = float(account.get("cash", 0))

        holdings = []
        for p in (positions if isinstance(positions, list) else []):
            qty       = float(p.get("qty", 0))
            avg_cost  = float(p.get("avg_entry_price", 0))
            cur_price = float(p.get("current_price", 0))
            mkt_val   = float(p.get("market_value", 0))
            unreal_pl = float(p.get("unrealized_pl", 0))
            cost_basis = avg_cost * qty
            unreal_pct = round(unreal_pl / cost_basis * 100, 2) if cost_basis else 0.0
            holdings.append({
                "ticker":            p.get("symbol"),
                "qty":               round(qty, 6),
                "avg_cost":          round(avg_cost, 4),
                "current_price":     round(cur_price, 4),
                "market_value":      round(mkt_val, 2),
                "unrealized_pl":     round(unreal_pl, 2),
                "unrealized_pl_pct": unreal_pct,
            })

        data = {
            "portfolio_value":  round(pv, 2),
            "starting_capital": STARTING_CASH,
            "cash":             round(cash, 2),
            "total_return":     round((pv - STARTING_CASH) / STARTING_CASH * 100, 2),
            "holdings":         holdings,
            "last_updated":     datetime.utcnow().isoformat() + "Z",
            "source":           "alpaca-live",
        }

        return Response(json.dumps(data), 200, headers)

    except Exception as exc:
        return Response(
            json.dumps({"error": str(exc)}),
            500, headers
        )


class Response:
    """Minimal response wrapper for Vercel Python runtime."""
    def __init__(self, body: str, status: int = 200, headers: dict = None):
        self.body    = body
        self.status  = status
        self.headers = headers or {}
