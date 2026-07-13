# Gestionale e-commerce AI — DEMO NEUTRA (by Axiom Labs)

Strumento **riutilizzabile per l'outreach**: gestionale e-commerce con funzioni AI, neutro
(nessun settore/brand), da mandare ai proprietari di e-commerce come dimostrazione.
Derivato dal gestionale costruito per G'local, reso generico.

## Come avviarlo
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python server.py
```
Poi apri: **http://127.0.0.1:8000/**

Un solo comando (`server.py`) serve il gestionale + le API AI sulla stessa porta.

## Le 3 funzioni "wow" (per il prospect)
- **Carica il tuo prodotto da foto** → l'AI riconosce categoria, nome, descrizione, prezzo
  (Claude vision). Rifinibile con un'istruzione in linguaggio naturale.
- **Genera foto ambientata** → dalla foto prodotto crea una foto lifestyle professionale,
  tenendo il prodotto identico (Google Nano Banana Pro, `gemini-3-pro-image-preview`).
- **Considerazione AI** su ogni prodotto (promozioni, cross-selling, prezzo) — Claude.

## File
- `index.html` → il gestionale (single page, CSS/JS inline). Chiamate AI a `/api/store/...`
- `server.py` → Flask: serve statico + endpoint AI
- `vision.py` → logica AI (generica, qualsiasi settore)
- `.env` → `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (**non committare**)

## Personalizzare per un prospect
- Brand demo: cerca "Demo Store" in `index.html` (logo/titolo) e sostituisci col nome del prospect.
- Catalogo di partenza: array `products` in `index.html` (8 prodotti neutri di esempio).
- Il resto (categorie, descrizioni) lo genera l'AI dalle foto caricate.

## Note
- Costi AI immagine: sulla chiave Gemini in `.env` (in produzione → chiave del cliente/prospect).
- Per una demo online serve un host che faccia girare `server.py` (Flask), non solo file statici.
