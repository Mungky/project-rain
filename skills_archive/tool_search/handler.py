async def run(inputs: dict) -> dict:
    query = inputs.get("query", "")
    return {"status": "mock", "message": f"Found tool/skill matching '{query}'. Proceed to use it."}