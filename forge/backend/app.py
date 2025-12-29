"""FastAPI backend for Forge (future implementation)"""

from fastapi import FastAPI

# This is a placeholder for future backend implementation
# The MVP runs entirely locally, but the architecture is designed
# to support a FastAPI backend for:
# - Job orchestration
# - Test generation queues
# - Result persistence
# - Dashboard APIs

app = FastAPI(title="Forge API", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Forge API - Coming soon"}

