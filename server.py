from flask import Flask, request, send_file, render_template_string, redirect
import os, uuid
from remove_watermark import remove_watermark
import asyncio

app = Flask(__name__)
APP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # 使用 run_in_executor 運行異步函數
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(remove_watermark(input_file, output_file))

    return send_file(output_file)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(open('index.html').read())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5566)