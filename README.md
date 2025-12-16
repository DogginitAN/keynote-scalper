# 🎙️ Keynote Scalper

Real-time speech-to-trade system for Kalshi "What will X say?" prediction markets.

## Features

- **Live Trigger Detection**: Matches spoken words to Kalshi contracts
- **Two-Derivative System**: 
  - 1st Degree: Direct contract words (e.g., "Bitcoin")
  - 2nd Degree: What speaker actually says (e.g., "Solana" → Bitcoin contract)
- **Negation Handling**: Skips triggers with "not", "don't", etc.
- **Market Monitoring**: Real-time price tracking
- **Trade Interface**: Manual trade execution

## Setup

1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `streamlit run app.py`

## Configuration

Set these environment variables or enter in the app:

- `DEEPGRAM_API_KEY`: For live audio transcription (optional)
- `TRIGGER_MAP_JSON`: Custom trigger mappings (optional)

## Usage

1. **Manual Mode**: Paste transcript text and click "Process"
2. **Live Mode**: Enter Deepgram API key for real-time audio capture

When a trigger is detected, the app will:
1. Flash an alert
2. Mark the contract as triggered
3. Log the detection for trade execution

## Trigger Map Structure

```json
{
    "bitcoin": {
        "contract": "Bitcoin",
        "ticker": "KXVLADTENEVMENTION-25DEC17-BITC",
        "degree": 1
    },
    "solana": {
        "contract": "Bitcoin",
        "ticker": "KXVLADTENEVMENTION-25DEC17-BITC",
        "degree": 2
    }
}
```

## Architecture

```
[Audio Input] → [Deepgram STT] → [Trigger Matcher] → [Trade Alert]
                                         ↓
                              [Negation Detection]
                                         ↓
                              [Contract Mapping]
```

## License

MIT
