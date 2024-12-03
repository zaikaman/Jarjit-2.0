from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Type

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
	AIMessage,
	BaseMessage,
	HumanMessage,
	SystemMessage,
	get_buffer_string,
)
from langchain_openai import ChatOpenAI

from browser_use.agent.message_manager.views import MessageHistory, MessageMetadata
from browser_use.agent.prompts import AgentMessagePrompt, SystemPrompt
from browser_use.agent.views import ActionResult, AgentOutput
from browser_use.browser.views import BrowserState

logger = logging.getLogger(__name__)


class MessageManager:
	def __init__(
		self,
		llm: BaseChatModel,
		task: str,
		action_descriptions: str,
		system_prompt_class: Type[SystemPrompt],
		max_input_tokens: int = 128000,
		estimated_tokens_per_character: int = 3,
		image_tokens: int = 800,
	):
		self.llm = llm
		self.system_prompt_class = system_prompt_class
		self.max_input_tokens = max_input_tokens
		self.history = MessageHistory()
		self.task = task
		self.action_descriptions = action_descriptions
		self.ESTIMATED_TOKENS_PER_CHARACTER = estimated_tokens_per_character
		self.IMG_TOKENS = image_tokens

		system_message = self.system_prompt_class(
			self.action_descriptions, current_date=datetime.now()
		).get_system_message()
		self._add_message_with_tokens(system_message)
		self.system_prompt = system_message
		task_message = HumanMessage(content=f'Your task is: {task}')
		self._add_message_with_tokens(task_message)

	def add_state_message(self, state: BrowserState, result: Optional[ActionResult] = None) -> None:
		"""Add browser state as human message"""

		# if keep in memory, add to directly to history and add state without result
		if result and result.include_in_memory:
			if result.extracted_content:
				msg = HumanMessage(content=str(result.extracted_content))
				self._add_message_with_tokens(msg)
			if result.error:
				msg = HumanMessage(content=str(result.error))
				self._add_message_with_tokens(msg)
			result = None

		# otherwise add state message and result to next message (which will not stay in memory)
		state_message = AgentMessagePrompt(state, result).get_user_message()
		self._add_message_with_tokens(state_message)

	def _remove_last_state_message(self) -> None:
		"""Remove last state message from history"""
		if len(self.history.messages) > 2 and isinstance(
			self.history.messages[-1].message, HumanMessage
		):
			self.history.remove_message()

	def add_model_output(self, model_output: AgentOutput) -> None:
		"""Add model output as AI message"""

		content = model_output.model_dump_json(exclude_unset=True)
		msg = AIMessage(content=content)
		self._add_message_with_tokens(msg)

	def get_messages(self) -> List[BaseMessage]:
		"""Get current message list, trimming old messages if total tokens exceed 7000"""
		# Always keep system message and task message (first 2 messages)
		essential_messages = self.history.messages[:2]
		other_messages = self.history.messages[2:]
		
		# Calculate total tokens in essential messages
		essential_tokens = sum(m.metadata.input_tokens for m in essential_messages)
		
		# Start with all messages
		current_messages = other_messages
		total_tokens = essential_tokens + sum(m.metadata.input_tokens for m in other_messages)
		
		# If total tokens exceed 7000, remove oldest messages until under limit
		while total_tokens > 7000 and len(current_messages) > 0:
			# Remove oldest non-essential message
			removed_msg = current_messages.pop(0)
			total_tokens -= removed_msg.metadata.input_tokens
			
		# Combine essential and remaining messages
		return [m.message for m in essential_messages + current_messages]

	def cut_messages(self):
		"""Get current message list, potentially trimmed to max tokens"""
		diff = self.history.total_tokens - self.max_input_tokens
		if diff <= 0:
			return None

		msg = self.history.messages[-1]

		# if list with image remove image
		if isinstance(msg.message.content, list):
			text = ''
			for item in msg.message.content:
				if 'image_url' in item:
					msg.message.content.remove(item)
					diff -= self.IMG_TOKENS
					msg.metadata.input_tokens -= self.IMG_TOKENS
					self.history.total_tokens -= self.IMG_TOKENS
					logger.debug(
						f'Removed image with {self.IMG_TOKENS} tokens - total tokens now: {self.history.total_tokens}/{self.max_input_tokens}'
					)
				elif 'text' in item and isinstance(item, dict):
					text += item['text']
			msg.message.content = text
			self.history.messages[-1] = msg

		if diff <= 0:
			return None

		# if still over, remove text from state message proportionally to the number of tokens needed with buffer
		# Calculate the proportion of content to remove
		proportion_to_remove = diff / msg.metadata.input_tokens
		if proportion_to_remove > 0.99:
			raise ValueError(
				f'Max token limit reached - history is too long - reduce the system prompt or task less tasks or remove old messages. '
				f'proportion_to_remove: {proportion_to_remove}'
			)
		logger.debug(
			f'Removing {proportion_to_remove * 100:.2f}% of the last message  {proportion_to_remove * msg.metadata.input_tokens:.2f} / {msg.metadata.input_tokens:.2f} tokens)'
		)

		content = msg.message.content
		characters_to_remove = int(len(content) * proportion_to_remove)
		content = content[:-characters_to_remove]

		# remove tokens and old long message
		self.history.remove_message(index=-1)

		# new message with updated content
		msg = HumanMessage(content=content)
		self._add_message_with_tokens(msg)

		last_msg = self.history.messages[-1]

		logger.debug(
			f'Added message with {last_msg.metadata.input_tokens} tokens - total tokens now: {self.history.total_tokens}/{self.max_input_tokens} - total messages: {len(self.history.messages)}'
		)

	def _add_message_with_tokens(self, message: BaseMessage) -> None:
		"""Add message with token count metadata"""
		token_count = self._count_tokens(message)
		metadata = MessageMetadata(input_tokens=token_count)
		self.history.add_message(message, metadata)

	def _count_tokens(self, message: BaseMessage) -> int:
		"""Count tokens in a message using the model's tokenizer"""
		tokens = 0
		if isinstance(message.content, list):
			for item in message.content:
				if 'image_url' in item:
					tokens += self.IMG_TOKENS
				elif isinstance(item, dict) and 'text' in item:
					tokens += self._count_text_tokens(item['text'])
		else:
			tokens += self._count_text_tokens(message.content)
		return tokens

	def _count_text_tokens(self, text: str) -> int:
		"""Count tokens in a text string"""
		if isinstance(self.llm, (ChatOpenAI, ChatAnthropic)):
			try:
				tokens = self.llm.get_num_tokens(text)
			except Exception as e:
				tokens = (
					len(text) // self.ESTIMATED_TOKENS_PER_CHARACTER
				)  # Rough estimate if no tokenizer available
		else:
			tokens = (
				len(text) // self.ESTIMATED_TOKENS_PER_CHARACTER
			)  # Rough estimate if no tokenizer available
		return tokens
