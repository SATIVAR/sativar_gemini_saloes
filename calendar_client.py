import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_calendar_service():
    """
    Autentica com a API do Google Calendar usando as credenciais da variável de ambiente
    e retorna um objeto de serviço para interagir com a API.
    """
    try:
        # Pega o JSON da variável de ambiente
        creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json_str:
            raise ValueError("A variável de ambiente GOOGLE_CREDS_JSON não foi encontrada.")
            
        creds_info = json.loads(creds_json_str)
        
        # Define os escopos (permissões) que solicitamos
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=creds)
        
        return service
    except Exception as e:
        print(f"Erro ao inicializar o serviço do Google Calendar: {e}")
        return None