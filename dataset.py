from langchain.document_loaders import UnstructuredPDFLoader
from langchain.vectorstores import Chroma, Pinecone
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

import json

from dotenv import load_dotenv

load_dotenv()



OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_API_ENV = os.environ.get('PINECONE_API_ENV')

# Local API key for testing

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

#pdf = "pdf/Full Dataset.pdf"


class JSONDatabase:
  """
  A class representing a simple local JSON database.
  """

  def __init__(self, filename):
    """
    Creates a new JSON database using the specified filename.

    :param filename: The name of the JSON file to use for the database.
    """

    # Define the database file and load its contents
    self.filename = filename
    self.db = self._load_db()

  def _load_db(self):
    """
    Loads the JSON database from the file.
    If the file does not exist or is not valid JSON, returns an empty dictionary.

    :return: A dictionary representing the JSON database.
    """

    try:
      with open(self.filename, 'r') as f:
        return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
      return {}

  def _write_db(self):
    """
    Writes the JSON database to the file.
    """

    with open(self.filename, 'w') as f:
      json.dump(self.db, f)

  def add_item(self, key, value):
    # Check if the database already contains an item with the specified key
    if key in self.db:
      # If it does, append the new value to the list of values for that key
      self.db[key] = value
      self._write_db()
    else:
      self.db[key] = value
      self._write_db()

  def read_item(self, key):
    """Reads an item from the database with the specified key."""
    return self.db.get(key, None)

  def change_item(self, key, value):
    """Changes the value of an item in the database with the specified key."""
    if key in self.db:
      self.db[key] = value
      self._write_db()

  def remove_item(self, key):
    """Removes an item from the database with the specified key."""
    if key in self.db:
      del self.db[key]
      self._write_db()


def checkTexts():
  db = JSONDatabase('database.json')
  textName = "datasets/" + db.read_item('selected_dataset') + '.txt'
  print(textName)
  if not os.path.exists(textName):
    return False

  print("FOUND")
  with open(textName, 'r') as f:
    texts = f.read().splitlines()

  return texts


def askText(questionasked):

  texts = checkTexts()
  if texts == False:
    return False
  pinecone.init(
    api_key=PINECONE_API_KEY,  # find at app.pinecone.io
    environment=PINECONE_API_ENV  # next to api key in console
  )

  index_name = "testings"  # put in the name of your pinecone index here
  docsearch = Pinecone.from_texts(texts, embeddings, index_name=index_name)
  print("DocSeach Done")
  #
  #query = "What is the story behind the stoning of the Jamaraat?"
  #docs = docsearch.similarity_search(query)
  #print(docs[0].page_content[:450])

  llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
  chain = load_qa_chain(llm, chain_type="stuff")
  print("LLM Loaded")
  print("Asking {} to the AI.".format(questionasked))
  docs = docsearch.similarity_search(questionasked)
  print(docs)
  print("Similarity Seach Completed")

  prompt = "You are a assistance bot. The user has asked the question {}. If you do not know the answer say, im sorry I do not know the answer to that.".format(
    questionasked)
  print("Asking {}".format(prompt))
  return chain.run(input_documents=docs, question=prompt)
