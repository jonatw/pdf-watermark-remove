from flask import Flask, request, send_file, render_template_string, redirect
import os
import fitz
import re
from collections import Counter
import uuid

app = Flask(__name__)
APP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def remove_watermark(input_file, output_file):
    doc = fitz.open(input_file)
    def most_frequent_substring(byte_array, length):
        count = {}
        for i in range(len(byte_array) - length + 1):
            substring = bytes(byte_array[i:i + length])
            if substring in count:
                count[substring] += 1
            else:
                count[substring] = 1
        most_frequent = max(count, key=count.get)
        return most_frequent, count[most_frequent]
    page = doc[0]
    page.clean_contents()
    xref = page.get_contents()[0]
    cont = bytearray(page.read_contents())
    byte_length = 100
    most_frequent, frequency = most_frequent_substring(cont, byte_length)
    for page in doc:
        page.clean_contents()
        xref = page.get_contents()[0]
        cont = bytearray(page.read_contents())
        while True:
            i1 = cont.find(most_frequent)
            if i1 < 0: break
            cont[i1 : i1+len(most_frequent)] = b""
        doc.update_stream(xref, cont)
    doc.ez_save(output_file)

@app.route('/upload', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    filename = str(uuid.uuid4())
    input_file = os.path.join(APP_FOLDER, 'input_' + filename + '.pdf')
    output_file = os.path.join(APP_FOLDER, 'output_' + filename + '.pdf')
    file.save(input_file)
    remove_watermark(input_file, output_file)
    return send_file(output_file)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(open('index.html').read())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)