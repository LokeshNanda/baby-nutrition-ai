# WhatsApp Business API Setup Guide

Step-by-step instructions to get your access token and configure WhatsApp for Baby Nutrition AI.

---

## Prerequisites

- Meta (Facebook) account
- Business details (for production) or use Meta's test environment

---

## 1. Create a Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Click **Get Started** (or log in)
3. Complete developer registration:
   - Accept Meta for Developers terms
   - Verify your identity if prompted

---

## 2. Create an App

1. In the [Meta for Developers dashboard](https://developers.facebook.com/apps), click **Create App**
2. Select **Other** as the app type
3. Choose **Business** as the use case
4. Enter your app name (e.g. "Baby Nutrition AI") and contact email
5. Click **Create App**

---

## 3. Add WhatsApp Product

1. Open your app in the dashboard
2. In the left sidebar, find **Products** → **Add Product**
3. Locate **WhatsApp** and click **Set Up**

---

## 4. Get Your Credentials

### 4a. Access Token (Temporary – for testing)

1. Go to **WhatsApp** → **API Setup** in your app
2. Under **Temporary access token**, click **Generate**
3. Copy the token – this expires in **24 hours** and is for development only

### 4b. Access Token (Permanent – for production)

1. Go to **Business Settings** (business.facebook.com)
2. Under **Users** → **System Users**, create a System User (or use existing)
3. Click **Generate new token**
4. Select your app
5. Enable scopes: `whatsapp_business_management`, `whatsapp_business_messaging`
6. Copy the token – store it securely; it does not expire but can be revoked

### 4c. Phone Number ID

1. In **WhatsApp** → **API Setup**
2. Find **From** (test phone number)
3. Copy the **Phone number ID** – this is `WHATSAPP_PHONE_ID`

> For testing, Meta provides a sandbox phone number. For production, you add your own number via WhatsApp Business Account.

---

## 5. Set Up Webhook

### 5a. Create a Verify Token

1. Choose a random string (e.g. `my-secret-verify-token-12345`)
2. This becomes `WHATSAPP_VERIFY_TOKEN` in your `.env`
3. Keep it secret – Meta will send it when verifying your webhook

### 5b. Expose Your Server

For local development, use a tunnel:

```bash
# Using ngrok
ngrok http 8000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok.io`).

### 5c. Configure Webhook in Meta

1. Go to **WhatsApp** → **Configuration** in your app
2. Under **Webhook**, click **Edit**
3. Enter:
   - **Callback URL**: `https://your-ngrok-url.ngrok.io/webhook`
   - **Verify token**: your `WHATSAPP_VERIFY_TOKEN`
4. Click **Verify and Save**

Meta will send a GET request to your URL. Your server must respond with the `hub.challenge` value.

### 5d. Subscribe to Webhook Fields

1. Still under **Webhook**, click **Manage**
2. Subscribe to **messages**
3. Optionally subscribe to **message_template_status_update** for delivery receipts

---

## 6. Optional: Webhook signature verification

To block spoofed webhook requests, add your App Secret:

1. Meta App Dashboard → **Settings** → **Basic** → **App Secret** (click Show)
2. Add to `.env`: `WHATSAPP_APP_SECRET=your_app_secret`
3. Redeploy

With this set, only requests signed by Meta are accepted. Recommended for production.

## 7. Environment Variables

Add to your `.env`:

```env
# From API Setup
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_ID=your_phone_number_id_here

# Your chosen verify token (same as in Meta webhook config)
WHATSAPP_VERIFY_TOKEN=my-secret-verify-token-12345
```

---

## 8. Test the Connection

1. Start your server: `uvicorn baby_nutrition_ai.main:app --port 8000`
2. Ensure ngrok is running and pointing to port 8000
3. Send a message to the **sandbox test number** from the WhatsApp API Setup page
4. Add your phone number as a test user:
   - **WhatsApp** → **API Setup** → **To** → **Manage phone number list**
   - Add your number with the code received via WhatsApp

5. Send `START` to the test number – you should receive a reply

---

## 9. Production: Add Your Own Number

1. Complete [Meta Business Verification](https://developers.facebook.com/docs/whatsapp/embedded-signup) if required
2. Create or connect a **WhatsApp Business Account**
3. Add your business phone number (requires verification via SMS/call)
4. Use the new **Phone number ID** for production

---

## Quick Reference

| Variable | Where to find |
|----------|---------------|
| `WHATSAPP_ACCESS_TOKEN` | API Setup → Temporary/Permanent token |
| `WHATSAPP_PHONE_ID` | API Setup → From → Phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | You create it; same value in Meta webhook config |

---

## Troubleshooting

- **Webhook verification fails**: Ensure `WHATSAPP_VERIFY_TOKEN` matches exactly in `.env` and Meta
- **No reply received**: Check server logs, ngrok is running, and your number is in the test list
- **Token expired**: Regenerate temporary token or use permanent System User token
- **403 on send**: Verify token has `whatsapp_business_messaging` scope

---

## Links

- [WhatsApp Cloud API docs](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Webhooks reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Access tokens guide](https://developers.facebook.com/docs/whatsapp/access-tokens)
