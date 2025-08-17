import json
from datetime import datetime, timedelta
from calendar_client import get_calendar_service # Importamos nosso novo cliente
from db import supabase # Importamos o cliente do Supabase

# Mapeia o nome do profissional para o ID do seu Google Calendar
# Você encontra o ID nas configurações de cada calendário do Google.
PROFESSIONALS_CALENDAR = {
    "juliana": "id_do_calendario_da_juliana@group.calendar.google.com",
    "fernando": "id_do_calendario_do_fernando@group.calendar.google.com"
}

def get_available_slots(service: str, professional: str, date_range: str):
    """
    Consulta a agenda REAL para encontrar horários livres.
    """
    print(f"EXECUTANDO FERRAMENTA REAL: get_available_slots para {professional}")
    
    service_client = get_calendar_service()
    if not service_client:
        return json.dumps({"error": "Falha ao conectar com a API do Calendário."})

    calendar_id = PROFESSIONALS_CALENDAR.get(professional.lower())
    if not calendar_id:
        return json.dumps({"error": f"Profissional '{professional}' não encontrado."})

    # Lógica simplificada de data (pode ser melhorada)
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z' # 'Z' indica UTC
    time_max = (now + timedelta(days=7)).isoformat() + 'Z' # Busca na próxima semana

    # Usamos o endpoint 'freeBusy' que é otimizado para isso
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": "America/Sao_Paulo",
        "items": [{"id": calendar_id}]
    }
    
    try:
        events_result = service_client.freebusy().query(body=body).execute()
        # A resposta nos dá os blocos OCUPADOS. Precisamos retornar uma mensagem
        # que a IA possa interpretar para sugerir horários.
        busy_slots = events_result['calendars'][calendar_id]['busy']
        
        if not busy_slots:
            return json.dumps({"message": f"A agenda de {professional} parece estar livre na próxima semana. Sugira horários comerciais (ex: 9h, 10h, etc.)."})
        
        # Para o MVP, informar a IA sobre os horários ocupados já é muito útil
        return json.dumps({
            "message": f"Aqui estão os horários já ocupados para {professional}. Use isso para sugerir horários livres.",
            "busy_slots": busy_slots
        })

    except Exception as e:
        print(f"Erro ao buscar horários: {e}")
        return json.dumps({"error": f"Não foi possível buscar os horários: {e}"})

async def create_appointment(userId: str, service: str, professional: str, datetime_str: str):
    """
    Agenda um novo serviço no Google Calendar e salva a referência no Supabase.
    Esta função precisa ser `async` para usar o `await` do Supabase.
    """
    print(f"EXECUTANDO FERRAMENTA REAL: create_appointment para {userId}")
    
    service_client = get_calendar_service()
    if not service_client:
        return json.dumps({"error": "Falha ao conectar com a API do Calendário."})
        
    calendar_id = PROFESSIONALS_CALENDAR.get(professional.lower())
    if not calendar_id:
        return json.dumps({"error": f"Profissional '{professional}' não encontrado."})

    try:
        start_time = datetime.fromisoformat(datetime_str)
        # Assumindo 1 hora de duração para qualquer serviço (pode ser melhorado)
        end_time = start_time + timedelta(hours=1)
        
        event_body = {
            'summary': f'{service} - Cliente Teste', # Usaremos um nome placeholder por enquanto
            'description': f'Serviço: {service}\nID do Usuário: {userId}',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
        }

        created_event = service_client.events().insert(calendarId=calendar_id, body=event_body).execute()
        google_event_id = created_event['id']

        # Agora, salve no Supabase
        db_response = await supabase.from_('appointments').insert({
            'user_id': userId, # Assumindo que o userId é um UUID válido
            'professional': professional,
            'service': service,
            'appointment_time': datetime_str,
            'google_calendar_event_id': google_event_id
        }).execute()
        
        if db_response.data:
            return json.dumps({
                "status": "success",
                "appointmentId": db_response.data[0]['id'],
                "message": f"Agendamento confirmado para '{service}' com {professional} em {start_time.strftime('%d/%m/%Y às %H:%M')}."
            })
        else:
             # Se o Supabase falhar, idealmente deveríamos deletar o evento do Google Calendar (lógica de rollback)
            return json.dumps({"error": "O evento foi criado no calendário, mas falhou ao salvar no nosso sistema."})
            
    except Exception as e:
        print(f"Erro ao criar agendamento: {e}")
        return json.dumps({"error": f"Não foi possível criar o agendamento: {e}"})

# Mapeamento precisa ser atualizado para refletir que create_appointment agora é async
AVAILABLE_TOOLS = {
    "get_available_slots": get_available_slots,
    "create_appointment": create_appointment,
}