"""
🎙️ Keynote Scalper - Live Audio Trading System
==============================================

A Streamlit app for real-time speech-to-trade on Kalshi "What will X say?" markets.

Features:
- Live audio transcription via Deepgram
- Trigger word detection with negation handling
- Real-time market prices from Kalshi
- Trade execution interface
"""

import streamlit as st
import json
import os
from datetime import datetime
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import numpy as np
from collections import deque
import threading
import queue
import requests

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
        animation: pulse 0.5s ease-in-out;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .market-card {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
    }
    .transcript-box {
        background: #0f0f23;
        padding: 15px;
        border-radius: 8px;
        font-family: monospace;
        max-height: 300px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'triggers_detected' not in st.session_state:
    st.session_state.triggers_detected = []
if 'trades_executed' not in st.session_state:
    st.session_state.trades_executed = []
if 'triggered_contracts' not in st.session_state:
    st.session_state.triggered_contracts = set()
if 'audio_queue' not in st.session_state:
    st.session_state.audio_queue = queue.Queue()

# Load trigger map from environment or default
def load_trigger_map():
    """Load the trigger map from environment or use defaults."""
    default_triggers = {
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
        "innovation": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 1},
        "innovate": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 1},
        "gold": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 1},
        
        # Second degree (what Vlad actually says)
        "crypto": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
        "btc": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
        "solana": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
        "ethereum": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
        "coinbase": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
        "bitstamp": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
        "x1": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
        "drivewealth": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
        "merger": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
        "deal": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
        "prediction market": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
        "polymarket": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
        "event contracts": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
        "robinhood gold": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
        "legend": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
        "cortex": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
        "staking": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
        "roth ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
        "401k": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
        "ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
        "smart contract": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
        "layer 1": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
        "gdp": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
        "inflation": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
        "fed": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
        "nfl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
        "nba": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
        "super bowl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    }
    
    # Try to load from environment (JSON string)
    env_triggers = os.environ.get('TRIGGER_MAP_JSON')
    if env_triggers:
        try:
            return json.loads(env_triggers)
        except:
            pass
    
    return default_triggers

TRIGGER_MAP = load_trigger_map()
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
            # Find trigger position
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
            
            # Check for negation
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
                    'context': text
                })
    
    return found_triggers


def process_transcript(text: str):
    """Process incoming transcript text."""
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


# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Keys
    st.subheader("🔑 API Keys")
    deepgram_key = st.text_input(
        "Deepgram API Key",
        type="password",
        value=os.environ.get('DEEPGRAM_API_KEY', ''),
        help="Get your key at console.deepgram.com"
    )
    
    st.divider()
    
    # Trading Settings
    st.subheader("💰 Trading Settings")
    quantity = st.number_input("Contracts per trade", value=10, min_value=1, max_value=100)
    max_price = st.slider("Max price (¢)", 50, 99, 85)
    dry_run = st.checkbox("🔒 Dry Run Mode", value=True, help="No real trades")
    
    st.divider()
    
    # Stats
    st.subheader("📊 Session Stats")
    st.metric("Triggers Detected", len(st.session_state.triggers_detected))
    st.metric("Trades Executed", len(st.session_state.trades_executed))
    st.metric("Transcripts", len(st.session_state.transcripts))
    
    # Reset button
    if st.button("🗑️ Reset Session", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.triggers_detected = []
        st.session_state.trades_executed = []
        st.session_state.triggered_contracts = set()
        st.rerun()


# Main content
st.title("🎙️ Keynote Scalper")
st.caption("Real-time speech-to-trade for 'What will X say?' markets")

# Mode indicator
mode_col1, mode_col2 = st.columns([1, 3])
with mode_col1:
    if dry_run:
        st.warning("🟡 **DRY RUN MODE**")
    else:
        st.error("🔴 **LIVE TRADING**")
with mode_col2:
    st.info(f"Max Price: {max_price}¢ | Quantity: {quantity} contracts")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎤 Live Capture", "🎯 Triggers", "📊 Markets", "📜 History"])

# Tab 1: Live Capture
with tab1:
    st.header("Audio Capture")
    
    # Manual input section
    st.subheader("📝 Manual Transcript Input")
    col1, col2 = st.columns([4, 1])
    with col1:
        manual_text = st.text_area(
            "Enter transcript text",
            placeholder="Type or paste transcript here...",
            height=100,
            label_visibility="collapsed"
        )
    with col2:
        if st.button("🚀 Process", use_container_width=True, type="primary"):
            if manual_text:
                process_transcript(manual_text)
                st.rerun()
    
    st.divider()
    
    # Recent transcript
    st.subheader("📜 Recent Transcript")
    transcript_container = st.container()
    with transcript_container:
        if st.session_state.transcripts:
            for t in st.session_state.transcripts[-10:]:
                st.text(f"[{t['time']}] {t['text']}")
        else:
            st.caption("No transcripts yet. Use manual input or audio capture.")
    
    # Trigger alerts
    if st.session_state.triggers_detected:
        st.divider()
        st.subheader("🚨 Recent Triggers")
        for trigger in st.session_state.triggers_detected[-5:]:
            degree_icon = "1️⃣" if trigger['degree'] == 1 else "2️⃣"
            st.markdown(f"""
            <div class="trigger-alert">
                <strong>{degree_icon} 🎯 TRIGGER: "{trigger['trigger']}"</strong><br>
                Contract: {trigger['contract']} | Ticker: {trigger['ticker'][-4:]}<br>
                <small>{trigger['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Triggers
with tab2:
    st.header("🎯 Trigger Map")
    
    # Group by contract
    contracts = {}
    for trigger, data in TRIGGER_MAP.items():
        contract = data['contract']
        if contract not in contracts:
            contracts[contract] = {'first': [], 'second': []}
        if data.get('degree', 1) == 1:
            contracts[contract]['first'].append(trigger)
        else:
            contracts[contract]['second'].append(trigger)
    
    # Display as cards
    for contract, triggers in sorted(contracts.items()):
        triggered = any(
            t['contract'] == contract 
            for t in st.session_state.triggers_detected
        )
        icon = "✅" if triggered else "⏳"
        
        with st.expander(f"{icon} {contract}", expanded=not triggered):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**1st Degree (Contract Words)**")
                for t in triggers['first']:
                    st.code(t)
            with col2:
                st.markdown("**2nd Degree (What Vlad Says)**")
                for t in triggers['second'][:8]:
                    st.code(t)
                if len(triggers['second']) > 8:
                    st.caption(f"... and {len(triggers['second']) - 8} more")

# Tab 3: Markets
with tab3:
    st.header("📊 Current Markets")
    
    # Market data (static for now, would refresh from Kalshi)
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
        triggered = any(
            t['contract'] == m['word'] 
            for t in st.session_state.triggers_detected
        )
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            icon = "✅" if triggered else "🟢" if m['ask'] < max_price else "🔴"
            st.write(f"{icon} **{m['word']}**")
        with col2:
            st.write(f"Ask: {m['ask']}¢")
        with col3:
            st.write(f"Upside: {upside}¢")
        with col4:
            if not triggered and m['ask'] < max_price:
                st.progress(upside / 100)
            elif triggered:
                st.write("✅ Done")
            else:
                st.write("—")

# Tab 4: History
with tab4:
    st.header("📜 Session History")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Triggers Detected")
        if st.session_state.triggers_detected:
            for t in reversed(st.session_state.triggers_detected):
                st.write(f"**{t['trigger']}** → {t['contract']} ({t['timestamp']})")
        else:
            st.caption("No triggers yet")
    
    with col2:
        st.subheader("Trades Executed")
        if st.session_state.trades_executed:
            for t in reversed(st.session_state.trades_executed):
                st.write(f"✅ {t['contract']} @ {t['price']}¢")
        else:
            st.caption("No trades yet")

# Footer
st.divider()
st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Triggers loaded: {len(TRIGGER_MAP)}")
