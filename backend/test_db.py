import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://hierardo:your_secure_password_here@localhost:5432/hierardo')
        print("Connected!")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(main())
