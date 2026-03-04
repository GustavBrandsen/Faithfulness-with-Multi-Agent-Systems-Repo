from typing import List, Dict
import json, os, time
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import time
from huggingface_hub import login

print("cuda available:", torch.cuda.is_available())
print("cuda version:", torch.version.cuda)
print("device:", torch.cuda.get_device_name(0))

POSSIBLE_MODELS = [
    'Qwen/Qwen2.5-3B-Instruct',
    'meta-llama/Llama-3.2-3B-Instruct',
    'allenai/OLMo-2-0425-1B-Instruct'
]

qwen_model_name = "Qwen/Qwen2.5-3B-Instruct"
qwen_tokenizer = AutoTokenizer.from_pretrained(qwen_model_name, trust_remote_code=True)
qwen_model = AutoModelForCausalLM.from_pretrained(
    qwen_model_name,
    dtype=torch.float16,
    device_map="cuda",
    trust_remote_code=True
)
qwen_pipe = pipeline("text-generation", model=qwen_model, tokenizer=qwen_tokenizer)
_ = qwen_pipe("Warmup.", max_new_tokens=1)

def qwen_generate_text(prompt: str) -> str:
    inputs = qwen_tokenizer(prompt, return_tensors="pt").to(qwen_model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        out = qwen_model.generate(
            **inputs,
            max_new_tokens=512*4,
            do_sample=False,
            pad_token_id=qwen_tokenizer.eos_token_id,
        )

    # Decode ONLY the generated continuation (not the prompt)
    gen_ids = out[0][input_len:]
    return qwen_tokenizer.decode(gen_ids, skip_special_tokens=True)


llama_model_name = "meta-llama/Llama-3.2-3B-Instruct"
llama_tokenizer = AutoTokenizer.from_pretrained(llama_model_name, trust_remote_code=True)
llama_model = AutoModelForCausalLM.from_pretrained(
    llama_model_name,
    dtype=torch.float16,
    device_map="cuda",
    trust_remote_code=True
)
llama_pipe = pipeline("text-generation", model=llama_model, tokenizer=llama_tokenizer)
_ = llama_pipe("Warmup.", max_new_tokens=1)

def llama_generate_text(prompt: str) -> str:
    inputs = llama_tokenizer(prompt, return_tensors="pt").to(llama_model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        out = llama_model.generate(
            **inputs,
            max_new_tokens=512*4,
            do_sample=False,
            pad_token_id=llama_tokenizer.eos_token_id,
        )

    # Decode ONLY the generated continuation (not the prompt)
    gen_ids = out[0][input_len:]
    return llama_tokenizer.decode(gen_ids, skip_special_tokens=True)

olmo_model_name = "allenai/OLMo-2-0425-1B-Instruct"
olmo_tokenizer = AutoTokenizer.from_pretrained(olmo_model_name, trust_remote_code=True)
olmo_model = AutoModelForCausalLM.from_pretrained(
    olmo_model_name,
    dtype=torch.float16,
    device_map="cuda",
    trust_remote_code=True
)
olmo_pipe = pipeline("text-generation", model=olmo_model, tokenizer=olmo_tokenizer)
_ = olmo_pipe("Warmup.", max_new_tokens=1)

def olmo_generate_text(prompt: str) -> str:
    inputs = olmo_tokenizer(prompt, return_tensors="pt").to(olmo_model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        out = olmo_model.generate(
            **inputs,
            max_new_tokens=512*4,
            do_sample=False,
            pad_token_id=olmo_tokenizer.eos_token_id,
        )

    # Decode ONLY the generated continuation (not the prompt)
    gen_ids = out[0][input_len:]
    return olmo_tokenizer.decode(gen_ids, skip_special_tokens=True)

def replace_prompt(raw_prompt: str, information: Dict[str, str]) -> str:
    for key, value in information.items():
        raw_prompt = raw_prompt.replace(f"%{key}%", value)

    return raw_prompt

def json_chat(messages: List[Dict[str, str]],
              response_format,
              model: str) -> str:
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
    
    def hugging_face_qwen_json_chat(max_retries=5):
        for attempt in range(max_retries):
            try:
                prompt = qwen_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                result = qwen_generate_text(prompt)

                json_content = extract_json(result)
                if not json_content:
                    raise ValueError("No JSON content found")
                

                return json.loads(json_content)

            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                time.sleep(1)

        raise RuntimeError("Model failed to produce valid JSON after retries")
    
    def hugging_face_llama_json_chat(max_retries=5):
        for attempt in range(max_retries):
            try:
                prompt = llama_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                result = llama_generate_text(prompt)

                json_content = extract_json(result)
                if not json_content:
                    raise ValueError("No JSON content found")
                

                return json.loads(json_content)

            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                time.sleep(1)

        raise RuntimeError("Model failed to produce valid JSON after retries")
    
    def hugging_face_olmo_json_chat(max_retries=5):
        for attempt in range(max_retries):
            try:
                prompt = olmo_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                result = olmo_generate_text(prompt)

                json_content = extract_json(result)
                if not json_content:
                    raise ValueError("No JSON content found")
                

                return json.loads(json_content)

            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                time.sleep(1)

        raise RuntimeError("Model failed to produce valid JSON after retries")

    if model in POSSIBLE_MODELS:
        if model == 'Qwen/Qwen2.5-3B-Instruct':
            return hugging_face_qwen_json_chat()
        elif model == 'meta-llama/Llama-3.2-3B-Instruct':
            return hugging_face_llama_json_chat()
        elif model == 'allenai/OLMo-2-0425-1B-Instruct':
            return hugging_face_olmo_json_chat()
    else:
        raise ValueError(f"Model {model} not supported")


def normal_chat(messages: List[Dict[str, str]], model: str) -> str:
    def hugging_face_qwen_normal_chat():
        while True:
            try:
                prompt = qwen_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                response = qwen_pipe(prompt, max_new_tokens=512, do_sample=False, return_full_text=False)
                return response[0]["generated_text"]
            except Exception as e:
                print(f"Error in hugging_face_qwen_normal_chat: {e}")
                continue
            
    def hugging_face_llama_normal_chat():
        while True:
            try:
                prompt = llama_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                response = llama_pipe(prompt, max_new_tokens=512, do_sample=False, return_full_text=False)
                return response[0]["generated_text"]
            except Exception as e:
                print(f"Error in hugging_face_llama_normal_chat: {e}")
                continue

    def hugging_face_olmo_normal_chat():
        while True:
            try:
                prompt = olmo_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                response = olmo_pipe(prompt, max_new_tokens=512, do_sample=False, return_full_text=False)
                return response[0]["generated_text"]
            except Exception as e:
                print(f"Error in hugging_face_olmo_normal_chat: {e}")
                continue
    
    if model in POSSIBLE_MODELS:
        if model == 'Qwen/Qwen2.5-3B-Instruct':
            return hugging_face_qwen_normal_chat()
        elif model == 'meta-llama/Llama-3.2-3B-Instruct':
            return hugging_face_llama_normal_chat()
        elif model == 'allenai/OLMo-2-0425-1B-Instruct':
            return hugging_face_olmo_normal_chat()
    else:
        raise ValueError(f"Model {model} not supported")


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