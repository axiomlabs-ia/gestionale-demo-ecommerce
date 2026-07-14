# 1 worker: il cap prove-AI è un contatore in memoria, con più worker non
# sarebbe condiviso e il limite a 3 non scatterebbe in modo affidabile.
web: gunicorn server:app --workers 1 --threads 4 --timeout 180 --bind 0.0.0.0:$PORT
