"""
Test browser automation using Mind2Web dataset tasks with pytest framework.
"""

import json
import os
from typing import Any, Dict, List

import pytest
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import SecretStr

from browser_use.agent.service import Agent
from browser_use.controller.service import Controller
from browser_use.utils import logger

# Constants
MAX_STEPS = 50
TEST_SUBSET_SIZE = 10


@pytest.fixture(scope='session')
def test_cases() -> List[Dict[str, Any]]:
	"""Load test cases from Mind2Web dataset"""
	file_path = os.path.join(os.path.dirname(__file__), 'mind2web_data/processed.json')
	logger.info(f'Loading test cases from {file_path}')

	with open(file_path, 'r') as f:
		data = json.load(f)

	subset = data[:TEST_SUBSET_SIZE]
	logger.info(f'Loaded {len(subset)}/{len(data)} test cases')
	return subset


@pytest.fixture
def llm():
	"""Initialize language model for testing"""

	# return ChatAnthropic(model_name='claude-3-5-sonnet-20240620', timeout=25, stop=None)
	return AzureChatOpenAI(
		model='gpt-4o',
		api_version='2024-10-21',
		azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
		api_key=SecretStr(os.getenv('AZURE_OPENAI_KEY', '')),
	)


@pytest.fixture(scope='function')
async def controller():
	"""Initialize the controller"""
	controller = Controller()
	try:
		yield controller
	finally:
		if controller.browser:
			await controller.browser.close(force=True)


# run with: pytest -s -v tests/test_mind2web.py:test_random_samples
@pytest.mark.asyncio
async def test_random_samples(test_cases: List[Dict[str, Any]], llm, controller, validator):
	"""Test a random sampling of tasks across different websites"""
	import random

	logger.info('=== Testing Random Samples ===')

	# Take random samples
	samples = random.sample(test_cases, 1)

	for i, case in enumerate(samples, 1):
		task = f"Go to {case['website']}.com and {case['confirmed_task']}"
		logger.info(f'--- Random Sample {i}/{len(samples)} ---')
		logger.info(f'Task: {task}\n')

		agent = Agent(task, llm, controller)

		await agent.run()

		logger.info('Validating random sample task...')

		# TODO: Validate the task


def test_dataset_integrity(test_cases):
	"""Test the integrity of the test dataset"""
	logger.info('\n=== Testing Dataset Integrity ===')

	required_fields = ['website', 'confirmed_task', 'action_reprs']
	missing_fields = []

	logger.info(f'Checking {len(test_cases)} test cases for required fields')

	for i, case in enumerate(test_cases, 1):
		logger.debug(f'Checking case {i}/{len(test_cases)}')

		for field in required_fields:
			if field not in case:
				missing_fields.append(f'Case {i}: {field}')
				logger.warning(f"Missing field '{field}' in case {i}")

		# Type checks
		if not isinstance(case.get('confirmed_task'), str):
			logger.error(f"Case {i}: 'confirmed_task' must be string")
			assert False, 'Task must be string'

		if not isinstance(case.get('action_reprs'), list):
			logger.error(f"Case {i}: 'action_reprs' must be list")
			assert False, 'Actions must be list'

		if len(case.get('action_reprs', [])) == 0:
			logger.error(f"Case {i}: 'action_reprs' must not be empty")
			assert False, 'Must have at least one action'

	if missing_fields:
		logger.error('Dataset integrity check failed')
		assert False, f'Missing fields: {missing_fields}'
	else:
		logger.info('✅ Dataset integrity check passed')


if __name__ == '__main__':
	pytest.main([__file__, '-v'])
