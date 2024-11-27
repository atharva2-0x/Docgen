import asyncio
import os
import time
import streamlit as st
from dotenv import load_dotenv
from fiservai import FiservAI
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("API_KEY")
if API_KEY is None or API_KEY == "":
    raise ValueError("API_KEY is not set. Check your environment variables or add a .env file with API_KEY and API_SECRET.")
API_SECRET = os.getenv("API_SECRET")
if API_SECRET is None or API_SECRET == "":
    raise ValueError("API_SECRET is not set. Check your environment variables or add a .env file with API_KEY and API_SECRET.")
BASE_URL = os.getenv("BASE_URL")

def print_diagnostics(resp, elapsed_time_sec):
    st.write(f"""[Model: {resp.model}, Prompt Tokens: {resp.usage.prompt_tokens}, Completion Tokens: {resp.usage.completion_tokens}, Total Tokens: {resp.usage.total_tokens}, Cost: ${resp.usage.cost}, Time: {elapsed_time_sec} sec]""")

# Create a FiservAI client
client = FiservAI.FiservAI(API_KEY, API_SECRET, base_url=BASE_URL if BASE_URL is not None else None)

# Directory to store conversations
CONVERSATION_DIR = 'conversations'

# Ensure the conversation directory exists
if not os.path.exists(CONVERSATION_DIR):
    os.makedirs(CONVERSATION_DIR)

# Generate a unique conversation file name based on the first prompt
def get_conversation_file():
    if 'conversation_file' not in st.session_state or st.session_state.new_conversation:
        first_prompt = st.session_state.prompts[0][:30] if st.session_state.prompts else "conversation"
        first_prompt = "".join([c if c.isalnum() else "_" for c in first_prompt]).strip("_")
        st.session_state.conversation_file = os.path.join(CONVERSATION_DIR, f'{first_prompt}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        st.session_state.new_conversation = False
    return st.session_state.conversation_file

# Function to save the conversation to a file
def save_conversation():
    with open(get_conversation_file(), 'w') as file:
        for prompt, response in zip(st.session_state.prompts, st.session_state.responses):
            file.write(f"User: {prompt}\nAssistant: {response}\n")

# Function to load conversation from a file
def load_conversation(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            prompts = []
            responses = []
            for i in range(0, len(lines), 2):
                prompts.append(lines[i].strip().replace("User: ", ""))
                responses.append(lines[i+1].strip().replace("Assistant: ", ""))
            return prompts, responses
    except FileNotFoundError:
        return [], []

# Initialize session state variables or load from file
if 'prompts' not in st.session_state:
    st.session_state.prompts, st.session_state.responses = [], []
    st.session_state.new_conversation = False

# Function to perform code documentation generation
async def generate_code_documentation(code):
    try:
        conversation = ""
        for prompt, response in zip(st.session_state.prompts, st.session_state.responses):
            conversation += f"User: {prompt}\nAssistant: {response}\n"
        prompt = f"{conversation}\n\n{code}"
        now = time.time()
        resp = await client.chat_completion_async(prompt)
        response_content = resp.choices[0].message.content

        st.session_state.prompts.append(prompt)
        st.session_state.responses.append(response_content)
        save_conversation()  # Save after appending new conversation

        st.write(response_content)
        print_diagnostics(resp, int(time.time() - now))
        st.write()
    except Exception as e:
        st.write(f"An exception occurred: {str(e)}")

async def main(code):
    await generate_code_documentation(code)

st.title("Code Documentation Generation")

st.sidebar.title("Navigation")
st.sidebar.write("Upload a file here!")

# Column for displaying conversation files
# col1, col2 = st.columns([2,1])

filetext = ""
uploaded_file = st.sidebar.file_uploader("Drag & drop files here to upload file.", type=None)
if uploaded_file is not None:
    filetext = uploaded_file.read().decode("utf-8")

st.header("Code Documentation Generation")
st.write("Enter a program below or drop a file and click the 'Submit' button to generate documentation.")

textbox = st.text_area("Enter your program here")

new_conversation_button = st.button("New Conversation")
if new_conversation_button:
    st.session_state.prompts, st.session_state.responses = [], []
    st.session_state.new_conversation = True

submit_button = st.button("Submit")

code = textbox + "\n" + filetext
if submit_button:
    if not st.session_state.prompts:
        st.session_state.prompts.append(code[:30] + ("..." if len(code) > 30 else ""))
    asyncio.run(main(code))

# Show the available conversation files
st.sidebar.header("Conversations History")
conversation_files = os.listdir(CONVERSATION_DIR)
for filename in sorted(conversation_files):
    if st.sidebar.button(filename):
        st.session_state.prompts, st.session_state.responses = load_conversation(os.path.join(CONVERSATION_DIR, filename))
        st.session_state.conversation_file = os.path.join(CONVERSATION_DIR, filename)
        st.session_state.new_conversation = False
    