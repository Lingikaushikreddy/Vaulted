from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio

app = FastAPI(title="Vaulted Enterprise Gateway")

class ModelRequest(BaseModel):
    client_id: str
    model_type: str
    target_tags: list[str]

@app.get("/")
def read_root():
    return {"status": "online", "system": "VAULTED Gateway"}

@app.post("/request-training")
async def request_training(request: ModelRequest):
    """
    Endpoint for enterprises to request a model training session.
    """
    print(f"Received training request from {request.client_id} for {request.model_type}")
    
    # Placeholder: In a real system, this would:
    # 1. Check Compliance/Consent (is client_id allowed?)
    # 2. Trigger the FL Orchestrator
    
    # simulating a check
    if request.client_id == "unauthorized_corp":
        raise HTTPException(status_code=403, detail="Consent denied for this entity.")
    
    return {
        "job_id": "job_12345", 
        "status": "initiated", 
        "message": "Federated Learning round scheduled."
    }

def start_gateway():
    print("Starting Secure Enterprise Gateway (TLS 1.3)...")
    # Enforce TLS
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )

if __name__ == "__main__":
    start_gateway()
