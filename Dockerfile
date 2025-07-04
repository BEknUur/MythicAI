FROM python:3.11-slim 


WORKDIR /usr/src/app 


COPY requirements.txt ./    

RUN pip install --no-cache-dir -r requirements.txt 

COPY . . 

VOLUME [ "/usr/src/app/data" ]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
