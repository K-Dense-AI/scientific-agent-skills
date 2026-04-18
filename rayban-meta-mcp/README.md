# Ray-Ban Meta MCP Server

Connect your Ray-Ban Meta smart glasses to any LLM (Claude, GPT-4, Gemini) via WhatsApp, with full MCP integration for Claude Code.

## Architecture

```
Ray-Ban Meta Glasses
    │ (voice / photo via WhatsApp)
    ▼
WhatsApp Cloud API → FastAPI Webhook
    │
    ├─ Audio → Whisper transcription → text
    ├─ Image → Vision LLM analysis
    └─ Text  → Intent classification → Tool dispatch
                    │
                    ├─ Web Search (Serper)
                    ├─ Calendar (Google)
                    ├─ Notes (save to folders)
                    ├─ Knowledge Base (FTS5 RAG)
                    └─ Conversation (multi-LLM)
    │
    ▼
Claude Code ←→ MCP Server (same process, /mcp)
```

## Features

- **Multi-provider LLM**: Claude 4.6, GPT-4o, Gemini 2.0 Flash (configurable)
- **Voice commands**: Whisper/Groq/Deepgram transcription
- **Vision analysis**: Photo analysis via any multimodal LLM
- **Smart tools**: Web search, calendar, notes with folder organization
- **RAG learning**: Tracks your activity patterns for faster, personalized responses
- **Folder-based knowledge**: "Save this to work/meetings" organizes notes by voice
- **MCP integration**: Full Claude Code access to glasses tools and data
- **Auto-chunking**: Messages split to 15 words for glasses display

## Quick Start

```bash
# 1. Install
cd rayban-meta-mcp
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Run
uvicorn rayban_meta.main:app --port 8080

# 4. Expose for WhatsApp webhook (dev)
ngrok http 8080
```

## MCP Integration

Add to your Claude Code config (`~/.claude.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "rayban-meta": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `send_message_to_glasses` | Send text to glasses via WhatsApp |
| `get_recent_messages` | Get conversation history |
| `get_recent_photos` | List photos from glasses camera |
| `analyze_photo` | Analyze a photo with vision LLM |
| `get_conversation_summary` | AI summary of recent interactions |
| `search_knowledge_base` | Search saved notes/knowledge |
| `add_to_knowledge_base` | Add info to knowledge base |
| `list_knowledge_folders` | List all note folders |
| `get_activity_patterns` | View usage patterns |
| `get_glasses_status` | Connection and config status |

## Voice Commands (from glasses)

- **"Search for..."** → web search
- **"Remind me tomorrow at 3pm..."** → calendar event
- **"Save this to work/meetings: ..."** → save to folder
- **"What did I save about...?"** → search knowledge base
- **[Take photo]** → automatic vision analysis

## Docker

```bash
docker compose up -d
```

## Setup WhatsApp

See [scripts/setup_meta_app.md](scripts/setup_meta_app.md) for the full Meta for Developers setup guide.
