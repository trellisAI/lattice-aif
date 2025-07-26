#from LatticePy.tools.Agents import Agent

from typing import Dict, Any, List, Optional, Tuple


class llmClient:
    def __init__(self,**connection):
        self.llmsource = connection
        self.url = connection.get('url', 'http://localhost:11434/')
        self.api_key =  connection.get('api_key', None)
        self.conid = connection.get('id', 'default')

    def _client(self, n=500) -> object:
        if self.llmsource['source'] == "ollama":
            from ollama import Client as OllamaClient
            cl=OllamaClient(self.url, timeout=n)
            print(f"Connected to Ollama at {self.url}")
            return cl
        else:
            raise ValueError(f"Unsupported LLM source: {self.llmsource}")
        
    def models(self) -> List[Dict[str, Any]]:
        cl = self._client(n=60)
        mos=[]
        if cl and self.llmsource['source'] == "ollama":
            try:
                mode=(cl.list()).model_dump()
                for mod in mode.get('models', []):
                    mos.append({'name': f"{self.conid}_{mod.get('model', '')}", 'model':mod.get('model', ''), 'source': self.llmsource, 'details': mod})
                return mos
            except Exception as e:
                print(f"unable to fetch model details {e}")
            return []

    def chat(self, model: str, prompt: str , message: str, tools: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        cl = self._client()
        if cl and self.llmsource['source'] == "ollama":
            if tools:
                # If tools are provided, use them in the chat
                res = cl.chat(model=model, messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}], tools=tools)
                if res.message.tool_calls:
                    res_dict=res.model_dump()
                    print(res_dict)
                    return res_dict['message']['content'], res_dict['message']['tool_calls']
                return res.message.content, [{}]
            res=cl.chat(model=model, messages=[{'role':'user', 'content':message}])
            return res.message.content, [{}]
        

# class litellmClient: