import os
import threading
import datetime
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string, session, jsonify
import requests
import logging
from collections import deque

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://nongflexv1.up.railway.app/callback")

GUILD_ID = 1207514483527000084
ROLE_ID = 1211224793060478976

WEBHOOK_SUCCESS = "https://discord.com/api/webhooks/1540031111223189701/KhD_TF8YMxmRih4KQCH-MtBnTy74Qcodk7trYCqjy7_z6-6zQ8frXd8dJX-FOaZ1MO7X"
WEBHOOK_ERROR = "https://discord.com/api/webhooks/1540065078278365204/8MNh3CWoP4GUM_8k2WLw53H5EumtDUY7p-uMTQ1kvCD30zxFS7VadBlMfRchuBjoVsX3"

BRAND_LOGO_URL = "https://media.discordapp.net/attachments/1554137226294857728/1554202597051601098/e380ca8bc4596b18d991b97d9e48c123.jpg?ex=6abc0776&is=6abab5f6&hm=2d442ec35bb67d1ec5fcbfa5e4ea9f616402af836df35e0282546963a2983e1f&=&format=webp"

AUDIO_URL = "https://files.catbox.moe/fyvd9o.mp3"
BACKGROUND_IMAGE = "https://files.catbox.moe/3jmrta.jpg"

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน"
    )

LOG_BUFFER_MAXLEN = 300
log_buffer = deque(maxlen=LOG_BUFFER_MAXLEN)

class MemoryLogHandler(logging.Handler):
    """เก็บ log ล่าสุดไว้ใน memory เพื่อโชว์แบบ live ในหน้า admin dashboard"""
    def emit(self, record):
        try:
            log_buffer.append({
                "time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "message": self.format(record),
            })
        except Exception:
            pass

logger = logging.getLogger("stifshop")
logger.setLevel(logging.INFO)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(logging.Formatter("%(message)s"))
_memory_handler = MemoryLogHandler()
_memory_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_stream_handler)
logger.addHandler(_memory_handler)
logger.propagate = False

def init_db():
    conn = sqlite3.connect("verifications.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            global_name TEXT,
            avatar_url TEXT,
            verified_at TEXT,
            role_name TEXT,
            role_color TEXT
        )
    """)
    conn.commit()

    cursor.execute("PRAGMA table_info(verified_users)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "role_name" not in existing_cols:
        cursor.execute("ALTER TABLE verified_users ADD COLUMN role_name TEXT")
    if "role_color" not in existing_cols:
        cursor.execute("ALTER TABLE verified_users ADD COLUMN role_color TEXT")
    conn.commit()
    conn.close()

init_db()

THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

def thai_date(dt=None):
    dt = dt or datetime.datetime.utcnow()
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="th">

<head>
  <meta charset="UTF-8">
  <meta name="viewport"
    content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>{{ title | default('ระบบยืนยันตัวตน by.น้องเจคอปเด็กชายบริสุทธิ์') }}</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700;800&display=swap"
    rel="stylesheet">

  <style>
    :root {
      --bg-dark: #04060f;
      --card-surface: rgba(12, 17, 34, 0.76);
      --table-header-bg: rgba(8, 12, 24, 0.8);
      --row-bg: rgba(14, 20, 40, 0.65);
      --row-hover: rgba(24, 35, 70, 0.92);
      --text-pure: #ffffff;
      --text-sub: #94a3b8;
      --text-dim: #54657e;
      --border-soft: rgba(255, 255, 255, 0.08);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }

    ::selection { background: #6366f1; color: #ffffff; }

    html, body {
      min-height: 100dvh;
      background-color: var(--bg-dark);
      font-family: 'Plus Jakarta Sans', 'Kanit', sans-serif;
      color: var(--text-pure);
      overflow-x: hidden;
    }

    body {
      padding: clamp(24px, 4vw, 56px) clamp(16px, 3.5vw, 32px);
      display: flex;
      justify-content: center;
      position: relative;
      perspective: 1400px;
    }

    #cursor-glow {
      position: fixed;
      width: 650px;
      height: 650px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(200, 200, 200, 0.10) 0%, rgba(150, 150, 150, 0.05) 35%, transparent 70%);
      pointer-events: none;
      transform: translate(-50%, -50%);
      z-index: 1;
      will-change: left, top;
    }

    #stars-canvas {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
    }

    .aurora-wrap {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 1;
      overflow: hidden;
      background-image:
        linear-gradient(rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.80)),
        url('{{ background_image }}');
      background-size: cover;
      background-position: center center;
      background-repeat: no-repeat;
      background-attachment: fixed;
      filter: grayscale(0.7) contrast(1.1) brightness(0.9);
    }

    .smoke-layer {
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background:
        radial-gradient(ellipse 400px 800px at 15% 90%, rgba(200, 200, 200, 0.06) 0%, transparent 60%),
        radial-gradient(ellipse 500px 900px at 85% 95%, rgba(180, 180, 180, 0.05) 0%, transparent 65%);
      animation: smokeFloat 18s ease-in-out infinite alternate;
    }

    @keyframes smokeFloat {
      0% { transform: translateY(0) scale(1); opacity: 0.7; }
      50% { transform: translateY(-30px) scale(1.05); opacity: 1; }
      100% { transform: translateY(-60px) scale(1.1); opacity: 0.6; }
    }

    .cyber-grid {
      position: fixed;
      inset: 0;
      z-index: 2;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
      background-size: 48px 48px;
      opacity: 0.9;
      mask-image: radial-gradient(circle at center, black 40%, transparent 88%);
      -webkit-mask-image: radial-gradient(circle at center, black 40%, transparent 88%);
    }

    .vignette-overlay {
      position: fixed;
      inset: 0;
      z-index: 3;
      pointer-events: none;
      background: radial-gradient(ellipse at center, transparent 35%, rgba(0, 0, 0, 0.65) 100%);
      mix-blend-mode: multiply;
    }

    .app-layout {
      position: relative;
      z-index: 10;
      width: 100%;
      max-width: 1240px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 36px;
    }

    .page-view {
      display: none;
      width: 100%;
      opacity: 0;
      transform: translateY(16px);
      transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .page-view.active {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 36px;
      opacity: 1;
      transform: translateY(0);
    }

    .top-action-bar {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      padding: 10px 18px;
      background: rgba(12, 17, 34, 0.55);
      border: 1px solid var(--border-soft);
      border-radius: 50px;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }

    .brand-cluster { display: flex; align-items: center; gap: 12px; }

    .brand-logo-gem {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: linear-gradient(135deg, #1a1d24 0%, #050608 100%);
      border: 1.5px solid rgba(255, 255, 255, 0.28);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 24px rgba(255, 255, 255, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.12);
      position: relative;
      overflow: hidden;
      flex-shrink: 0;
    }

    .brand-logo-gem::after {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.18), transparent 60%);
      pointer-events: none;
    }

    .brand-logo-gem svg {
      width: 34px;
      height: 34px;
      position: relative;
      z-index: 1;
      filter: drop-shadow(0 0 6px rgba(255, 255, 255, 0.4));
    }

    .brand-title {
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 800;
      font-size: 0.95rem;
      letter-spacing: 0.6px;
      color: #ffffff;
    }

    .brand-sub {
      font-size: 0.74rem;
      color: var(--text-sub);
      font-family: 'JetBrains Mono', monospace;
    }

    .portal-container {
      width: 100%;
      max-width: 480px;
      position: relative;
      transform-style: preserve-3d;
    }

    .hologram-glow-border {
      position: relative;
      border-radius: 42px;
      padding: 1.5px;
      background: linear-gradient(135deg, rgba(120, 120, 120, 0.65), rgba(200, 200, 200, 0.65), rgba(150, 150, 150, 0.65), rgba(220, 220, 220, 0.55));
      background-size: 300% 300%;
      animation: rainbowGlow 8s ease infinite;
      box-shadow: 0 35px 90px rgba(0, 0, 0, 0.9), 0 0 55px rgba(200, 200, 200, 0.15);
    }

    @keyframes rainbowGlow {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    .hologram-card {
      position: relative;
      background: linear-gradient(180deg, rgba(16, 20, 28, 0.88) 0%, rgba(6, 8, 12, 0.96) 100%);
      backdrop-filter: blur(40px);
      -webkit-backdrop-filter: blur(40px);
      border-radius: 40px;
      padding: 42px 32px 34px;
      text-align: center;
      overflow: hidden;
      transform-style: preserve-3d;
      transition: box-shadow 0.4s ease, transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .hologram-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 12%;
      right: 12%;
      height: 3px;
      background: linear-gradient(90deg, transparent, #e5e7eb, #9ca3af, #f3f4f6, transparent);
      background-size: 200% 100%;
      animation: sheenRun 4s linear infinite;
      border-radius: 100px;
      box-shadow: 0 0 20px rgba(255, 255, 255, 0.7);
    }

    @keyframes sheenRun {
      0% { background-position: 100% 0; }
      100% { background-position: -100% 0; }
    }

    .system-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 18px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 100px;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: #e2e8f0;
      margin-bottom: 24px;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }

    .badge-gem {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #e5e7eb;
      box-shadow: 0 0 14px #ffffff;
      animation: gemPulse 1.6s ease-in-out infinite;
    }

    @keyframes gemPulse {
      0%, 100% { transform: scale(1); opacity: 0.7; }
      50% { transform: scale(1.4); opacity: 1; }
    }

    .scanner-viewport {
      position: relative;
      width: 170px;
      height: 170px;
      margin: 0 auto 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .progress-svg-ring {
      position: absolute;
      inset: 0;
      transform: rotate(-90deg);
    }

    .progress-circle-bg {
      fill: none;
      stroke: rgba(255, 255, 255, 0.08);
      stroke-width: 4;
    }

    .progress-circle-bar {
      fill: none;
      stroke: url(#cyanPurpleGrad);
      stroke-width: 5;
      stroke-linecap: round;
      stroke-dasharray: 471;
      stroke-dashoffset: 471;
      transition: stroke-dashoffset 0.25s ease;
      filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.8));
    }

    .gyro-orbit {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      pointer-events: none;
    }

    .orbit-outer {
      border: 2px dashed rgba(255, 255, 255, 0.55);
      animation: spinClockwise 10s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      box-shadow: 0 0 30px rgba(255, 255, 255, 0.2);
    }

    .orbit-mid {
      inset: 16px;
      border: 2.5px solid transparent;
      border-top: 2.5px solid #e5e7eb;
      border-bottom: 2.5px solid #9ca3af;
      animation: spinCounter 7s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite;
      box-shadow: 0 0 35px rgba(200, 200, 200, 0.3);
    }

    .orbit-inner {
      inset: 32px;
      border: 1.5px dotted rgba(255, 255, 255, 0.6);
      animation: spinClockwise 8s linear infinite;
    }

    .reactor-core {
      position: relative;
      width: 76px;
      height: 76px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(120, 120, 120, 0.55), rgba(220, 220, 220, 0.45));
      border: 1.5px solid rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 45px rgba(200, 200, 200, 0.6);
      animation: coreBreathing 2.6s ease-in-out infinite alternate;
      z-index: 5;
    }

    .reactor-core svg {
      width: 28px;
      height: 28px;
      stroke: #ffffff;
      filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.9));
    }

    .laser-scan-line {
      position: absolute;
      left: 10px;
      right: 10px;
      height: 2px;
      background: linear-gradient(90deg, transparent, #ffffff, #9ca3af, transparent);
      box-shadow: 0 0 15px #ffffff;
      animation: laserScan 2.4s ease-in-out infinite alternate;
      pointer-events: none;
      z-index: 10;
    }

    @keyframes laserScan {
      0% { top: 15%; opacity: 0.2; }
      50% { opacity: 1; }
      100% { top: 85%; opacity: 0.2; }
    }

    @keyframes spinClockwise { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    @keyframes spinCounter { 0% { transform: rotate(360deg); } 100% { transform: rotate(0deg); } }
    @keyframes coreBreathing {
      0% { transform: scale(0.95); box-shadow: 0 0 25px rgba(120, 120, 120, 0.5); }
      100% { transform: scale(1.08); box-shadow: 0 0 55px rgba(255, 255, 255, 0.8); }
    }

    .loading-status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      border-radius: 50px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.25);
      font-size: 0.8rem;
      font-weight: 700;
      color: #e5e7eb;
      margin-bottom: 14px;
      animation: pulseGlow 1.8s ease-in-out infinite;
    }

    .portal-headline {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 1.55rem;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 8px;
      letter-spacing: -0.3px;
    }

    .portal-subtext {
      font-size: 0.92rem;
      color: var(--text-sub);
      line-height: 1.65;
      margin-bottom: 24px;
    }

    .phase-panel {
      display: none;
      opacity: 0;
      transform: translateY(12px) scale(0.98);
    }

    .phase-panel.active {
      display: block;
      animation: panelEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes panelEnter {
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* ==== LOADING SCREEN ==== */
    .loading-screen {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 30px 0;
      transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .loading-screen.hide {
      opacity: 0;
      transform: scale(0.9);
      pointer-events: none;
    }

    .loading-ring {
      width: 140px;
      height: 140px;
      position: relative;
      margin-bottom: 28px;
    }

    .loading-ring::before,
    .loading-ring::after {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 3px solid transparent;
      animation: loadingSpin 1.4s cubic-bezier(0.5, 0, 0.5, 1) infinite;
    }

    .loading-ring::before {
      border-top-color: #e5e7eb;
      border-right-color: #9ca3af;
      animation-duration: 1.2s;
    }

    .loading-ring::after {
      inset: 14px;
      border-bottom-color: #f3f4f6;
      border-left-color: #6b7280;
      animation-duration: 1.6s;
      animation-direction: reverse;
    }

    .loading-ring-inner {
      position: absolute;
      inset: 32px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(120, 120, 120, 0.55), rgba(220, 220, 220, 0.45));
      border: 1.5px solid rgba(255, 255, 255, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 45px rgba(200, 200, 200, 0.6);
      animation: coreBreathing 2.6s ease-in-out infinite alternate;
    }

    .loading-ring-inner svg {
      width: 30px;
      height: 30px;
      stroke: #ffffff;
      fill: none;
      stroke-width: 2.4;
      stroke-linecap: round;
      stroke-linejoin: round;
      filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.9));
    }

    @keyframes loadingSpin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-text {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 1.15rem;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 10px;
      letter-spacing: -0.3px;
    }

    .loading-subtext {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      color: var(--text-sub);
      letter-spacing: 0.5px;
    }

    .loading-dots {
      display: inline-flex;
      gap: 4px;
      margin-left: 4px;
    }

    .loading-dots span {
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: #e5e7eb;
      animation: dotPulse 1.4s ease-in-out infinite;
    }

    .loading-dots span:nth-child(1) { animation-delay: 0s; }
    .loading-dots span:nth-child(2) { animation-delay: 0.2s; }
    .loading-dots span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes dotPulse {
      0%, 100% { opacity: 0.3; transform: scale(0.8); }
      50% { opacity: 1; transform: scale(1.3); }
    }

    .loading-progress {
      width: 180px;
      height: 3px;
      border-radius: 100px;
      background: rgba(255, 255, 255, 0.08);
      overflow: hidden;
      margin-top: 22px;
    }

    .loading-progress-bar {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #9ca3af, #ffffff, #e5e7eb);
      border-radius: 100px;
      box-shadow: 0 0 12px rgba(255, 255, 255, 0.6);
      animation: progressFill 10s cubic-bezier(0.3, 0, 0.7, 1) forwards;
    }

    @keyframes progressFill {
      0% { width: 0%; }
      50% { width: 65%; }
      85% { width: 90%; }
      100% { width: 100%; }
    }

    .btn-godtier {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      width: 100%;
      padding: 18px 24px;
      border-radius: 20px;
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 1.05rem;
      font-weight: 800;
      color: #0a0c11;
      text-decoration: none;
      background: linear-gradient(135deg, #e5e7eb 0%, #ffffff 50%, #9ca3af 100%);
      background-size: 200% auto;
      border: none;
      box-shadow: 0 14px 35px rgba(200, 200, 200, 0.35);
      cursor: pointer;
      overflow: hidden;
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .btn-godtier:hover {
      background-position: right center;
      transform: translateY(-2px) scale(1.01);
      box-shadow: 0 18px 45px rgba(255, 255, 255, 0.45);
    }

    .btn-godtier:active { transform: translateY(1px) scale(0.99); }

    .identity-capsule {
      background: linear-gradient(180deg, rgba(22, 30, 54, 0.92) 0%, rgba(11, 16, 30, 0.98) 100%);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 28px;
      padding: 24px 22px;
      margin-bottom: 26px;
      position: relative;
      overflow: hidden;
      text-align: left;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.65);
    }

    .avatar-row {
      display: flex;
      align-items: center;
      gap: 18px;
      margin-bottom: 20px;
    }

    .avatar-frame {
      position: relative;
      flex-shrink: 0;
    }

    .avatar-photo {
      width: 76px;
      height: 76px;
      border-radius: 22px;
      border: 2px solid rgba(255, 255, 255, 0.25);
      object-fit: cover;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.55);
      display: block;
    }

    .avatar-halo {
      position: absolute;
      inset: -6px;
      border-radius: 26px;
      border: 2px solid rgba(255, 255, 255, 0.75);
      animation: haloPulse 2.5s ease-in-out infinite;
      pointer-events: none;
    }

    @keyframes haloPulse {
      0%, 100% { opacity: 0.6; transform: scale(1); }
      50% { opacity: 1; border-color: #e5e7eb; transform: scale(1.04); }
    }

    .status-dot-mini {
      position: absolute;
      bottom: -3px;
      right: -3px;
      width: 20px;
      height: 20px;
      background: #10b981;
      border: 3.5px solid #0d121f;
      border-radius: 50%;
      box-shadow: 0 0 12px #10b981;
    }

    .user-meta { min-width: 0; flex: 1; }

    .user-royal-name {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 1.3rem;
      font-weight: 800;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-discord-handle {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.84rem;
      color: var(--text-sub);
      margin-top: 3px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .btn-copy-id {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-sub);
      cursor: pointer;
      font-size: 0.7rem;
      transition: all 0.2s ease;
    }

    .btn-copy-id:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: #ffffff;
      color: #ffffff;
    }

    .verified-crown-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      padding: 5px 12px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.05));
      border: 1px solid rgba(255, 255, 255, 0.4);
      border-radius: 12px;
      font-size: 0.72rem;
      font-weight: 800;
      color: #ffffff;
      position: relative;
      overflow: hidden;
    }

    .verified-crown-tag::after {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
      animation: tagShimmer 3s infinite;
    }

    @keyframes tagShimmer { 100% { left: 100%; } }

    .meta-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 16px;
      padding: 14px 16px;
    }

    .meta-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.88rem;
    }

    .meta-title {
      color: var(--text-sub);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .role-vip-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 5px 14px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.86rem;
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.14);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }

    .role-light-dot { width: 8px; height: 8px; border-radius: 50%; }

    .error-capsule {
      background: linear-gradient(180deg, rgba(50, 18, 25, 0.9) 0%, rgba(25, 10, 15, 0.98) 100%);
      border: 1px solid rgba(244, 63, 94, 0.35);
      border-radius: 26px;
      padding: 24px 20px;
      margin-bottom: 24px;
      text-align: center;
    }

    .error-icon-wrap {
      width: 64px;
      height: 64px;
      border-radius: 20px;
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
      color: #f43f5e;
      box-shadow: 0 0 25px rgba(244, 63, 94, 0.35);
    }

    #fx-canvas {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 30;
    }

    .stats-bar {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }

    .stat-card {
      background: var(--card-surface);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--border-soft);
      border-radius: 22px;
      padding: 20px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
      position: relative;
      overflow: hidden;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .stat-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--accent-gradient, linear-gradient(90deg, #9ca3af, transparent));
      opacity: 0.8;
    }

    .stat-card:hover {
      transform: translateY(-3px);
      border-color: rgba(255, 255, 255, 0.2);
      box-shadow: 0 18px 45px rgba(0, 0, 0, 0.6);
    }

    .stat-label {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: var(--text-sub);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .stat-value {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.85rem;
      font-weight: 800;
      margin-top: 4px;
      color: #ffffff;
      display: flex;
      align-items: baseline;
      gap: 8px;
    }

    .stat-value .unit {
      font-size: 0.88rem;
      color: var(--text-dim);
      font-weight: 600;
      font-family: 'Kanit', sans-serif;
    }

    .stat-icon-wrap {
      width: 48px;
      height: 48px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
    }

    .stat-icon-wrap svg { width: 24px; height: 24px; }

    .live-activity-card {
      width: 100%;
      background: var(--card-surface);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid var(--border-soft);
      border-radius: 30px;
      padding: clamp(22px, 3vw, 36px);
      box-shadow: 0 30px 70px rgba(0, 0, 0, 0.7);
      position: relative;
    }

    .activity-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 22px;
    }

    .title-group .eyebrow {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 2px;
      color: #9ca3af;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .title-group .main-title {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 1.85rem;
      font-weight: 800;
      color: #ffffff;
      margin-top: 2px;
    }

    .badge-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 18px;
      border-radius: 100px;
      font-size: 0.84rem;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #e5e7eb;
    }

    .live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #e5e7eb;
      box-shadow: 0 0 12px #ffffff;
      animation: pulseGlow 1.5s ease-in-out infinite;
    }

    @keyframes pulseGlow {
      0%, 100% { opacity: 0.5; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.35); }
    }

    .badge-rounds {
      display: inline-flex;
      align-items: center;
      padding: 7px 16px;
      border-radius: 100px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text-sub);
    }

    .table-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 18px;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 14px;
      padding: 10px 16px;
      min-width: 260px;
      flex: 1;
      max-width: 420px;
      transition: all 0.2s ease;
    }

    .search-box:focus-within {
      border-color: #e5e7eb;
      background: rgba(255, 255, 255, 0.06);
      box-shadow: 0 0 16px rgba(255, 255, 255, 0.15);
    }

    .search-box input {
      background: transparent;
      border: none;
      outline: none;
      color: #ffffff;
      font-size: 0.88rem;
      font-family: 'Plus Jakarta Sans', 'Kanit', sans-serif;
      width: 100%;
    }

    .search-box input::placeholder { color: var(--text-dim); }

    .filter-chips { display: flex; gap: 8px; }

    .chip-btn {
      padding: 8px 16px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--text-sub);
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .chip-btn:hover { background: rgba(255, 255, 255, 0.09); color: #ffffff; }

    .chip-btn.active {
      background: rgba(200, 200, 200, 0.18);
      border-color: #e5e7eb;
      color: #ffffff;
    }

    .table-wrapper {
      overflow-x: auto;
      border-radius: 20px;
      border: 1px solid var(--border-soft);
      background: var(--table-header-bg);
      box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4);
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 8px;
      padding: 10px;
      min-width: 760px;
    }

    th {
      font-family: 'Space Grotesk', 'Kanit', sans-serif;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 1.4px;
      text-transform: uppercase;
      color: var(--text-dim);
      text-align: left;
      padding: 14px 20px;
    }

    tbody tr {
      background: var(--row-bg);
      border-radius: 16px;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      cursor: pointer;
    }

    tbody tr:hover {
      background: var(--row-hover);
      transform: translateX(4px) scale(1.003);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    td {
      padding: 16px 20px;
      font-size: 0.94rem;
      vertical-align: middle;
    }

    td:first-child { border-top-left-radius: 16px; border-bottom-left-radius: 16px; }
    td:last-child { border-top-right-radius: 16px; border-bottom-right-radius: 16px; }

    .user-cell { display: flex; align-items: center; gap: 14px; }

    .user-avatar-circle {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid rgba(255, 255, 255, 0.35);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.45);
      flex-shrink: 0;
    }

    .user-title { font-weight: 700; color: #ffffff; font-size: 0.98rem; }
    .user-sub { font-size: 0.78rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }

    .id-badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.86rem;
      font-weight: 600;
      color: #e5e7eb;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.18);
      padding: 6px 14px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .id-badge:hover {
      background: rgba(255, 255, 255, 0.18);
      border-color: #ffffff;
      color: #ffffff;
    }

    .role-tag-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.88rem;
      color: #ffffff;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }

    .role-dot-glow { width: 8px; height: 8px; border-radius: 50%; }

    .time-text {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.84rem;
      color: var(--text-sub);
      white-space: nowrap;
    }

    .floating-music-player {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 90;
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 10px 20px;
      background: rgba(12, 17, 34, 0.92);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 50px;
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.7), 0 0 24px rgba(255, 255, 255, 0.08);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .floating-music-player:hover {
      border-color: rgba(255, 255, 255, 0.5);
      box-shadow: 0 16px 45px rgba(0, 0, 0, 0.85), 0 0 30px rgba(255, 255, 255, 0.2);
    }

    .music-disc-icon {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: linear-gradient(135deg, #e5e7eb, #9ca3af);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: spinClockwise 4s linear infinite;
      box-shadow: 0 0 14px rgba(255, 255, 255, 0.4);
      flex-shrink: 0;
      cursor: pointer;
    }

    .music-disc-icon.paused {
      animation-play-state: paused;
      background: linear-gradient(135deg, #54657e, #334155);
      box-shadow: none;
    }

    .music-disc-icon svg { width: 18px; height: 18px; fill: #0a0c11; }

    .music-track-meta {
      display: flex;
      flex-direction: column;
      max-width: 220px;
      overflow: hidden;
    }

    .music-track-name {
      font-size: 0.84rem;
      font-weight: 700;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .music-track-status {
      font-size: 0.7rem;
      color: #d1d5db;
      font-family: 'JetBrains Mono', monospace;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .eq-wave-group { display: flex; align-items: flex-end; gap: 3px; height: 14px; }

    .eq-bar {
      width: 3px;
      background: #e5e7eb;
      border-radius: 2px;
      animation: eqDance 0.8s ease-in-out infinite alternate;
    }

    .eq-bar:nth-child(1) { height: 6px; animation-delay: 0.1s; }
    .eq-bar:nth-child(2) { height: 12px; animation-delay: 0.3s; }
    .eq-bar:nth-child(3) { height: 8px; animation-delay: 0.15s; }
    .eq-bar:nth-child(4) { height: 14px; animation-delay: 0.4s; }

    .paused .eq-bar { animation: none; height: 3px; background: #54657e; }

    @keyframes eqDance { 0% { height: 3px; } 100% { height: 14px; } }

    .btn-music-toggle {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s ease;
      flex-shrink: 0;
    }

    .btn-music-toggle:hover {
      background: rgba(255, 255, 255, 0.2);
      border-color: rgba(255, 255, 255, 0.5);
      box-shadow: 0 0 12px rgba(255, 255, 255, 0.4);
    }

    #toast-notice {
      position: fixed;
      bottom: 100px;
      right: 28px;
      z-index: 100;
      background: rgba(12, 17, 34, 0.95);
      border: 1px solid #e5e7eb;
      box-shadow: 0 10px 30px rgba(255, 255, 255, 0.2);
      padding: 12px 20px;
      border-radius: 14px;
      font-size: 0.88rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
      backdrop-filter: blur(16px);
      transform: translateY(80px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: none;
    }

    #toast-notice.show { transform: translateY(0); opacity: 1; }

    @media (max-width: 768px) {
      body { padding: 16px 12px 64px; }
      .app-layout { gap: 22px; }
      .page-view.active { gap: 22px; }
      .hologram-glow-border { border-radius: 34px; }
      .hologram-card { padding: 28px 20px 24px; border-radius: 32px; }
      .scanner-viewport { width: 140px; height: 140px; margin-bottom: 18px; }
      .reactor-core { width: 62px; height: 62px; }
      .portal-headline { font-size: 1.3rem; }
      .portal-subtext { font-size: 0.85rem; margin-bottom: 20px; }
      .identity-capsule { padding: 18px 16px; border-radius: 22px; margin-bottom: 20px; }
      .avatar-photo { width: 60px; height: 60px; border-radius: 18px; }
      .user-royal-name { font-size: 1.1rem; }
      .btn-godtier { padding: 15px; font-size: 0.98rem; border-radius: 16px; }
      .stats-bar { grid-template-columns: repeat(2, 1fr); gap: 12px; }
      .stat-card { padding: 14px 14px; border-radius: 18px; }
      .stat-label { font-size: 0.7rem; }
      .stat-value { font-size: 1.4rem; }
      .stat-value .unit { font-size: 0.75rem; }
      .stat-icon-wrap { width: 38px; height: 38px; border-radius: 10px; }
      .live-activity-card { padding: 20px 14px; border-radius: 24px; }
      .table-toolbar { flex-direction: column; align-items: stretch; }
      .search-box { max-width: 100%; }
      .table-wrapper { border-radius: 16px; -webkit-overflow-scrolling: touch; }
      table { min-width: 620px; padding: 6px; }
      th { padding: 10px 14px; font-size: 0.72rem; }
      td { padding: 12px 14px; font-size: 0.86rem; }
      .user-avatar-circle { width: 38px; height: 38px; }
      .user-title { font-size: 0.9rem; }
      .id-badge { font-size: 0.78rem; padding: 4px 10px; }
      .role-tag-badge { font-size: 0.82rem; padding: 5px 12px; }
      .floating-music-player { bottom: 14px; right: 14px; padding: 8px 14px; }
      .music-track-meta { max-width: 140px; }
      .loading-ring { width: 110px; height: 110px; }
      .loading-ring-inner { inset: 26px; }
      .loading-ring-inner svg { width: 24px; height: 24px; }
    }
  </style>
</head>

<body>

  <div id="cursor-glow"></div>
  <canvas id="stars-canvas"></canvas>

  <div class="aurora-wrap"></div>
  <div class="smoke-layer"></div>
  <div class="cyber-grid"></div>
  <div class="vignette-overlay"></div>

  <div class="app-layout">

    {% if user %}
    <!-- ============================================= -->
    <!-- PAGE 2 : DASHBOARD -->
    <!-- ============================================= -->
    <div class="page-view active" id="page-dashboard">

      <div class="top-action-bar">
        <div class="brand-cluster">
          <div class="brand-logo-gem">
            <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.2" stroke-dasharray="3 4"/>
              <ellipse cx="17" cy="22" rx="4" ry="4.6" fill="#ffffff"/>
              <ellipse cx="31" cy="22" rx="4" ry="4.6" fill="#ffffff"/>
              <circle cx="17" cy="22.5" r="2.1" fill="#0a0c11"/>
              <circle cx="31" cy="22.5" r="2.1" fill="#0a0c11"/>
              <circle cx="16.2" cy="21.6" r="0.8" fill="#ffffff"/>
              <circle cx="30.2" cy="21.6" r="0.8" fill="#ffffff"/>
              <line x1="12" y1="28" x2="10" y2="36" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="16" y1="28.5" x2="15" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="20" y1="28.5" x2="20" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="28" y1="28.5" x2="28" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="32" y1="28.5" x2="33" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="36" y1="28" x2="38" y2="36" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <path d="M21 33 Q24 34 27 33" fill="none" stroke="#ffffff" stroke-width="1.4" stroke-linecap="round"/>
              <rect x="27" y="32.4" width="7" height="1.6" rx="0.8" fill="#ffffff"/>
              <circle cx="34.4" cy="33.2" r="0.9" fill="#ff6b3d"/>
              <path d="M35.5 31 Q37 28 36 25 Q35 22 37 19" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="brand-title">ระบบยืนยันตัวตน by.น้องเจคอปเด็กชายบริสุทธิ์</div>
            <div class="brand-sub">v1.0 · DASHBOARD</div>
          </div>
        </div>
      </div>

      <div class="portal-container">
        <div class="hologram-glow-border">
          <div class="hologram-card" id="hologramCard">
            <canvas id="fx-canvas"></canvas>
            <div class="system-badge">
              <span class="badge-gem"></span>
              <span>VERIFICATION SUCCESS</span>
            </div>

            <div class="phase-panel active">
              <div class="identity-capsule">
                <div class="avatar-row">
                  <div class="avatar-frame">
                    <div class="avatar-halo"></div>
                    <img src="{{ user.avatar_url }}" class="avatar-photo" alt="User Avatar">
                    <div class="status-dot-mini" title="ออนไลน์ (Active)"></div>
                  </div>
                  <div class="user-meta">
                    <div class="user-royal-name">{{ user.global_name or user.username }}</div>
                    <div class="user-discord-handle">
                      <span>@{{ user.username }}</span>
                      <button class="btn-copy-id" onclick="copyToClipboard('{{ user.id }}', 'Discord ID')">📋 Copy ID</button>
                    </div>
                    <div class="verified-crown-tag">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="#ffffff">
                        <path d="M2 19h20v2H2zM2 5l5 7 5-8 5 8 5-7v11H2z" />
                      </svg>
                      <span>VERIFIED MEMBER</span>
                    </div>
                  </div>
                </div>

                <div class="meta-grid">
                  <div class="meta-row">
                    <span class="meta-title">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                      ยศที่ได้รับ
                    </span>
                    <div class="role-vip-badge">
                      <span class="role-light-dot" style="background: {{ role_color or '#e5e7eb' }}; box-shadow: 0 0 10px {{ role_color or '#e5e7eb' }};"></span>
                      <span style="color: {{ role_color or '#e5e7eb' }};">{{ role_name or 'Verified Member' }}</span>
                    </div>
                  </div>
                  <div class="meta-row">
                    <span class="meta-title">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      วันที่เข้าร่วม
                    </span>
                    <span style="color: #ffffff; font-weight: 700; font-size: 0.85rem; font-family: 'JetBrains Mono', monospace;">{{ user.joined_at }}</span>
                  </div>
                </div>
              </div>

              <a href="https://discord.com/app" id="btnReturn" class="btn-godtier" onclick="playSuccessBeep()">
                <span>เข้าสู่ Discord Server ทันที</span>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div class="stats-bar">
        <div class="stat-card" style="--accent-gradient: linear-gradient(90deg, #e5e7eb, transparent);">
          <div>
            <div class="stat-label">
              <span class="live-dot"></span>
              <span>ออนไลน์ในดิสคอร์ด</span>
            </div>
            <div class="stat-value" id="count-online">
              <span class="counter-num" data-target="{{ discord_online or 0 }}">{{ discord_online or 0 }}</span>
              <span class="unit">คน (Active)</span>
            </div>
          </div>
          <div class="stat-icon-wrap" style="color: #e5e7eb;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 20a6 6 0 0 0-12 0" />
              <circle cx="12" cy="10" r="4" />
              <circle cx="12" cy="12" r="10" />
            </svg>
          </div>
        </div>

        <div class="stat-card" style="--accent-gradient: linear-gradient(90deg, #9ca3af, transparent);">
          <div>
            <div class="stat-label">สมาชิกทั้งหมด</div>
            <div class="stat-value" id="count-members">
              <span class="counter-num" data-target="{{ discord_members or 0 }}">{{ discord_members or 0 }}</span>
              <span class="unit">คน</span>
            </div>
          </div>
          <div class="stat-icon-wrap" style="color: #9ca3af;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
        </div>

        <div class="stat-card" style="--accent-gradient: linear-gradient(90deg, #ffffff, transparent);">
          <div>
            <div class="stat-label">ยืนยันตัวตนแล้ว</div>
            <div class="stat-value" style="color: #ffffff;" id="count-verified">
              <span class="counter-num" data-target="{{ total_count or 0 }}">{{ total_count or 0 }}</span>
              <span class="unit">คน</span>
            </div>
          </div>
          <div class="stat-icon-wrap" style="color: #ffffff;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
        </div>

        <div class="stat-card" style="--accent-gradient: linear-gradient(90deg, #d1d5db, transparent);">
          <div>
            <div class="stat-label">รับยศวันนี้</div>
            <div class="stat-value" style="color: #d1d5db;" id="count-today">
              <span class="counter-num" data-target="{{ today_count or 0 }}">{{ today_count or 0 }}</span>
              <span class="unit">รายการ</span>
            </div>
          </div>
          <div class="stat-icon-wrap" style="color: #d1d5db;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
        </div>
      </div>

      <div class="live-activity-card">
        <div class="activity-header">
          <div class="title-group">
            <div class="eyebrow">
              <span class="live-dot"></span>
              <span>LIVE STREAM</span>
            </div>
            <h1 class="main-title">ฟีดสดคนรับยศล่าสุด</h1>
          </div>
          <div class="header-actions" style="display: flex; align-items: center; gap: 10px;">
            <div class="badge-pill">
              <span class="live-dot"></span>
              <span>อัปเดตแบบเรียลไทม์</span>
            </div>
            <div class="badge-rounds" id="total-rounds-badge">รายการล่าสุด</div>
          </div>
        </div>

        <div class="table-toolbar">
          <div class="search-box">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-dim);">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input type="text" id="searchInput" placeholder="ค้นหาชื่อผู้ใช้ หรือ Discord ID..." oninput="filterData()">
          </div>
          <div class="filter-chips">
            <button class="chip-btn active" onclick="setRoleFilter('all', this)">ทั้งหมด</button>
            <button class="chip-btn" onclick="setRoleFilter('vip', this)">👑 VIP</button>
            <button class="chip-btn" onclick="setRoleFilter('verified', this)">⚡ Verified</button>
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th style="width: 32%;">ผู้ใช้งาน (Discord Member)</th>
                <th style="width: 28%;">Discord User ID</th>
                <th style="width: 24%;">ยศที่ได้รับ (Role Assigned)</th>
                <th style="width: 16%; text-align: right;">เวลาที่ได้รับ</th>
              </tr>
            </thead>
            <tbody id="activity-tbody"></tbody>
          </table>
        </div>
      </div>

    </div>

    {% else %}
    <!-- ============================================= -->
    <!-- PAGE 1 : LANDING / VERIFY / ERROR -->
    <!-- ============================================= -->
    <div class="page-view active" id="page-verify">

      <div class="top-action-bar">
        <div class="brand-cluster">
          <div class="brand-logo-gem">
            <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.2" stroke-dasharray="3 4"/>
              <ellipse cx="17" cy="22" rx="4" ry="4.6" fill="#ffffff"/>
              <ellipse cx="31" cy="22" rx="4" ry="4.6" fill="#ffffff"/>
              <circle cx="17" cy="22.5" r="2.1" fill="#0a0c11"/>
              <circle cx="31" cy="22.5" r="2.1" fill="#0a0c11"/>
              <circle cx="16.2" cy="21.6" r="0.8" fill="#ffffff"/>
              <circle cx="30.2" cy="21.6" r="0.8" fill="#ffffff"/>
              <line x1="12" y1="28" x2="10" y2="36" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="16" y1="28.5" x2="15" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="20" y1="28.5" x2="20" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="28" y1="28.5" x2="28" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="32" y1="28.5" x2="33" y2="37" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <line x1="36" y1="28" x2="38" y2="36" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
              <path d="M21 33 Q24 34 27 33" fill="none" stroke="#ffffff" stroke-width="1.4" stroke-linecap="round"/>
              <rect x="27" y="32.4" width="7" height="1.6" rx="0.8" fill="#ffffff"/>
              <circle cx="34.4" cy="33.2" r="0.9" fill="#ff6b3d"/>
              <path d="M35.5 31 Q37 28 36 25 Q35 22 37 19" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="brand-title">ระบบยืนยันตัวตน by.น้องเจคอปเด็กชายบริสุทธิ์</div>
            <div class="brand-sub">v1.0 · MONOCHROME EDITION</div>
          </div>
        </div>
      </div>

      <div class="portal-container" id="tiltContainer">
        <div class="hologram-glow-border">
          <div class="hologram-card">

            <div class="system-badge">
              <span class="badge-gem"></span>
              <span>ระบบยืนยันตัวตน</span>
            </div>

            {% if error_message %}
            <div class="phase-panel active">
              <div class="error-capsule">
                <div class="error-icon-wrap">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                </div>
                <h2 class="portal-headline" style="color: #f43f5e;">เกิดข้อผิดพลาดในการยืนยัน</h2>
                <p class="portal-subtext" style="color: #fda4af;">{{ error_message }}</p>
              </div>
              <a href="https://discord.com/app" class="btn-godtier" style="background: linear-gradient(135deg, #f43f5e, #e11d48); color: #ffffff; box-shadow: 0 14px 35px rgba(244, 63, 94, 0.4);">
                <span>กลับไปที่ Discord</span>
              </a>
            </div>
            {% else %}
            <!-- PHASE 1: LOADING (10 วินาที) -->
            <div class="loading-screen" id="loadingScreen">
              <div class="loading-ring">
                <div class="loading-ring-inner">
                  <svg viewBox="0 0 24 24">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <path d="m9 12 2 2 4-4" />
                  </svg>
                </div>
              </div>
              <div class="loading-text">
                กำลังเชื่อมต่อระบบ
                <span class="loading-dots">
                  <span></span><span></span><span></span>
                </span>
              </div>
              <div class="loading-subtext">INITIALIZING SECURE GATEWAY</div>
              <div class="loading-progress">
                <div class="loading-progress-bar"></div>
              </div>
            </div>

            <!-- PHASE 2: VERIFY -->
            <div class="phase-panel" id="verifyPanel" style="display: none;">
              <div class="scanner-viewport">
                <svg class="progress-svg-ring" width="170" height="170" viewBox="0 0 170 170">
                  <defs>
                    <linearGradient id="cyanPurpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#e5e7eb" />
                      <stop offset="50%" stop-color="#9ca3af" />
                      <stop offset="100%" stop-color="#f3f4f6" />
                    </linearGradient>
                  </defs>
                  <circle class="progress-circle-bg" cx="85" cy="85" r="75" />
                  <circle class="progress-circle-bar" cx="85" cy="85" r="75" />
                </svg>

                <div class="gyro-orbit orbit-outer"></div>
                <div class="gyro-orbit orbit-mid"></div>
                <div class="gyro-orbit orbit-inner"></div>
                <div class="laser-scan-line"></div>

                <div class="reactor-core">
                  <svg viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <path d="m9 12 2 2 4-4" />
                  </svg>
                </div>
              </div>

              <div class="loading-status-badge">
                <span class="live-dot"></span>
                <span>ระบบพร้อมเชื่อมต่อ Discord Gateway</span>
              </div>

              <h2 class="portal-headline">ระบบยืนยันตัวตนอัตโนมัติ</h2>
              <p class="portal-subtext">
                by.น้องเจคอปเด็กชายบริสุทธิ์<br>
                กรุณากดปุ่มด้านล่างเพื่อรับยศทันที
              </p>

              <a href="{{ button_url | default('https://discord.com/app') }}" class="btn-godtier">
                <span>ยืนยันตัวตนผ่าน Discord</span>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
                </svg>
              </a>
            </div>
            {% endif %}

          </div>
        </div>
      </div>

    </div>
    {% endif %}

  </div>

  <div class="floating-music-player" id="musicPlayerHud">
    <div class="music-disc-icon" id="musicDisc" onclick="toggleMusic()">
      <svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
    </div>
    <div class="music-track-meta">
      <div class="music-track-name">MEYOU - อีกแล้ว ft. Jigsaw</div>
      <div class="music-track-status">
        <span id="musicStateLabel">กำลังเตรียมเพลง...</span>
        <div class="eq-wave-group paused" id="eqWaves">
          <div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div>
        </div>
      </div>
    </div>
    <div class="music-controls-mini">
      <button class="btn-music-toggle" id="btnMusicPlayPause" onclick="toggleMusic()">
        <svg id="musicBtnIcon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      </button>
    </div>
  </div>

  <div id="toast-notice">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e5e7eb" stroke-width="2.4"><polyline points="20 6 9 17 4 12"/></svg>
    <span id="toast-text">คัดลอกสำเร็จ!</span>
  </div>

  <audio id="bgAudio" loop preload="auto" crossorigin="anonymous"></audio>

  <script>
    // =========================================================
    // AUDIO PLAYER
    // =========================================================
    const AUDIO_URL = "{{ audio_url | default('https://files.catbox.moe/fyvd9o.mp3') }}";
    const audio = document.getElementById('bgAudio');
    audio.src = AUDIO_URL;
    audio.loop = true;
    audio.volume = 0.75;
    audio.muted = true;

    let isPlaying = false;
    let userHasInteracted = false;

    function startSilentPlay() {
      audio.muted = true;
      audio.volume = 0;
      const p = audio.play();
      if (p !== undefined) {
        p.then(() => { isPlaying = true; updateMusicUI(true); })
         .catch(err => console.warn("Autoplay (muted) blocked:", err.name));
      }
    }

    function unlockAudio() {
      if (userHasInteracted) return;
      userHasInteracted = true;
      try {
        audio.muted = false;
        audio.volume = 0.75;
        if (audio.paused) audio.play().catch(() => {});
        isPlaying = true;
        updateMusicUI(true);
      } catch (e) {}
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', startSilentPlay);
    } else {
      startSilentPlay();
    }
    audio.addEventListener('loadedmetadata', () => { if (!isPlaying) startSilentPlay(); }, { once: true });
    audio.addEventListener('canplay', () => { if (!isPlaying) startSilentPlay(); }, { once: true });

    window.addEventListener('pointerdown', unlockAudio, { once: true, passive: true });
    window.addEventListener('keydown', unlockAudio, { once: true });

    function toggleMusic() {
      if (!userHasInteracted) unlockAudio();
      if (audio.paused) {
        audio.muted = false; audio.volume = 0.75;
        audio.play().catch(() => {});
        showToast("▶️ เล่นเพลง");
      } else {
        audio.pause();
        showToast("⏸️ พักเพลง");
      }
    }

    audio.addEventListener('play', () => { isPlaying = true; updateMusicUI(true); });
    audio.addEventListener('pause', () => { isPlaying = false; updateMusicUI(false); });

    function updateMusicUI(playing) {
      const disc = document.getElementById('musicDisc');
      const label = document.getElementById('musicStateLabel');
      const eq = document.getElementById('eqWaves');
      const btnIcon = document.getElementById('musicBtnIcon');
      if (playing) {
        if (disc) disc.classList.remove('paused');
        if (eq) eq.classList.remove('paused');
        if (label) label.textContent = 'กำลังเล่นเพลง';
        if (btnIcon) btnIcon.innerHTML = `<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>`;
      } else {
        if (disc) disc.classList.add('paused');
        if (eq) eq.classList.add('paused');
        if (label) label.textContent = 'หยุดชั่วคราว';
        if (btnIcon) btnIcon.innerHTML = `<polygon points="5 3 19 12 5 21 5 3"/>`;
      }
    }

    // =========================================================
    // SFX + Toast + Copy
    // =========================================================
    let sfxCtx = null;
    function getSfxCtx() {
      if (!sfxCtx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        sfxCtx = new AC();
      }
      if (sfxCtx.state === 'suspended') sfxCtx.resume();
      return sfxCtx;
    }

    function playSuccessBeep() {
      try {
        const ctx = getSfxCtx();
        const osc = ctx.createOscillator(); const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(); osc.stop(ctx.currentTime + 0.35);
      } catch (e) {}
    }

    function playNotificationTone() {
      try {
        const ctx = getSfxCtx();
        const osc = ctx.createOscillator(); const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(); osc.stop(ctx.currentTime + 0.25);
      } catch (e) {}
    }

    function showToast(msg) {
      const t = document.getElementById('toast-notice');
      document.getElementById('toast-text').textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2400);
    }

    function copyToClipboard(text, label) {
      navigator.clipboard.writeText(text).then(() => {
        playNotificationTone();
        showToast(`คัดลอก ${label}: ${text} แล้ว! 📋`);
      }).catch(() => showToast(`คัดลอก: ${text}`));
    }

    // =========================================================
    // CURSOR + TILT + STARFIELD
    // =========================================================
    const cursorGlow = document.getElementById('cursor-glow');
    document.addEventListener('mousemove', (e) => {
      cursorGlow.style.left = e.clientX + 'px';
      cursorGlow.style.top = e.clientY + 'px';
    });

    const tiltContainer = document.getElementById('tiltContainer');
    const card = tiltContainer ? tiltContainer.querySelector('.hologram-card') : null;
    if (card) {
      document.addEventListener('mousemove', (e) => {
        const { innerWidth, innerHeight } = window;
        const x = (e.clientX - innerWidth / 2) / (innerWidth / 2);
        const y = (e.clientY - innerHeight / 2) / (innerHeight / 2);
        card.style.transform = `rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateY(-2px)`;
      });
      document.addEventListener('mouseleave', () => {
        card.style.transform = 'rotateY(0deg) rotateX(0deg) translateY(0)';
      });
    }

    const starCanvas = document.getElementById('stars-canvas');
    const starCtx = starCanvas.getContext('2d');
    let stars = [];
    function resizeStarfield() {
      starCanvas.width = window.innerWidth;
      starCanvas.height = window.innerHeight;
      stars = Array.from({ length: 65 }, () => ({
        x: Math.random() * starCanvas.width,
        y: Math.random() * starCanvas.height,
        size: Math.random() * 2 + 0.6,
        speed: Math.random() * 0.35 + 0.1,
        alpha: Math.random() * 0.7 + 0.3
      }));
    }
    window.addEventListener('resize', resizeStarfield);
    resizeStarfield();
    function renderStarfield() {
      starCtx.clearRect(0, 0, starCanvas.width, starCanvas.height);
      starCtx.fillStyle = '#ffffff';
      stars.forEach(s => {
        s.y -= s.speed;
        if (s.y < 0) s.y = starCanvas.height;
        starCtx.globalAlpha = s.alpha;
        starCtx.beginPath();
        starCtx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        starCtx.fill();
      });
      requestAnimationFrame(renderStarfield);
    }
    renderStarfield();

    // =========================================================
    // CELEBRATION FX
    // =========================================================
    const fxCanvas = document.getElementById('fx-canvas');
    const fxCtx = fxCanvas ? fxCanvas.getContext('2d') : null;
    let particles = [];
    function fireCelebration() {
      if (!fxCanvas || !card) return;
      fxCanvas.width = card.offsetWidth;
      fxCanvas.height = card.offsetHeight;
      particles = [];
      const colors = ['#e5e7eb', '#9ca3af', '#f3f4f6', '#d1d5db', '#ffffff', '#6b7280'];
      for (let i = 0; i < 65; i++) {
        particles.push({
          x: fxCanvas.width / 2, y: fxCanvas.height * 0.36,
          vx: (Math.random() - 0.5) * 14, vy: (Math.random() - 0.75) * 15,
          size: Math.random() * 6 + 2.5,
          color: colors[Math.floor(Math.random() * colors.length)],
          gravity: 0.28, alpha: 1,
          rot: Math.random() * 360,
          rotSpeed: (Math.random() - 0.5) * 12
        });
      }
    }
    function renderFX() {
      if (!fxCtx) return;
      fxCtx.clearRect(0, 0, fxCanvas.width, fxCanvas.height);
      particles.forEach((p, idx) => {
        p.x += p.vx; p.y += p.vy; p.vy += p.gravity;
        p.alpha -= 0.013; p.rot += p.rotSpeed;
        if (p.alpha > 0) {
          fxCtx.save();
          fxCtx.globalAlpha = p.alpha;
          fxCtx.translate(p.x, p.y);
          fxCtx.rotate(p.rot * Math.PI / 180);
          fxCtx.fillStyle = p.color;
          fxCtx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.3);
          fxCtx.restore();
        } else { particles.splice(idx, 1); }
      });
      if (particles.length > 0) requestAnimationFrame(renderFX);
    }

    // =========================================================
    // LIVE ACTIVITY TABLE
    // =========================================================
    let activityData = [];
    let currentFilter = 'all';
    let searchQuery = '';

    function setRoleFilter(filter, btn) {
      currentFilter = filter;
      document.querySelectorAll('.filter-chips .chip-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      renderTable();
    }

    function filterData() {
      searchQuery = document.getElementById('searchInput').value.trim().toLowerCase();
      renderTable();
    }

    function renderTable() {
      const tbody = document.getElementById('activity-tbody');
      if (!tbody) return;
      tbody.innerHTML = '';

      const filtered = activityData.filter(row => {
        const matchesSearch = row.user.toLowerCase().includes(searchQuery) ||
                              row.handle.toLowerCase().includes(searchQuery) ||
                              row.id.includes(searchQuery);
        if (!matchesSearch) return false;
        if (currentFilter === 'vip') return row.isVIP;
        if (currentFilter === 'verified') return !row.isVIP;
        return true;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim); padding: 36px;">🔍 ยังไม่มีข้อมูล</td></tr>`;
        return;
      }

      filtered.forEach((row) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>
            <div class="user-cell">
              <img src="${row.avatar || 'https://cdn.discordapp.com/embed/avatars/0.png'}" class="user-avatar-circle" alt="Avatar">
              <div>
                <div class="user-title">${row.user}</div>
                <div class="user-sub">@${row.handle}</div>
              </div>
            </div>
          </td>
          <td>
            <span class="id-badge" onclick="copyToClipboard('${row.id}', 'Discord ID')">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              ${row.id}
            </span>
          </td>
          <td>
            <div class="role-tag-badge" style="border-color: ${row.roleColor}40;">
              <span class="role-dot-glow" style="background: ${row.roleColor}; box-shadow: 0 0 12px ${row.roleColor};"></span>
              <span style="color: ${row.roleColor}; font-weight: 700;">${row.role}</span>
            </div>
          </td>
          <td style="text-align: right;" class="time-text">${row.time}</td>
        `;
        tbody.appendChild(tr);
      });

      const badge = document.getElementById('total-rounds-badge');
      if (badge) badge.textContent = `${activityData.length} รายการล่าสุด`;
    }

    async function pollLiveActivity() {
      try {
        const res = await fetch('/api/live_activity');
        if (res.ok) {
          const data = await res.json();
          if (data.verified_stats) {
            const totalEl = document.querySelector('#count-verified .counter-num');
            if (totalEl) totalEl.textContent = Number(data.verified_stats.total || 0).toLocaleString();
            const todayEl = document.querySelector('#count-today .counter-num');
            if (todayEl) todayEl.textContent = Number(data.verified_stats.today || 0).toLocaleString();
          }
          if (data.discord_stats) {
            const onlineEl = document.querySelector('#count-online .counter-num');
            if (onlineEl) onlineEl.textContent = Number(data.discord_stats.online || 0).toLocaleString();
            const memEl = document.querySelector('#count-members .counter-num');
            if (memEl) memEl.textContent = Number(data.discord_stats.total_members || 0).toLocaleString();
          }
          if (data.users && data.users.length > 0) {
            activityData = data.users.map(u => {
              const isV = (u.role_name || '').includes('VIP');
              return {
                user: u.global_name || u.username,
                handle: u.username,
                id: u.user_id,
                avatar: u.avatar_url,
                role: u.role_name || 'Verified Member',
                roleColor: u.role_color || '#e5e7eb',
                time: u.verified_at,
                isVIP: isV
              };
            });
            renderTable();
          }
        }
      } catch (e) {}
    }

    {% if user %}
    setInterval(pollLiveActivity, 4000);
    pollLiveActivity();
    renderTable();
    setTimeout(() => { fireCelebration(); renderFX(); }, 300);
    {% endif %}

    // =========================================================
    // LOADING → VERIFY TRANSITION (10 วินาที)
    // =========================================================
    {% if not user and not error_message %}
    (function initLoadingFlow() {
      const loadingScreen = document.getElementById('loadingScreen');
      const verifyPanel = document.getElementById('verifyPanel');

      if (!loadingScreen || !verifyPanel) return;

      // หลัง 10 วิ → ซ่อน loading, โชว์ verify
      setTimeout(() => {
        loadingScreen.classList.add('hide');

        // หลัง fade out 0.5 วิ → โชว์ verify
        setTimeout(() => {
          loadingScreen.style.display = 'none';
          verifyPanel.style.display = 'block';
          verifyPanel.classList.add('active');

          // เล่น beep เบาๆ ตอน transition
          try {
            const ctx = getSfxCtx();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(440, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.1);
            gain.gain.setValueAtTime(0.06, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            osc.connect(gain); gain.connect(ctx.destination);
            osc.start(); osc.stop(ctx.currentTime + 0.3);
          } catch (e) {}
        }, 500);
      }, 10000);
    })();
    {% endif %}
  </script>
</body>

</html>"""

ERROR_TEMPLATE = HTML_TEMPLATE
ADMIN_STATS_TEMPLATE = HTML_TEMPLATE

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "stifshop_secret_key_change_me")

@app.route('/favicon.ico')
def favicon():
    return '', 204

def _role_color_hex(color_int):
    if not color_int:
        return "#06b6d4"
    return f"#{color_int:06x}"

def get_role_info(guild_id, role_id):
    try:
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
        )
        resp.raise_for_status()
        for role in resp.json():
            if str(role.get("id")) == str(role_id):
                return {
                    "name": role.get("name"),
                    "color": _role_color_hex(role.get("color")),
                }
    except Exception as e:
        logger.error(f"ดึงข้อมูลยศไม่สำเร็จ: {e}")
    return {"name": "Verified", "color": "#06b6d4"}

def send_webhook_log(webhook_url, title, description, color, avatar_url=None,
                     author_name=None, fields=None, footer_text="Verification Gateway • ระบบยืนยันตัวตน"):
    if not webhook_url or webhook_url.startswith("ใส่_"):
        logger.warning("[webhook] skipped: no url configured")
        return
    try:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if author_name:
            embed["author"] = {"name": author_name}
            if avatar_url:
                embed["author"]["icon_url"] = avatar_url

        if avatar_url:
            embed["thumbnail"] = {"url": avatar_url}

        if fields:
            embed["fields"] = fields

        if footer_text:
            embed["footer"] = {"text": footer_text}

        payload = {"embeds": [embed]}
        resp = requests.post(webhook_url, json=payload, timeout=10)

        if resp.status_code != 204:
            logger.error(f"[webhook] FAILED status={resp.status_code} body={resp.text[:300]}")
        else:
            logger.info(f"[webhook] sent ok -> {title}")

    except Exception as e:
        logger.error(f"[webhook] exception: {e}")

@app.route("/")
def home():
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
    )
    return render_template_string(
        HTML_TEMPLATE,
        title="ระบบยืนยันตัวตน",
        button_url=discord_login_url,
        user=None,
        audio_url=AUDIO_URL,
        background_image=BACKGROUND_IMAGE,
    )

@app.route("/callback", strict_slashes=False)
def callback():
    code = request.args.get("code")
    if not code:
        return render_template_string(ERROR_TEMPLATE, error_message="ไม่พบรหัสยืนยันตัวตนจาก Discord กรุณาลองใหม่อีกครั้ง", audio_url=AUDIO_URL, background_image=BACKGROUND_IMAGE)

    try:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")

        if not access_token:
            logger.error("❌ ไม่สามารถขอ Access Token จาก Discord ได้ (OAuth token exchange failed)")
            send_webhook_log(WEBHOOK_ERROR, "❌ ยืนยันตัวตนล้มเหลว", "ไม่สามารถขอ Access Token จาก Discord ได้", 16711680)
            return render_template_string(ERROR_TEMPLATE, error_message="เกิดข้อผิดพลาดในการขอ Token จากระบบ Discord", audio_url=AUDIO_URL, background_image=BACKGROUND_IMAGE)

        user_data = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
        user_id = user_data.get("id")
        username = user_data.get("username")
        global_name = user_data.get("global_name")
        avatar_id = user_data.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

        conn = sqlite3.connect("verifications.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM verified_users WHERE user_id = ?", (user_id,))
        already_verified = cursor.fetchone()
        conn.close()

        timestamp = ((int(user_id) >> 22) + 1420070400000) / 1000
        joined_dt = datetime.datetime.utcfromtimestamp(timestamp)
        joined_date_thai = thai_date(joined_dt)

        user_info = {
            "id": user_id,
            "username": username,
            "global_name": global_name,
            "avatar_url": avatar_url,
            "joined_at": joined_date_thai
        }

        role_info = get_role_info(GUILD_ID, ROLE_ID)

        bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
        add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
        r = requests.put(add_role_url, headers=bot_headers)

        if r.status_code not in [200, 204]:
            logger.error(f"❌ เพิ่มยศไม่สำเร็จ สำหรับ {username} ({user_id}) — API status {r.status_code}")
            send_webhook_log(WEBHOOK_ERROR, "❌ เพิ่มยศไม่สำเร็จ", f"ผู้ใช้: {username} (`{user_id}`)\nAPI Error Code: {r.status_code}", 16711680)
        else:
            logger.info(f"✅ {username} ({user_id}) ยืนยันตัวตนสำเร็จ — ได้รับยศ {role_info['name']}")

            if not already_verified:
                conn = sqlite3.connect("verifications.db")
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO verified_users
                       (user_id, username, global_name, avatar_url, verified_at, role_name, role_color)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        username,
                        global_name,
                        avatar_url,
                        str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        role_info["name"],
                        role_info["color"],
                    )
                )
                conn.commit()
                conn.close()

                send_webhook_log(
                    WEBHOOK_SUCCESS,
                    "`✅` **มีผู้ยืนยันตัวตนสำเร็จ**",
                    f"- **ผู้ใช้งาน:** **{global_name or username}** (`@{username}`)\n- **ID:** **{user_id}**\n- **ยศที่ได้รับ:** **{role_info['name']}**",
                    2318169,
                    avatar_url=avatar_url,
                )
            else:
                logger.info(f"ℹ️ {username} ({user_id}) ยืนยันตัวตนซ้ำ (มีอยู่ในระบบแล้ว)")
                send_webhook_log(
                    WEBHOOK_SUCCESS,
                    "`🔁` **มีผู้ยืนยันตัวตนซ้ำ**",
                    f"- **ผู้ใช้งาน:** **{global_name or username}** (`@{username}`)\n- **ID:** **{user_id}**\n- **ยศที่ได้รับ:** **{role_info['name']}**\n- หมายเหตุ: ผู้ใช้นี้เคยยืนยันตัวตนไปแล้วก่อนหน้านี้",
                    3447003,
                    avatar_url=avatar_url,
                )

        disc_stats = get_discord_guild_stats()
        conn = sqlite3.connect("verifications.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM verified_users")
        total_count = cursor.fetchone()[0]
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM verified_users WHERE verified_at LIKE ?", (f"{today_str}%",))
        today_count = cursor.fetchone()[0]
        conn.close()

        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            user=user_info,
            role_name=role_info["name"],
            role_color=role_info["color"],
            audio_url=AUDIO_URL,
            background_image=BACKGROUND_IMAGE,
            discord_online=disc_stats.get("online", 0),
            discord_members=disc_stats.get("total_members", 0),
            total_count=total_count,
            today_count=today_count,
        )

    except Exception as e:
        logger.error(f"💥 Exception ในหน้า /callback: {e}")
        send_webhook_log(WEBHOOK_ERROR, "💥 ระบบเกิดข้อผิดพลาดรุนแรง (Exception)", f"Error details: `{str(e)}`", 16711680)
        return render_template_string(ERROR_TEMPLATE, error_message="เกิดข้อผิดพลาดบางประการจากระบบเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้งในภายหลัง", audio_url=AUDIO_URL, background_image=BACKGROUND_IMAGE)

def get_discord_guild_stats():
    """ดึงจำนวนคนออนในดิสคอร์ด และจำนวนสมาชิกทั้งหมด"""
    try:
        guild = bot.get_guild(int(GUILD_ID))
        if guild:
            online_count = sum(1 for m in guild.members if m.status != discord.Status.offline)
            member_count = guild.member_count or len(guild.members)
            if online_count > 0:
                return {"online": online_count, "total_members": member_count, "name": guild.name}

        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}?with_counts=true",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=4
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "online": data.get("approximate_presence_count", 0),
                "total_members": data.get("approximate_member_count", 0),
                "name": data.get("name", "Discord Server")
            }
    except Exception as e:
        logger.error(f"Error fetching discord stats: {e}")
    return {"online": 0, "total_members": 0, "name": "Discord Server"}

@app.route("/api/live_activity")
def api_live_activity():
    try:
        conn = sqlite3.connect("verifications.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM verified_users")
        total_count = cursor.fetchone()[0]

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM verified_users WHERE verified_at LIKE ?", (f"{today_str}%",))
        today_count = cursor.fetchone()[0]

        cursor.execute(
            """SELECT user_id, username, global_name, avatar_url, verified_at, role_name, role_color
               FROM verified_users ORDER BY verified_at DESC LIMIT 50"""
        )
        raw_users = cursor.fetchall()
        conn.close()

        users_list = []
        for u in raw_users:
            users_list.append({
                "user_id": u[0],
                "username": u[1],
                "global_name": u[2],
                "avatar_url": u[3],
                "verified_at": u[4],
                "role_name": u[5],
                "role_color": u[6],
            })

        disc_stats = get_discord_guild_stats()
        return jsonify({
            "discord_stats": disc_stats,
            "verified_stats": {"total": total_count, "today": today_count},
            "users": users_list
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/stats")
def admin_stats():
    admin_auth_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri=https%3A%2F%2Fstifshop.up.railway.app%2Fadmin/login&response_type=code&scope=identify%20guilds"
    )

    if not session.get("is_admin"):
        return redirect(admin_auth_url)

    conn = sqlite3.connect("verifications.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM verified_users")
    total_count = cursor.fetchone()[0]

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM verified_users WHERE verified_at LIKE ?", (f"{today_str}%",))
    today_count = cursor.fetchone()[0]

    cursor.execute(
        """SELECT user_id, username, global_name, avatar_url, verified_at, role_name, role_color
           FROM verified_users ORDER BY verified_at DESC LIMIT 50"""
    )
    users = cursor.fetchall()
    conn.close()

    disc_stats = get_discord_guild_stats()

    return render_template_string(
        ADMIN_STATS_TEMPLATE,
        total_count=total_count,
        today_count=today_count,
        users=users,
        discord_online=disc_stats.get("online", 0),
        discord_members=disc_stats.get("total_members", 0),
        logo_url=BRAND_LOGO_URL,
        audio_url=AUDIO_URL,
        background_image=BACKGROUND_IMAGE,
    )

@app.route("/admin/logs")
def admin_logs():
    if not session.get("is_admin"):
        return jsonify({"error": "unauthorized"}), 403
    return jsonify({"logs": list(log_buffer)})

@app.route("/admin/login", strict_slashes=False)
def admin_login():
    code = request.args.get("code")
    if not code:
        return redirect("/admin/stats")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://stifshopv2.up.railway.app/admin/login",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    access_token = token_resp.json().get("access_token")

    if access_token:
        guilds_resp = requests.get("https://discord.com/api/users/@me/guilds", headers={"Authorization": f"Bearer {access_token}"})
        if guilds_resp.status_code == 200:
            for g in guilds_resp.json():
                if str(g.get("id")) == str(GUILD_ID):
                    permissions = int(g.get("permissions", 0))
                    if (permissions & 0x8) == 0x8 or g.get("owner"):
                        session["is_admin"] = True
                        return redirect("/admin/stats")

    logger.warning("⚠️ มีความพยายามเข้าหน้า admin โดยไม่มีสิทธิ์ (ไม่ใช่ผู้ดูแลเซิร์ฟเวอร์)")
    return render_template_string(ERROR_TEMPLATE, error_message="คุณไม่มีสิทธิ์เข้าถึงหน้าแดชบอร์ดแอดมิน (ต้องเป็นผู้ดูแลเซิร์ฟเวอร์เท่านั้น)", audio_url=AUDIO_URL, background_image=BACKGROUND_IMAGE)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="ยืนยันตัวตนเข้าดิส",
                url=f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=https%3A%2F%2Fnongflexv1.up.railway.app%2Fcallback&scope=openid+gdm.join+identify",
                style=discord.ButtonStyle.link,
                emoji="<a:emoji_125:1283873278129213471>",
            )
        )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    activity = discord.Streaming(name="ระบบรับยศออโต้ 24 ชม.", url="https://www.twitch.tv/Jxycop_x")
    await bot.change_presence(status=discord.Status.idle, activity=activity)

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

@bot.tree.command(name="setup", description="ส่งหน้าต่างยืนยันตัวตนสำหรับสมาชิก")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ VERIFICATION SYSTEM",
        description=f"🤖 **ระบบรับยศอัตโนมัติ 24 ชั่วโมง**\n\n"
                    f"📥 กดปุ่มด้านล่างเพื่อยืนยันตัวตนและรับยศ <@&{ROLE_ID}> ทันที",
        color=discord.Color(0x6366f1)
    )
    embed.set_footer(
        text="VERIFICATION SYSTEM • by.น้องเจคอปเด็กชายบริสุทธิ์",
        icon_url='https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif'
    )
    embed.set_thumbnail(url='https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif')
    await interaction.response.send_message("✅ สร้างปุ่มยืนยันตัวตนสำเร็จ!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

def run_web():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    bot.run(BOT_TOKEN)
