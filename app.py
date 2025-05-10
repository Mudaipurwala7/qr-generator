from flask import Flask, request, send_file, render_template_string
import qrcode
import zipfile
import os
import io
import pandas as pd

app = Flask(__name__)

# HTML page for upload
HTML_UPLOAD = """
<!doctype html>
<title>Bulk QR Code Generator</title>
<h2>Upload CSV to Generate QR Codes</h2>
<form action="/generate" method=post enctype=multipart/form-data>
  <input type=file name=file accept=".csv" required>
  <input type=submit value="Generate QR Codes">
</form>
"""

# HTML page while processing
HTML_PROCESSING = """
<!doctype html>
<title>Generating...</title>
<h2>Processing your file, please wait...</h2>
<p>This may take a few seconds depending on file size.</p>
"""

@app.route('/')
def index():
    return render_template_string(HTML_UPLOAD)

@app.route('/generate', methods=['POST'])
def generate_qr():
    if 'file' not in request.files:
        return 'No file part in request.'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file.'

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return f'Error reading CSV: {str(e)}'

    if df.shape[1] != 3:
        return 'CSV must have exactly three columns: Thaali Number, Name, ID Number.'

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for i, row in df.iterrows():
            qr_content = f"Thaali Number: {row[0]}\nName: {row[1]}\nID Number: {row[2]}"
            img = qrcode.make(qr_content)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            zipf.writestr(f'qr_{i+1}.png', img_byte_arr.getvalue())

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        download_name='qr_codes.zip',
        as_attachment=True
    )

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
