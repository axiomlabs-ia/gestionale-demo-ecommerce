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
import threading
from datetime import date

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, '.env'))

import vision

app = Flask(__name__, static_folder=None)

# ── Usage cap (protegge le chiavi AI su un deploy pubblico) ──────────
# Ogni visitatore ha diritto a un numero limitato di prove AND c'è un tetto
# globale giornaliero come rete di sicurezza contro l'abuso da molti IP.
FREE_USES_PER_IP = int(os.environ.get('DEMO_FREE_USES', 3))     # "3 utilizzi" a prospect
GLOBAL_DAILY_CAP = int(os.environ.get('DEMO_GLOBAL_DAILY_CAP', 150))  # backstop chiavi

_usage_lock = threading.Lock()
_ip_uses: dict[str, int] = {}      # ip -> prove AI consumate (oggi)
_global_uses = {'day': None, 'count': 0}


def _client_ip() -> str:
    # Railway/proxy: il vero IP è nel primo elemento di X-Forwarded-For.
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _reset_if_new_day() -> None:
    today = date.today().isoformat()
    if _global_uses['day'] != today:
        _global_uses['day'] = today
        _global_uses['count'] = 0
        _ip_uses.clear()


def check_and_count_use():
    """Consuma una prova AI per l'IP chiamante. Ritorna (ok, remaining, reason).
    ok=False => la vista deve rispondere col 'cartello' (limit_reached)."""
    ip = _client_ip()
    with _usage_lock:
        _reset_if_new_day()
        if _global_uses['count'] >= GLOBAL_DAILY_CAP:
            return False, 0, 'global'
        used = _ip_uses.get(ip, 0)
        if used >= FREE_USES_PER_IP:
            return False, 0, 'ip'
        _ip_uses[ip] = used + 1
        _global_uses['count'] += 1
        return True, FREE_USES_PER_IP - (used + 1), 'ok'


def _limit_response(reason: str):
    """Il 'cartello': invita a contattare Axiom quando le prove sono finite."""
    msg = ("Hai esaurito le prove gratuite di questa demo. "
           "Scrivici per attivare la versione completa del gestionale sul tuo store.")
    return jsonify({
        'success': False,
        'limit_reached': True,
        'reason': reason,
        'error': msg,
        'contact': {
            'nome': 'Axiom Labs',
            'email': 'axiomlabs.ia@gmail.com',
            'telefono': '+39 345 783 5222',
        },
    }), 429


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
    ok, _rem, reason = check_and_count_use()
    if not ok:
        return _limit_response(reason)
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
    ok, _rem, reason = check_and_count_use()
    if not ok:
        return _limit_response(reason)
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
    ok, _rem, reason = check_and_count_use()
    if not ok:
        return _limit_response(reason)
    try:
        url = vision.genera_ambientata(img, media, data.get('descrizione') or '', data.get('categoria') or '')
        return jsonify({'success': True, 'image_url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/api/store/product-insight', methods=['POST'])
def api_insight():
    d = request.get_json(silent=True) or {}
    ok, _rem, reason = check_and_count_use()
    if not ok:
        return _limit_response(reason)
    try:
        txt = vision.insight_prodotto(d.get('nome') or 'prodotto', d.get('categoria') or '',
                                      d.get('prezzo') or 0, d.get('giacenza') or 0)
        return jsonify({'success': True, 'insight': txt})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:200]})


@app.route('/healthz')
def healthz():
    return jsonify({'ok': True})


@app.route('/api/usage-debug')
def usage_debug():
    """Diagnostica temporanea: cosa vede il server per il cap prove-AI."""
    with _usage_lock:
        return jsonify({
            'seen_ip': _client_ip(),
            'x_forwarded_for': request.headers.get('X-Forwarded-For', ''),
            'remote_addr': request.remote_addr,
            'ip_uses': dict(_ip_uses),
            'global': dict(_global_uses),
            'free_per_ip': FREE_USES_PER_IP,
            'worker_pid': os.getpid(),
        })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    # 0.0.0.0 così funziona anche dietro il proxy di Railway; in locale resta
    # raggiungibile su 127.0.0.1. Debug solo fuori produzione.
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    print(f"\n  Gestionale e-commerce (demo) su http://127.0.0.1:{port}/\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
