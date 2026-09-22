from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import Base,engine
from .api.routes import router
from .config.settings import settings
Base.metadata.create_all(engine)
app=FastAPI(title='CalibrateAI API',version='1.0.0',description='Competence calibration and evidence-based learning diagnostics')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(router)
@app.get('/api/health')
def health():return {'status':'ok','ai_mode':'real' if settings.ai_api_key else 'demo'}
@app.exception_handler(Exception)
async def safe_error(request:Request,exc:Exception):return JSONResponse(status_code=500,content={'detail':'An unexpected error occurred. Please retry.'})
