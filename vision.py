"""AI per il gestionale e-commerce (versione NEUTRA, qualsiasi settore).
Dalla foto di un prodotto deduce categoria, nome, descrizione e prezzo; genera una
foto ambientata/lifestyle del prodotto; dà una considerazione da store manager.
by Axiom Labs."""
import json
import os
import re

import anthropic

NEGOZIO = "un negozio online (e-commerce)"


def _estrai_json(raw):
    s = (raw or '').strip()
    if s.startswith('```'):
        s = re.sub(r'^```[a-zA-Z]*\s*', '', s)
        s = re.sub(r'\s*```$', '', s)
    m = re.search(r'\{.*\}', s, re.S)
    return json.loads(m.group(0) if m else s)


def heic_to_jpeg(image_b64, max_side=1600, quality=88):
    """Converte una foto HEIC/HEIF (iPhone) in JPEG e la ridimensiona.
    Ritorna il base64 del JPEG (senza prefisso data-URL)."""
    import base64
    import io
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    raw = base64.b64decode(image_b64)
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    w, h = im.size
    if max(w, h) > max_side:
        if w >= h:
            im = im.resize((max_side, max(1, round(h * max_side / w))))
        else:
            im = im.resize((max(1, round(w * max_side / h)), max_side))
    buf = io.BytesIO()
    im.save(buf, format='JPEG', quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


def analizza_prodotto(image_b64, media_type='image/jpeg', negozio=NEGOZIO):
    """Ritorna {categoria, nome, descrizione, prezzo_suggerito} dalla foto di un prodotto qualsiasi."""
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    system = (
        f"Sei l'assistente catalogo di {negozio}. Guarda la foto del prodotto e "
        "restituisci SOLO un JSON valido con questi campi: "
        '{"categoria":"categoria merceologica adatta, 1-2 parole (es. Abbigliamento, Elettronica, '
        'Arredo, Bellezza, Food, Accessori...)",'
        '"nome":"nome commerciale breve e accattivante del prodotto",'
        '"descrizione":"2-3 frasi in italiano, pronte per la scheda prodotto e-commerce: '
        'materiali/caratteristiche, uso, stile",'
        '"prezzo_suggerito":numero_intero_in_euro}. '
        "Deduci la categoria dal prodotto che vedi. Nessun testo fuori dal JSON."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=500, system=system,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": media_type, "data": image_b64}},
            {"type": "text", "text": "Analizza questo prodotto per il catalogo."}]}])
    d = _estrai_json(msg.content[0].text)
    try:
        prezzo = int(d.get('prezzo_suggerito') or 0) or None
    except (TypeError, ValueError):
        prezzo = None
    return {
        'categoria': (d.get('categoria') or 'Prodotti').strip(),
        'nome': (d.get('nome') or 'Nuovo prodotto').strip(),
        'descrizione': (d.get('descrizione') or '').strip(),
        'prezzo_suggerito': prezzo,
    }


def affina_prodotto(image_b64, media_type, istruzione, corrente, negozio=NEGOZIO):
    """Rifinisce il riconoscimento seguendo un'istruzione libera dell'utente
    (es. "è in cotone, non lino", "descrizione più breve", "alza il prezzo").
    Ritorna {categoria, nome, descrizione, prezzo_suggerito} aggiornati."""
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    system = (
        f"Sei l'assistente catalogo di {negozio}. Hai gia' analizzato la foto di un prodotto e "
        "prodotto una scheda. L'utente ti da' un'istruzione per correggerla o migliorarla. "
        "Applica l'istruzione e restituisci SOLO un JSON valido con TUTTI questi campi aggiornati: "
        '{"categoria":"categoria merceologica, 1-2 parole",'
        '"nome":"nome commerciale breve",'
        '"descrizione":"2-3 frasi in italiano, pronte per la scheda prodotto",'
        '"prezzo_suggerito":numero_intero_in_euro}. '
        "Mantieni invariato cio' che l'istruzione non chiede di cambiare. Se l'istruzione riguarda "
        "materiali o dettagli visibili, ricontrolla la foto. Nessun testo fuori dal JSON."
    )
    scheda = (
        f"Scheda attuale:\n- categoria: {corrente.get('categoria','')}\n- nome: {corrente.get('nome','')}\n"
        f"- descrizione: {corrente.get('descrizione','')}\n- prezzo: {corrente.get('prezzo','')}\n\n"
        f"Istruzione dell'utente: {istruzione}"
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=500, system=system,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": media_type, "data": image_b64}},
            {"type": "text", "text": scheda}]}])
    d = _estrai_json(msg.content[0].text)
    try:
        prezzo = int(d.get('prezzo_suggerito') or 0) or None
    except (TypeError, ValueError):
        prezzo = None
    return {
        'categoria': (d.get('categoria') or corrente.get('categoria') or 'Prodotti').strip(),
        'nome': (d.get('nome') or corrente.get('nome') or 'Nuovo prodotto').strip(),
        'descrizione': (d.get('descrizione') or corrente.get('descrizione') or '').strip(),
        'prezzo_suggerito': prezzo,
    }


def genera_ambientata(image_b64, media_type='image/jpeg', descrizione='', categoria=''):
    """Genera una foto AI AMBIENTATA/lifestyle del prodotto (stile e-commerce), partendo dalla
    foto prodotto. Usa Nano Banana Pro (Google `gemini-3-pro-image-preview`): tiene il prodotto
    identico e lo mette in una scena professionale. Ritorna una data-URL (base64)."""
    import base64
    import os as _os
    from google import genai
    from google.genai import types

    prompt = ("Generate a professional lifestyle e-commerce photograph of THIS EXACT product, "
              "placed in an appealing, tasteful real-life setting suited to the product, naturally "
              "styled with soft professional lighting and a clean, elegant background. Keep the "
              "product perfectly identical to the input photo: same shape, colours, materials, "
              "text/logos and proportions. Photorealistic, high quality.")
    if (descrizione or '').strip():
        prompt += " The product: " + descrizione.strip()

    client = genai.Client(api_key=_os.environ.get('GEMINI_API_KEY'))
    raw = base64.b64decode(image_b64)
    resp = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[types.Part.from_bytes(data=raw, mime_type=media_type or 'image/jpeg'), prompt])

    cands = getattr(resp, 'candidates', None) or []
    if not cands:
        raise RuntimeError('nessuna immagine generata (risposta vuota)')
    for part in (cands[0].content.parts or []):
        inline = getattr(part, 'inline_data', None)
        if inline and inline.data:
            b64 = base64.b64encode(inline.data).decode()
            mt = inline.mime_type or 'image/png'
            return f"data:{mt};base64,{b64}"
    raise RuntimeError('nessuna immagine nella risposta del modello')


def insight_prodotto(nome, categoria='', prezzo=0, giacenza=0):
    """Considerazione AI 'da store manager' su un prodotto: promozione, abbinamenti,
    posizionamento prezzo, vendite recenti (plausibili). Testo breve in italiano."""
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    system = ("Sei l'assistente di un gestionale e-commerce. "
              "Dai UNA considerazione breve e concreta su un prodotto, come un bravo store manager: "
              "valuta se conviene una promozione (in base a giacenza alta/bassa e prezzo), possibili "
              "abbinamenti o cross-selling, il posizionamento di prezzo, vendite recenti plausibili. "
              "2-3 frasi al massimo, in italiano, tono pratico e utile. Niente elenco puntato, solo il consiglio. "
              "Usa **grassetto** per l'idea chiave.")
    user = (f"Prodotto: {nome} · categoria: {categoria or 'prodotto'} · prezzo: {prezzo}€ · "
            f"giacenza: {giacenza} pezzi a magazzino.")
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=260, system=system,
                                 messages=[{"role": "user", "content": user}])
    return msg.content[0].text.strip()
