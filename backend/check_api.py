"""Quick API health check."""
import asyncio
import json
import httpx

async def check():
    async with httpx.AsyncClient() as c:
        r = await c.get("http://localhost:8000/health")
        print("Health:", r.json())

        r2 = await c.get("http://localhost:8000/api/vessels?per_page=3")
        d = r2.json()
        print("Vessels total:", d.get("total"))
        if d.get("items"):
            for v in d["items"][:3]:
                print("  %s (IMO %s) flag=%s type=%s" % (v["name"], v["imo"], v.get("flag"), v.get("vessel_type")))

        r3 = await c.get("http://localhost:8000/api/enriched/vessels")
        ev = r3.json()
        print("Enriched vessels:", len(ev) if isinstance(ev, list) else "N/A")
        if isinstance(ev, list) and ev:
            v = ev[0]
            print("  Sample: %s risk=%s lat=%s lon=%s" % (v.get("name"), v.get("risk_score"), v.get("latitude"), v.get("longitude")))

asyncio.run(check())
