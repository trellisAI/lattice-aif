
from latticepy.engine.interfaces.clientinterface import LLMmodels
from latticepy.engine.interfaces.agentinterface import LatticeAgent
from latticepy.engine.interfaces.llminterface import llmClient
from latticepy.engine.interfaces.serverinterface import callserver
from latticepy.engine.services.toolengine import ToolCall

available_models = LLMmodels().listdown()


class Chatinterface:
    def __init__(self, message, model, tag):

        modelob=LLMmodels()
        self.modelinfo = modelob.get(model)
        self.message = message
        self.tag=tag
        if self.modelinfo:
            self.llm=llmClient(**(self.modelinfo.source).model_dump())
        else:
            return("unable to fetch the response")
        self.depth=3

    def chat(self) ->str:
        """
        Sends a message to the LLM and returns the response.
        If the model supports tool calls, it will return the tool call information.
        """
        if not self.modelinfo or not self.message:
            raise ValueError("Model and message must be provided")
        if self.tag.lower().startswith('agent_'):
            self.system_prompt = LatticeAgent.get(self.tag)['prompt']
            return self._tool_chat()
        else:
            c_response, t_response=self.llm.chat(self.modelinfo.model, self.message)
            return c_response
    
    def _tool_chat(self) -> str:
        """
        Handles chat with tools.
        This method should implement the logic to call tools based on the model's configuration.
        """
        # Placeholder for tool call logic
        # You would typically check if the model has tools and call them accordingly
        toolconfig= LatticeAgent.get(self.tag)['recalltools']
        toolsob=ToolCall(toolconfig)
        print('fetching tools')
        tools=toolsob.active_tools
        print('fetching prompt')
        prompt= LatticeAgent.get(self.tag)['prompt'] or 'You are a helpful assistant.'
        iresponse = self.llm.chat(self.modelinfo.model, prompt, self.message, tools=tools)
        print(f"Response from LLM: {iresponse}")
        def final_response(toolresponse) -> str:
            for tool in toolresponse:
                tres=callserver(tool['function']['name'], tool['function']['arguments'])
                recall_opt=toolsob.getrecall(tool['function']['name'])
                if recall_opt == 'recall':
                    response=self.llm.chat(self.modelinfo.model, prompt, self.message, tools=tools)
                    fresponse=final_response(toolresponse)
                    return fresponse
                if recall_opt == 'filter':
                    response=self.llm.chat(self.modelinfo.model, prompt, f'Filter from data provided as reponse to the query {self.message} and precisely answer :{tres}')
                    return response[0]
                if recall_opt == 'direct':
                    response=self.llm.chat(self.modelinfo.model, prompt, f'Please find the data as requested {self.message} :{tres}')
                    return response[0]
                response=self.llm.chat(self.modelinfo.model, prompt, f'Rephrase the data provided in suitable format:{tres}')
                return response[0]
            else:
                return iresponse[0]
        if iresponse[1] != [{}]:
            fresponse= final_response(iresponse[1])
            return fresponse
        else:
            return iresponse[0]