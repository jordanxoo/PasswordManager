from unittest.mock import AsyncMock
import asyncio                                                                           
db = AsyncMock()                                                                         
db.execute.return_value.scalar_one_or_none.return_value = None
async def test():                                                                        
    result = await db.execute('query')
    print(result.scalar_one_or_none())
    await asyncio.run(test())
