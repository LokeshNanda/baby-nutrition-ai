# Deployment Guide

How to host Baby Nutrition AI on free cloud platforms. For production use, you need persistent storage (Redis) because most free tiers have ephemeral filesystems.

---

## Prerequisites

- GitHub account (for deployment)
- [Upstash](https://upstash.com) account (free Redis)
- Meta WhatsApp Business API configured ([docs/WHATSAPP_SETUP.md](WHATSAPP_SETUP.md))
- OpenAI or compatible LLM API key

---

## 1. Create Upstash Redis (free)

1. Go to [console.upstash.com](https://console.upstash.com)
2. Create a Redis database (choose a region near your users)
3. Copy the **Redis URL** (starts with `rediss://`)

---

## 2. Option A: Railway

Railway offers $5 free credit per month. No sleep; simple deployment.

### Deploy

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. **New Project** → **Deploy from GitHub repo** → select `baby-nutrition-ai`
3. Railway detects the Dockerfile and builds automatically
4. Add variables (Settings → Variables):

| Variable | Value |
|----------|-------|
| `LLM_API_KEY` | Your OpenAI API key |
| `LLM_MODEL` | gpt-4o-mini |
| `WHATSAPP_VERIFY_TOKEN` | Your webhook verify token |
| `WHATSAPP_ACCESS_TOKEN` | Meta access token |
| `WHATSAPP_PHONE_ID` | Phone number ID |
| `REDIS_URL` | Your Upstash Redis URL |

5. Deploy. Railway provides a URL like `https://baby-nutrition-ai-production.up.railway.app`
6. Set WhatsApp webhook to `https://your-app.up.railway.app/webhook`

---

## 3. Option B: Render

Render free tier sleeps after 15 minutes of inactivity. Use UptimeRobot to keep it awake (within 750 hrs/month).

### Deploy

1. Go to [render.com](https://render.com) and sign in with GitHub
2. **New** → **Web Service** → connect your repo
3. Settings:
   - **Build Command**: (leave empty; uses Dockerfile)
   - **Start Command**: (leave empty)
   - **Instance Type**: Free
4. **Environment** → Add variables (same as Railway table above, including `REDIS_URL`)
5. Create Web Service
6. Copy the URL (e.g. `https://baby-nutrition-ai.onrender.com`)

### Keep free tier awake (optional)

1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor: HTTP(s), URL `https://your-app.onrender.com/health`, interval 5 minutes
3. Prevents spin-down (uses ~720 of 750 free hours/month)

---

## 4. Option C: Fly.io

Fly.io offers 3 shared VMs free. Supports persistent volumes if you skip Redis, but Redis is simpler.

### Setup

1. Install [flyctl](https://fly.io/docs/hacks/install-flyctl/)
2. `fly auth login`
3. From project root: `fly launch` (accept defaults or customize)
4. Add secrets:

```bash
fly secrets set LLM_API_KEY=sk-xxx
fly secrets set WHATSAPP_VERIFY_TOKEN=xxx
fly secrets set WHATSAPP_ACCESS_TOKEN=xxx
fly secrets set WHATSAPP_PHONE_ID=xxx
fly secrets set REDIS_URL=rediss://xxx
```

5. Deploy: `fly deploy`
6. Webhook URL: `https://your-app.fly.dev/webhook`

---

## 5. Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | OpenAI or compatible API key |
| `LLM_MODEL` | No | Default: gpt-4o-mini |
| `LLM_BASE_URL` | No | Custom API base (e.g. LiteLLM) |
| `WHATSAPP_VERIFY_TOKEN` | Yes | Webhook verification token |
| `WHATSAPP_ACCESS_TOKEN` | Yes | Meta WhatsApp API token |
| `WHATSAPP_PHONE_ID` | Yes | WhatsApp Business phone number ID |
| `REDIS_URL` | For cloud | Upstash Redis URL for persistent storage |
| `DATA_DIR` | No | Local file storage path (default: ./data) |
| `PORT` | No | Server port (default: 8000) |

**Important:** Without `REDIS_URL`, data is stored in local files. On Render/Railway free tiers, the filesystem is ephemeral, so profiles and conversations are lost on restart. Always set `REDIS_URL` for cloud deployments.

---

## 6. Platform Comparison

| Platform | Free Tier | Sleep | Persistent Storage | Best For |
|----------|-----------|-------|--------------------|----------|
| Railway | $5 credit/mo | No | Via Redis | Demos, small prod |
| Render | 750 hrs/mo | 15 min idle | Via Redis | Demos with UptimeRobot |
| Fly.io | 3 VMs | No | Volumes or Redis | Production, global |

---

## 7. Troubleshooting

- **Webhook verification fails**: Ensure `WHATSAPP_VERIFY_TOKEN` matches exactly in Meta and your env
- **No reply on WhatsApp**: Check logs; verify `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_ID`
- **Data lost after deploy**: Set `REDIS_URL`; file storage is ephemeral on cloud
- **Render sleeps**: Use UptimeRobot to ping `/health` every 5 min
