from langchain.document_loaders import UnstructuredPDFLoader
from langchain.vectorstores import Chroma, Pinecone
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone
from langchain.document_loaders import UnstructuredPDFLoader, OnlinePDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from sklearn.metrics.pairwise import cosine_similarity
import os
import openai
from boto3 import session
from botocore.client import Config
import json
from fileservices import DigitalOceanSpaces

from dotenv import load_dotenv

load_dotenv()

import time


ACCESS_ID = os.environ.get('ACCESS_ID')
SECRET_KEY = os.environ.get('SECRET_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_API_ENV = os.environ.get('PINECONE_API_ENV')

# Local API key for testing

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

#pdf = "pdf/Full Dataset.pdf"
dosfile = DigitalOceanSpaces('exon-hosting', 'nyc3', 'https://nyc3.digitaloceanspaces.com', os.environ.get('ACCESS_ID'), os.environ.get('SECRET_KEY'))


def preprocess_and_embed_texts(dataset):
    # Get all files in the PDF folder
    # Download the file
    dosfile.download_file("temp.pdf", dataset)
    loader = UnstructuredPDFLoader("temp.pdf")
    data = loader.load()
    print (f'You have {len(data)} document(s) in your data')
    print (f'There are {len(data[0].page_content)} characters in your document')

    text_splitter = RecursiveCharacterTextSplitter(
      chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(data)

    print (f'Now you have {len(texts)} documents')

    #print(texts)
    pinecone.init(
        api_key=PINECONE_API_KEY,  # find at app.pinecone.io
        environment=PINECONE_API_ENV # next to api key in console
    )
    index_name = "exon-hostings"
    namespace = "text"
    # Time how long it takes to index the documents
    totalStart = time.time()
    start = time.time()
    index = pinecone.Index(index_name)
    index.delete(deleteAll='true', namespace=namespace)
    Pinecone.from_texts(
      [t.page_content for t in texts], embeddings,
      index_name=index_name, namespace=namespace)
    
    return "Complete"
    
    
    
      
      

      


def ask(query):
    index_name = "exon-hostings"
    namespace = "text"

    totalStart = time.time()
    docsearch = Pinecone.from_existing_index(index_name, embeddings)
    end = time.time()
    print(f"Indexing took {end - start} seconds")

    start = time.time()
    llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
    chain = load_qa_chain(llm, chain_type="stuff")
    end = time.time()
    print(f"Loading the chain took {end - start} seconds")

    #query = "What is webroot?"
    start = time.time()
    docs = docsearch.similarity_search(query,
      namespace=namespace)
    end = time.time()
    print(f"Searching took {end - start} seconds")

    start = time.time()
    answer = chain.run(input_documents=docs, question=query)
    end = time.time()
    totalEnd = time.time()

    print(f"Answering took {end - start} seconds")
    print(f"Total time: {totalEnd - totalStart} seconds")
    # Format the answer so that it's easier to read and there isnt any extra newlines or spaces before the answer
    answer = answer.replace("\n", "")
    return answer



#print(ask("What folder is gunicorn in?"))