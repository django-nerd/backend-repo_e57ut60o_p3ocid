import os
import random
from datetime import datetime, timezone
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
