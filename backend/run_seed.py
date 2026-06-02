"""Execute seed SQL against Supabase using asyncpg."""
import asyncio
import sys

import asyncpg


async def main():
    import os
    from urllib.parse import urlparse, unquote
    
    # Load dotenv if available or import settings
    try:
        from dotenv import load_dotenv
        load_dotenv("../.env")
    except ImportError:
        pass

    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    
    # Replace asyncpg driver if present in url
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        
    parsed = urlparse(url)
    
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else None,
        database=parsed.path.lstrip('/'),
        ssl="require" if "supabase" in parsed.netloc else None,
    )

    print("Connected to Supabase!")

    # Read the SQL file
    with open("seed_data.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    # Execute the SQL
    try:
        await conn.execute(sql)
        print("Seed data loaded successfully!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # Try executing statements one by one if batch fails
        print("Trying individual statements...", file=sys.stderr)
        # Split on semicolons but keep the transaction commands
        statements = []
        current = []
        for line in sql.split("\n"):
            if line.startswith("--"):
                continue
            current.append(line)
            if line.rstrip().endswith(";"):
                stmt = "\n".join(current).strip()
                if stmt and stmt != ";":
                    statements.append(stmt)
                current = []

        success = 0
        errors = 0
        for stmt in statements:
            try:
                await conn.execute(stmt)
                success += 1
            except Exception as ex:
                errors += 1
                # Print first 100 chars of the failing statement
                preview = stmt[:100].replace("\n", " ")
                print(f"  SKIP: {preview}... => {ex}", file=sys.stderr)

        print(f"Done: {success} succeeded, {errors} failed")

    # Verify
    count = await conn.fetchval("SELECT COUNT(*) FROM vessels")
    print(f"Vessels in database: {count}")

    pos_count = await conn.fetchval("SELECT COUNT(*) FROM vessel_positions")
    print(f"Positions in database: {pos_count}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
