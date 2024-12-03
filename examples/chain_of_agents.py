import os
import sys

from langchain_openai import ChatOpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from browser_use import Agent, Controller

# Persist the browser state across agents
controller = Controller()

model = ChatOpenAI(model='gpt-4o')

# Initialize browser agent
agent1 = Agent(
	task='Open 2 tabs with wikipedia articles about the history of the meta and one random wikipedia article.',
	llm=model,
	controller=controller,
)
agent2 = Agent(
	task='Considering all open tabs give me the names of the wikipedia article.',
	llm=model,
	controller=controller,
)


# Video: https://preview.screen.studio/share/8Elaq9sm
async def main():
	await agent1.run()
	await agent2.run()


asyncio.run(main())
