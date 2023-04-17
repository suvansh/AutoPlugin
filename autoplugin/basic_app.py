from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def get_app():
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # You can specify a list of allowed origins, or use ["*"] to allow all origins.
        allow_credentials=True,
        allow_methods=["*"],  # You can specify a list of allowed methods, or use ["*"] to allow all methods.
        allow_headers=["*"],  # You can specify a list of allowed headers, or use ["*"] to allow all headers.
    )
    return app