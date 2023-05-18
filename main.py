from twilio.rest import Client
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from dataset import askText
from googletrans import Translator
import os
from PyPDF2 import PdfReader
import random
import json
import time

app = Flask(__name__)
static_url_path = '/static'
app.config['UPLOAD_FOLDER'] = 'PDFupload/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Your Twilio account SID and auth token
account_sid = 'ACee4dbbd1a5e69ec1594f80e5b07be9dc'
auth_token = 'f8ae17f3e2fba54b5c1a1526837e9553'
client = Client(account_sid, auth_token)

sandBoxNumber = "whatsapp:+19046086893"
twilioNumber = "whatsapp:+14155238886"

# JSON Database -----------------------------------

import json


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


db = JSONDatabase('database.json')
# Text Translation Services ------------------------------------------------------------------


def detect_and_translate(text):
  translator = Translator()
  result = translator.translate(text, dest='en')
  detected_source_language = result.src
  translated_text = result.text
  return translated_text, detected_source_language


def translate_to_language(text, target_language):
  translator = Translator()
  result = translator.translate(text, dest=target_language)
  return result.text


# Twilio Messaging Services ------------------------------------------------------------------


def send_message(to, body, detected_language):
  translated_text = translate_to_language(body, detected_language)
  client.messages.create(to=to, from_=twilioNumber, body=translated_text)


def receive_message(message, responseNumber):
  translated_text, detected_language = detect_and_translate(message)
  # Your logic here
  print("User asked: {}".format(translated_text))
  response = askText(translated_text)
  print(response)
  if response == False:
    send_message(sandBoxNumber, "Your Selected Texts Pool is not working.",
                 detected_language)
    send_message(responseNumber,
                 "The system crashed, please contact your admin.",
                 detected_language)
  else:
    send_message(responseNumber, response, detected_language)


# PDF Handling -------------------------------------------------------------------


def generate_random_name(length=10):
  """Generates a random name of the specified length."""
  # Define a list of characters to use in the name
  characters = 'abcdefghijklmnopqrstuvwxyz'
  # Generate a random name by selecting `length` number of random characters
  name = ''.join(random.choice(characters) for i in range(length))
  return name


def pdf_to_text(pdf_path):
  pdf_file = open(pdf_path, 'rb')
  pdf_reader = PdfReader(pdf_file)

  text = ''
  for page in pdf_reader.pages:
    text += page.extract_text()

  pdf_file.close()
  # Remove newlines from the text
  text = text.replace('\n', '')

  return text


def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# PYTHON FLASK APP -------------------------------------------------------------------


@app.route("/sms", methods=['POST'])  # Python Messaging Recive Messaging SMS
def sms_reply():
  senderNumber = request.form['From']
  message_body = request.form['Body']
  print("Senders Phone Number is {}".format(senderNumber))
  receive_message(message_body, senderNumber)


# Continue the previous python code


@app.route('/upload', methods=['POST'])
def upload_file():
  # check if the post request has the file part
  if 'file' not in request.files:
    return redirect(request.url)

  print("Starting the file upload process. ----------------------------------")
  full_text = ""
  files = request.files.getlist('file')

  # Use the user-provided dataset name instead of a random name
  dataset_name = request.form['dataset_name']
  print("Dataset name: {}".format(dataset_name))

  for file in files:
    if file and allowed_file(file.filename):
      filename = dataset_name + "ID" + secure_filename(file.filename)
      print("Uploading: {}".format(filename))
      file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
      # Save the file with a new name
      file.save(file_path)
      print("File saved: {}".format(file_path))
      full_text += pdf_to_text(file_path)
      print("Text extracted from file: {}".format(file_path))

  print("Writing extracted text to file.")
  with open("datasets/" + dataset_name + ".txt", 'w') as f:
    f.write(full_text)
  print("Written to file: {}".format("datasets/" + dataset_name + ".txt"))

  # Delete PDF files
  print("Deleting the uploaded PDF files.")
  for file in files:
    filename = dataset_name + "ID" + secure_filename(file.filename)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    print("Deleted file: {}".format(
      os.path.join(app.config['UPLOAD_FOLDER'], filename)))

  print("Redirecting to home.")
  return redirect("/", code=302)


@app.route('/select_dataset', methods=['POST'])
def select_dataset():
  selected_dataset = request.form['dataset']
  print(selected_dataset)
  # Check to see if the selecteddataset exsits in the database
  db.add_item('selected_dataset', selected_dataset)
  return redirect("/", code=302)


@app.route('/')
def index():
  datasets = []
  for filename in os.listdir('datasets'):
    if filename.endswith('.txt'):
      with open('datasets/' + filename, 'r') as f:
        count = len(f.read().splitlines())
      datasets.append({
        'name': filename[:-4],  # remove .txt extension
        'count': count,
      })
  selected_dataset = db.read_item('selected_dataset')
  return render_template('index.html',
                         datasets=datasets,
                         selected_dataset=selected_dataset)


@app.route('/upload_success/<filename>', methods=['GET'])
def upload_success(filename):
  return render_template('upload_success.html')

# This was for repl.it
#if __name__ == "__main__":
#app.run(host='0.0.0.0', port=81, debug=True)


# This is for heroku
if __name__ == "__main__":
    app.run(debug=True)
