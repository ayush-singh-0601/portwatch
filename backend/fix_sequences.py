"""Fix auto-increment sequences after seed data insertion."""
import asyncio
import asyncpg

async def fix_sequences():
    conn = await asyncpg.connect("postgresql://postgres@localhost:5432/portwatch")
    
    sequences = [
        ("ownership_entities_id_seq", "ownership_entities"),
        ("ownership_edges_id_seq", "ownership_edges"),
        ("risk_scores_id_seq", "risk_scores"),
        ("risk_factors_id_seq", "risk_factors"),
        ("sanctions_entries_id_seq", "sanctions_entries"),
        ("sanctions_matches_id_seq", "sanctions_matches"),
        ("port_calls_id_seq", "port_calls"),
    ]
    
    for seq_name, table_name in sequences:
        max_id = await conn.fetchval(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
        await conn.execute(f"SELECT setval('{seq_name}', {max_id + 1}, false)")
        print(f"  {seq_name} reset to {max_id + 1}")
    
    # Current counts
    vc = await conn.fetchval("SELECT COUNT(*) FROM vessels")
    pc = await conn.fetchval("SELECT COUNT(*) FROM vessel_positions")
    print(f"\nVessels: {vc}")
    print(f"Positions: {pc}")
    
    await conn.close()

asyncio.run(fix_sequences())
