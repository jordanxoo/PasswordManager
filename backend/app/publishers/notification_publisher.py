import logging                                                                           
from datetime import datetime                                                            
from app.rabbitmq_client import publish_event                                            

logger = logging.getLogger(__name__)                                                     
                
                                                                                        
async def publish_email(to: str, subject: str, body: str):
    message = {
        "to": to,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat()
    }                                                                                    
    await publish_event("notify.email", message)
                                                                                        
                
async def publish_account_locked_email(email: str, ip: str):
    await publish_email(
        to=email,
        subject="Twoje konto zostało zablokowane",                                       
        body=f"Wykryto 10 nieudanych prób logowania z IP: {ip}. Konto zablokowane na 15 minut."                                                                                  
    )           
                                                                                        
                
async def publish_suspicious_login_email(email: str, ip: str):
    await publish_email(
        to=email,
        subject="Logowanie z nowego urządzenia",
        body=f"Wykryto logowanie z nowego adresu IP: {ip}. Jeśli to nie byłeś Ty, zmień hasło."                                                                                  
    )                     