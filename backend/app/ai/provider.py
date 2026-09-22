from abc import ABC,abstractmethod
class AIProvider(ABC):
 @abstractmethod
 async def generate(self,kind:str,payload:dict)->dict:...
