#from LatticePy.tools.Agents import Agent

from typing import Dict, Any, List, Optional, Tuple
import json


class llmClient:
    registry={}
    def __init__(self, connection, timeout=300):
        self.connection=connection.model_dump(exclude_unset=True)
        self.llmsource = self.connection.get('source', 'ollama')
        self.url = self.connection.get('url', 'http://localhost:11434/')
        self.api_key =  self.connection.get('api_key', None)
        self.conid = self.connection.get('id', 'default')
        if self.connection.get('details'):
            self.details=json.loads(self.connection.get('details'))
        else:
            self.details={}
        self.modelname=self.connection.get('model', None)
        self.timeout=timeout
    
    @classmethod
    def reigister(cls,name):
        def llmprovider(subclass):
            print(f"Registering {name} LLM provider")
            cls.registry[name] = subclass
            return subclass
        return llmprovider

    @classmethod
    def get_client(cls, connection: Dict[str, Any]):
        if connection.source == "ollama":
            return OllamalClient(connection)
        if connection.source == "openai":
            return OpenAIClient(connection)
        if connection.source == "azure":
            return AzureOpenAIclient(connection)
        if connection.source == "gemini":
            return GeminiClient(connection)
        else:
            raise ValueError(f"Unsupported LLM source: {connection}")


    def models(self):
        pass

    def send_request(self, model: str, prompt: str , message: str, tools: Optional[List[Dict[str, Any]]] = None, structured_output:Optional[Dict[str, Any]] = None, stream:Optional [bool]=False, reasoning:Optional[bool]=False, **llmsettings) -> Tuple[str, List[Dict[str, Any]]]:
        pass


@llmClient.reigister("ollama")
class OllamalClient(llmClient):
    def __init__(self,connection):
        super().__init__(connection)
        from ollama import Client as OllamaClient
        self.cl=OllamaClient(self.url, timeout=self.timeout)

    def models(self):
        mos=[]
        try:
            llmmodels=self.cl.list()['models']
            print('llmmodels', llmmodels)
            for mod in llmmodels:
                mos.append({'name': f"{self.conid}_{mod.get('model', '')}", 'model':mod.get('model', ''), 'source': self.connection, 'details': mod.model_dump(exclude_unset=True)})
            return mos
        except Exception as e:
            print(f"unable to fetch model details {e}")
        return []
    def send_request(self, model: str, prompt: str , message: str, tools: Optional[List[Dict[str, Any]]] = None, structured_output:Optional[Dict[str, Any]] = None, stream:Optional [bool]=False, reasoning:Optional[bool]=False, **llmsettings) -> Tuple[str, List[Dict[str, Any]]]:
        print(f"Sending message to Ollama model")
        if structured_output:
            res = self.cl.chat(model=model, messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}], tools=tools)
            if res.message.tool_calls:
                res_dict=res.model_dump()
                #print(res_dict)
                return res_dict['message']['content'], res_dict['message']['tool_calls']
            return res.message.content, [{}]
        res = self.cl.chat(model=model, messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}], tools=tools)
        if res.message.tool_calls:
            res_dict=res.model_dump()
            #print(res_dict)
            return res_dict['message']['content'], res_dict['message']['tool_calls']
        return res.message.content, [{}]

@llmClient.reigister("azure")
class AzureOpenAIclient(llmClient):
    def __init__(self,connection):
        from openai import AzureOpenAI
        super().__init__(connection)
        self.cl=AzureOpenAI(
            azure_endpoint=self.url,
            api_key=self.api_key,
            api_version=self.details.get('api_version', '2025-01-01-preview')
        )

    def models(self):
        mos=[]
        if self.modelname:
            mos.append({'name': f"{self.conid}_{self.modelname}", 'model':self.modelname, 'source': self.connection, 'details': {}})
        else:
            try:
                print('connection in azure', self.connection)
                llmmodels=self.cl.models.list()
                for mod in llmmodels:
                    mos.append({'name': f"{self.conid}_{mod.id}", 'model':mod.id, 'source': self.connection, 'details': {}})
                return mos
            except Exception as e:
                print(f"unable to fetch model details {e}")
                return []
        return mos

    def send_request(self, model: str, prompt: str , message: str, tools: Optional[List[Dict[str, Any]]] = None, structured_output:Optional[Dict[str, Any]] = None, stream:Optional [bool]=False, reasoning:Optional[bool]=False, **llmsettings) -> Tuple[str, List[Dict[str, Any]]]:
        print('request sent to azure')
        print('self.modelname', self.modelname)
        print('prompt', prompt)
        print('message', message)
        print('tools', tools)
        print('structured_output', structured_output)
        try:
            if structured_output:
                response = self.cl.chat.completions.parse(model=self.modelname, messages = 
                                                            [ {'role': 'system', 'content': prompt},{'role': 'user', 'content': message} ],
                                                            response_format=structured_output, tools=tools)
            else:
                response = self.cl.chat.completions.create(model=self.modelname, messages = 
                                                            [ {'role': 'system', 'content': prompt},{'role': 'user', 'content': message} ],
                                                            tools=tools)
            print(response)
            if response.choices[0].message.tool_calls:
                res_dict=response.model_dump()
                #print(res_dict)
                return res_dict['choices'][0]['message']['content'], res_dict['choices'][0]['message']['tool_calls']
            return response.choices[0].message.content, [{}]
        except Exception as e:
            print('error calling azure llm')
            print(e)

