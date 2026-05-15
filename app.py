"""QR Code Updater - Flask web app.

Upload a PDF, extract its ST00012 payment QR, edit the Purpose field,
and get a scannable updated QR back in the browser.
"""

import base64
import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from qr_processor import (
    extract_purpose,
    find_qr_in_pdf,
    generate_qr_png,
    update_purpose,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

gunicorn_logger = logging.getLogger('gunicorn.error')
if gunicorn_logger.handlers:
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
else:
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)


@app.before_request
def log_request():
    app.logger.info(
        "request %s %s from %s",
        request.method,
        request.path,
        request.remote_addr,
    )

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
    app.logger.info(
        "process: content-type=%r content-length=%s",
        request.content_type,
        request.content_length,
    )
    file = request.files.get('pdf')
    if file is None:
        app.logger.warning(
            "process: 'pdf' field missing; form=%s files=%s",
            list(request.form.keys()),
            list(request.files.keys()),
        )
        return jsonify({'error': 'No PDF uploaded'}), 400
    if not file.filename:
        app.logger.warning("process: 'pdf' field present but filename empty")
        return jsonify({'error': 'No PDF uploaded'}), 400

    pdf_bytes = file.read()
    app.logger.info("process: %s (%d bytes)", file.filename, len(pdf_bytes))

    qr_text = find_qr_in_pdf(pdf_bytes)
    if not qr_text:
        app.logger.warning("process: no QR found in %s", file.filename)
        return jsonify({'error': 'No ST00012 UTF-8 QR code found in PDF'}), 400

    current_purpose = extract_purpose(qr_text) or ''
    app.logger.info("process: extracted purpose=%r", current_purpose)
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
        app.logger.warning("generate: missing decoded or purpose")
        return jsonify({'error': 'Missing decoded text or purpose'}), 400

    updated_text = update_purpose(decoded, new_purpose)
    app.logger.info("generate: new purpose=%r", new_purpose)
    png_b64 = base64.b64encode(generate_qr_png(updated_text)).decode()
    return jsonify({
        'qr_png': f'data:image/png;base64,{png_b64}',
        'updated_text': updated_text,
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
