from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# 项目根目录在 ../../../
env_path = Path(__file__).parents[3] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def get_chat_model(temperature: float = 0.7, model_name: str = "qwen3-max"):

    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key is None:
        raise RuntimeError(
            "缺少 API Key：请在 .env 中设置  OPENAI_API_KEY"
        )

    if base_url is None:
        print("[警告] 未设置 base_url，使用默认 OpenAI 接口。")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )

# if __name__ == "__main__":
#     model = get_chat_model()
#     print(model.invoke("你是谁?"))
