FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir .[dev]
RUN pip install --no-cache-dir einops ftfy regex
RUN pip install --no-cache-dir git+https://github.com/openai/CLIP.git
RUN pip install --no-cache-dir git+https://github.com/matthias-k/DeepGaze.git

RUN pip install --no-cache-dir transformers ckip-transformers scikit-learn joblib pandas openpyxl odfpy opencc-python-reimplemented requests

RUN python -c "from transformers import AutoModel, AutoTokenizer; \
    AutoModel.from_pretrained('ckiplab/bert-base-chinese-ws'); \
    AutoTokenizer.from_pretrained('ckiplab/bert-base-chinese-ws'); \
    AutoModel.from_pretrained('ckiplab/bert-base-chinese-pos'); \
    AutoTokenizer.from_pretrained('ckiplab/bert-base-chinese-pos')"

RUN playwright install chromium --with-deps

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm wget gnupg \
    && npm install -g lighthouse \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
