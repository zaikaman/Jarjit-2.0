import asyncio
import json

import pytest

from browser_use.browser.service import Browser, BrowserConfig
from browser_use.dom.views import ElementTreeSerializer
from browser_use.utils import time_execution_sync


# run with: pytest browser_use/browser/tests/test_clicks.py
@pytest.mark.asyncio
async def test_highlight_elements():
	browser = Browser(config=BrowserConfig(headless=False, keep_open=False, disable_security=True))

	session = await browser.get_session()

	print(session)

	page = await browser.get_current_page()
	# await page.goto('https://immobilienscout24.de')
	# await page.goto('https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/service-plans')
	await page.goto('https://google.com/search?q=elon+musk')
	# await page.goto('https://kayak.com')
	# await page.goto('https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_iframe')

	await asyncio.sleep(1)

	while True:
		try:
			# await asyncio.sleep(10)
			state = await browser.get_state()

			with open('./tmp/page.json', 'w') as f:
				json.dump(
					ElementTreeSerializer.dom_element_node_to_json(state.element_tree),
					f,
					indent=1,
				)

			# await time_execution_sync('highlight_selector_map_elements')(
			# 	browser.highlight_selector_map_elements
			# )(state.selector_map)

			# Find and print duplicate XPaths
			xpath_counts = {}
			if not state.selector_map:
				continue
			for selector in state.selector_map.values():
				xpath = selector.xpath
				if xpath in xpath_counts:
					xpath_counts[xpath] += 1
				else:
					xpath_counts[xpath] = 1

			print('\nDuplicate XPaths found:')
			for xpath, count in xpath_counts.items():
				if count > 1:
					print(f'XPath: {xpath}')
					print(f'Count: {count}\n')

			print(list(state.selector_map.keys()), 'Selector map keys')
			print(state.element_tree.clickable_elements_to_string())
			action = input('Select next action: ')

			await time_execution_sync('remove_highlight_elements')(browser.remove_highlights)()

			node_element = state.selector_map[int(action)]

			# check if index of selector map are the same as index of items in dom_items

			await browser._click_element_node(node_element)

		except Exception as e:
			print(e)
