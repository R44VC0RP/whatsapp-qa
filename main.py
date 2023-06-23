from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
#from dataset import preprocess_and_embed_texts, ask
from datasetv3 import preprocess_and_embed_texts, ask
from googletrans import Translator

import os
from PyPDF2 import PdfReader
import random
import json
import time
from dotenv import load_dotenv
from fileservices import DigitalOceanSpaces
from PyPDF2 import PdfWriter, PdfFileReader
import logging
# from boto3 import session
# from botocore.client import Config

load_dotenv()



dosfile = DigitalOceanSpaces('exon-hosting', 'nyc3', 'https://nyc3.digitaloceanspaces.com', os.environ.get('ACCESS_ID'), os.environ.get('SECRET_KEY'))



print("Starting the Flask App. ----------------------------------")

# Flask Setup -----------------------------------------------------------------------

app = Flask(__name__)
static_url_path = '/static'
app.config['UPLOAD_FOLDER'] = 'PDFupload/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Twilio Setup ----------------------------------------------------------------------

# Your Twilio account SID and auth token
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

client = Client(account_sid, auth_token)

sandBoxNumber = "whatsapp:+19046086893"
twilioNumber = "whatsapp:+14155238886"

logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

# Text Translation Services ------------------------------------------------------------------


def detect_and_translate(text):
  translator = Translator()
  result = translator.translate(text, dest='en')
  detected_source_language = result.src
  translated_text = result.text
  return translated_text, detected_source_language


def translate_to_language(text, target_language):
  translator = Translator(service_urls=[
      'translate.google.com'
    ])
  print("Translating {} to {}".format(target_language, text))
  result = translator.translate(text, dest=target_language)
  return result.text


# Twilio Messaging Services ------------------------------------------------------------------


def send_twilio_message(to, body):
  print("Sending message '{}' to {}".format(body, to))
  try:
    message = client.messages.create(to=to, from_=twilioNumber, body=body)
    print("Message sent successfully.")
    print(message.sid)
  except TwilioRestException as e:
    print(f"Failed to send message. Error: {e}")

def send_message(to, body, detected_language):
  translated_text = translate_to_language(body, detected_language)
  send_twilio_message(to, translated_text)
  


def receive_message(message, responseNumber):
  translated_text, detected_language = detect_and_translate(message)
  # Your logic here
  print("User asked: {}".format(translated_text))
  response = ask(translated_text, responseNumber)
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


# File Handling -------------------------------------------------------------------

# PYTHON FLASK APP -------------------------------------------------------------------
@app.route('/send_chat', methods=['POST'])
def send_chat():
  message = request.json['message']
  # Do something with the message, such as processing it or storing it in a database
  response = ask(message)
  print("User asked: {} and System Responded with {}".format(message, response))
  if response == False:
    return jsonify({'message': 'The system crashed, please contact your admin.'})
  else:
    return jsonify({'message': response})

  print(message)
  response = {'message': f'You sent: {message}'}
  return jsonify(response)

@app.route("/sms", methods=['POST'])  # Python Messaging Recive Messaging SMS
def sms_reply():
  logging.info("Starting the SMS reply process. ----------------------------------")
  logging.info("User asked: {}".format(request.form['Body']))
  print("Starting the SMS reply process. ----------------------------------")
  print("User asked: {}".format(request.form['Body']))
  senderNumber = request.form['From']
  message_body = request.form['Body']
  print("Senders Phone Number is {}".format(senderNumber))
  receive_message(message_body, senderNumber)


@app.route('/upload', methods=['POST'])
def upload_file():
  # check if the post request has the file part
  if 'file' not in request.files:
    return redirect(request.url)

  print("Starting the file upload process. ----------------------------------")
  full_text = ""
  files = request.files.getlist('file')
  print(files)
        

  # Use the user-provided dataset name instead of a random name
  dataset_name = request.form['dataset_name']
  print("Dataset name: {}".format(dataset_name))
  allPDFs = []
  for file in files:
    if file and allowed_file(file.filename):
      filename = dataset_name + "-ID-" + secure_filename(file.filename)
      print("Processing: {}".format(filename))
      file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
      print("File path: {}".format(file_path))
      # Save the file with a new name
      file.save(file_path)
      print("File saved.")
      allPDFs.append(file_path)

      # upload_file(file, "pdf")
      # print("File {} uploaded ".format(filename))
      # downloadfile(filename, "pdf")
      # full_text += pdf_to_text(file_path)
      # print("Text extracted from file: {}".format(filename))

  # print("Writing extracted text to file.")
  # with open(dataset_name + ".txt", "w") as text_file:
  #   text_file.write(full_text)
  # print("Uploading file to Digital Ocean Spaces.")
  # dosfile.upload_file(dataset_name + ".txt", "datasets/plain/" + dataset_name + ".txt")
  # print("Written to file: {}".format("datasets/" + dataset_name + ".txt"))

  # Merging the PDF files
  merger = PdfWriter()

  for pdf in allPDFs:
    merger.append(pdf)
  
  merger.write(dataset_name + ".pdf")
  merger.close()

  # Uploading the PDF file
  print("Uploading the PDF file.")
  dosfile.upload_file(dataset_name + ".pdf", "datasets/pdf/" + dataset_name + ".pdf")

  # Deleting the PDF files
  print("Deleting the PDF files.")
  for file in files:
    if file and allowed_file(file.filename):
      filename = dataset_name + "-ID-" + secure_filename(file.filename)
      file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
      os.remove(file_path)
      print("Deleted file: {}".format(filename))
  
  print("Redirecting to home.")
  return redirect("/", code=302)

@app.route('/select_dataset', methods=['POST'])
def select_dataset():
  selected_dataset = request.form['dataset']
  
  # Check to see if the selecteddataset exsits in the database
  fullpath = "datasets/pdf/" + selected_dataset + ".pdf"
  print(preprocess_and_embed_texts(fullpath))


  dosfile.db_write('selected_dataset', selected_dataset)
  return redirect("/", code=302)

@app.route('/')
def index():
  logging.info("Starting the index process. ----------------------------------")
  print("Starting the index process. ----------------------------------")
  datasets = []
  # Get the files in the embeddings folder in datasets
  datasetFiles = dosfile.list_files("datasets/pdf/")
  
  for filename in datasetFiles:
    fname = filename.replace("datasets/pdf/", "").replace(".pdf", "")
    datasets.append({
      'name': fname,  # remove .txt extension
    })

  # Get the selected dataset from the database
  selected_dataset = dosfile.db_read('selected_dataset')
  return render_template('index.html', datasets=datasets, selected_dataset=selected_dataset)



# This is for heroku
if __name__ == "__main__":
    print("Starting the application. ----------------------------------")
    send_twilio_message("whatsapp:+9046086893", "Hello from Python!")
    app.run()





# Flask application that provides services for handling incoming SMS messages, file uploads, and dataset selection. 
# It interacts with several external APIs and services, such as Twilio, Google Translate, PyPDF2, and DigitalOcean Spaces. Let's break down the key features:
# Twilio Messaging: This application uses the Twilio API for handling incoming SMS messages and replying to them. 
# The function sms_reply is mapped to the "/sms" route and handles POST requests. When a POST request is made to this route (which typically happens when a new SMS is received), it takes the body of the message and the sender's phone number, translates the received message, generates a response, and sends this response back to the sender.
# File Upload and Handling: The application also allows users to upload files to the server. 
# The function upload_file handles these uploads, ensuring only PDFs are accepted. 
# It generates a new, unique name for each uploaded file, saves them to a local directory, 
# processes the text within the PDFs, merges them into one single file, and finally uploads the merged file to a 
# DigitalOcean Spaces storage bucket.
# Dataset Selection: The application also provides an endpoint '/select_dataset' that allows users to select a dataset for 
# further operations. The name of the selected dataset is stored in the DigitalOcean Spaces database.
# PDF Text Extraction: The pdf_to_text function is responsible for converting the content of uploaded PDFs into plain text.
# Translation Services: Google Translate API is used in this application to detect and translate text. 
# The functions detect_and_translate and translate_to_language are used for these purposes respectively.
# Index Page Rendering: The root route of the application ("/") renders an index page that lists available datasets and 
# the currently selected dataset.
# To understand the application better, it's recommended to familiarize yourself with the Flask framework, Twilio API, 
# Google Translate API, PyPDF2 library, and DigitalOcean Spaces API. Also, it would be beneficial to understand how the 
# files are structured and organized in the project.