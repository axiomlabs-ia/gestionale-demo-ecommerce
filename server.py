"""Gestionale e-commerce AI (demo NEUTRA) — by Axiom Labs.
Serve il gestionale (index.html) E le funzioni AI su un'unica porta.

Avvio:
    python -m venv venv
    venv/bin/pip install -r requirements.txt
    venv/bin/python server.py
Poi apri:  http://127.0.0.1:8000/
"""
import os
import re

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, '.env'))

import vision

app = Flask(__name__, static_folder=None)


@app.route('/')
def home():
    return send_from_directory(HERE, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(HERE, filename)


def _img_from_payload(data):
    img = data.get('image') or ''
    media = 'image/jpeg'
    if img.startswith('data:'):
        head, _, b64 = img.partition(',')
        m = re.match(r'data:([^;]+)', head)
        if m:
            media = m.group(1)
        img = b64
    return img, media


@app.route('/api/store/convert-heic', methods=['POST'])
def api_convert_heic():
    data = request.get_json(silent=True) or {}
    img, media = _img_from_payload(data)
    if not img:
        return jsonify({'success': False, 'error': 'image required'}), 400
    try:
        jpeg_b64 = vision.heic_to_jpeg(img)
        return jsonify({'success': True, 'image': 'data:image/jpeg;base64,' + jpeg_b64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/api/store/vision', methods=['POST'])
def api_vision():
    data = request.get_json(silent=True) or {}
    img, media = _img_from_payload(data)
    if not img:
        return jsonify({'success': False, 'error': 'image required'}), 400
    try:
        return jsonify({'success': True, **vision.analizza_prodotto(img, media)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/api/store/refine', methods=['POST'])
def api_refine():
    data = request.get_json(silent=True) or {}
    img, media = _img_from_payload(data)
    istruzione = (data.get('istruzione') or '').strip()
    if not img:
        return jsonify({'success': False, 'error': 'image required'}), 400
    if not istruzione:
        return jsonify({'success': False, 'error': 'istruzione required'}), 400
    try:
        return jsonify({'success': True, **vision.affina_prodotto(img, media, istruzione, data.get('corrente') or {})})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/api/store/generate-scene', methods=['POST'])
def api_scene():
    data = request.get_json(silent=True) or {}
    img, media = _img_from_payload(data)
    if not img:
        return jsonify({'success': False, 'error': 'image required'}), 400
    try:
        url = vision.genera_ambientata(img, media, data.get('descrizione') or '', data.get('categoria') or '')
        return jsonify({'success': True, 'image_url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/api/store/product-insight', methods=['POST'])
def api_insight():
    d = request.get_json(silent=True) or {}
    try:
        txt = vision.insight_prodotto(d.get('nome') or 'prodotto', d.get('categoria') or '',
                                      d.get('prezzo') or 0, d.get('giacenza') or 0)
        return jsonify({'success': True, 'insight': txt})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"\n  Gestionale e-commerce (demo) su http://127.0.0.1:{port}/\n")
    app.run(host='127.0.0.1', port=port, debug=True)
