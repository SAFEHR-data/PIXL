from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hasher import __version__, icon, settings

package = "hasher"

app = FastAPI(
    title=package,
    description=f"{icon} Secure Hashing Service ",
    version=__version__,
    debug=settings.DEBUG,  # type: ignore
    default_response_class=JSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/heart-beat", summary="GET Health Check")
async def heart_beat() -> str:
    return "OK"
