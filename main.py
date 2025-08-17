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

@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def handle_chat_message(body: ChatMessage):
    try:
        user_message = body.message.strip().lower()

        # 1. Cache First
        try:
            cache_response = await supabase.from_("faqs").select("answer").eq("question", user_message).single().execute()
            if cache_response.data:
                print("CACHE HIT!")
                return {"reply": cache_response.data['answer']}
        except Exception:
            pass
        
        print("CACHE MISS. Acionando fluxo de IA...")

        # 2. Chamada à IA com ferramentas
        response = await model.generate_content_async(user_message, tools=tools_definition)

        if not response.candidates:
            raise ValueError("A resposta da IA não contém candidatos válidos.")
        
        response_part = response.candidates[0].content.parts[0]

        # ### INÍCIO DA SEÇÃO MODIFICADA ###

        # Verificamos se a IA pediu para chamar uma função
        if response_part.function_call:
            function_call = response_part.function_call
            tool_name = function_call.name
            tool_args = dict(function_call.args)

            if tool_name in AVAILABLE_TOOLS:
                # Pega a função do nosso dicionário de ferramentas
                tool_function = AVAILABLE_TOOLS[tool_name]
                
                # Adiciona o userId nos argumentos se for a ferramenta de criação de agendamento
                if 'userId' in tool_function.__code__.co_varnames:
                    tool_args['userId'] = body.userId

                # AQUI ESTÁ A LÓGICA CHAVE:
                # Verificamos se a função é 'async' (uma coroutine).
                if inspect.iscoroutinefunction(tool_function):
                    # Se for async, chamamos com 'await'
                    tool_result = await tool_function(**tool_args)
                else:
                    # Se for uma função normal, chamamos diretamente
                    tool_result = tool_function(**tool_args)

                # Enviamos o resultado da ferramenta de volta para a IA para que ela possa formular uma resposta final
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
                # Caso a IA chame uma função que não existe em nosso AVAILABLE_TOOLS
                return {"reply": "Desculpe, ocorreu um erro ao tentar executar uma ação."}
        else:
            # A IA respondeu diretamente sem usar ferramentas
            return {"reply": response.text}
            
        # ### FIM DA SEÇÃO MODIFICADA ###

    except Exception as e:
        print(f"ERRO CRÍTICO NA FUNÇÃO: {e}")
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno no servidor: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)