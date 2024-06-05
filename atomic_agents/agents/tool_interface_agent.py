from pydantic import Field, create_model
from atomic_agents.agents.base_chat_agent import BaseChatAgent
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator, SystemPromptInfo
from atomic_agents.lib.utils.format_tool_message import format_tool_message
from atomic_agents.lib.tools.searx import SearxNGSearchTool
from rich.console import Console
import instructor
import openai

class ToolInterfaceAgent(BaseChatAgent):
    def __init__(self, tool_instance, return_raw_output=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.tool_instance = tool_instance
        
        self.input_schema = create_model(
            self.tool_instance.tool_name,
            tool_input=(str, Field(..., description=f"{self.tool_instance.tool_name} tool input. Presented as a single question or instruction", alias=f'tool_input_{self.tool_instance.tool_name}')),
            __config__=type('Config', (), {
                'title': self.tool_instance.tool_name,
                'description': self.tool_instance.tool_description,
                'json_schema_extra': {
                    "title": self.tool_instance.tool_name,
                    "description": self.tool_instance.tool_description
                }
            })
        )
        
        self.return_raw_output = return_raw_output
        if self.return_raw_output:
            self.output_schema = self.tool_instance.output_schema
            
        self.system_prompt_generator = SystemPromptGenerator(
            system_prompt_info=SystemPromptInfo(
                background=[
                    f"This AI agent is designed to interact with the {self.tool_instance.tool_name} tool.",
                    f"Tool description: {self.tool_instance.tool_description}"
                ],
                steps=[
                    "Get the user input.",
                    "Convert the input to the proper parameters to call the tool.",
                    "Call the tool with the parameters.",
                    "Respond to the user"
                ],
                output_instructions=[
                    "Make sure the tool call will maximize the utility of the tool in the context of the user input.",
                    "Process the output of the tool into a human readable format and/or use it to respond to the user input." if return_raw_output else "Return the raw output of the tool."
                ]
            )
        )
        
    def _get_and_handle_response(self):
        tool_input = self.get_response(response_model=self.tool_instance.input_schema)
        formatted_tool_input = format_tool_message(tool_input)
        self.memory.add_message('assistant', '', tool_message=formatted_tool_input, tool_id=formatted_tool_input['id'])
        tool_output = self.tool_instance.run(tool_input)
        self.memory.add_message('tool', tool_output.model_dump_json(), tool_id=formatted_tool_input['id'])
        
        if self.return_raw_output:
            return tool_output
        
        response = self.get_response(response_model=self.output_schema)        
        return response