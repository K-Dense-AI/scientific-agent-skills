# Meta for Developers – WhatsApp Setup Guide

## Prerequisites
- Meta Business Account (business.facebook.com)
- Ray-Ban Meta glasses paired with your phone
- WhatsApp Business API access

## Steps

### 1. Create Meta App
1. Go to **developers.facebook.com** → Create App → Business type
2. Add **WhatsApp** product to the app

### 2. Get Credentials
- **Phone Number ID**: WhatsApp → Getting Started → note it
- **Temporary Token**: Generate from the same page (expires in 24h)
- **Permanent Token**: Business Settings → System Users → Generate token with `whatsapp_business_messaging` permission

### 3. Configure Webhook
1. WhatsApp → Configuration → Callback URL:
   - **URL**: `https://your-domain.com/whatsapp/webhook` (use ngrok for dev)
   - **Verify Token**: same as `WHATSAPP_WEBHOOK_VERIFY_TOKEN` in `.env`
2. Subscribe to: **messages**

### 4. Local Development with ngrok
```bash
# Terminal 1: start the server
uvicorn rayban_meta.main:app --port 8080

# Terminal 2: expose via ngrok
ngrok http 8080
```
Copy the ngrok HTTPS URL to Meta webhook config.

### 5. Test
- Send a WhatsApp message from your phone (or glasses)
- Check server logs for incoming webhook
- Verify response comes back

### 6. Glasses Integration
- Open WhatsApp on glasses: **"Hey Meta, send a message to [bot name]"**
- The bot contact is your WhatsApp Business number
- Voice messages are transcribed automatically
- Photos are analyzed with vision AI

## .env Configuration
```
WHATSAPP_AUTH_TOKEN=your_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=my-secret-token
WHATSAPP_RECIPIENT_PHONE=your_personal_number
```
