FROM python:3

WORKDIR /usr/src/Pypher

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "./pypher.py"]
