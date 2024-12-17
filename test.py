import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent as BaseAgent, BrowserConfig, Controller
from browser_use.agent.api_manager import api_key_manager, AZURE_OPENAI_BASE_URL, AZURE_OPENAI_MODEL
from pydantic import SecretStr
from openai import RateLimitError
from browser_use.agent.views import AgentHistoryList
import time

class Agent(BaseAgent):
    async def run(self, max_steps: int = 50) -> AgentHistoryList:
        while True:
            try:
                return await super().run(max_steps)
            except RateLimitError:
                print("\nRate limit reached. Switching to next API key...")
                # Create new LLM instance with next API key
                self.llm = ChatOpenAI(
                    model=AZURE_OPENAI_MODEL,
                    api_key=SecretStr(api_key_manager.get_next_key()),
                    base_url=AZURE_OPENAI_BASE_URL,
                    temperature=0
                )

def get_user_prompt():
    print("\n=== Browser Use AI Agent ===")
    print("Ví dụ các task có thể thực hiện:")
    print("1. Go to amazon.com, search for laptop, sort by best rating")
    print("2. Go to google.com/flights and find flights from New York to London")
    print("3. Go to weather.com and check weather for Tokyo")
    print("4. Go to google.com and search for 'Python tutorials'")
    print("\nLưu ý: Agent không thể tự động đăng nhập vào các trang yêu cầu xác thực như ChatGPT, Gmail, Facebook...\n")
    
    return input("Nhập task bạn muốn thực hiện: ")

async def main():
    agent = None
    try:
        # Lấy prompt từ người dùng
        task = get_user_prompt()
        
        # Khởi tạo ChatOpenAI với Azure OpenAI và API key từ round-robin manager
        llm = ChatOpenAI(
            model=AZURE_OPENAI_MODEL,
            api_key=SecretStr(api_key_manager.get_next_key()),
            base_url=AZURE_OPENAI_BASE_URL,
            temperature=0
        )

        # Cấu hình stealth mode cho browser
        browser_config = BrowserConfig(
            headless=False,  # Set False để dễ debug
            extra_chromium_args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-automation',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--window-size=1920,1080',
                '--start-maximized',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
        )

        # Khởi tạo Controller với browser config
        controller = Controller(browser_config=browser_config)

        # Khởi tạo Agent với task từ người dùng
        agent = Agent(
            task=task,
            llm=llm,
            controller=controller
        )

        # Chạy agent với giới hạn bước cao hơn cho task phức tạp
        await agent.run(max_steps=1000000000000000000000)  # Tăng lên 1000 bước

    except KeyboardInterrupt:
        print("\nĐã dừng chương trình theo yêu cầu của người dùng.")
    except Exception as e:
        print(f"\nCó lỗi xảy ra: {str(e)}")
    finally:
        if agent and agent.controller and agent.controller.browser:
            await agent.controller.browser.close()

if __name__ == "__main__":
    asyncio.run(main())