import json
import asyncio
import aiohttp
import ssl
import certifi
from tqdm import tqdm
from datasets import Dataset, DatasetDict
from sklearn.model_selection import train_test_split

# Load dataset
with open("prompt_dataset_1000.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

prompts = [item["prompt"] for item in dataset]

# OpenAI API settings (REDACTED KEY)
MODEL = "gpt-4o-mini"  # Or gpt-3.5-turbo
OPENAI_SECRET_KEY = "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"  # Replace with your actual key
API_URL = "https://api.openai.com/v1/chat/completions"

# Limit concurrent requests
CONCURRENT_REQUESTS = 5

async def call_chatgpt_async(session, prompt):
    """Send a single prompt to OpenAI and return the response."""
    messages = [{"role": "user", "content": prompt}]

    payload = {
        'model': MODEL,
        'messages': messages
    }

    try:
        async with session.post(
                url=API_URL,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_SECRET_KEY}"},
                json=payload,
                ssl=ssl.create_default_context(cafile=certifi.where())
        ) as response:
            result = await response.json()

            if "error" in result:
                print(f"❌ OpenAI request failed: {result['error']}")
                return {"input": "User:\n" + prompt + "\n\nAssistant:", "output": None}  # Return None for failed outputs

            content = result['choices'][0]['message']['content']
            return {"input": "User:\n" + prompt + "\n\nAssistant:", "output": content}

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {"input": "User:\n" + prompt + "\n\nAssistant:", "output": None}  # Return None for exceptions


async def process_prompts(prompts):
    """Process all prompts with limited concurrency and track progress."""
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    results = None

    async def limited_call(prompt, progress_bar, counter):
        async with semaphore:
            result = await call_chatgpt_async(session, prompt)
            progress_bar.update(1)

            if counter % 500 == 0 and counter!=0:
                print(f"Processed {counter} prompts. Waiting for 30 seconds...")
                await asyncio.sleep(30)  # Wait for 30 seconds after every 500 requests

            return result

    async with aiohttp.ClientSession() as session:
        with tqdm(total=len(prompts), desc="Processing Prompts") as progress_bar:
            tasks = []
            counter = 0
            for prompt in prompts:
                tasks.append(limited_call(prompt, progress_bar, counter))
                counter += 1

            results = await asyncio.gather(*tasks)

    return results

if __name__ == "__main__":
    # print("User:\n" + prompts[0] + "\n\nAssistant:")
    results = asyncio.run(process_prompts(prompts))

    # Split dataset
    train_data, test_data = train_test_split(results, test_size=0.1, random_state=42)

    # Save to JSONL format
    def save_to_jsonl(data, filename):
        with open(filename, "w", encoding="utf-8") as f:
            for item in data:
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')

    save_to_jsonl(train_data, "train_1000.jsonl")
    save_to_jsonl(test_data, "test_1000.jsonl")

    print("✅ JSONL datasets saved to train.jsonl and test.jsonl")

    # Verification: Print an example
    with open("train.jsonl", "r", encoding="utf-8") as f:
        first_line = f.readline()
        print(first_line)  # Should print a JSON object