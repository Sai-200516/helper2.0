from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google.generativeai import GenerativeModel, configure
import os
import uvicorn
import time
import logging
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Gemini Chatbot API")

# Trial constants
TRIAL_ACTIVATION_CODE = "Helper2.0_Trail"
TRIAL_REG_NO = "Helper2.0_Trail"  # Shared trial reg_no
TRIAL_COMMAND_LIMIT = 20
TRIAL_EXPIRY = datetime(2025, 5, 21, 7, 0, 0, tzinfo=pytz.timezone("Asia/Kolkata"))
PREMIUM_EMAIL = os.getenv("gmail", "gmail")
PREMIUM_PRICE = 500

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongo_db_uri")
try:
    client = MongoClient(MONGO_URI)
    db = client["helper_db"]
    reg_nos_collection = db["reg_nos"]
    activations_collection = db["activations"]
    trial_usage_collection = db["trial_usage"]
    # Create unique indexes
    reg_nos_collection.create_index("reg_no", unique=True)
    activations_collection.create_index("reg_no", unique=True)
    activations_collection.create_index("mac_address", unique=True)
    trial_usage_collection.create_index("mac_address", unique=True)
    logger.info("Connected to MongoDB and initialized collections")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

# Configure Gemini API
try:
    API_KEY = os.getenv("GEMINI_API_KEY", "Your Gemini Api Key")
    configure(api_key=API_KEY)
    model = GenerativeModel("gemini-1.5-flash")
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {str(e)}")
    raise

# API key authentication
API_KEY_NAME = "X-API-Key"
API_KEY_VALUE = os.getenv("API_KEY_VALUE", "APi Key Value")
api_key_header = APIKeyHeader(name=API_KEY_NAME)

# Admin API key authentication
ADMIN_API_KEY_NAME = "X-Admin-API-Key"
ADMIN_API_KEY_VALUE = os.getenv("HELPER_ADMIN_API_KEY", "Helper")
admin_api_key_header = APIKeyHeader(name=ADMIN_API_KEY_NAME)

# Registration number and MAC address headers
REG_NO_NAME = "X-Reg-No"
MAC_ADDRESS_NAME = "X-MAC-Address"

# Cache for responses
cache = {}

class ChatRequest(BaseModel):
    query: str

class ActivationRequest(BaseModel):
    reg_no: str
    mac_address: str

class AddRegNoRequest(BaseModel):
    reg_no: str
    is_active: bool = True

class TrialActivationRequest(BaseModel):
    activation_code: str
    mac_address: str

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY_VALUE:
        logger.warning(f"Invalid API key provided: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

def verify_admin_api_key(admin_api_key: str = Depends(admin_api_key_header)):
    if admin_api_key != ADMIN_API_KEY_VALUE:
        logger.warning(f"Invalid admin API key provided")
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return admin_api_key

def verify_reg_no(reg_no: str = Depends(APIKeyHeader(name=REG_NO_NAME)), mac_address: str = Depends(APIKeyHeader(name=MAC_ADDRESS_NAME))):
    if reg_no == TRIAL_REG_NO:
        # Check trial usage for MAC address
        trial_usage = trial_usage_collection.find_one({"mac_address": mac_address, "reg_no": reg_no})
        if not trial_usage:
            logger.warning(f"No trial activation found for mac_address={mac_address}, reg_no={reg_no}")
            raise HTTPException(status_code=403, detail="No trial activation found for this MAC address")
    else:
        # Check premium activation
        activation = activations_collection.find_one({"reg_no": reg_no})
        if not activation:
            logger.warning(f"Invalid or unactivated reg_no: {reg_no}")
            raise HTTPException(status_code=403, detail="Invalid or unactivated registration number")
        if activation["mac_address"] != mac_address:
            logger.warning(f"MAC address mismatch for reg_no={reg_no}. Stored: {activation['mac_address']}, Provided: {mac_address}")
            raise HTTPException(status_code=403, detail="MAC address does not match the registered MAC address")
    return reg_no

@app.on_event("startup")
async def startup_event():
    try:
        # Ensure trial reg_no exists
        reg_nos_collection.update_one(
            {"reg_no": TRIAL_REG_NO},
            {
                "$setOnInsert": {
                    "reg_no": TRIAL_REG_NO,
                    "is_active": True,
                    "created_at": datetime.now(pytz.UTC).isoformat(),
                    "is_trial": True
                }
            },
            upsert=True
        )
        logger.info(f"Trial reg_no {TRIAL_REG_NO} initialized")
    except Exception as e:
        logger.error(f"Failed to initialize trial reg_no: {str(e)}")
        raise

@app.post("/admin/add_reg_no")
async def add_reg_no(
    request: AddRegNoRequest,
    admin_api_key: str = Depends(verify_admin_api_key)
):
    logger.info(f"Admin adding reg_no: {request.reg_no}, is_active: {request.is_active}")
    try:
        reg_nos_collection.insert_one({
            "reg_no": request.reg_no,
            "is_active": request.is_active,
            "created_at": datetime.now(pytz.UTC).isoformat(),
            "is_trial": False
        })
        logger.info(f"Successfully added reg_no: {request.reg_no}")
        return {"message": f"Registration number {request.reg_no} added successfully"}
    except DuplicateKeyError:
        logger.warning(f"Registration number already exists: {request.reg_no}")
        raise HTTPException(status_code=400, detail="Registration number already exists")
    except Exception as e:
        logger.error(f"Failed to add reg_no: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add reg_no: {str(e)}")

@app.post("/trial_activate")
async def trial_activate(request: TrialActivationRequest):
    logger.info(f"Trial activation request: code={request.activation_code}, mac_address={request.mac_address}")

    # Verify activation code
    if request.activation_code != TRIAL_ACTIVATION_CODE:
        logger.warning(f"Invalid trial activation code: {request.activation_code}")
        raise HTTPException(status_code=400, detail="Invalid trial activation code")

    # Check if mac_address is already used for trial or premium
    if trial_usage_collection.find_one({"mac_address": request.mac_address}):
        logger.warning(f"MAC address already used for trial: {request.mac_address}")
        raise HTTPException(status_code=400, detail="MAC address already used for trial")
    if activations_collection.find_one({"mac_address": request.mac_address}):
        logger.warning(f"MAC address already associated with premium: {request.mac_address}")
        raise HTTPException(status_code=400, detail="MAC address already associated with a premium registration")

    # Store trial usage for this MAC address
    try:
        trial_usage_collection.insert_one({
            "mac_address": request.mac_address,
            "reg_no": TRIAL_REG_NO,
            "command_count": 0,
            "created_at": datetime.now(pytz.UTC).isoformat()
        })
        logger.info(f"Trial activation successful for mac_address={request.mac_address}, reg_no={TRIAL_REG_NO}")
        return {"message": "Trial activation successful", "reg_no": TRIAL_REG_NO}
    except DuplicateKeyError:
        logger.warning(f"Trial activation conflict for mac_address={request.mac_address}")
        raise HTTPException(status_code=400, detail="Trial activation conflict, please try again")
    except Exception as e:
        logger.error(f"Trial activation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trial activation failed: {str(e)}")

@app.post("/activate")
async def activate(
    request: ActivationRequest,
    api_key: str = Depends(verify_api_key)
):
    reg_no = request.reg_no
    mac_address = request.mac_address
    logger.info(f"Activation request: reg_no={reg_no}, mac_address={mac_address}")

    # Check if reg_no exists and is active
    reg_no_doc = reg_nos_collection.find_one({"reg_no": reg_no})
    if not reg_no_doc:
        logger.warning(f"Registration number not found: {reg_no}")
        raise HTTPException(status_code=400, detail="Registration number not found")
    if not reg_no_doc["is_active"]:
        logger.warning(f"Registration number is inactive: {reg_no}")
        raise HTTPException(status_code=400, detail="Registration number is inactive")
    if reg_no_doc.get("is_trial"):
        logger.warning(f"Trial reg_no cannot be used for premium activation: {reg_no}")
        raise HTTPException(status_code=400, detail="Trial registration number cannot be used for premium activation")

    # Check if reg_no is already activated
    existing_activation = activations_collection.find_one({"reg_no": reg_no})
    if existing_activation:
        # Check if the provided MAC address matches the stored MAC address
        if existing_activation["mac_address"] == mac_address:
            logger.info(f"MAC address matches for reg_no={reg_no}. Updating activation.")
            try:
                activations_collection.update_one(
                    {"reg_no": reg_no},
                    {
                        "$set": {
                            "mac_address": mac_address,
                            "activation_timestamp": datetime.now(pytz.UTC).isoformat()
                        }
                    }
                )
                logger.info(f"Re-activation successful: reg_no={reg_no}, mac_address={mac_address}")
                return {"message": "Activation successful"}
            except Exception as e:
                logger.error(f"Re-activation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Re-activation failed: {str(e)}")
        else:
            logger.warning(f"MAC address mismatch for reg_no={reg_no}. Stored: {existing_activation['mac_address']}, Provided: {mac_address}")
            raise HTTPException(status_code=400, detail="MAC address does not match the stored MAC address")

    # Check if mac_address is already associated with another registration
    if activations_collection.find_one({"mac_address": mac_address}):
        logger.warning(f"MAC address already associated with another registration: {mac_address}")
        raise HTTPException(status_code=400, detail="MAC address already associated with another registration")

    # Store new activation
    try:
        activations_collection.insert_one({
            "reg_no": reg_no,
            "mac_address": mac_address,
            "activation_timestamp": datetime.now(pytz.UTC).isoformat(),
            "is_trial": False
        })
        logger.info(f"Activation successful: reg_no={reg_no}, mac_address={mac_address}")
        return {"message": "Activation successful"}
    except Exception as e:
        logger.error(f"Activation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")

@app.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    reg_no: str = Depends(verify_reg_no),
    mac_address: str = Depends(APIKeyHeader(name=MAC_ADDRESS_NAME))
):
    start_time = time.time()
    logger.info(f"Processing query: {request.query} (reg_no={reg_no}, mac_address={mac_address})")

    # Check if reg_no is trial
    current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
    if reg_no == TRIAL_REG_NO:
        # Check trial expiry
        if current_time > TRIAL_EXPIRY:
            logger.info(f"Trial expired for reg_no={reg_no}, mac_address={mac_address}")
            raise HTTPException(
                status_code=403,
                detail=f"Trial period has ended. Please contact {PREMIUM_EMAIL} to get a premium subscription for all exams at ?{PREMIUM_PRICE}."
            )

        # Check command limit for this MAC address
        trial_usage = trial_usage_collection.find_one({"mac_address": mac_address, "reg_no": reg_no})
        command_count = trial_usage.get("command_count", 0)
        if command_count >= TRIAL_COMMAND_LIMIT:
            logger.info(f"Trial command limit reached for mac_address={mac_address}")
            raise HTTPException(
                status_code=403,
                detail=f"Trial command limit of {TRIAL_COMMAND_LIMIT} reached. Please contact {PREMIUM_EMAIL} to get a premium subscription for all exams at ?{PREMIUM_PRICE}."
            )

        # Increment command count
        trial_usage_collection.update_one(
            {"mac_address": mac_address, "reg_no": reg_no},
            {"$inc": {"command_count": 1}}
        )
        logger.info(f"Trial command count updated: {command_count + 1}/{TRIAL_COMMAND_LIMIT} for mac_address={mac_address}")

    # Check cache
    if request.query in cache:
        elapsed = time.time() - start_time
        logger.info(f"Cache hit: {request.query} ({elapsed:.2f}s)")
        return {"response": cache[request.query]}

    # Process query
    try:
        response = model.generate_content(request.query)
        if not response.text:
            raise ValueError("Empty response from Gemini API")
        cache[request.query] = response.text
        elapsed = time.time() - start_time
        logger.info(f"API call successful: {request.query} ({elapsed:.2f}s)")
        return {"response": response.text}
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Gemini API error: {str(e)} ({elapsed:.2f}s)")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    