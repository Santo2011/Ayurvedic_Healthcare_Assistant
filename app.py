import streamlit as st
import os
import base64
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from PIL import Image
import io
import requests

load_dotenv()
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Function to encode local image as base64
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()
    return encoded_image

# Path to your local image
local_image_path = "static/bg.jpeg"  # Replace with your image path
background_image_base64 = get_base64_image(local_image_path)

# Inject CSS for background image
st.markdown(
    f"""
    <style>
    /* Body background styling */
    body {{
        background: url("data:image/jpg;base64,{background_image_base64}") no-repeat center center fixed; 
        background-size: cover;
    }}
    /* Override the main content styling to make it transparent */
    .stApp {{
        background: transparent;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("आयुर्वेद Assistant")

llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

mode = st.radio("Choose your mode", options=["Ayurvedic Tutor", "Healthcare Assistant"])

if "user_responses" not in st.session_state:
    st.session_state.user_responses = []
if "assistant_responses" not in st.session_state:
    st.session_state.assistant_responses = []
if "plant_recommended" not in st.session_state:
    st.session_state.plant_recommended = False

def vector_embedding():
    if "vectors" not in st.session_state:
        st.session_state.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        st.session_state.loader = PyPDFDirectoryLoader("./dataset")
        st.session_state.docs = st.session_state.loader.load()
        st.session_state.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        st.session_state.final_documents = st.session_state.text_splitter.split_documents(st.session_state.docs[:20])
        st.session_state.vectors = FAISS.from_documents(st.session_state.final_documents, st.session_state.embeddings)

def extract_image_from_herbs_folder_or_web(plant_name, groq_api_key, folder_path="C:/Users/Shanmugam/OneDrive/Desktop/Chittu Kuruvi/AyurHerbs"):
    plant_image = None
    plant_name_words = plant_name.lower().split()

    if not os.path.exists(folder_path):
        st.write(f"Error: The folder '{folder_path}' does not exist.")
        return None

    found_in_folder = False
    for file_name in os.listdir(folder_path):
        file_name_lower = file_name.lower()
        if all(word in file_name_lower for word in plant_name_words):
            image_path = os.path.join(folder_path, file_name)
            try:
                plant_image = Image.open(image_path)
                found_in_folder = True
                break
            except Exception as e:
                st.write(f"Error loading image from file {file_name}: {e}")

    if not found_in_folder:
        st.write("No matching image found. Attempting to fetch from the web.")
        try:
            prompt = f"Find a clear image of the herb called {plant_name} and provide the link to the image."
            response = llm.invoke(prompt)

            if 'url' in response:
                image_url = response['url']
                image_data = requests.get(image_url).content
                plant_image = Image.open(io.BytesIO(image_data))
                st.write("Image fetched from the web.")
            else:
                st.write("No image URL found.")
        except Exception as e:
            st.write(f"Error fetching image: {e}")

    return plant_image

if st.button("Create Document Embeddings"):
    vector_embedding()
    st.write("Vector Store DB is ready")

if mode == "Healthcare Assistant":
    st.subheader("Chat with your Ayurvedic Assistant")

    for user_msg, assistant_msg in zip(st.session_state.user_responses, st.session_state.assistant_responses):
        st.markdown(f"<div class='chat-container'><div class='chat-bubble-user'>{user_msg}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chat-container'><div class='chat-bubble-assistant'>{assistant_msg}</div></div>", unsafe_allow_html=True)

    user_symptoms = st.text_input("Type your message:", key="user_input", placeholder="Enter your symptoms here...")

    if user_symptoms:
        st.session_state.user_responses.append(user_symptoms)
        
        if len(st.session_state.user_responses) < 3:
            assistant_reply = "Please provide more details about your symptoms."
        else:
            if "vectors" not in st.session_state:
                vector_embedding()
            prompt = ChatPromptTemplate.from_template("""Analyze symptoms and provide a suitable plant. User: {input} <context>{context}</context>""")
            retriever = st.session_state.vectors.as_retriever()
            retrieval_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(llm, prompt))
            response = retrieval_chain.invoke({'input': " ".join(st.session_state.user_responses), 'context': st.session_state.vectors})
            plant_name = response['answer']
            assistant_reply = f"Recommended Plant: {plant_name}"
            st.session_state.plant_recommended = True

            plant_image = extract_image_from_herbs_folder_or_web(plant_name, groq_api_key)
            if plant_image:
                st.image(plant_image, caption=f"Image of {plant_name}")
            else:
                assistant_reply += f"\nNo image found for {plant_name}."

        st.session_state.assistant_responses.append(assistant_reply)

elif mode == "Ayurvedic Tutor":
    plant_name = st.text_input("Enter the plant name", placeholder="Enter plant name here...")

    if plant_name:
        if "vectors" not in st.session_state:
            vector_embedding()

        prompt = ChatPromptTemplate.from_template(
            """Provide specific insights from the PDF documents. User: {input} <context>{context}</context>"""
        )
        
        retriever = st.session_state.vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(llm, prompt))
        response = retrieval_chain.invoke({'input': plant_name, 'context': st.session_state.vectors})
        
        st.write(f"Information about {plant_name}:")
        st.write(response['answer'])

        plant_image = extract_image_from_herbs_folder_or_web(plant_name, groq_api_key)
        if plant_image:
            st.image(plant_image, caption=f"Image of {plant_name}")
        else:
            st.write(f"No image found for {plant_name} in AyurHerbs folder.")