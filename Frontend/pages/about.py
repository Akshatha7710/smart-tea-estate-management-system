import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from shared import COLORS, login_guard, render_shell, render_footer

st.set_page_config(
    page_title="About – STEMS",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded"
)
login_guard()

C = COLORS

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

.about-hero {{
    background: linear-gradient(135deg, rgba(30,77,51,0.13) 0%, rgba(46,107,69,0.18) 100%);
    border: 1px solid rgba(46,107,69,0.16);
    border-radius: 22px;
    padding: 52px 56px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}}
.about-hero::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {C['tea_green']}, {C['tea_green_light']}, transparent);
}}
.about-hero-watermark {{
    position: absolute;
    right: 52px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 120px;
    opacity: 0.10;
    line-height: 1;
    pointer-events: none;
    user-select: none;
}}
.about-hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(46,107,69,0.10);
    color: #1E4D33;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.8px;
    padding: 5px 14px;
    margin-bottom: 20px;
    font-family: 'DM Sans', sans-serif;
    text-transform: uppercase;
    border: 1px solid rgba(46,107,69,0.20);
}}
.about-hero-desc {{
    font-size: 15px;
    line-height: 1.9;
    color: #3a5a44;
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    padding-right: 180px;
}}
.about-hero-desc strong {{
    color: #1E4D33;
    font-weight: 600;
}}
.about-hero-tagline {{
    margin-top: 24px;
    font-size: 15px;
    color: rgba(30,77,51,0.55);
    font-style: italic;
    font-family: 'Cormorant Garamond', serif;
}}

.about-section-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: {C['tea_green']};
    margin-bottom: 16px;
    margin-top: 8px;
}}

.about-components-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 32px;
}}
.about-comp-card {{
    background: #ffffff;
    border: 1.5px solid #E4DFD8;
    border-radius: 18px;
    padding: 24px 26px;
    display: flex;
    align-items: flex-start;
    gap: 18px;
    transition: box-shadow 0.22s, transform 0.22s, border-color 0.22s;
    position: relative;
    overflow: hidden;
}}
.about-comp-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {C['tea_green']}, {C['tea_green_light']});
    opacity: 0;
    transition: opacity 0.2s;
}}
.about-comp-card:hover {{
    box-shadow: 0 8px 28px rgba(30,77,51,0.11);
    transform: translateY(-3px);
    border-color: rgba(46,107,69,0.30);
}}
.about-comp-card:hover::before {{
    opacity: 1;
}}
.about-comp-icon {{
    width: 48px;
    height: 48px;
    border-radius: 13px;
    background: linear-gradient(135deg, #EEF4F1 0%, #D8EDE0 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(30,77,51,0.10);
    transition: transform 0.2s;
}}
.about-comp-card:hover .about-comp-icon {{
    transform: scale(1.08);
}}
.about-comp-name {{
    font-size: 15px;
    font-weight: 600;
    color: {C['text_dark']};
    margin-bottom: 6px;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.2;
}}
.about-comp-desc {{
    font-size: 13px;
    color: {C['text_muted']};
    line-height: 1.65;
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
}}

.about-estate-strip {{
    background: {C['card_bg']};
    border: 1.5px solid #E4DFD8;
    border-radius: 18px;
    padding: 22px 32px;
    display: flex;
    align-items: center;
    justify-content: space-evenly;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 28px;
}}
.about-estate-item {{
    display: flex;
    flex-direction: column;
    gap: 3px;
    align-items: center;
}}
.about-estate-label {{
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: {C['text_muted']};
    font-family: 'DM Sans', sans-serif;
}}
.about-estate-value {{
    font-size: 14px;
    font-weight: 600;
    color: {C['text_dark']};
    font-family: 'DM Sans', sans-serif;
}}
.about-estate-divider {{
    width: 1px;
    height: 36px;
    background: #D9D4CC;
    flex-shrink: 0;
}}
</style>
""", unsafe_allow_html=True)

content_html = f"""
<div class="about-hero">
    <div class="about-hero-watermark">🍃</div>
    <div class="about-hero-badge">🍃 &nbsp;STEMS</div>
    <div class="about-hero-desc">
        <p style="margin:0 0 14px 0;">At <strong>Vellai Oya Estate</strong>, every decision matters, and STEMS is here to make them smarter.</p>
        <p style="margin:0 0 14px 0;">STEMS (Smart Tea Estate Management System) brings together data, intelligence, and innovation to support modern tea cultivation. Through four components: Soil Analysis, Fertilizer Scheduling, Harvest Readiness, and Production Analytics, the system turns everyday estate data into clear, actionable insights.</p>
        <p style="margin:0;">From knowing when to fertilize to when to harvest, STEMS helps estate managers make confident decisions that improve yield, quality, and sustainability.</p>
    </div>
    <div class="about-hero-tagline">Because growing great tea isn't just tradition: it's smart thinking. 🌱</div>
</div>

<div class="about-section-label">Main Components</div>
<div class="about-components-grid">
    <div class="about-comp-card">
        <div class="about-comp-icon">🌱</div>
        <div>
            <div class="about-comp-name">Fertilizer Scheduling</div>
            <div class="about-comp-desc">Predicts fertilizer quantity and application date using climate, yield, plucking, and fertilizer history.</div>
        </div>
    </div>
    <div class="about-comp-card">
        <div class="about-comp-icon">🧪</div>
        <div>
            <div class="about-comp-name">Soil Quality</div>
            <div class="about-comp-desc">Predicts soil pH and Carbon to provide proactive, data-driven soil management recommendations.</div>
        </div>
    </div>
    <div class="about-comp-card">
        <div class="about-comp-icon">📈</div>
        <div>
            <div class="about-comp-name">Production Analytics</div>
            <div class="about-comp-desc">Predicts yield using labour and climate data, and presents estate production analytics and trends.</div>
        </div>
    </div>
    <div class="about-comp-card">
        <div class="about-comp-icon">🌿</div>
        <div>
            <div class="about-comp-name">Harvest Readiness</div>
            <div class="about-comp-desc">Predicts optimal plucking time to ensure maximum quality leaf yield from the estate.</div>
        </div>
    </div>
</div>

<div class="about-section-label">Estate Details</div>
<div class="about-estate-strip">
    <div class="about-estate-item">
        <div class="about-estate-label">Estate</div>
        <div class="about-estate-value">Vellai Oya Tea Estate</div>
    </div>
    <div class="about-estate-divider"></div>
    <div class="about-estate-item">
        <div class="about-estate-label">Location</div>
        <div class="about-estate-value">Hatton, Sri Lanka</div>
    </div>
    <div class="about-estate-divider"></div>
    <div class="about-estate-item">
        <div class="about-estate-label">System</div>
        <div class="about-estate-value">STEMS v1.0 &nbsp;&middot;&nbsp; 2026</div>
    </div>
    <div class="about-estate-divider"></div>
</div>
"""

render_shell(
    active_label="About STEMS",
    page_title="About STEMS",
    page_subtitle="Smart Tea Estate Management System; built for Vellai Oya Estate.",
    content_html=content_html,
)

render_footer()