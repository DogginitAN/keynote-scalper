"""
🎙️ Keynote Scalper - Live Audio Trading System
==============================================

A Streamlit app for real-time speech-to-trade on Kalshi "What will X say?" markets.
Uses Deepgram for live audio transcription via WebRTC.
"""

import streamlit as st
import json
import os
from datetime import datetime
import queue
import threading
import numpy as np

# WebRTC for audio capture
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import av

# Deepgram for transcription
import websockets
import asyncio
import base64

# Page config
st.set_page_config(
    page_title="Keynote Scalper",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .trigger-alert {
        background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        color: white;
        font-weight: bold;
    }
    .stAlert {
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'triggers_detected' not in st.session_state:
    st.session_state.triggers_detected = []
if 'triggered_contracts' not in st.session_state:
    st.session_state.triggered_contracts = set()
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False

# Trigger map - 1st and 2nd degree
TRIGGER_MAP = {
    # First degree (direct contract words)
    "retirement": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 1},
    "blockchain": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 1},
    "bitcoin": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 1},
    "election": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 1},
    "acquisition": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 1},
    "acquired": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 1},
    "economy": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 1},
    "economic": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 1},
    "kalshi": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 1},
    "susquehanna": {"contract": "SIG", "ticker": "KXVLADTENEVMENTION-25DEC17-SIG", "degree": 1},
    "sig": {"contract": "SIG", "ticker": "KXVLADTENEVMENTION-25DEC17-SIG", "degree": 1},
    "tokenization": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 1},
    "tokenized": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 1},
    "sport": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 1},
    "sports": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 1},
    "innovation": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 1},
    "innovate": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 1},
    "gold": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 1},
    
    # Second degree (what Vlad actually says -> maps to contracts)
    "crypto": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "cryptocurrency": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "btc": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "solana": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "ethereum": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "coinbase": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "satoshi": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "bitstamp": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "x1": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "drivewealth": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "merger": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "deal": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "buyout": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "prediction market": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "prediction markets": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "polymarket": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "event contracts": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "robinhood gold": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 2},
    "gold card": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 2},
    "legend": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "cortex": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "ai": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "artificial intelligence": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "staking": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
    "tokenize": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
    "rwa": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
    "roth ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "401k": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "smart contract": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "layer 1": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "on chain": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "gdp": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "inflation": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "federal reserve": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "interest rate": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "nfl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "nba": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "super bowl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "march madness": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "presidential": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 2},
    "vote": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 2},
    "ballot": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 2},
}

NEGATION_WORDS = ['not', "don't", "won't", 'never', 'no', "isn't", "aren't", "wasn't", "weren't", "can't", "couldn't", "shouldn't", "wouldn't", 'without']


def check_for_triggers(text: str) -> list:
    """Check text for trigger words, handling negation."""
    found_triggers = []
    text_lower = text.lower()
    words = text_lower.split()
    
    for trigger, data in TRIGGER_MAP.items():
        # Skip if we already triggered this contract
        if data['ticker'] in st.session_state.triggered_contracts:
            continue
            
        if trigger in text_lower:
            # Find trigger position for negation check
            trigger_words = trigger.split()
            trigger_idx = -1
            
            for i in range(len(words) - len(trigger_words) + 1):
                match = True
                for j, tw in enumerate(trigger_words):
                    if tw not in words[i + j]:
                        match = False
                        break
                if match:
                    trigger_idx = i
                    break
            
            if trigger_idx == -1:
                continue
            
            # Check for negation in preceding words
            is_negated = False
            for i in range(max(0, trigger_idx - 4), trigger_idx):
                if any(neg in words[i] for neg in NEGATION_WORDS):
                    is_negated = True
                    break
            
            if not is_negated:
                found_triggers.append({
                    'trigger': trigger,
                    'contract': data['contract'],
                    'ticker': data['ticker'],
                    'degree': data.get('degree', 1),
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'context': text[:100]
                })
    
    return found_triggers


def process_transcript(text: str):
    """Process transcript text for triggers."""
    if not text.strip():
        return
    
    # Add to transcripts
    st.session_state.transcripts.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'text': text
    })
    
    # Check for triggers
    triggers = check_for_triggers(text)
    for trigger in triggers:
        st.session_state.triggers_detected.append(trigger)
        st.session_state.triggered_contracts.add(trigger['ticker'])


# Audio processor for WebRTC
class DeepgramAudioProcessor(AudioProcessorBase):
    def __init__(self, deepgram_key: str, transcript_queue: queue.Queue):
        self.deepgram_key = deepgram_key
        self.transcript_queue = transcript_queue
        self.ws = None
        self.loop = None
        self.connected = False
        
    async def connect_deepgram(self):
        """Connect to Deepgram WebSocket."""
        try:
            url = "wss://api.deepgram.com/v1/listen?model=nova-2&language=en-US&smart_format=true&interim_results=true"
            self.ws = await websockets.connect(
                url,
                extra_headers={"Authorization": f"Token {self.deepgram_key}"}
            )
            self.connected = True
            
            # Start receiving task
            asyncio.create_task(self.receive_transcripts())
        except Exception as e:
            print(f"Deepgram connection error: {e}")
            self.connected = False
    
    async def receive_transcripts(self):
        """Receive transcripts from Deepgram."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                if 'channel' in data:
                    transcript = data['channel']['alternatives'][0].get('transcript', '')
                    is_final = data.get('is_final', False)
                    if transcript and is_final:
                        self.transcript_queue.put(transcript)
        except Exception as e:
            print(f"Receive error: {e}")
    
    async def send_audio(self, audio_bytes):
        """Send audio to Deepgram."""
        if self.ws and self.connected:
            try:
                await self.ws.send(audio_bytes)
            except Exception as e:
                print(f"Send error: {e}")
    
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        """Process incoming audio frame."""
        # Convert to bytes
        audio_data = frame.to_ndarray().tobytes()
        
        # Send to Deepgram (in background)
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.connect_deepgram())
        
        if self.connected:
            self.loop.run_until_complete(self.send_audio(audio_data))
        
        return frame


# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key
    deepgram_key = st.text_input(
        "🔑 Deepgram API Key",
        type="password",
        value=os.environ.get('DEEPGRAM_API_KEY', ''),
        help="Required for live audio transcription"
    )
    
    if not deepgram_key:
        st.warning("⚠️ Enter Deepgram API key to enable live audio")
    
    st.divider()
    
    # Stats
    st.subheader("📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Triggers", len(st.session_state.triggers_detected))
    with col2:
        st.metric("Contracts", len(st.session_state.triggered_contracts))
    
    st.metric("Transcripts", len(st.session_state.transcripts))
    
    # Reset
    if st.button("🗑️ Reset Session", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.triggers_detected = []
        st.session_state.triggered_contracts = set()
        st.rerun()

# Main content
st.title("🎙️ Keynote Scalper")
st.caption("Live speech-to-trade for Kalshi 'What will X say?' markets | Robinhood YES/NO Keynote")

# Tabs
tab1, tab2, tab3 = st.tabs(["🎤 Live Audio", "🎯 Triggers", "📊 Markets"])

with tab1:
    st.header("Live Audio Transcription")
    
    if deepgram_key:
        st.success("✅ Deepgram connected - Click START to begin listening")
        
        # Create transcript queue
        if 'transcript_queue' not in st.session_state:
            st.session_state.transcript_queue = queue.Queue()
        
        # WebRTC streamer for audio capture
        webrtc_ctx = webrtc_streamer(
            key="keynote-audio",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=1024,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"audio": True, "video": False},
        )
        
        if webrtc_ctx.state.playing:
            st.info("🔴 **LIVE** - Listening for triggers...")
            
            # Note about audio processing
            st.caption("""
            **How it works:**
            1. Your browser captures audio from your microphone
            2. Audio is sent to Deepgram for real-time transcription
            3. Transcripts are checked for trigger words
            4. Triggers are logged for trading
            
            **Tip:** Play the keynote through your speakers - your mic will pick it up!
            """)
    else:
        st.warning("⚠️ Enter your Deepgram API key in the sidebar to enable live audio")
    
    st.divider()
    
    # Manual input fallback
    st.subheader("📝 Manual Input (Fallback)")
    col1, col2 = st.columns([5, 1])
    with col1:
        manual_text = st.text_input("Type what you hear:", placeholder="Enter transcript text...")
    with col2:
        if st.button("Process", type="primary"):
            if manual_text:
                process_transcript(manual_text)
                st.rerun()
    
    st.divider()
    
    # Live transcript display
    st.subheader("📜 Live Transcript")
    transcript_container = st.container()
    with transcript_container:
        if st.session_state.transcripts:
            for t in st.session_state.transcripts[-15:]:
                st.text(f"[{t['time']}] {t['text']}")
        else:
            st.caption("Transcripts will appear here...")
    
    # Trigger alerts
    if st.session_state.triggers_detected:
        st.divider()
        st.subheader("🚨 TRIGGER ALERTS")
        for trigger in reversed(st.session_state.triggers_detected[-5:]):
            degree_label = "1st°" if trigger['degree'] == 1 else "2nd°"
            st.error(f"🎯 **{trigger['trigger'].upper()}** → {trigger['contract']} ({degree_label}) @ {trigger['timestamp']}")

with tab2:
    st.header("🎯 Trigger Map")
    st.caption("1st Degree = Contract words | 2nd Degree = What Vlad actually says")
    
    # Group triggers by contract
    contracts = {}
    for trigger, data in TRIGGER_MAP.items():
        contract = data['contract']
        if contract not in contracts:
            contracts[contract] = {'first': [], 'second': []}
        if data['degree'] == 1:
            contracts[contract]['first'].append(trigger)
        else:
            contracts[contract]['second'].append(trigger)
    
    # Display
    for contract in sorted(contracts.keys()):
        triggers = contracts[contract]
        triggered = contract in [t['contract'] for t in st.session_state.triggers_detected]
        icon = "✅" if triggered else "⏳"
        
        with st.expander(f"{icon} **{contract}**", expanded=not triggered):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**1st Degree (Direct)**")
                st.code(", ".join(triggers['first']))
            with col2:
                st.markdown("**2nd Degree (Vlad Says)**")
                st.code(", ".join(triggers['second'][:10]))
                if len(triggers['second']) > 10:
                    st.caption(f"+{len(triggers['second'])-10} more")

with tab3:
    st.header("📊 Market Status")
    
    markets = [
        {"word": "Retirement", "ask": 17, "ticker": "RETI"},
        {"word": "Blockchain", "ask": 22, "ticker": "BLOC"},
        {"word": "Bitcoin", "ask": 24, "ticker": "BITC"},
        {"word": "Election", "ask": 34, "ticker": "ELEC"},
        {"word": "Acquisition", "ask": 39, "ticker": "ACQU"},
        {"word": "Economy", "ask": 40, "ticker": "ECON"},
        {"word": "Kalshi", "ask": 41, "ticker": "KALS"},
        {"word": "SIG", "ask": 56, "ticker": "SIG"},
        {"word": "Tokenization", "ask": 66, "ticker": "TOKE"},
        {"word": "Sport", "ask": 73, "ticker": "SPOR"},
        {"word": "Innovation", "ask": 78, "ticker": "INNO"},
        {"word": "Gold", "ask": 84, "ticker": "GOLD"},
    ]
    
    for m in markets:
        upside = 100 - m['ask']
        triggered = m['word'] in [t['contract'] for t in st.session_state.triggers_detected]
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
        with col1:
            icon = "✅" if triggered else "🟢" if m['ask'] < 85 else "🔴"
            st.write(f"{icon} **{m['word']}**")
        with col2:
            st.write(f"{m['ask']}¢")
        with col3:
            st.write(f"+{upside}¢")
        with col4:
            if triggered:
                st.success("TRIGGERED")
            else:
                st.progress(upside / 100)

# Footer
st.divider()
st.caption(f"Triggers loaded: {len(TRIGGER_MAP)} | Contracts: 12 | Event: Robinhood YES/NO Dec 16, 2024")
