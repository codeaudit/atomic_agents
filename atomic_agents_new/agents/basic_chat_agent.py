from typing import Callable, List
from pydantic import BaseModel, Field
from datetime import datetime
from abc import ABC, abstractmethod
from atomic_agents.lib.chat_memory import ChatMemory
from atomic_agents.lib.utils.logger import logger
from atomic_agents.tools.searx import SearxNGSearchTool
from atomic_agents_new.lib.system_prompt_generator import DynamicInfoProviderBase, SystemPromptInfo, SystemPromptGenerator

class BasicChatAgentInputSchema(BaseModel):
    chat_input: str = Field(..., description='The input text for the chat agent.')

class BasicChatAgentResponse(BaseModel):    
    response: str = Field(..., description='The markdown-enabled response from the chat agent.')
    
    class Config:
        title = 'BasicChatAgentResponse'
        description = 'Response from the basic chat agent. The response can be in markdown format.'
        json_schema_extra = {
            'title': title,
            'description': description
        }

class GeneralPlanStep(BaseModel):
    step: str
    description: str
    substeps: List[str] = []

class GeneralPlanResponse(BaseModel):
    observations: List[str] = Field(..., description='Key points or observations about the input.')
    thoughts: List[str] = Field(..., description='Thought process or considerations involved in preparing the response.')
    response_plan: List[GeneralPlanStep] = Field(..., description='Steps involved in generating the response.')

    class Config:
        title = 'GeneralPlanResponse'
        description = 'General response plan from the chat agent.'
        json_schema_extra = {
            'title': title,
            'description': description
        }

class BasicChatAgent:
    def __init__(self, client, system_prompt_generator: SystemPromptGenerator = None, model: str = 'gpt-3.5-turbo',  memory: ChatMemory = None, include_planning_step = False, input_schema = BasicChatAgentInputSchema, output_schema = BasicChatAgentResponse):
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.client = client
        self.model = model
        self.memory = memory or ChatMemory()
        self.system_prompt_generator = system_prompt_generator or SystemPromptGenerator()
        self.include_planning_step = include_planning_step

    def get_system_prompt(self) -> str:
        return self.system_prompt_generator.generate_prompt()

    def get_response(self, response_model=None) -> BaseModel:
        if response_model is None:
            response_model = self.output_schema
        
        messages = [{'role': 'system', 'content': self.get_system_prompt()}] + self.memory.get_history()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_model=response_model
        )
        return response

    def run(self, user_input: str) -> str:
        self.memory.add_message('user', user_input)
        self._pre_run()
        if self.include_planning_step:
            self.memory.add_message('assistant', 'I will now note the observations about the input and context and the thought process involved in preparing the response.')
            plan = self.get_response(response_model=GeneralPlanResponse)
            self.memory.add_message('assistant', plan.model_dump_json())
        response = self.get_response(response_model=self.output_schema)
        self.memory.add_message('assistant', response.model_dump_json())
        self._post_run()
        return response

    def _pre_run(self):
        pass
    
    def _post_run(self):
        pass