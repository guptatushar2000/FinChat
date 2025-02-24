from fastapi import FastAPI
from fastapi.responses import RedirectResponse

import gradio as gr

import httpx
import requests
import json

home_url = r'http://localhost:8000'
worker_url = r'http://localhost:8080'
gradio_url = r'http://localhost:7860/'

app = FastAPI()

non_intellectual_questions = ['hello']

async def chat(message, history):
    # response_text = f"You said: {message}"
    if message.lower() in non_intellectual_questions:
        response  = requests.get(f'{home_url}/home')
        response = json.loads(response.json())['message']
        return response
    else:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
                response = await client.post(f'{worker_url}/query', json={"question": message})
            response = response.json()['message']
        except httpx.TimeoutException as ex:
            response = 'Your request has timed out.'
        finally:
            return response


@app.get("/home")
async def home():
    r = httpx.get('http://localhost:8080/')
    return r.content

def is_gradio_running():

    try:
        response = requests.get(gradio_url)
        return response.status_code == 200
    except requests.exceptions.RequestException as ex:
        return False

@app.get("/")
async def root():
    if not is_gradio_running():
        chat_interface = gr.ChatInterface(
            chat,
            chatbot=gr.Chatbot(height=300),
            textbox=gr.Textbox(placeholder="Ask me a question", container=False, scale=7),
            title="Chat with FinChat",
            description="Enter you message below and get a response.",
            theme="soft",
            examples=["Hello"],
            cache_examples=True
        )
        chat_interface.launch(share=True, server_port=7860, prevent_thread_lock=True)

    return RedirectResponse(url=gradio_url)
