from typing import List, Dict
import json, os, time
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from dotenv import load_dotenv
from huggingface_hub import login
load_dotenv()

login(token = os.getenv("HUGGINGFACE_LOGIN"))

print("cuda available:", torch.cuda.is_available())
print("cuda version:", torch.version.cuda)
print("device:", torch.cuda.get_device_name(0))

POSSIBLE_MODELS = [
    'Qwen/Qwen2.5-3B-Instruct',
    'meta-llama/Llama-3.2-3B-Instruct',
    'allenai/Olmo-3-7B-Instruct',
    'allenai/Olmo-3-7B-Think'
]

# Declare our module-level variables
tokenizer = None
model = None
pipe = None

def init_model(model_name: str):
    global tokenizer, model, pipe
    
    if model_name not in POSSIBLE_MODELS:
        raise ValueError(f"Model {model_name} not supported")
        
    print(f"Loading {model_name} into memory...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16,
        device_map="cuda",
        trust_remote_code=True
    )
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
    _ = pipe("Warmup.", max_new_tokens=1)


def generate_text(prompt: str, model_name: str) -> str:
    # Use the global model and tokenizer directly
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=512*4,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Decode ONLY the generated continuation (not the prompt)
    gen_ids = out[0][input_len:]
    return tokenizer.decode(gen_ids, skip_special_tokens=True)


def replace_prompt(raw_prompt: str, information: Dict[str, str]) -> str:
    for key, value in information.items():
        raw_prompt = raw_prompt.replace(f"%{key}%", value)

    return raw_prompt

def json_chat(messages: List[Dict[str, str]],
              response_format,
              model_name: str) -> str:
    def extract_json(input_string):
        input_string = input_string.replace("\n", "")
        stack = []
        json_start_positions = []

        for pos, char in enumerate(input_string):
            if char in '{[':
                stack.append(char)
                if len(stack) == 1:
                    json_start_positions.append(pos)
            elif char in '}]':
                if len(stack) == 0:
                    raise ValueError(f"unexpected {char} at position {pos}")
                last_open = stack.pop()
                if (last_open == '{' and char != '}') or (last_open == '[' and char != ']'):
                    raise ValueError(f"mismatched brackets {last_open} and {char} at position {pos}")
                if len(stack) == 0:
                    return input_string[json_start_positions.pop():pos+1]
        return None
    
    def hugging_face_json_chat(max_retries=5):
        for attempt in range(max_retries):
            try:
                # Use the global tokenizer
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                result = generate_text(prompt, model_name)

                json_content = extract_json(result)
                if not json_content:
                    raise ValueError("No JSON content found")
                
                return json.loads(json_content)

            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries} failed on {model_name}: {e}")
                time.sleep(1)

        raise RuntimeError("Model failed to produce valid JSON after retries")

    def extract_format(input_string):
        delimiter = "The answer is:"
        if delimiter not in input_string:
            return None
            
        parts = input_string.split(delimiter)
        rationale = parts[0].strip()
        # Clean up any trailing periods before the delimiter
        if rationale.endswith('.'):
            rationale = rationale[:-1].strip()
            
        answer = parts[-1].strip()
        
        # Use Pydantic's model fields to figure out the correct key for the answer ("vote" vs "decision")
        expected_keys = getattr(response_format, '__annotations__', {})
        
        result_dict = {"rationale": rationale}
        if "vote" in expected_keys:
            result_dict["vote"] = answer
        elif "decision" in expected_keys:
            result_dict["decision"] = answer
        else:
            result_dict["answer"] = answer
            
        return result_dict

    def hugging_face_format_chat(max_retries=5):
        for attempt in range(max_retries):
            try:
                # Use the global tokenizer
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                result = generate_text(prompt, model_name)

                parsed_content = extract_format(result)
                if not parsed_content:
                    raise ValueError("Delimiter 'The answer is:' not found in response")
                
                return parsed_content

            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries} failed on {model_name}: {e}")
                time.sleep(1)

        raise RuntimeError("Model failed to produce valid format after retries")

    # Switched to hugging_face_format_chat
    if model_name in POSSIBLE_MODELS:
        # return hugging_face_json_chat() # If the model returns JSON
        return hugging_face_format_chat() # IF the model uses "The answer is:" format
    else:
        raise ValueError(f"Model {model_name} not supported")


def normal_chat(messages: List[Dict[str, str]], model_name: str) -> str:
    def hugging_face_normal_chat():
        while True:
            try:
                # Use the global tokenizer and pipe
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                response = pipe(prompt, max_new_tokens=512, do_sample=False, return_full_text=False)
                return response[0]["generated_text"]
            except Exception as e:
                print(f"Error in hugging_face_normal_chat for {model_name}: {e}")
                continue
    
    if model_name in POSSIBLE_MODELS:
        return hugging_face_normal_chat()
    else:
        raise ValueError(f"Model {model_name} not supported")

class VoteResponse(BaseModel):
    vote: str
    rationale: str

class DecisionResponse(BaseModel):
    decision: str
    rationale: str

class TaskResponse(BaseModel):
    name: str
    description: str
    shared_information: List[str]
    hidden_information: List[str]
    possible_answers: List[str]
    correct_answer: str