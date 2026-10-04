import os

import uvicorn


def main() -> None:
    """Start the FastAPI resume matching service."""
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.api:app", host=host, port=port)


if __name__ == "__main__":
    main()
