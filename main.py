import os
import random
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TCR Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "TCR Finance Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/rates")
def get_rates():
    """
    Return indicative rates for USDT ⇄ BRL. These are demo quotes with light jitter.
    """
    # Base rates (indicative)
    base_usdt_to_brl = 5.40  # BRL you get for 1 USDT
    base_brl_to_usdt = 1 / 5.48  # USDT you get for 1 BRL (includes spread)
    base_spread_bps = 45  # basis points

    # Add small random jitter to simulate live movement
    jitter_brl = random.uniform(-0.03, 0.03)
    jitter_usdt = random.uniform(-0.0002, 0.0002)
    jitter_bps = random.randint(-5, 5)

    usdt_to_brl = max(0.0, base_usdt_to_brl + jitter_brl)
    brl_to_usdt = max(0.0, base_brl_to_usdt + jitter_usdt)
    spread_bps = max(0, base_spread_bps + jitter_bps)

    return {
        "usdt_to_brl": usdt_to_brl,
        "brl_to_usdt": brl_to_usdt,
        "spread_bps": spread_bps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _safe_get(url: str, timeout: float = 4.0) -> Dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@app.get("/ticker")
def ticker():
    """
    Aggregate real-time public data for ticker bar with graceful fallbacks.
    Sources used (no API keys):
      - Binance prices (USDTBRL, BTCBRL, ETHBRL)
      - Etherchain Gas Oracle (ETH gwei)
      - Polygon Gas Station v2 (Polygon gwei)
    """
    now = datetime.now(timezone.utc).isoformat()

    # Prices (BRL pairs) — Binance
    price_symbols = {
        "USDTBRL": None,
        "BTCBRL": None,
        "ETHBRL": None,
    }
    for sym in price_symbols.keys():
        data = _safe_get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}")
        try:
            price_symbols[sym] = float(data.get("price")) if data.get("price") else None
        except Exception:
            price_symbols[sym] = None

    # ETH Gas (gwei) — Etherchain
    eth_gas_data = _safe_get("https://www.etherchain.org/api/gasPriceOracle")
    eth_gwei = None
    if eth_gas_data:
        # Use 'standard' if available, else try 'currentBaseFee'
        eth_gwei = (
            eth_gas_data.get("standard")
            or eth_gas_data.get("safeLow")
            or eth_gas_data.get("currentBaseFee")
        )
        try:
            eth_gwei = float(eth_gwei) if eth_gwei is not None else None
        except Exception:
            eth_gwei = None

    # Polygon Gas (gwei) — Gas Station
    poly_gas_data = _safe_get("https://gasstation-mainnet.matic.network/v2")
    polygon_gwei = None
    if poly_gas_data:
        # Data example: { standard: { maxFee: 55, maxPriorityFee: 35 }, ... }
        std = poly_gas_data.get("standard") or {}
        polygon_gwei = std.get("maxFee") or std.get("maxPriorityFee")
        try:
            polygon_gwei = float(polygon_gwei) if polygon_gwei is not None else None
        except Exception:
            polygon_gwei = None

    result = {
        "timestamp": now,
        "prices": {
            "USDTBRL": price_symbols.get("USDTBRL"),
            "BTCBRL": price_symbols.get("BTCBRL"),
            "ETHBRL": price_symbols.get("ETHBRL"),
        },
        "gas": {
            "ETH_gwei": eth_gwei,
            "Polygon_gwei": polygon_gwei,
        },
        "status": {
            "desk": "Online",
            "latency_ms": 100 + int(random.random() * 80),
        },
    }

    return result


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
