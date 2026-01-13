
import json
import logging

logger = logging.getLogger(__name__)

from latticepy.engine.interfaces.clientinterface import LLMmodels
from latticepy.engine.interfaces.agentinterface import LatticeAgent
from latticepy.engine.interfaces.llminterface import llmClient
from latticepy.engine.interfaces.serverinterface import callserver
from latticepy.engine.services.toolengine import ToolLoad

available_models = LLMmodels().listdown()


class Chatinterface:
    def __init__(self, message, model, agent):

        modelob=LLMmodels()
        self.modelinfo = modelob.get(model)
        self.message = message
        self.agent=agent
        if self.modelinfo:
            self.llm=llmClient(**(self.modelinfo.source).model_dump())
        else:
            return("unable to fetch the response")
        self.depth=3

    def chat(self):
        """
        Sends a message to the LLM and returns the response.
        if the model supports tool calls, it will return the tool call information.
        """
        logger.info(f"Chatinterface: modelinfo={self.modelinfo}, message={self.message}, agent={self.agent}")
        if not self.modelinfo or not self.message:
            raise ValueError("Model and message must be provided")
        if self.agent:
            #self.system_prompt = LatticeAgent.get(self.agent)['prompt']
            return self._tool_chat()
        else:
            response =self.llm.chat(self.modelinfo.model, "", self.message)
            return response[0], "", {}
    
    def _tool_chat(self):
        """
        Handles chat with tools.
        This method should implement the logic to call tools based on the model's configuration.
        """
        # Placeholder for tool call logic
        # You would typically check if the model has tools and call them accordingly
        toolsob=ToolLoad(self.agent)
        agentdetails=LatticeAgent.get(self.agent)
        logger.debug('fetching prompt')
        prompt= agentdetails['prompt'] or 'You are a helpful assistant.'
        tools= agentdetails['tools'] or None
        tools=json.loads(tools) if tools else None
        logger.debug(f"Using prompt: {prompt}")
        logger.debug(f"Using tools: {[tool['function']['name'] for tool in tools] if tools else 'No tools'}")
        iresponse = self.llm.chat(self.modelinfo.model, prompt, self.message, tools=tools)
        logger.debug(f"Response from LLM: {iresponse}")
        def final_response(toolresponse):
            #creating various interfaces for final response
            for tool in toolresponse:
                tresponse =callserver(tool['function']['name'], tool['function']['arguments'])
                logger.debug(f'Tool response: {tresponse}')
                if tresponse.success:
                    tres=tresponse.data
                else:
                    tres=f"Error calling tool {tool['function']['name']}: {tresponse.error}"
                recall_opt=toolsob.getrecall(tool['function']['name'])
                logger.debug(f"Recall option: {recall_opt}")
                if recall_opt == 'flow':
                    response=self.llm.chat(self.modelinfo.model, prompt, self.message, tools=tools)
                    fresponse=final_response(toolresponse)
                    return fresponse, "", {}
                if recall_opt == 'rephrase':
                    response=self.llm.chat(self.modelinfo.model, prompt, f'use the data provided precisely answer {tres} in suitable format, data: {self.message}')
                    return response[0], "", {}
                if recall_opt == 'pass':
                    response=self.llm.chat(self.modelinfo.model, prompt, f'Please find the data as requested {self.message} :{tres}')
                    return response[0], "", {}
                if recall_opt == 'RAG':
                    pass
                else:
                    return iresponse[0], "", {}
        if iresponse[1] != [{}]:
            fresponse= final_response(iresponse[1])
            return fresponse
        else:
            return iresponse[0], "", {}