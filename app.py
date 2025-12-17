"""
🎙️ Keynote Scalper - Live Audio Trading System
==============================================
"""

import streamlit as st
import json
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Keynote Scalper",
    page_icon="🎙️",
    layout="wide"
)

# Initialize session state
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'triggers_detected' not in st.session_state:
    st.session_state.triggers_detected = []
if 'triggered_contracts' not in st.session_state:
    st.session_state.triggered_contracts = set()

# Load Deepgram key from secrets (hidden)
DEEPGRAM_KEY = os.environ.get('DEEPGRAM_API_KEY', '')

# Trigger map
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
    
    # Second degree (what Vlad actually says)
    "crypto": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "cryptocurrency": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "btc": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "solana": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "ethereum": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "eth": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "coinbase": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "satoshi": {"contract": "Bitcoin", "ticker": "KXVLADTENEVMENTION-25DEC17-BITC", "degree": 2},
    "bitstamp": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "x1": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "x1 card": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "drivewealth": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "say technologies": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "merger": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "deal": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "buyout": {"contract": "Acquisition", "ticker": "KXVLADTENEVMENTION-25DEC17-ACQU", "degree": 2},
    "prediction market": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "prediction markets": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "polymarket": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "event contracts": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "betting": {"contract": "Kalshi", "ticker": "KXVLADTENEVMENTION-25DEC17-KALS", "degree": 2},
    "robinhood gold": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 2},
    "premium": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 2},
    "subscription": {"contract": "Gold", "ticker": "KXVLADTENEVMENTION-25DEC17-GOLD", "degree": 2},
    "legend": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "cortex": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "ai": {"contract": "Innovation", "ticker": "KXVLADTENEVMENTION-25DEC17-INNO", "degree": 2},
    "staking": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
    "rwa": {"contract": "Tokenization", "ticker": "KXVLADTENEVMENTION-25DEC17-TOKE", "degree": 2},
    "roth ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "401k": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "ira": {"contract": "Retirement", "ticker": "KXVLADTENEVMENTION-25DEC17-RETI", "degree": 2},
    "smart contract": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "layer 1": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "layer 2": {"contract": "Blockchain", "ticker": "KXVLADTENEVMENTION-25DEC17-BLOC", "degree": 2},
    "gdp": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "inflation": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "fed": {"contract": "Economy", "ticker": "KXVLADTENEVMENTION-25DEC17-ECON", "degree": 2},
    "nfl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "nba": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "super bowl": {"contract": "Sport", "ticker": "KXVLADTENEVMENTION-25DEC17-SPOR", "degree": 2},
    "presidential": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 2},
    "vote": {"contract": "Election", "ticker": "KXVLADTENEVMENTION-25DEC17-ELEC", "degree": 2},
}

NEGATION_WORDS = ['not', "don't", "won't", 'never', 'no', "isn't", "aren't"]


def check_for_triggers(text: str) -> list:
    """Check text for trigger words, handling negation."""
    found_triggers = []
    text_lower = text.lower()
    words = text_lower.split()
    
    for trigger, data in TRIGGER_MAP.items():
        if data['ticker'] in st.session_state.triggered_contracts:
            continue
            
        if trigger in text_lower:
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
            
            # Check negation
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
                    'degree': data['degree'],
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
    
    return found_triggers


def process_transcript(text: str):
    """Process transcript text."""
    if not text.strip():
        return
    
    st.session_state.transcripts.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'text': text
    })
    
    triggers = check_for_triggers(text)
    for trigger in triggers:
        st.session_state.triggers_detected.append(trigger)
        st.session_state.triggered_contracts.add(trigger['ticker'])


# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check if API key is set from secrets
    if DEEPGRAM_KEY:
        st.success("✅ Deepgram API key loaded from secrets")
    else:
        st.warning("⚠️ Add DEEPGRAM_API_KEY to secrets")
    
    st.divider()
    
    st.subheader("📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Triggers", len(st.session_state.triggers_detected))
    with col2:
        st.metric("Contracts", len(st.session_state.triggered_contracts))
    
    st.metric("Transcripts", len(st.session_state.transcripts))
    
    if st.button("🗑️ Reset", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.triggers_detected = []
        st.session_state.triggered_contracts = set()
        st.rerun()

# Main
st.title("🎙️ Keynote Scalper")
st.caption("Live speech-to-trade for Kalshi markets | Robinhood YES/NO Keynote")

# Tabs
tab1, tab2, tab3 = st.tabs(["🎤 Live Input", "🎯 Triggers", "📊 Markets"])

with tab1:
    st.header("Live Transcript Input")
    
    # Info about live audio (for now it's manual)
    if not DEEPGRAM_KEY:
        st.warning("⚠️ Add DEEPGRAM_API_KEY to app secrets for automatic transcription")
    
    # Manual input
    st.subheader("📝 Enter What You Hear")
    col1, col2 = st.columns([5, 1])
    with col1:
        manual_text = st.text_input(
            "Transcript",
            placeholder="Type what Vlad says...",
            label_visibility="collapsed"
        )
    with col2:
        if st.button("Process", type="primary", use_container_width=True):
            if manual_text:
                process_transcript(manual_text)
                st.rerun()
    
    st.caption("💡 **Quick test:** Type 'bitcoin' and click Process to see a trigger!")
    
    st.divider()
    
    # Live transcript
    st.subheader("📜 Transcript Log")
    if st.session_state.transcripts:
        for t in st.session_state.transcripts[-15:]:
            st.text(f"[{t['time']}] {t['text']}")
    else:
        st.caption("Your transcripts will appear here...")
    
    # Trigger alerts
    if st.session_state.triggers_detected:
        st.divider()
        st.subheader("🚨 TRIGGER ALERTS")
        for trigger in reversed(st.session_state.triggers_detected[-5:]):
            degree = "1st°" if trigger['degree'] == 1 else "2nd°"
            st.error(f"🎯 **{trigger['trigger'].upper()}** → {trigger['contract']} ({degree}) @ {trigger['timestamp']}")

with tab2:
    st.header("🎯 Trigger Map")
    st.caption("1st Degree = Contract words | 2nd Degree = What Vlad says")
    
    contracts = {}
    for trigger, data in TRIGGER_MAP.items():
        contract = data['contract']
        if contract not in contracts:
            contracts[contract] = {'first': [], 'second': []}
        if data['degree'] == 1:
            contracts[contract]['first'].append(trigger)
        else:
            contracts[contract]['second'].append(trigger)
    
    for contract in sorted(contracts.keys()):
        triggers = contracts[contract]
        triggered = contract in [t['contract'] for t in st.session_state.triggers_detected]
        icon = "✅" if triggered else "⏳"
        
        with st.expander(f"{icon} **{contract}**", expanded=not triggered):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**1st Degree (Direct)**")
                for t in triggers['first']:
                    st.code(t)
            with col2:
                st.markdown("**2nd Degree (Product Names)**")
                for t in triggers['second'][:8]:
                    st.code(t)
                if len(triggers['second']) > 8:
                    st.caption(f"+{len(triggers['second'])-8} more")

with tab3:
    st.header("📊 Market Status")
    
    markets = [
        {"word": "Retirement", "ask": 17},
        {"word": "Blockchain", "ask": 22},
        {"word": "Bitcoin", "ask": 24},
        {"word": "Election", "ask": 34},
        {"word": "Acquisition", "ask": 39},
        {"word": "Economy", "ask": 40},
        {"word": "Kalshi", "ask": 41},
        {"word": "SIG", "ask": 56},
        {"word": "Tokenization", "ask": 66},
        {"word": "Sport", "ask": 73},
        {"word": "Innovation", "ask": 78},
        {"word": "Gold", "ask": 84},
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
st.caption(f"Triggers: {len(TRIGGER_MAP)} | Contracts: 12 | Event: Robinhood YES/NO @ 9pm ET")
