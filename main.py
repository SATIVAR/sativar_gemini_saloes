# main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import asyncpg # Adicione esta importação para um erro específico da Vercel
# Importe o cliente supabase que configuramos
from db import supabase
# main.py (adicione estas importações no topo)
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from tools import AVAILABLE_TOOLS # Importa nosso mapeamento de ferramentas
from fastapi import HTTPException
import inspect # <<< ADICIONE ESTE IMPORT NO TOPO

load_dotenv()

# Configure o cliente Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="Você é um assistente de salão de beleza. Seja amigável e direto. Sua função é responder perguntas e agendar serviços. Use as ferramentas disponíveis quando necessário para verificar horários ou criar agendamentos."
)

# --- Definição das ferramentas para o modelo entender ---
tools_definition = [
    {
        "name": "get_available_slots",
        "description": "Obtém os horários disponíveis para um serviço com um profissional em um intervalo de datas.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "O serviço desejado, ex: 'corte de cabelo'."},
                "professional": {"type": "string", "description": "O nome do profissional, ex: 'Juliana'."},
                "date_range": {"type": "string", "description": "O período de busca, ex: 'hoje', 'amanhã', 'próxima semana'."}
            },
            "required": ["service", "professional", "date_range"]
        }
    },
    {
        "name": "create_appointment",
        "description": "Cria um agendamento para um usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {"type": "string", "description": "O ID do usuário que está agendando."},
                "service": {"type": "string", "description": "O serviço a ser agendado."},
                "professional": {"type": "string", "description": "O nome do profissional."},
                "datetime_str": {"type": "string", "description": "A data e hora do agendamento no formato ISO, ex: '2025-08-20T10:00:00'."}
            },
            "required": ["userId", "service", "professional", "datetime_str"]
        }
    }
]

app = FastAPI()

# Modelo de dados para a requisição (o que o frontend envia)
class ChatMessage(BaseModel):
    userId: str
    message: str

# Modelo de dados para a resposta (o que o backend devolve)
class ChatResponse(BaseModel):
    reply: str

@app.get("/")
def read_root():
    return {"Status": "Agente de Salão AI Backend Ativo"}

@app.get("/api/v1/debug/env")
async def debug_env():
    s_url = os.environ.get("SUPABASE_URL")
    s_key = os.environ.get("SUPABASE_KEY")
    g_key = os.environ.get("GEMINI_API_KEY")

    # Para segurança, nunca retornamos a chave completa.
    # Vamos retornar informações sobre ela para podermos validar.
    key_info = {
        "is_present": s_key is not None,
        "length": len(s_key) if s_key else 0,
        "start": s_key[:5] if s_key else None, # Primeiros 5 caracteres
        "end": s_key[-5:] if s_key else None,   # Últimos 5 caracteres
    }

    return {
        "message": "Valores das variáveis de ambiente lidos pelo script Python.",
        "supabase_url": s_url,
        "supabase_key_info": key_info,
        "gemini_key_is_present": g_key is not None
    }

@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def handle_chat_message(body: ChatMessage):
    try:
        user_message = body.message.strip().lower()

        # 1. (Otimização de Custo) Cache First - VERSÃO CORRIGIDA
        # REMOVEMOS o .single() para obter uma lista de resultados
        cache_response = await supabase.from_("faqs").select("answer").eq("question", user_message).execute()
        
        # VERIFICAMOS se a lista de dados não está vazia
        if cache_response.data:
            print("CACHE HIT!")
            # Se houver dados, pegamos a resposta do PRIMEIRO item da lista
            return {"reply": cache_response.data[0]['answer']}

        print("CACHE MISS. Acionando fluxo de IA...")

        # 2. Chamada à IA com ferramentas (código continua o mesmo)
        response = await model.generate_content_async(
            user_message,
            tools=tools_definition
        )
        
        # ... (resto da sua lógica de function calling) ...

        # Se a resposta não tiver function_call, retorne o texto
        return {"reply": response.text}

    except Exception as e:
        # Dica de depuração: Use repr(e) para obter uma mensagem de erro mais detalhada
        print(f"ERRO CRÍTICO NA FUNÇÃO: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno no servidor: {repr(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)