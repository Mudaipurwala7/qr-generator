from flask import Flask, request, send_file, render_template_string, send_from_directory
import qrcode
from PIL import Image, ImageDraw, ImageFont
import zipfile
import os
import io
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB file limit

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Bulk QR Code Generator</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f4f6f8;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 50px;
    }
    h1 {
      color: #333;
      margin-bottom: 10px;
    }
    p {
      color: #555;
      font-size: 14px;
      margin-bottom: 30px;
      max-width: 500px;
      text-align: center;
    }
    form {
      background-color: #fff;
      padding: 30px 40px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    input[type="file"] {
      margin-bottom: 20px;
    }
    input[type="submit"] {
      background-color: #2e86de;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 16px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    input[type="submit"]:hover {
      background-color: #1e5faa;
    }
  </style>
</head>
<body>
  <h1>Bulk QR Code Generator</h1>
  <p>
    Upload a CSV file with the following columns:<br>
    <strong>Tiffin Number, HOF ITS, Name, Sabeel Number, ITS Members List (Je Sagla mumineen thaali ma si jame che)</strong><br>
    You will receive a zip file with one QR code per row.
  </p>
  <a href="/sample-template" style="
    margin-bottom: 20px;
    background-color: #27ae60;
    color: white;
    padding: 10px 16px;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 500;
  ">
    ⬇️ Download Sample CSV
  </a>
  <p style="font-size: 13px; color: #c0392b; margin-top: 5px; margin-bottom: 20px;">
    ⚠️ Please do not modify the first row (headers) of the CSV file. Just fill in your data below it.
  </p>
  <form action="/generate" method="post" enctype="multipart/form-data">
    <input type="file" name="file" accept=".csv" required>
    <input type="submit" value="Generate QR Codes">
  </form>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate_qr():
    if 'file' not in request.files:
        return 'No file part in request.'
    file = request.files['file']

    if file.filename == '' or not file.filename.lower().endswith('.csv'):
        return 'Invalid file type. Please upload a .csv file.'

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return f'Failed to read CSV file. Error: {str(e)}'

    expected_col = "ITS Members List (Je Sagla mumineen thaali ma si jame che)"
    if expected_col not in df.columns or len(df.columns) != 5:
        return 'CSV must have 5 columns including: "Tiffin Number , HOF ITS, Name, Sabeel Number, ITS Members List (Je Sagla mumineen thaali ma si jame che)"'

    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for i, row in df.iterrows():
                try:
                    tiffin_number = row.iloc[0]
                    hof_its = row.iloc[1]
                    name = row.iloc[2]
                    sabeel = row.iloc[3]
                    its_list_raw = str(row[expected_col])

                    its_list = its_list_raw.replace(';', ',').split(',')
                    its_lines = '\n'.join([f"- {its.strip()}" for its in its_list if its.strip()])

                    qr_content = (
                        f"Tiffin Number: {tiffin_number}\n"
                        f"HOF ITS: {hof_its}\n"
                        f"Name: {name}\n"
                        f"Sabeel Number: {sabeel}\n"
                        f"ITS Members List (Je Sagla mumineen thaali ma si jame che):\n{its_lines}"
                    )

                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=6,
                        border=2
                    )
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

                    label_height = 50
                    final_img = Image.new("RGB", (qr_img.width, qr_img.height + label_height), "white")
                    final_img.paste(qr_img, (0, 0))

                    draw = ImageDraw.Draw(final_img)
                    try:
                        font = ImageFont.truetype("arial.ttf", 22)
                    except:
                        font = ImageFont.load_default()

                    label_text = f"Tiffin #: {tiffin_number}"
                    text_box = draw.textbbox((0, 0), label_text, font=font)
                    text_width = text_box[2] - text_box[0]
                    draw.text(((qr_img.width - text_width) // 2, qr_img.height + 10), label_text, fill="black", font=font)

                    img_byte_arr = io.BytesIO()
                    final_img.save(img_byte_arr, format='PNG')
                    zipf.writestr(f'qr_{i+1}_tiffin_{tiffin_number}.png', img_byte_arr.getvalue())
                except Exception as qr_err:
                    print(f"Error on row {i+1}: {qr_err}")
                    continue
    except Exception as e:
        return f"An error occurred while generating QR codes: {str(e)}"

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', download_name='qr_codes.zip', as_attachment=True)

@app.route('/sample-template')
def download_sample():
    return send_from_directory('static', 'sample_template.csv', as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
