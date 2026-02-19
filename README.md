# Baby Nutrition AI

WhatsApp-first AI system for age-appropriate baby meal planning and bedtime stories. Follows WHO and Indian Academy of Pediatrics complementary feeding guidelines.

## Features

- **Commands**: `START`, `PROFILE`, `UPDATE`, `TODAY`, `MONTH`, `STORY`
- **4 meals per day** - age-appropriate textures, quantities in spoons
- **Rule engine** - overrides AI output for safety (no salt/sugar before 12m, etc.)
- **Bedtime stories** - 60–90 second, Indian context
- **Config-driven** - food rules in YAML, no hardcoded items
- **Stateless APIs** - idempotent message sending

## Local Development

### Option A: Docker (easiest)

Requires [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

```bash
# Clone and enter project
cd baby-nutrition-ai

# Copy env template and add your keys
cp .env.example .env
# Edit .env with LLM_API_KEY, WHATSAPP_* values

# Run
docker compose up --build
```

- API: http://localhost:8000
- Data persists in `./data` on your machine
- Use `docker compose up -d` to run in background

Without Compose:
```bash
docker build -t baby-nutrition-ai .
docker run -p 8000:8000 -v $(pwd)/data:/app/data --env-file .env baby-nutrition-ai
```

### Option B: Python

#### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) or pip

#### Setup

```bash
# Clone and enter project
cd baby-nutrition-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Or with uv:
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Environment Variables

Create `.env` in the project root:

```env
# LLM (OpenAI or compatible API like LiteLLM)
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
# Optional: custom base URL for OpenAI-compatible APIs
# LLM_BASE_URL=https://your-llm-proxy/v1

# WhatsApp Business API (Meta)
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
WHATSAPP_PHONE_ID=your_phone_number_id

# Data directory (default: ./data)
DATA_DIR=./data
```

### Run Server

```bash
uvicorn baby_nutrition_ai.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### WhatsApp Webhook

For detailed token and setup steps, see **[docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md)**.

1. **Expose locally** (for testing): use [ngrok](https://ngrok.com/) or similar
   ```bash
   ngrok http 8000
   ```

2. **Configure Meta App**:
   - Webhook URL: `https://your-ngrok-url/webhook`
   - Verify token: same as `WHATSAPP_VERIFY_TOKEN`
   - Subscribe to `messages` field

3. **Test**: Send `START` from your WhatsApp number

### Updating Profile

After START creates a default profile, send **UPDATE** to edit it. You'll get a menu (1-8) to update:
- Date of birth, feeding type, preferences, allergies, foods introduced, location, weight, height

Reply with the number, enter the value when prompted. Send **0** when done, or **CANCEL** to exit without saving.

### Project Structure

```
src/baby_nutrition_ai/
├── main.py           # FastAPI app
├── config.py         # Settings, food rules
├── models/           # BabyProfile, MealPlan, Story
├── persistence/      # ProfileStore (JSON)
├── rules/            # RuleEngine (age, texture, safety)
├── llm/              # OpenAI-compatible client
├── services/         # MealPlan, Story, Profile, AI
├── whatsapp/         # Webhook, Sender
└── media/            # Image/PDF stubs

config/
└── food_rules.yaml   # WHO/IAP rules - edit here
```

### Testing Without WhatsApp

Use the API docs at `/docs` or curl:

```bash
# Health check
curl http://localhost:8000/health

# Simulate webhook (requires valid payload structure)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"field":"messages","value":{"metadata":{},"messages":[{"from":"1234567890","id":"wamid.xxx","type":"text","text":{"body":"TODAY"}}]}}]}]}'
```

## Safety

- No salt/sugar/honey before 12 months
- No whole nuts for young children
- Disclaimer: *"This is a guidance tool. Consult your pediatrician for medical concerns."*
- No medical advice - nutrition guidance only

## License

MIT
