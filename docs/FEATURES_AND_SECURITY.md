# Features & Security

## Security: Open API and Webhook Protection

### Is an open webhook URL a problem?

Yes. Without protection, anyone who discovers your webhook URL can:

- **POST fake messages** – Trigger LLM calls (incurring cost) and send WhatsApp messages to arbitrary numbers
- **Spam your service** – Cause rate limits, exhaust resources
- **Inject malicious payloads** – Though our handlers validate structure, it’s still an attack surface

### Why not add API key / Bearer auth?

Meta’s servers do **not** send any authentication headers when calling your webhook. They only POST the payload. If you require an API key or Bearer token, Meta’s requests would fail with 401/403, and WhatsApp integration would break.

### Recommended: Webhook signature verification

Meta signs every webhook request with `X-Hub-Signature-256`. You can verify this signature using your **App Secret** (from Meta App Dashboard → Settings → Basic).

**Implemented:** When `WHATSAPP_APP_SECRET` is set, the app verifies the signature on every POST to `/webhook`. Invalid or missing signatures are rejected with 403. This blocks spoofed requests without affecting Meta’s normal flow.

**Setup:** Add `WHATSAPP_APP_SECRET` to your environment (Railway, .env, etc.). Get it from [developers.facebook.com](https://developers.facebook.com) → Your App → Settings → Basic → App Secret.

### Other measures

- **`/health`** – Safe to leave public (needed for load balancers)
- **Rate limiting** – Optional; add with slowapi or similar to cap requests per IP
- **No auth on webhook** – Required for Meta; use signature verification instead

---

## New Feature Ideas

### High impact, moderate effort

| Feature | Description | Effort |
|--------|-------------|--------|
| **Monthly PDF** | Generate and send monthly meal plan PDF (stub exists) | Medium |
| **Meal plan image** | Send meal plan as PNG image (stub exists) | Medium |
| **Shopping list** | “Shopping list for this week” → summarize ingredients from meal plans | Low |
| **Recipe how-to** | “How do I make that dal?” → short recipe from meal + tips | Low |
| **Rate limiting** | Limit requests per phone/IP to prevent abuse | Low |

### High impact, higher effort

| Feature | Description | Effort |
|---------|-------------|--------|
| **Multi-baby support** | Multiple profiles per user, “switch to Ravi” | Medium |
| **Regional languages** | Hindi, Tamil, etc. for prompts and responses | Medium |
| **Weekly summary** | “What did we feed this week?” (needs meal logging) | Medium |
| **Audio stories** | Text-to-speech bedtime stories | High |
| **Pediatric dashboard** | Web UI for pediatricians / admins | High |

### Quick wins

| Feature | Description | Effort |
|---------|-------------|--------|
| **Reminder flow** | “Remind me to introduce egg next week” (cron + simple scheduler) | Low |
| **Usage logging** | Log token usage for cost tracking | Low |
| **Better error messages** | Friendlier copy when profile missing, LLM fails | Low |
| **HELP command** | Short help for commands and conversational examples | Low |

### From ROADMAP

- Phase 2: Monthly PDF, image-based meal chart
- Phase 3: Regional languages, audio stories, pediatric dashboard

---

## Implementation order suggestion

1. **Security** – Set `WHATSAPP_APP_SECRET` and ensure signature verification is active
2. **Rate limiting** – Add per-phone or per-IP limits
3. **HELP command** – Improve discoverability
4. **Shopping list / Recipe** – Extend conversational tools
5. **Monthly PDF** – Implement the existing stub
6. **Multi-baby** – If you expect multiple children per user
