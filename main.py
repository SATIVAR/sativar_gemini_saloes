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

load_dotenv()

# Configure o cliente Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="Você é um assistente de salão de beleza. Seja amigável e direto. Sua função é responder perguntas e agendar serviços. Use as ferramentas disponíveis quando necessário para verificar horários ou criar agendamentos."
)

# --- Definição das ferramentas para o modelo entender ---
# Isto é o que o Gemini usa para saber quais funções chamar
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

# Substitua o endpoint `handle_chat_message` por esta versão completa
@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def handle_chat_message(body: ChatMessage):
    user_message = body.message.strip().lower()

    # 1. Cache First (código anterior)
    try:
        cache_response = await supabase.from_("faqs").select("answer").eq("question", user_message).single().execute()
        if cache_response.data:
            print("CACHE HIT!")
            return {"reply": cache_response.data['answer']}
    except Exception:
        pass
    
    print("CACHE MISS. Acionando fluxo de IA...")

    # 2. Chamada à IA com ferramentas
    # Primeira chamada para a IA: ela pode responder diretamente ou pedir para usar uma ferramenta
    response = await model.generate_content_async(
        user_message,
        tools=tools_definition
    )
    
    response_part = response.candidates[0].content.parts[0]

    if response_part.function_call:
        # A IA instruiu o uso de uma ferramenta
        function_call = response_part.function_call
        tool_name = function_call.name
        tool_args = dict(function_call.args)

        if tool_name in AVAILABLE_TOOLS:
            # Executa a função localmente
            tool_function = AVAILABLE_TOOLS[tool_name]
            # Adiciona o userId nos argumentos se for a ferramenta de criação
            if 'userId' in tool_function.__code__.co_varnames:
                tool_args['userId'] = body.userId

            tool_result = tool_function(**tool_args)

            # Segunda chamada para a IA: envia o resultado da ferramenta para que a IA formule a resposta final
            final_response = await model.generate_content_async(
                [
                    user_message, # Mensagem original do usuário
                    response.candidates[0].content, # Resposta anterior do modelo com a chamada de função
                    {"role": "user", "parts": [{"function_response": {"name": tool_name, "response": {"content": tool_result}}}]}
                ],
                tools=tools_definition
            )
            return {"reply": final_response.text}
        else:
            return {"reply": "Desculpe, ocorreu um erro ao tentar executar uma ação."}
    else:
        # A IA respondeu diretamente sem usar ferramentas
        return {"reply": response.text}