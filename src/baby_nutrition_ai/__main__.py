"""Run with: python -m baby_nutrition_ai"""

import uvicorn

from baby_nutrition_ai.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "baby_nutrition_ai.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
