FROM python:3.10-bullseye

WORKDIR /twilio-chatbot

COPY requirements.txt .

ARG GITHUB_TOKEN ENV GITHUB_TOKEN=${GITHUB_TOKEN}

RUN if [ -z "$GITHUB_TOKEN" ] ; then echo "GITHUB_TOKEN must be set during build" && exit 1; fi

# RUN sed -i "s/GITHUB_TOKEN_PLACEHOLDER/${GITHUB_TOKEN}/g" requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]