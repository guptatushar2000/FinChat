from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from openai import OpenAI
import time
from typing import Annotated
import io
import sys
import pandas as pd

app = FastAPI()

gpt_assistant = None
loan_data_columns = None
assistant_instructions = None
backend_url = "http://localhost:8080"

# instructions=f"You are programmer. {loan_data_columns} is the list of column names from a dataframe we are interested in. Your job is to take user query and give code to perform that query on the data. If you need to read the dataframe put path_to_user_data which will be replaced by the user with actual path. ONLY CODE. NO TEXT. NO COMMENTS. NO DESCRIPTION. BE QUIET. as less words as possible. always check datatype for columns if any math operation is required. ALWAYS PRINT RESULT TO STDOUT. User is non-technical, so explain the result to user in proper sentences. If user asks for explaination instead of query, write it as a print statement."

class MyGPTAssistant:

    def __init__(self) -> None:
        self.client = OpenAI()
        self.assistant = self.client.beta.assistants.create(
            name="ProGrammer",
            instructions=assistant_instructions,
            model="gpt-4-1106-preview"
        )
        self.thread = self.client.beta.threads.create()

@app.on_event("startup")
async def startup_event():
    global gpt_assistant
    global loan_data_columns
    global assistant_instructions

    df = pd.read_csv(r'/Users/blitzsleek/Downloads/LoanDataSliced.csv')
    loan_data_columns = df.columns.to_list()

    assistant_instructions=f'''
        1. {loan_data_columns} is the list of column names from a dataframe we are interested in.
        2. Analyse the column names and create an understanding of how these values can be used.
        2. You are a mathematician and programmer with knowledge of finance. Your job is to take user query and give code to perform that query on the data.
        3. Use the column names as basis to understand the data and create the query.
        4. ONLY CODE. NO TEXT. NO COMMENTS. NO DESCRIPTION. BE QUIET. as less words as possible.
        5. If you need to read the dataframe put path_to_user_data which will be replaced by the user with actual path. Dataframe needs to read every time user requests a query.
        6. Always check datatype for columns if any math operation is required. 
        7. ALWAYS PRINT RESULT TO STDOUT. 
        8. User is non-technical, so explain the result to user in proper sentences. 
        9. If user asks for explaination instead of query, write it as a print statement.
        10. If user requests an image/graph, save the image in current working directory. Then ONLY send the following Response: {backend_url}/name_of_the_image. DONT SHOW THE IMAGE.
        '''

    gpt_assistant = MyGPTAssistant()

async def get_gpt_assistant():
    return gpt_assistant

def get_gpt_response(question, assistant):
    if assistant is None:
        return "assistant not initialised"
    
    message = assistant.client.beta.threads.messages.create(
        thread_id=assistant.thread.id,
        role="user",
        content=question
    )

    run = assistant.client.beta.threads.runs.create(
        thread_id=assistant.thread.id,
        assistant_id=assistant.assistant.id
    )

    while run.status in ["queued", "in_progress"]:
        run = assistant.client.beta.threads.runs.retrieve(
            thread_id=assistant.thread.id,
            run_id=run.id
        )
        time.sleep(0.5)

    messages = assistant.client.beta.threads.messages.list(
        thread_id=assistant.thread.id,
        order="asc",
        after=message.id
    )

    return messages.dict()['data'][0]['content'][0]['text']['value']

def execute_remote_code(code_str: str):
    code_str = code_str.replace("```python", "").replace("```", "").strip()

    code_str = code_str.replace("path_to_user_data", "/Users/blitzsleek/Downloads/LoanData.csv")

    output = io.StringIO()

    original_stdout = sys.stdout
    sys.stdout = output

    try:
        exec(code_str)
    except Exception as ex:
        raise Exception(f"{type(ex).__name__} - {str(ex)}")
    finally:
        sys.stdout = original_stdout

    return output.getvalue()

@app.get("/")
async def home():
    return {"message": "Welcome to home!"}

@app.post("/query")
async def query(question_data: dict, assistant: Annotated[MyGPTAssistant, Depends(get_gpt_assistant)]):
    question = question_data.get('question', 'Say Hi!')
    # response = get_gpt_response(question=question, assistant=assistant)
    # response = execute_remote_code(response)

    while True:
        try:
            response = get_gpt_response(question=question, assistant=assistant)
            response = execute_remote_code(response)
            break
        except Exception as ex:
            question = f"Error Encountered in your code: {ex}. Fix it"

    # if len(response.split("\n")) < 2:
    #     return {"message": response}
    
    # response_type = response.split("\n")[-2]
    # response = "\n".join(response.split("\n")[:-2])

    # if response_type == "['image-type']":
    #     return {"message": FileResponse(response)}

    return {"message": response}
