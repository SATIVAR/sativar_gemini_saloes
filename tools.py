# tools.py
import json
from datetime import datetime

# Mock de dados para simular os profissionais
PROFESSIONALS_CALENDAR = {
    "Juliana": "juliana@seu_salao.com",
    "Fernando": "fernando@seu_salao.com"
}

# --- Ferramentas que serão expostas para a IA ---

def get_available_slots(service: str, professional: str, date_range: str):
    """
    Consulta a agenda para encontrar horários livres para um serviço, 
    com um profissional específico, em um intervalo de datas.
    """
    print(f"EXECUTANDO FERRAMENTA: get_available_slots para {professional} em {date_range}")
    # LÓGICA REAL: Aqui você implementaria a chamada à API do Google Calendar
    # para o calendar_id correspondente ao 'professional'.
    # Por enquanto, retornaremos dados fixos para teste.
    return json.dumps({
        "available_slots": [
            "2025-08-20T10:00:00",
            "2025-08-20T11:00:00",
            "2025-08-21T14:00:00"
        ]
    })

def create_appointment(userId: str, service: str, professional: str, datetime_str: str):
    """
    Agenda um novo serviço para um usuário com um profissional em uma data e hora específicas.
    """
    print(f"EXECUTANDO FERRAMENTA: create_appointment para {userId} com {professional} em {datetime_str}")
    # LÓGICA REAL:
    # 1. Chamar a API do Google Calendar para criar o evento.
    # 2. Salvar a referência do agendamento na tabela 'appointments' do Supabase.
    # Por enquanto, retornaremos uma confirmação simples.
    return json.dumps({
        "status": "success",
        "appointmentId": "appt_12345",
        "message": f"Agendamento confirmado para o serviço '{service}' com {professional} em {datetime_str}."
    })

# Mapeamento para chamar as funções pelo nome
AVAILABLE_TOOLS = {
    "get_available_slots": get_available_slots,
    "create_appointment": create_appointment,
}