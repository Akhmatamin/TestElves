import random

def generate_otp():
    return str(random.randint(100000, 999999))

def send_sms(phone, code):
    print(f"SMS sent to {phone}: {code}")
    # Здесь позже подключишь Megacom/Twilio/O!
