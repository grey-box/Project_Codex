from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import json
import os
import time
from datetime import datetime

app = FastAPI(
    title="Codex Middleware Translation Request API",
    description="Handles JSON passing between Frontend -> Translation Program -> Medication Database -> Frontend."
                "Now contains seperated paths more push-based, giving more control to those teams",
    version="2.2"
)

#Files fro inbetween checking and forwarding

TRANSLATION_INPUT = "translation_input.json"
TRANSLATION_OUTPUT = "translation_output.json"
BACKEND_INPUT = "lookup_input.json"
BACKEND_OUTPUT = "lookup_output.json"

#Added a log file to track info
LOG_FILE = "middleware.log"


#Basic Models for checking and formating
class FrontendInput(BaseModel):
    original_language: str
    requested_language: str
    original_medication: str

class TranslationInput(BaseModel):
    translated_medication: str
    supported: bool = True
    message: str | None = None

class BackendInputModel(BaseModel):
    matches: list
    success: bool = True

#Helper Functions

#Logs Info into Log File
def log_event(event: str, details: dict):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "event": event,
        "details": details
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

#Cleans up old JSONs after error or completed pathing.
def cleanup_all():
    for f in [
        TRANSLATION_INPUT,
        TRANSLATION_OUTPUT,
        BACKEND_INPUT,
        BACKEND_OUTPUT
    ]:
        if os.path.exists(f):
            os.remove(f)
    log_event("cleanup", {"status": "all temp JSONs deleted"})

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


#From Frontend to translation team for original medication translation.
@app.post("/frontend_to_translation")
async def frontend_to_translation(data: FrontendInput, request: Request):
    log_event("frontend_received", {
        "from": request.client.host,
        "payload": data.dict()
    })

    # Validates and Checks for any Errors, if User input Error throw 400 Bad Request
    if not data.original_language.strip():
        cleanup_all()
        raise HTTPException(400, "Original language cannot be empty")
    if not data.requested_language.strip():
        cleanup_all()
        raise HTTPException(400, "Requested language cannot be empty")
    if not data.original_medication.strip():
        cleanup_all()
        raise HTTPException(400, "Original medication cannot be empty")

    #Writes JSON to forward to the Translation team after cleanup, also Logs info.
    write_json(TRANSLATION_INPUT, data.dict())
    log_event("translation_input_written", data.dict())

    return {"status": "OK", "message": "Forwarded to translation team"}


#Translation team to Backend.
@app.post("/translation_to_backend")
async def translation_to_backend(data: TranslationInput, request: Request):

    log_event("translation_output_received", {
        "from": request.client.host,
        "payload": data.dict()
    })

    # 400 Bad Request Error, if data is unsupported will send this.
    if data.supported is False:
        cleanup_all()
        raise HTTPException(400, f"Translation error: {data.message}")

    # 500 Unexpected Error, nothing returned from translation
    if not data.translated_medication.strip():
        cleanup_all()
        raise HTTPException(500, "No translated medication returned")

    # Missing original JSON, throws 500 Unexpected Error
    if not os.path.exists(TRANSLATION_INPUT):
        cleanup_all()
        raise HTTPException(500, "Missing original frontend JSON")

    original = json.load(open(TRANSLATION_INPUT))

    # Makes backend Input JSON
    backend_input = {
        "translated_medication": data.translated_medication.strip(),
        "requested_language": original["requested_language"],
        "original_medication": original["original_medication"]
    }

    write_json(BACKEND_INPUT, backend_input)
    log_event("backend_input_written", backend_input)

    return {"status": "OK", "message": "Forwarded to backend team"}

#Backend to frontend final output

@app.post("/backend_to_frontend")
async def backend_to_frontend(data: BackendInputModel, request: Request):

    log_event("backend_output_received", {
        "from": request.client.host,
        "payload": data.dict()
    })

    # Throws 404 Not Found Error, Bakcend has no matching medication
    if not data.success:
        cleanup_all()
        raise HTTPException(404, "No matching medications found")

    #Throws 500 Unexpected error, invalid data returned
    if data.matches is None or not isinstance(data.matches, list):
        cleanup_all()
        raise HTTPException(500, "Backend returned invalid match data")

    # Checks for original inputs if not found throws 500 Unexpected Error
    if not os.path.exists(TRANSLATION_INPUT):
        cleanup_all()
        raise HTTPException(500, "Lost original frontend input")

    if not os.path.exists(BACKEND_INPUT):
        cleanup_all()
        raise HTTPException(500, "Lost backend input")

    original = json.load(open(TRANSLATION_INPUT))
    backend_in = json.load(open(BACKEND_INPUT))

    # Configures final JSON Response to send to front end, then Logs it.
    final_output = {
        "original_language": original["original_language"],
        "requested_language": original["requested_language"],
        "original_medication": original["original_medication"],
        "translated_medication": backend_in["translated_medication"],
        "medication_matches": [
            {"generic": m.get("generic"), "brand": m.get("brand")}
            for m in data.matches
        ]
    }

    log_event("final_output_sent", final_output)

    # Cleans up everything to ensure info is passed correctly.
    cleanup_all()

    return final_output