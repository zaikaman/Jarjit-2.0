from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Type

from openai import RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from browser_use.browser.views import BrowserState, BrowserStateHistory
from browser_use.controller.registry.views import ActionModel
from browser_use.dom.history_tree_processor import (
	DOMElementNode,
	DOMHistoryElement,
	HistoryTreeProcessor,
)
from browser_use.dom.views import SelectorMap


class ActionResult(BaseModel):
	"""Result of executing an action"""

	is_done: Optional[bool] = False
	extracted_content: Optional[str] = None
	error: Optional[str] = None
	include_in_memory: bool = False  # whether to include in past messages as context or not


class AgentBrain(BaseModel):
	"""Current state of the agent"""

	valuation_previous_goal: str
	memory: str
	next_goal: str


class AgentOutput(BaseModel):
	"""Output model for agent

	@dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
	"""

	model_config = ConfigDict(arbitrary_types_allowed=True)

	current_state: AgentBrain
	action: ActionModel

	@staticmethod
	def type_with_custom_actions(custom_actions: Type[ActionModel]) -> Type['AgentOutput']:
		"""Extend actions with custom actions"""
		return create_model(
			'AgentOutput',
			__base__=AgentOutput,
			action=(custom_actions, Field(...)),  # Properly annotated field with no default
			__module__=AgentOutput.__module__,
		)


class AgentHistory(BaseModel):
	"""History item for agent actions"""

	model_output: AgentOutput | None
	result: ActionResult
	state: BrowserStateHistory

	model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

	@staticmethod
	def get_interacted_element(
		model_output: AgentOutput, selector_map: SelectorMap
	) -> DOMHistoryElement | None:
		index = model_output.action.get_index()
		if index:
			el: DOMElementNode = selector_map[index]
			return HistoryTreeProcessor.convert_dom_element_to_history_element(el)

		return None

	def model_dump(self, **kwargs) -> Dict[str, Any]:
		"""Custom serialization handling circular references"""

		# Handle action serialization
		model_output_dump = None
		if self.model_output:
			action_dump = self.model_output.action.model_dump(exclude_none=True)
			model_output_dump = {
				'current_state': self.model_output.current_state.model_dump(),
				'action': action_dump,  # This preserves the actual action data
			}

		return {
			'model_output': model_output_dump,
			'result': self.result.model_dump(exclude_none=True),
			'state': self.state.to_dict(),
		}


class AgentHistoryList(BaseModel):
	"""List of agent history items"""

	history: list[AgentHistory]

	def __str__(self) -> str:
		"""Representation of the AgentHistoryList object"""
		return f'AgentHistoryList(all_results={self.action_results()}, all_model_outputs={self.model_actions()})'

	def __repr__(self) -> str:
		"""Representation of the AgentHistoryList object"""
		return self.__str__()

	def save_to_file(self, filepath: str | Path) -> None:
		"""Save history to JSON file with proper serialization"""
		try:
			Path(filepath).parent.mkdir(parents=True, exist_ok=True)
			data = self.model_dump()
			with open(filepath, 'w', encoding='utf-8') as f:
				json.dump(data, f, indent=2)
		except Exception as e:
			raise e

	def model_dump(self, **kwargs) -> Dict[str, Any]:
		"""Custom serialization that properly uses AgentHistory's model_dump"""
		return {
			'history': [h.model_dump(**kwargs) for h in self.history],
		}

	@classmethod
	def load_from_file(
		cls, filepath: str | Path, output_model: Type[AgentOutput]
	) -> 'AgentHistoryList':
		"""Load history from JSON file"""
		with open(filepath, 'r', encoding='utf-8') as f:
			data = json.load(f)
		# loop through history and validate output_model actions to enrich with custom actions
		for h in data['history']:
			if h['model_output']:
				if isinstance(h['model_output'], dict):
					h['model_output'] = output_model.model_validate(h['model_output'])
				else:
					h['model_output'] = None
			if 'interacted_element' not in h['state']:
				h['state']['interacted_element'] = None
		history = cls.model_validate(data)
		return history

	def last_action(self) -> None | dict:
		"""Last action in history"""
		if self.history and self.history[-1].model_output:
			return self.history[-1].model_output.action.model_dump(exclude_none=True)
		return None

	def errors(self) -> list[str]:
		"""Get all errors from history"""
		return [h.result.error for h in self.history if h.result.error]

	def final_result(self) -> None | str:
		"""Final result from history"""
		if self.history and self.history[-1].result.extracted_content:
			return self.history[-1].result.extracted_content
		return None

	def is_done(self) -> bool:
		"""Check if the agent is done"""
		if self.history and self.history[-1].result.is_done:
			return self.history[-1].result.is_done
		return False

	def has_errors(self) -> bool:
		"""Check if the agent has any errors"""
		return len(self.errors()) > 0

	def urls(self) -> list[str]:
		"""Get all unique URLs from history"""
		return [h.state.url for h in self.history if h.state.url]

	def screenshots(self) -> list[str]:
		"""Get all screenshots from history"""
		return [h.state.screenshot for h in self.history if h.state.screenshot]

	def action_names(self) -> list[str]:
		"""Get all action names from history"""
		return [list(action.keys())[0] for action in self.model_actions()]

	def model_thoughts(self) -> list[AgentBrain]:
		"""Get all thoughts from history"""
		return [h.model_output.current_state for h in self.history if h.model_output]

	def model_outputs(self) -> list[AgentOutput]:
		"""Get all model outputs from history"""
		return [h.model_output for h in self.history if h.model_output]

	# get all actions with params
	def model_actions(self) -> list[dict]:
		"""Get all actions from history"""
		outputs = []

		for h in self.history:
			if h.model_output:
				output = h.model_output.action.model_dump(exclude_none=True)

				outputs.append(output)
		return outputs

	def action_results(self) -> list[ActionResult]:
		"""Get all results from history"""
		return [h.result for h in self.history if h.result]

	def extracted_content(self) -> list[str]:
		"""Get all extracted content from history"""
		return [h.result.extracted_content for h in self.history if h.result.extracted_content]

	def model_actions_filtered(self, include: list[str] = []) -> list[dict]:
		"""Get all model actions from history as JSON"""
		outputs = self.model_actions()
		result = []
		for o in outputs:
			for i in include:
				if i == list(o.keys())[0]:
					result.append(o)
		return result


class AgentError:
	"""Container for agent error handling"""

	VALIDATION_ERROR = 'Invalid model output format. Please follow the correct schema.'
	RATE_LIMIT_ERROR = 'Rate limit reached. Waiting before retry.'
	NO_VALID_ACTION = 'No valid action found'

	@staticmethod
	def format_error(error: Exception, include_trace: bool = False) -> str:
		"""Format error message based on error type and optionally include trace"""
		message = ''
		if isinstance(error, ValidationError):
			return f'{AgentError.VALIDATION_ERROR}\nDetails: {str(error)}'
		if isinstance(error, RateLimitError):
			return AgentError.RATE_LIMIT_ERROR
		return f'Unexpected error: {str(error)}\nStacktrace:\n{traceback.format_exc()}'
