import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pydantic import BaseModel

from .compiler import TelosVMCompiler
from .core import HallucinationError, TelosCompilationError, TelosExecutionError
from .executor import WasmExecutor

# Set up Enterprise OpenTelemetry Tracing
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
tracer = trace.get_tracer(__name__)

# Set up structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("telosvm_control_plane")

app = FastAPI(
    title="TelosVM Inference Control Plane",
    description="The world's first AI-Native Semantic Compiler and Execution Gatekeeper with OpenTelemetry.",
    version="1.0.0"
)

FastAPIInstrumentor.instrument_app(app)

compiler = TelosVMCompiler()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Outgoing response: {response.status_code}")
    return response

class CompileResponse(BaseModel):
    status: str
    wat_code: str | None = None
    error: str | None = None
    repair_prompt: str | None = None

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/compile", response_model=CompileResponse)
def compile_llm_intent(payload: dict[str, Any]):
    import json
    try:
        ast = compiler.parse_and_verify(json.dumps(payload))
        wat_code = compiler.compile_to_wat(ast)
        return CompileResponse(status="success", wat_code=wat_code)
    except HallucinationError as e:
        return CompileResponse(status="hallucination_detected", error=str(e), repair_prompt=f"Hallucination: {str(e)}.")
    except TelosCompilationError as e:
        return CompileResponse(status="schema_error", error=str(e), repair_prompt=f"Schema violation: {str(e)}.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute")
def execute_compiled_wat(payload: dict[str, str]):
    wat_code = payload.get("wat_code")
    if not wat_code: raise HTTPException(status_code=400, detail="Missing 'wat_code' field.")
    try:
        result = WasmExecutor.execute(wat_code)
        return {"status": "success", "result": result}
    except TelosExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))
