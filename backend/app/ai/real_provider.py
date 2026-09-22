import json,httpx
from .provider import AIProvider
from .mock_provider import MockAIProvider
from ..config.settings import settings
class RealAIProvider(AIProvider):
 async def generate(self,kind,payload):
  prompt=f"Return valid JSON only. Educational diagnostic task: {kind}. Input: {json.dumps(payload)}. Never diagnose personality or psychology."
  try:
   async with httpx.AsyncClient(timeout=20) as c:
    r=await c.post(f'{settings.ai_base_url}/chat/completions',headers={'Authorization':f'Bearer {settings.ai_api_key}'},json={'model':settings.ai_model,'response_format':{'type':'json_object'},'messages':[{'role':'user','content':prompt}]}); r.raise_for_status()
    return json.loads(r.json()['choices'][0]['message']['content'])
  except Exception:return await MockAIProvider().generate(kind,payload)
def provider():return RealAIProvider() if settings.ai_api_key else MockAIProvider()
