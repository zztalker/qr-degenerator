"""QR Code Updater - Flask web app.

Upload a PDF, extract its ST00012 payment QR, edit the Purpose field,
and get a scannable updated QR back in the browser.
"""

import base64
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from qr_processor import (
    extract_purpose,
    find_qr_in_pdf,
    generate_qr_png,
    update_purpose,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

APPEND_FILE = Path(__file__).parent / "append.txt"


def get_append_text():
    if APPEND_FILE.exists():
        return APPEND_FILE.read_text()
    return ""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/healthz')
def healthz():
    return 'ok', 200


@app.route('/process', methods=['POST'])
def process():
    file = request.files.get('pdf')
    if file is None or not file.filename:
        return jsonify({'error': 'No PDF uploaded'}), 400

    qr_text = find_qr_in_pdf(file.read())
    if not qr_text:
        return jsonify({'error': 'No ST00012 UTF-8 QR code found in PDF'}), 400

    current_purpose = extract_purpose(qr_text) or ''
    return jsonify({
        'decoded': qr_text,
        'current_purpose': current_purpose,
        'suggested_purpose': current_purpose + get_append_text(),
    })


@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(silent=True) or {}
    decoded = data.get('decoded', '')
    new_purpose = data.get('purpose', '').strip()
    if not decoded or not new_purpose:
        return jsonify({'error': 'Missing decoded text or purpose'}), 400

    updated_text = update_purpose(decoded, new_purpose)
    png_b64 = base64.b64encode(generate_qr_png(updated_text)).decode()
    return jsonify({
        'qr_png': f'data:image/png;base64,{png_b64}',
        'updated_text': updated_text,
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
