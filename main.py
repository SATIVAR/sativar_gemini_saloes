from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "Agente de Salão AI Backend Ativo"}