import base64
import logging
import math
import os
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import chatbot
import comparison
import database
import llm_engine
import recommendations
from config import APP_NAME, APP_VERSION, OLLAMA_MODEL


logger = logging.getLogger(__name__)

app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description="JSON API for AutoVerse AI vehicle intelligence features.",
)

default_origins = (
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:5500,"
    "http://127.0.0.1:5500"
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv("AUTOVERSE_CORS_ORIGINS", default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class CompareRequest(BaseModel):
    model_names: list[str] = Field(min_length=2, max_length=3)


class RecommendationRequest(BaseModel):
    budget: float = Field(gt=0, le=1_000_000_000)
    fuel_preference: str = Field(default="Any", min_length=1, max_length=40)
    seats: int = Field(default=5, ge=1, le=12)
    transmission: str = Field(default="Any", min_length=1, max_length=40)
    usage: str = Field(default="Mixed", min_length=1, max_length=80)
    priority: str = Field(default="Fuel Efficiency", min_length=1, max_length=80)
    limit: int = Field(default=4, ge=1, le=10)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_history: list[ChatMessage] = Field(default_factory=list, max_length=20)


def _success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": jsonable_encoder(data)}


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return jsonable_encoder(_json_safe(frame.to_dict(orient="records")))


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "encoding": "base64",
            "data": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error = exc.detail
    else:
        error = {"code": "REQUEST_ERROR", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": jsonable_encoder(error)},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    issues = [
        {"location": issue["loc"], "message": issue["msg"], "type": issue["type"]}
        for issue in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request contains invalid parameters.",
                "details": jsonable_encoder(issues),
            },
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "The request could not be completed.",
            },
        },
    )


@app.get("/api/health")
def get_health() -> dict[str, Any]:
    stats = database.get_database_stats()
    ollama_online, models, ollama_error = llm_engine.check_ollama_status()
    configured_model_base = OLLAMA_MODEL.split(":", maxsplit=1)[0].lower()
    model_installed = any(
        model.split(":", maxsplit=1)[0].lower() == configured_model_base
        for model in models
    )
    return _success(
        {
            "status": "ok" if ollama_online and model_installed else "degraded",
            "database": {
                "available": True,
                "tables": len(stats),
                "records": sum(stats.values()),
            },
            "ollama": {
                "online": ollama_online,
                "configured_model": OLLAMA_MODEL,
                "model_installed": model_installed,
                "models": models,
                "error": ollama_error,
            },
        }
    )


@app.get("/api/vehicles")
def list_vehicles(
    query: str | None = Query(default=None, max_length=200),
    brand: str | None = Query(default=None, max_length=100),
    model: str | None = Query(default=None, max_length=100),
    fuel_type: str | None = Query(default=None, max_length=40),
    transmission: str | None = Query(default=None, max_length=40),
    min_price: float | None = Query(default=None, ge=0, le=1_000_000_000),
    max_price: float | None = Query(default=None, ge=0, le=1_000_000_000),
    city: str | None = Query(default=None, max_length=100),
    vehicle_type: Literal["All", "New", "Used"] = "All",
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    if min_price is not None and not math.isfinite(min_price):
        raise HTTPException(status_code=422, detail="min_price must be finite.")
    if max_price is not None and not math.isfinite(max_price):
        raise HTTPException(status_code=422, detail="max_price must be finite.")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=422, detail="min_price must not exceed max_price."
        )

    vehicles = database.search_vehicles(
        query=query,
        brand=brand,
        model=model,
        fuel_type=fuel_type,
        transmission=transmission,
        min_price=min_price,
        max_price=max_price,
        city=city,
        vehicle_type=vehicle_type,
        limit=limit,
    )
    records = _records(vehicles)
    return _success({"vehicles": records, "count": len(records)})


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(
    vehicle_id: str = Path(min_length=1, max_length=120),
) -> dict[str, Any]:
    # The existing detail function is keyed by exact model name, not a numeric ID.
    vehicle_id = vehicle_id.strip()
    if not vehicle_id:
        raise HTTPException(status_code=422, detail="vehicle_id must not be blank.")
    details = database.get_vehicle_details(vehicle_id)
    if not details:
        raise HTTPException(
            status_code=404,
            detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle model not found."},
        )
    details["variants"] = _records(details["variants"])
    return _success({"vehicle_id": vehicle_id, **details})


@app.post("/api/compare")
def compare_vehicles(request: CompareRequest) -> dict[str, Any]:
    model_names = [name.strip() for name in request.model_names]
    if any(not name or len(name) > 100 for name in model_names):
        raise HTTPException(
            status_code=422,
            detail="Model names must be non-blank and at most 100 characters.",
        )
    if len({name.casefold() for name in model_names}) != len(model_names):
        raise HTTPException(status_code=422, detail="Model names must be distinct.")

    known_models = set(database.get_models_by_brand())
    unknown_models = [name for name in model_names if name not in known_models]
    if unknown_models:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VEHICLE_NOT_FOUND",
                "message": "One or more vehicle models were not found.",
                "models": unknown_models,
            },
        )

    specs = database.get_comparison_data(model_names)
    if specs.empty:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "COMPARISON_UNAVAILABLE",
                "message": "Comparison data was not found for the selected models.",
            },
        )
    analysis = comparison.generate_ai_vehicle_comparison(model_names)
    return _success(
        {
            "models": model_names,
            "specifications": _records(specs),
            "analysis": analysis,
        }
    )


@app.post("/api/recommendations")
def get_recommendations(request: RecommendationRequest) -> dict[str, Any]:
    if not math.isfinite(request.budget):
        raise HTTPException(status_code=422, detail="budget must be finite.")
    preferences = {
        "fuel_preference": request.fuel_preference.strip(),
        "transmission": request.transmission.strip(),
        "usage": request.usage.strip(),
        "priority": request.priority.strip(),
    }
    if any(not value for value in preferences.values()):
        raise HTTPException(
            status_code=422, detail="Recommendation preferences must not be blank."
        )
    result = recommendations.get_ai_recommendations(
        budget=request.budget,
        fuel_preference=preferences["fuel_preference"],
        seats=request.seats,
        transmission=preferences["transmission"],
        usage=preferences["usage"],
        priority=preferences["priority"],
        limit=request.limit,
    )
    candidates = result["candidates"]
    return _success(
        {
            "candidates": _records(candidates),
            "total_matches": result["total_matches"],
            "ai_rationale": result["ai_rationale"],
        }
    )


@app.get("/api/analytics")
def get_analytics() -> dict[str, Any]:
    datasets = database.get_analytics_data()
    return _success({name: _records(frame) for name, frame in datasets.items()})


@app.post("/api/chat")
def post_chat(request: ChatRequest) -> dict[str, Any]:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be blank.")
    if any(not item.content.strip() for item in request.conversation_history):
        raise HTTPException(
            status_code=422, detail="Conversation history messages must not be blank."
        )
    history = [
        {"role": item.role, "content": item.content.strip()}
        for item in request.conversation_history[-4:]
    ]
    result = chatbot.handle_user_message(message, history)
    if result.get("is_error"):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "OLLAMA_UNAVAILABLE",
                "message": result["answer"],
            },
        )
    return _success(result)
