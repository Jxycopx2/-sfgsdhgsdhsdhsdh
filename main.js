require('dotenv').config();
const express = require('express');
const session = require('express-session');
const axios = require('axios');
const Database = require('better-sqlite3');
const { SimpleShardingStrategy } = require('@discordjs/ws');
const {
    Client,
    GatewayIntentBits,
    Events,
    REST,
    Routes,
    SlashCommandBuilder,
    PermissionFlagsBits,
    ActivityType,
} = require('discord.js');

const BOT_TOKEN = process.env.BOT_TOKEN;
const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT_URI = process.env.REDIRECT_URI || 'https://nongflexv2.up.railway.app/callback';
const GUILD_ID = process.env.GUILD_ID || '1554125892329017366';
const ROLE_ID = process.env.ROLE_ID || '1554203720965689408';
const PORT = process.env.PORT || 5000;
const SESSION_SECRET = process.env.FLASK_SECRET_KEY || 'change_me_please';

const WEBHOOK_SUCCESS = process.env.WEBHOOK_SUCCESS || 'https://canary.discord.com/api/webhooks/1554209848982376568/P1C1eXW37m9rez3KwSm7WSlZJO3dXhW5-TdVBCpR4BZbKrGwFuMnMcWHLjaNxDJ7X91k';
const WEBHOOK_ERROR = process.env.WEBHOOK_ERROR || 'https://canary.discord.com/api/webhooks/1554209851997954130/Yb-juLPFnC3HmVftMZ0klEB9OJdKzlWZ2ZdkN4sDyVw6S_ZYK--bSwm2jo_qi6uyG6mZ';

const AUDIO_URL = 'https://files.catbox.moe/fyvd9o.mp3';
const BACKGROUND_IMAGE = 'https://files.catbox.moe/3jmrta.jpg';

if (!BOT_TOKEN || !CLIENT_SECRET || !CLIENT_ID) {
    console.error('❌ กรุณาตั้งค่า BOT_TOKEN, CLIENT_ID, CLIENT_SECRET');
    process.exit(1);
}

const THAILAND_OFFSET_MS = 7 * 60 * 60 * 1000;
function nowTH() { return new Date(Date.now() + THAILAND_OFFSET_MS); }
function formatThaiDateTime(date = null) {
    const d = date || nowTH();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}
function todayTH() { return formatThaiDateTime().split(' ')[0]; }

const THAI_MONTHS = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
function thaiDate(date = null) {
    const d = date || nowTH();
    return `${d.getUTCDate()} ${THAI_MONTHS[d.getUTCMonth() + 1]} ${d.getUTCFullYear() + 543}`;
}

const db = new Database('verifications.db');
db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS verified_users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    global_name TEXT,
    avatar_url TEXT,
    verified_at TEXT,
    role_name TEXT,
    role_color TEXT
  )
`);

const cols = db.prepare(`PRAGMA table_info(verified_users)`).all().map(c => c.name);
if (!cols.includes('role_name')) db.exec(`ALTER TABLE verified_users ADD COLUMN role_name TEXT`);
if (!cols.includes('role_color')) db.exec(`ALTER TABLE verified_users ADD COLUMN role_color TEXT`);

console.log('✅ SQLite ready: verifications.db');

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { maxAge: 1000 * 60 * 60 * 24 },
}));

app.get('/favicon.ico', (req, res) => res.status(204).end());
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok', uptime: process.uptime() });
});

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildPresences,
    ],
    ws: {
        buildStrategy: (manager) => {
            manager.options.identifyProperties = {
                os: 'iOS',
                browser: 'Discord iOS',
                device: 'iOS',
            };
            return new SimpleShardingStrategy(manager);
        },
    },
});

function buildVerifyMessage() {
    const setEmoji = '<a:3899gift:1543925620394958978>';
    const parseEmoji = (str) => {
        const match = str.match(/^<(a?):(\w+):(\d+)>$/);
        if (!match) return null;
        return { name: match[2], id: match[3], animated: match[1] === 'a' };
    };
    const buttonEmoji = parseEmoji(setEmoji);

    const verifyUrl =
        `https://discord.com/oauth2/authorize?client_id=${CLIENT_ID}` +
        `&response_type=code` +
        `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
        `&scope=openid%20identify%20guilds%20guilds.join`;

    const bigImageUrl = 'https://media.discordapp.net/attachments/1552288828910473267/1554483641625608324/1790688171573.jpg?ex=6abd0d35&is=6abbbbb5&hm=8a97fa21b45fe2abd17a115976b30476997391a140d5dee0d4c55e3bfb77b991&=&format=webp';

    return {
        flags: 32768,
        components: [
            {
                type: 17,
                accent_color: 0x000000,
                components: [
                    {
                        type: 9,
                        components: [{ type: 10, content: '# \`⚙️\` **VERIFICATION SYSTEM**\n- **ระบบรับยศอัตโนมัติ 24 ชั่วโมง**' }],
                        accessory: { type: 11, media: { url: 'https://i.pinimg.com/736x/f3/bb/93/f3bb93abfa0a228fd9398df264470d5f.jpg' } }
                    },
                    { type: 14, divider: true, spacing: 1 },
                    {
                        type: 10,
                        content:
                            `- **กดปุ่มด้านล่างเพื่อยืนยันตัวตน**\n\n` +
                            `-  \`🔔\` **รับยศ** <@&${ROLE_ID}> **ทันที**\n\n` +
                            '- \`⚠️\` **ระบบปลอดภัย ทำงาน 24 ชม.**'
                    },
                    { type: 12, items: [{ media: { url: bigImageUrl }, description: 'Verification Banner' }] },
                    { type: 14, divider: false, spacing: 2 },
                    {
                        type: 1,
                        components: [{
                            type: 2,
                            style: 5,
                            label: 'ยืนยันตัวตนเข้าดิส',
                            emoji: buttonEmoji,
                            emoji_position: 'right',
                            url: verifyUrl
                        }]
                    }
                ]
            }
        ]
    };
}


function roleColorHex(colorInt) {
    if (!colorInt) return '#141414';
    return '#' + colorInt.toString(16).padStart(6, '0');
}

async function getRoleInfo(guildId, roleId) {
    try {
        const resp = await axios.get(
            `https://discord.com/api/v10/guilds/${guildId}/roles`,
            { headers: { Authorization: `Bot ${BOT_TOKEN}` } }
        );
        const role = resp.data.find(r => String(r.id) === String(roleId));
        if (role) return { name: role.name, color: roleColorHex(role.color) };
    } catch (err) {
        console.error('❌ getRoleInfo error:', err.message);
    }
    return { name: 'Verified', color: '#06b6d4' };
}

async function sendWebhookLog(webhookUrl, title, description, color, avatarUrl = null) {
    if (!webhookUrl) return;
    try {
        const embed = {
            title, description, color,
            timestamp: new Date().toISOString(),
            footer: { text: '• ระบบยืนยันตัวตน' }
        };
        if (avatarUrl) embed.thumbnail = { url: avatarUrl };
        const resp = await axios.post(webhookUrl, { embeds: [embed] }, { timeout: 10000 });
        if (resp.status !== 204) console.error(`[webhook] FAILED status=${resp.status}`);
        else console.log(`[webhook] sent ok -> ${title}`);
    } catch (err) {
        console.error('[webhook] exception:', err.message);
    }
}

async function getDiscordGuildStats() {
    try {
        const guild = client.guilds.cache.get(GUILD_ID);
        if (guild) {
            const online = guild.members.cache.filter(m => m.presence && m.presence.status !== 'offline').size;
            const total = guild.memberCount;
            if (online > 0) return { online, total_members: total, name: guild.name };
        }
        const resp = await axios.get(
            `https://discord.com/api/v10/guilds/${GUILD_ID}?with_counts=true`,
            { headers: { Authorization: `Bot ${BOT_TOKEN}` }, timeout: 4000 }
        );
        return {
            online: resp.data.approximate_presence_count || 0,
            total_members: resp.data.approximate_member_count || 0,
            name: resp.data.name || 'Discord Server'
        };
    } catch (err) {
        console.error('Error fetching discord stats:', err.message);
        return { online: 0, total_members: 0, name: 'Discord Server' };
    }
}

function renderHTML(opts) {
    const {
        title = 'ระบบยืนยันตัวตน',
        user = null,
        roleName = '',
        roleColor = '',
        buttonUrl = '#',
        errorMessage = '',
        stats = {},
        users = []
    } = opts;

    const escape = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));

    const roleNameSafe = escape(roleName || 'Verified Member');
    const roleColorSafe = escape(roleColor || '#e5e7eb');
    const errorSafe = escape(errorMessage);
    const totalCount = stats.total_count || 0;
    const todayCount = stats.today_count || 0;
    const discordOnline = stats.discord_online || 0;
    const discordMembers = stats.discord_members || 0;

    const usersList = users.map(u => ({
        user: u.global_name || u.username,
        handle: u.username,
        id: u.user_id,
        avatar: u.avatar_url,
        role: u.role_name || 'Verified Member',
        roleColor: u.role_color || '#e5e7eb',
        time: u.verified_at
    }));

    const usersJson = JSON.stringify(usersList).replace(/</g, '\\u003c');
    const isUser = !!user;

    return `<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>${escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg-dark:#04060f;--card-surface:rgba(12,17,34,.76);--table-header-bg:rgba(8,12,24,.8);--row-bg:rgba(14,20,40,.65);--row-hover:rgba(24,35,70,.92);--text-pure:#fff;--text-sub:#94a3b8;--text-dim:#54657e;--border-soft:rgba(255,255,255,.08)}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
::selection{background:#6366f1;color:#fff}
html,body{min-height:100dvh;background:var(--bg-dark);font-family:'Plus Jakarta Sans','Kanit',sans-serif;color:var(--text-pure);overflow-x:hidden}
body{padding:clamp(24px,4vw,56px) clamp(16px,3.5vw,32px);display:flex;justify-content:center;position:relative;perspective:1400px}
#cursor-glow{position:fixed;width:650px;height:650px;border-radius:50%;background:radial-gradient(circle,rgba(200,200,200,.1) 0%,rgba(150,150,150,.05) 35%,transparent 70%);pointer-events:none;transform:translate(-50%,-50%);z-index:1;will-change:left,top}
#stars-canvas{position:fixed;inset:0;pointer-events:none;z-index:0}
.aurora-wrap{position:fixed;inset:0;pointer-events:none;z-index:1;overflow:hidden;background-image:linear-gradient(rgba(0,0,0,.55),rgba(0,0,0,.8)),url('${BACKGROUND_IMAGE}');background-size:cover;background-position:center;background-repeat:no-repeat;background-attachment:fixed;filter:grayscale(.7) contrast(1.1) brightness(.9)}
.smoke-layer{position:fixed;inset:0;z-index:1;pointer-events:none;background:radial-gradient(ellipse 400px 800px at 15% 90%,rgba(200,200,200,.06) 0%,transparent 60%),radial-gradient(ellipse 500px 900px at 85% 95%,rgba(180,180,180,.05) 0%,transparent 65%);animation:smokeFloat 18s ease-in-out infinite alternate}
@keyframes smokeFloat{0%{transform:translateY(0) scale(1);opacity:.7}50%{transform:translateY(-30px) scale(1.05);opacity:1}100%{transform:translateY(-60px) scale(1.1);opacity:.6}}
.cyber-grid{position:fixed;inset:0;z-index:2;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);background-size:48px 48px;opacity:.9;mask-image:radial-gradient(circle at center,black 40%,transparent 88%);-webkit-mask-image:radial-gradient(circle at center,black 40%,transparent 88%)}
.vignette-overlay{position:fixed;inset:0;z-index:3;pointer-events:none;background:radial-gradient(ellipse at center,transparent 35%,rgba(0,0,0,.65) 100%);mix-blend-mode:multiply}
.app-layout{position:relative;z-index:10;width:100%;max-width:1240px;display:flex;flex-direction:column;align-items:center;gap:36px}
.top-action-bar{width:100%;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding:10px 18px;background:rgba(12,17,34,.55);border:1px solid var(--border-soft);border-radius:50px;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);box-shadow:0 10px 30px rgba(0,0,0,.4)}
.brand-cluster{display:flex;align-items:center;gap:12px}
.brand-logo-gem{width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,#1a1d24 0%,#050608 100%);border:1.5px solid rgba(255,255,255,.28);display:flex;align-items:center;justify-content:center;box-shadow:0 0 24px rgba(255,255,255,.18),inset 0 1px 0 rgba(255,255,255,.12);position:relative;overflow:hidden;flex-shrink:0}
.brand-logo-gem::after{content:'';position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle at 30% 20%,rgba(255,255,255,.18),transparent 60%);pointer-events:none}
.brand-logo-gem svg{width:34px;height:34px;position:relative;z-index:1;filter:drop-shadow(0 0 6px rgba(255,255,255,.4))}
.brand-title{font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:.95rem;letter-spacing:.6px;color:#fff}
.brand-sub{font-size:.74rem;color:var(--text-sub);font-family:'JetBrains Mono',monospace}
.portal-container{width:100%;max-width:480px;position:relative;transform-style:preserve-3d}
.hologram-glow-border{position:relative;border-radius:42px;padding:1.5px;background:linear-gradient(135deg,rgba(120,120,120,.65),rgba(200,200,200,.65),rgba(150,150,150,.65),rgba(220,220,220,.55));background-size:300% 300%;animation:rainbowGlow 8s ease infinite;box-shadow:0 35px 90px rgba(0,0,0,.9),0 0 55px rgba(200,200,200,.15)}
@keyframes rainbowGlow{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.hologram-card{position:relative;background:linear-gradient(180deg,rgba(16,20,28,.88) 0%,rgba(6,8,12,.96) 100%);backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);border-radius:40px;padding:42px 32px 34px;text-align:center;overflow:hidden}
.hologram-card::before{content:'';position:absolute;top:0;left:12%;right:12%;height:3px;background:linear-gradient(90deg,transparent,#e5e7eb,#9ca3af,#f3f4f6,transparent);background-size:200% 100%;animation:sheenRun 4s linear infinite;border-radius:100px;box-shadow:0 0 20px rgba(255,255,255,.7)}
@keyframes sheenRun{0%{background-position:100% 0}100%{background-position:-100% 0}}
.system-badge{display:inline-flex;align-items:center;gap:8px;padding:6px 18px;background:linear-gradient(135deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.14);border-radius:100px;font-family:'Space Grotesk',sans-serif;font-size:.75rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#e2e8f0;margin-bottom:24px;box-shadow:0 6px 20px rgba(0,0,0,.4)}
.badge-gem{width:8px;height:8px;border-radius:50%;background:#e5e7eb;box-shadow:0 0 14px #fff;animation:gemPulse 1.6s ease-in-out infinite}
@keyframes gemPulse{0%,100%{transform:scale(1);opacity:.7}50%{transform:scale(1.4);opacity:1}}
.scanner-viewport{position:relative;width:170px;height:170px;margin:0 auto 24px;display:flex;align-items:center;justify-content:center}
.gyro-orbit{position:absolute;inset:0;border-radius:50%;pointer-events:none}
.orbit-outer{border:2px dashed rgba(255,255,255,.55);animation:spinCW 10s cubic-bezier(.4,0,.2,1) infinite}
.orbit-mid{inset:16px;border:2.5px solid transparent;border-top:2.5px solid #e5e7eb;border-bottom:2.5px solid #9ca3af;animation:spinCCW 7s cubic-bezier(.45,.05,.55,.95) infinite}
.orbit-inner{inset:32px;border:1.5px dotted rgba(255,255,255,.6);animation:spinCW 8s linear infinite}
.reactor-core{position:relative;width:76px;height:76px;border-radius:50%;background:linear-gradient(135deg,rgba(120,120,120,.55),rgba(220,220,220,.45));border:1.5px solid rgba(255,255,255,.4);backdrop-filter:blur(16px);display:flex;align-items:center;justify-content:center;box-shadow:0 0 45px rgba(200,200,200,.6);animation:coreBreathing 2.6s ease-in-out infinite alternate;z-index:5}
.reactor-core svg{width:28px;height:28px;stroke:#fff;filter:drop-shadow(0 0 10px rgba(255,255,255,.9))}
.laser-scan-line{position:absolute;left:10px;right:10px;height:2px;background:linear-gradient(90deg,transparent,#fff,#9ca3af,transparent);box-shadow:0 0 15px #fff;animation:laserScan 2.4s ease-in-out infinite alternate;pointer-events:none;z-index:10}
@keyframes laserScan{0%{top:15%;opacity:.2}50%{opacity:1}100%{top:85%;opacity:.2}}
@keyframes spinCW{100%{transform:rotate(360deg)}}
@keyframes spinCCW{100%{transform:rotate(-360deg)}}
@keyframes coreBreathing{0%{transform:scale(.95);box-shadow:0 0 25px rgba(120,120,120,.5)}100%{transform:scale(1.08);box-shadow:0 0 55px rgba(255,255,255,.8)}}
.loading-status-badge{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;border-radius:50px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.25);font-size:.8rem;font-weight:700;color:#e5e7eb;margin-bottom:14px;animation:pulseGlow 1.8s ease-in-out infinite}
@keyframes pulseGlow{0%,100%{opacity:.5;transform:scale(.9)}50%{opacity:1;transform:scale(1.35)}}
.portal-headline{font-family:'Space Grotesk','Kanit',sans-serif;font-size:1.55rem;font-weight:800;color:#fff;margin-bottom:8px;letter-spacing:-.3px}
.portal-subtext{font-size:.92rem;color:var(--text-sub);line-height:1.65;margin-bottom:24px}
.phase-panel{display:none;opacity:0;transform:translateY(12px) scale(.98)}
.phase-panel.active{display:block;animation:panelEnter .5s cubic-bezier(.16,1,.3,1) forwards}
@keyframes panelEnter{to{opacity:1;transform:translateY(0) scale(1)}}
.loading-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px 0;transition:opacity .5s ease,transform .5s cubic-bezier(.16,1,.3,1)}
.loading-screen.hide{opacity:0;transform:scale(.9);pointer-events:none}
.loading-ring{width:140px;height:140px;position:relative;margin-bottom:28px}
.loading-ring::before,.loading-ring::after{content:'';position:absolute;inset:0;border-radius:50%;border:3px solid transparent;animation:loadingSpin 1.4s cubic-bezier(.5,0,.5,1) infinite}
.loading-ring::before{border-top-color:#e5e7eb;border-right-color:#9ca3af;animation-duration:1.2s}
.loading-ring::after{inset:14px;border-bottom-color:#f3f4f6;border-left-color:#6b7280;animation-duration:1.6s;animation-direction:reverse}
.loading-ring-inner{position:absolute;inset:32px;border-radius:50%;background:linear-gradient(135deg,rgba(120,120,120,.55),rgba(220,220,220,.45));border:1.5px solid rgba(255,255,255,.4);display:flex;align-items:center;justify-content:center;box-shadow:0 0 45px rgba(200,200,200,.6);animation:coreBreathing 2.6s ease-in-out infinite alternate}
.loading-ring-inner svg{width:30px;height:30px;stroke:#fff;fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 10px rgba(255,255,255,.9))}
@keyframes loadingSpin{100%{transform:rotate(360deg)}}
.loading-text{font-family:'Space Grotesk','Kanit',sans-serif;font-size:1.15rem;font-weight:800;color:#fff;margin-bottom:10px}
.loading-subtext{font-family:'JetBrains Mono',monospace;font-size:.82rem;color:var(--text-sub);letter-spacing:.5px}
.loading-dots{display:inline-flex;gap:4px;margin-left:4px}
.loading-dots span{width:4px;height:4px;border-radius:50%;background:#e5e7eb;animation:dotPulse 1.4s ease-in-out infinite}
.loading-dots span:nth-child(2){animation-delay:.2s}
.loading-dots span:nth-child(3){animation-delay:.4s}
@keyframes dotPulse{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:1;transform:scale(1.3)}}
.loading-progress{width:180px;height:3px;border-radius:100px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:22px}
.loading-progress-bar{height:100%;width:0%;background:linear-gradient(90deg,#9ca3af,#fff,#e5e7eb);border-radius:100px;box-shadow:0 0 12px rgba(255,255,255,.6);animation:progressFill 10s cubic-bezier(.3,0,.7,1) forwards}
.loading-progress-bar.dashboard{animation:progressFill 5s cubic-bezier(.3,0,.7,1) forwards}
@keyframes progressFill{0%{width:0}50%{width:65%}85%{width:90%}100%{width:100%}}
.dashboard-loading-overlay{position:fixed;inset:0;z-index:9999;background:rgba(4,6,15,.96);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);display:flex;align-items:center;justify-content:center;padding:24px}
.dashboard-loading-overlay.hide{opacity:0;transform:scale(.94);pointer-events:none;transition:all .6s ease}
.dashboard-loading-overlay{animation:autoHideLoading .6s ease 6s forwards}
@keyframes autoHideLoading{to{opacity:0;visibility:hidden;pointer-events:none}}
#page-dashboard{animation:autoShowDashboard .6s ease 6.5s forwards}
@keyframes autoShowDashboard{from{opacity:0}to{opacity:1}}
.btn-godtier{position:relative;display:flex;align-items:center;justify-content:center;gap:12px;width:100%;padding:18px 24px;border-radius:20px;font-family:'Space Grotesk','Kanit',sans-serif;font-size:1.05rem;font-weight:800;color:#0a0c11;text-decoration:none;background:linear-gradient(135deg,#e5e7eb 0%,#fff 50%,#9ca3af 100%);background-size:200% auto;border:none;box-shadow:0 14px 35px rgba(200,200,200,.35);cursor:pointer;overflow:hidden;transition:all .35s cubic-bezier(.16,1,.3,1)}
.btn-godtier:hover{background-position:right center;transform:translateY(-2px) scale(1.01);box-shadow:0 18px 45px rgba(255,255,255,.45)}
.btn-godtier:active{transform:translateY(1px) scale(.99)}
.identity-capsule{background:linear-gradient(180deg,rgba(22,30,54,.92) 0%,rgba(11,16,30,.98) 100%);border:1px solid rgba(255,255,255,.15);border-radius:28px;padding:24px 22px;margin-bottom:26px;position:relative;overflow:hidden;text-align:left;box-shadow:0 20px 45px rgba(0,0,0,.65)}
.avatar-row{display:flex;align-items:center;gap:18px;margin-bottom:20px}
.avatar-frame{position:relative;flex-shrink:0}
.avatar-photo{width:76px;height:76px;border-radius:22px;border:2px solid rgba(255,255,255,.25);object-fit:cover;box-shadow:0 12px 28px rgba(0,0,0,.55);display:block}
.avatar-halo{position:absolute;inset:-6px;border-radius:26px;border:2px solid rgba(255,255,255,.75);animation:haloPulse 2.5s ease-in-out infinite;pointer-events:none}
@keyframes haloPulse{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;border-color:#e5e7eb;transform:scale(1.04)}}
.status-dot-mini{position:absolute;bottom:-3px;right:-3px;width:20px;height:20px;background:#10b981;border:3.5px solid #0d121f;border-radius:50%;box-shadow:0 0 12px #10b981}
.user-meta{min-width:0;flex:1}
.user-royal-name{font-family:'Space Grotesk','Kanit',sans-serif;font-size:1.3rem;font-weight:800;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.user-discord-handle{font-family:'JetBrains Mono',monospace;font-size:.84rem;color:var(--text-sub);margin-top:3px;display:flex;align-items:center;gap:6px}
.btn-copy-id{display:inline-flex;align-items:center;justify-content:center;padding:3px 8px;border-radius:6px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);color:var(--text-sub);cursor:pointer;font-size:.7rem;transition:all .2s ease}
.btn-copy-id:hover{background:rgba(255,255,255,.15);border-color:#fff;color:#fff}
.verified-crown-tag{display:inline-flex;align-items:center;gap:6px;margin-top:8px;padding:5px 12px;background:linear-gradient(135deg,rgba(255,255,255,.18),rgba(255,255,255,.05));border:1px solid rgba(255,255,255,.4);border-radius:12px;font-size:.72rem;font-weight:800;color:#fff;position:relative;overflow:hidden}
.verified-crown-tag::after{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.4),transparent);animation:tagShimmer 3s infinite}
@keyframes tagShimmer{100%{left:100%}}
.meta-grid{display:flex;flex-direction:column;gap:12px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:14px 16px}
.meta-row{display:flex;align-items:center;justify-content:space-between;font-size:.88rem}
.meta-title{color:var(--text-sub);display:flex;align-items:center;gap:6px}
.role-vip-badge{display:inline-flex;align-items:center;gap:8px;padding:5px 14px;border-radius:10px;font-weight:700;font-size:.86rem;color:#fff;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);box-shadow:0 4px 12px rgba(0,0,0,.25)}
.role-light-dot{width:8px;height:8px;border-radius:50%}
.error-capsule{background:linear-gradient(180deg,rgba(50,18,25,.9) 0%,rgba(25,10,15,.98) 100%);border:1px solid rgba(244,63,94,.35);border-radius:26px;padding:24px 20px;margin-bottom:24px;text-align:center}
.error-icon-wrap{width:64px;height:64px;border-radius:20px;background:rgba(244,63,94,.15);border:1px solid rgba(244,63,94,.35);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;color:#f43f5e;box-shadow:0 0 25px rgba(244,63,94,.35)}
.stats-bar{width:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
.stat-card{background:var(--card-surface);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:1px solid var(--border-soft);border-radius:22px;padding:20px 24px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 12px 32px rgba(0,0,0,.45);position:relative;overflow:hidden;transition:all .3s cubic-bezier(.16,1,.3,1)}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent-gradient,linear-gradient(90deg,#9ca3af,transparent));opacity:.8}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(255,255,255,.2);box-shadow:0 18px 45px rgba(0,0,0,.6)}
.stat-label{font-family:'Space Grotesk','Kanit',sans-serif;font-size:.8rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--text-sub);display:flex;align-items:center;gap:8px}
.stat-value{font-family:'Space Grotesk',sans-serif;font-size:1.85rem;font-weight:800;margin-top:4px;color:#fff;display:flex;align-items:baseline;gap:8px}
.stat-value .unit{font-size:.88rem;color:var(--text-dim);font-weight:600;font-family:'Kanit',sans-serif}
.stat-icon-wrap{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);box-shadow:0 8px 20px rgba(0,0,0,.25)}
.stat-icon-wrap svg{width:24px;height:24px}
.live-activity-card{width:100%;background:var(--card-surface);backdrop-filter:blur(28px);-webkit-backdrop-filter:blur(28px);border:1px solid var(--border-soft);border-radius:30px;padding:clamp(22px,3vw,36px);box-shadow:0 30px 70px rgba(0,0,0,.7);position:relative}
.activity-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:22px}
.title-group .eyebrow{font-family:'Space Grotesk',sans-serif;font-size:.76rem;font-weight:800;letter-spacing:2px;color:#9ca3af;text-transform:uppercase;display:flex;align-items:center;gap:6px}
.title-group .main-title{font-family:'Space Grotesk','Kanit',sans-serif;font-size:1.85rem;font-weight:800;color:#fff;margin-top:2px}
.badge-pill{display:inline-flex;align-items:center;gap:8px;padding:7px 18px;border-radius:100px;font-size:.84rem;font-weight:700;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.2);color:#e5e7eb}
.live-dot{width:8px;height:8px;border-radius:50%;background:#e5e7eb;box-shadow:0 0 12px #fff;animation:pulseGlow 1.5s ease-in-out infinite}
.badge-rounds{display:inline-flex;align-items:center;padding:7px 16px;border-radius:100px;font-family:'JetBrains Mono',monospace;font-size:.82rem;font-weight:700;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:var(--text-sub)}
.table-toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.search-box{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:10px 16px;min-width:260px;flex:1;max-width:420px;transition:all .2s ease}
.search-box:focus-within{border-color:#e5e7eb;background:rgba(255,255,255,.06);box-shadow:0 0 16px rgba(255,255,255,.15)}
.search-box input{background:transparent;border:none;outline:none;color:#fff;font-size:.88rem;font-family:'Plus Jakarta Sans','Kanit',sans-serif;width:100%}
.search-box input::placeholder{color:var(--text-dim)}
.filter-chips{display:flex;gap:8px}
.chip-btn{padding:8px 16px;border-radius:12px;font-size:.8rem;font-weight:700;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);color:var(--text-sub);cursor:pointer;transition:all .2s ease}
.chip-btn:hover{background:rgba(255,255,255,.09);color:#fff}
.chip-btn.active{background:rgba(200,200,200,.18);border-color:#e5e7eb;color:#fff}
.table-wrapper{overflow-x:auto;border-radius:20px;border:1px solid var(--border-soft);background:var(--table-header-bg);box-shadow:inset 0 2px 6px rgba(0,0,0,.4)}
table{width:100%;border-collapse:separate;border-spacing:0 8px;padding:10px;min-width:760px}
th{font-family:'Space Grotesk','Kanit',sans-serif;font-size:.78rem;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--text-dim);text-align:left;padding:14px 20px}
tbody tr{background:var(--row-bg);border-radius:16px;transition:all .25s cubic-bezier(.16,1,.3,1)}
tbody tr:hover{background:var(--row-hover);transform:translateX(4px) scale(1.003);box-shadow:0 8px 24px rgba(0,0,0,.4)}
td{padding:16px 20px;font-size:.94rem;vertical-align:middle}
td:first-child{border-top-left-radius:16px;border-bottom-left-radius:16px}
td:last-child{border-top-right-radius:16px;border-bottom-right-radius:16px}
.user-cell{display:flex;align-items:center;gap:14px}
.user-avatar-circle{width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,.35);box-shadow:0 6px 16px rgba(0,0,0,.45);flex-shrink:0}
.user-title{font-weight:700;color:#fff;font-size:.98rem}
.user-sub{font-size:.78rem;color:var(--text-dim);font-family:'JetBrains Mono',monospace}
.id-badge{font-family:'JetBrains Mono',monospace;font-size:.86rem;font-weight:600;color:#e5e7eb;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);padding:6px 14px;border-radius:10px;display:inline-flex;align-items:center;gap:8px;cursor:pointer;transition:all .2s ease}
.id-badge:hover{background:rgba(255,255,255,.18);border-color:#fff;color:#fff}
.role-tag-badge{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;border-radius:12px;font-weight:700;font-size:.88rem;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);box-shadow:0 4px 12px rgba(0,0,0,.25)}
.role-dot-glow{width:8px;height:8px;border-radius:50%}
.time-text{font-family:'JetBrains Mono',monospace;font-size:.84rem;color:var(--text-sub);white-space:nowrap}
.floating-music-player{position:fixed;bottom:24px;right:24px;z-index:90;display:flex;align-items:center;gap:14px;padding:10px 20px;background:rgba(12,17,34,.92);border:1px solid rgba(255,255,255,.2);border-radius:50px;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);box-shadow:0 12px 35px rgba(0,0,0,.7),0 0 24px rgba(255,255,255,.08);transition:all .3s cubic-bezier(.16,1,.3,1)}
.floating-music-player:hover{border-color:rgba(255,255,255,.5);box-shadow:0 16px 45px rgba(0,0,0,.85),0 0 30px rgba(255,255,255,.2)}
.music-disc-icon{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#e5e7eb,#9ca3af);display:flex;align-items:center;justify-content:center;animation:spinCW 4s linear infinite;box-shadow:0 0 14px rgba(255,255,255,.4);flex-shrink:0;cursor:pointer}
.music-disc-icon.paused{animation-play-state:paused;background:linear-gradient(135deg,#54657e,#334155);box-shadow:none}
.music-disc-icon svg{width:18px;height:18px;fill:#0a0c11}
.music-track-meta{display:flex;flex-direction:column;max-width:220px;overflow:hidden}
.music-track-name{font-size:.84rem;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.music-track-status{font-size:.7rem;color:#d1d5db;font-family:'JetBrains Mono',monospace;display:flex;align-items:center;gap:6px}
.eq-wave-group{display:flex;align-items:flex-end;gap:3px;height:14px}
.eq-bar{width:3px;background:#e5e7eb;border-radius:2px;animation:eqDance .8s ease-in-out infinite alternate}
.eq-bar:nth-child(1){height:6px;animation-delay:.1s}
.eq-bar:nth-child(2){height:12px;animation-delay:.3s}
.eq-bar:nth-child(3){height:8px;animation-delay:.15s}
.eq-bar:nth-child(4){height:14px;animation-delay:.4s}
.paused .eq-bar{animation:none;height:3px;background:#54657e}
@keyframes eqDance{0%{height:3px}100%{height:14px}}
.btn-music-toggle{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s ease;flex-shrink:0}
.btn-music-toggle:hover{background:rgba(255,255,255,.2);border-color:rgba(255,255,255,.5);box-shadow:0 0 12px rgba(255,255,255,.4)}
#toast-notice{position:fixed;bottom:100px;right:28px;z-index:100;background:rgba(12,17,34,.95);border:1px solid #e5e7eb;box-shadow:0 10px 30px rgba(255,255,255,.2);padding:12px 20px;border-radius:14px;font-size:.88rem;font-weight:700;color:#fff;display:flex;align-items:center;gap:10px;backdrop-filter:blur(16px);transform:translateY(80px);opacity:0;transition:all .3s cubic-bezier(.16,1,.3,1);pointer-events:none}
#toast-notice.show{transform:translateY(0);opacity:1}
@media (max-width:768px){
  body{padding:16px 12px 64px}
  .app-layout{gap:22px}
  .hologram-glow-border{border-radius:34px}
  .hologram-card{padding:28px 20px 24px;border-radius:32px}
  .scanner-viewport{width:140px;height:140px;margin-bottom:18px}
  .reactor-core{width:62px;height:62px}
  .portal-headline{font-size:1.3rem}
  .btn-godtier{padding:15px;font-size:.98rem;border-radius:16px}
  .stats-bar{grid-template-columns:repeat(2,1fr);gap:12px}
  .stat-card{padding:14px;border-radius:18px}
  .stat-value{font-size:1.4rem}
  .stat-icon-wrap{width:38px;height:38px;border-radius:10px}
  .live-activity-card{padding:20px 14px;border-radius:24px}
  .table-toolbar{flex-direction:column;align-items:stretch}
  .search-box{max-width:100%}
  table{min-width:620px;padding:6px}
  th{padding:10px 14px;font-size:.72rem}
  td{padding:12px 14px;font-size:.86rem}
  .floating-music-player{bottom:14px;right:14px;padding:8px 14px}
  .loading-ring{width:110px;height:110px}
  .loading-ring-inner{inset:26px}
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
${isUser ? renderDashboard({
        user, roleNameSafe, roleColorSafe, usersJson,
        discordOnline, discordMembers, totalCount, todayCount
    }) : renderVerify({ errorSafe, buttonUrl })}
</div>

<div class="floating-music-player">
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
  <button class="btn-music-toggle" id="btnMusicPlayPause" onclick="toggleMusic()">
    <svg id="musicBtnIcon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
  </button>
</div>

<div id="toast-notice">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e5e7eb" stroke-width="2.4"><polyline points="20 6 9 17 4 12"/></svg>
  <span id="toast-text">คัดลอกสำเร็จ!</span>
</div>

<audio id="bgAudio" loop preload="auto" crossorigin="anonymous"></audio>

<script>
window.__INITIAL_USERS__ = ${usersJson};
window.__HAS_USER__ = ${isUser ? 'true' : 'false'};
window.__AUDIO_URL__ = ${JSON.stringify(AUDIO_URL)};
</script>
<script src="/static/app.js"></script>
</body>
</html>`;
}

function renderDashboard({ user, roleNameSafe, roleColorSafe, usersJson, discordOnline, discordMembers, totalCount, todayCount }) {
    const escape = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    const usersArr = JSON.parse(usersJson);

    return `
<div class="dashboard-loading-overlay" id="dashboardLoadingScreen">
  <div style="display:flex;flex-direction:column;align-items:center;text-align:center">
    <div class="loading-ring">
      <div class="loading-ring-inner">
        <svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
      </div>
    </div>
    <div class="loading-text">กำลังยืนยันตัวตน<span class="loading-dots"><span></span><span></span><span></span></span></div>
    <div class="loading-subtext">VERIFYING CREDENTIALS</div>
    <div class="loading-progress"><div class="loading-progress-bar dashboard"></div></div>
  </div>
</div>

<div id="page-dashboard" style="opacity:0;width:100%;display:flex;flex-direction:column;align-items:center;gap:36px">

  <div class="top-action-bar">
    <div class="brand-cluster">
      <div class="brand-logo-gem">
        <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
          <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.2" stroke-dasharray="3 4"/>
          <ellipse cx="17" cy="22" rx="4" ry="4.6" fill="#fff"/>
          <ellipse cx="31" cy="22" rx="4" ry="4.6" fill="#fff"/>
          <circle cx="17" cy="22.5" r="2.1" fill="#0a0c11"/>
          <circle cx="31" cy="22.5" r="2.1" fill="#0a0c11"/>
          <circle cx="16.2" cy="21.6" r="0.8" fill="#fff"/>
          <circle cx="30.2" cy="21.6" r="0.8" fill="#fff"/>
          <line x1="12" y1="28" x2="10" y2="36" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <line x1="16" y1="28.5" x2="15" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <line x1="20" y1="28.5" x2="20" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <line x1="28" y1="28.5" x2="28" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <line x1="32" y1="28.5" x2="33" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <line x1="36" y1="28" x2="38" y2="36" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M21 33 Q24 34 27 33" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round"/>
          <rect x="27" y="32.4" width="7" height="1.6" rx="0.8" fill="#fff"/>
        </svg>
      </div>
      <div>
        <div class="brand-title">ระบบยืนยันตัวตน</div>
        <div class="brand-sub">v1.0</div>
      </div>
    </div>
  </div>

  <div class="portal-container">
    <div class="hologram-glow-border">
      <div class="hologram-card" id="hologramCard">
        <div class="system-badge"><span class="badge-gem"></span><span>VERIFICATION SUCCESS</span></div>
        <div class="phase-panel active">
          <div class="identity-capsule">
            <div class="avatar-row">
              <div class="avatar-frame">
                <div class="avatar-halo"></div>
                <img src="${escape(user.avatar_url)}" class="avatar-photo" alt="Avatar">
                <div class="status-dot-mini"></div>
              </div>
              <div class="user-meta">
                <div class="user-royal-name">${escape(user.global_name || user.username)}</div>
                <div class="user-discord-handle">
                  <span>@${escape(user.username)}</span>
                  <button class="btn-copy-id" data-uid="${escape(user.id)}">📋 Copy ID</button>
                </div>
                <div class="verified-crown-tag">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="#fff"><path d="M2 19h20v2H2zM2 5l5 7 5-8 5 8 5-7v11H2z"/></svg>
                  <span>VERIFIED MEMBER</span>
                </div>
              </div>
            </div>
            <div class="meta-grid">
              <div class="meta-row">
                <span class="meta-title">⭐ ยศที่ได้รับ</span>
                <div class="role-vip-badge">
                  <span class="role-light-dot" style="background:${roleColorSafe};box-shadow:0 0 10px ${roleColorSafe}"></span>
                  <span style="color:${roleColorSafe}">${roleNameSafe}</span>
                </div>
              </div>
              <div class="meta-row">
                <span class="meta-title">🕐 วันที่เข้าร่วม</span>
                <span style="color:#fff;font-weight:700;font-size:.85rem;font-family:'JetBrains Mono',monospace">${escape(user.joined_at || '')}</span>
              </div>
            </div>
          </div>
          <a href="https://discord.com/app" class="btn-godtier" id="btnReturn">
            <span>เข้าสู่ Discord Server ทันที</span>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
          </a>
        </div>
      </div>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat-card" style="--accent-gradient:linear-gradient(90deg,#e5e7eb,transparent)">
      <div>
        <div class="stat-label"><span class="live-dot"></span><span>ออนไลน์ในดิสคอร์ด</span></div>
        <div class="stat-value"><span class="counter-num">${discordOnline}</span><span class="unit">คน (Active)</span></div>
      </div>
      <div class="stat-icon-wrap" style="color:#e5e7eb">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20a6 6 0 0 0-12 0"/><circle cx="12" cy="10" r="4"/><circle cx="12" cy="12" r="10"/></svg>
      </div>
    </div>
    <div class="stat-card" style="--accent-gradient:linear-gradient(90deg,#9ca3af,transparent)">
      <div>
        <div class="stat-label">สมาชิกทั้งหมด</div>
        <div class="stat-value"><span class="counter-num">${discordMembers}</span><span class="unit">คน</span></div>
      </div>
      <div class="stat-icon-wrap" style="color:#9ca3af">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>
    </div>
    <div class="stat-card" style="--accent-gradient:linear-gradient(90deg,#fff,transparent)">
      <div>
        <div class="stat-label">ยืนยันตัวตนแล้ว</div>
        <div class="stat-value" style="color:#fff"><span class="counter-num">${totalCount}</span><span class="unit">คน</span></div>
      </div>
      <div class="stat-icon-wrap" style="color:#fff">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
      </div>
    </div>
    <div class="stat-card" style="--accent-gradient:linear-gradient(90deg,#d1d5db,transparent)">
      <div>
        <div class="stat-label">รับยศวันนี้</div>
        <div class="stat-value" style="color:#d1d5db"><span class="counter-num">${todayCount}</span><span class="unit">รายการ</span></div>
      </div>
      <div class="stat-icon-wrap" style="color:#d1d5db">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      </div>
    </div>
  </div>

  <div class="live-activity-card">
    <div class="activity-header">
      <div class="title-group">
        <div class="eyebrow"><span class="live-dot"></span><span>LIVE STREAM</span></div>
        <h1 class="main-title"></h1>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <div class="badge-pill"><span class="live-dot"></span><span>อัปเดตแบบเรียลไทม์</span></div>
        <div class="badge-rounds" id="total-rounds-badge">${usersArr.length} รายการล่าสุด</div>
      </div>
    </div>
    <div class="table-toolbar">
      <div class="search-box">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-dim)"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" id="searchInput" placeholder="ค้นหาชื่อผู้ใช้ หรือ Discord ID...">
      </div>
      <div class="filter-chips">
        <button class="chip-btn active" data-filter="all">ทั้งหมด</button>
      </div>
    </div>
    <div class="table-wrapper">
      <table>
        <thead><tr>
          <th style="width:32%">ผู้ใช้งาน (Discord Member)</th>
          <th style="width:28%">Discord User ID</th>
          <th style="width:24%">ยศที่ได้รับ (Role Assigned)</th>
          <th style="width:16%;text-align:right">เวลาที่ได้รับ</th>
        </tr></thead>
        <tbody id="activity-tbody"></tbody>
      </table>
    </div>
  </div>

</div>`;
}

function renderVerify({ errorSafe, buttonUrl }) {
    const hasError = !!errorSafe;
    return `
<div class="top-action-bar">
  <div class="brand-cluster">
    <div class="brand-logo-gem">
      <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.2" stroke-dasharray="3 4"/>
        <ellipse cx="17" cy="22" rx="4" ry="4.6" fill="#fff"/>
        <ellipse cx="31" cy="22" rx="4" ry="4.6" fill="#fff"/>
        <circle cx="17" cy="22.5" r="2.1" fill="#0a0c11"/>
        <circle cx="31" cy="22.5" r="2.1" fill="#0a0c11"/>
        <circle cx="16.2" cy="21.6" r="0.8" fill="#fff"/>
        <circle cx="30.2" cy="21.6" r="0.8" fill="#fff"/>
        <line x1="12" y1="28" x2="10" y2="36" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="16" y1="28.5" x2="15" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="20" y1="28.5" x2="20" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="28" y1="28.5" x2="28" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="32" y1="28.5" x2="33" y2="37" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="36" y1="28" x2="38" y2="36" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M21 33 Q24 34 27 33" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round"/>
        <rect x="27" y="32.4" width="7" height="1.6" rx="0.8" fill="#fff"/>
      </svg>
    </div>
    <div>
      <div class="brand-title">ระบบยืนยันตัวตน by.น้องเจคอปเด็กชายบริสุทธิ์</div>
      <div class="brand-sub">v1.0</div>
    </div>
  </div>
</div>

<div class="portal-container" id="tiltContainer">
  <div class="hologram-glow-border">
    <div class="hologram-card">
      <div class="system-badge"><span class="badge-gem"></span><span>ระบบยืนยันตัวตน</span></div>
      ${hasError ? `
      <div class="phase-panel active">
        <div class="error-capsule">
          <div class="error-icon-wrap">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <h2 class="portal-headline" style="color:#f43f5e">เกิดข้อผิดพลาดในการยืนยัน</h2>
          <p class="portal-subtext" style="color:#fda4af">${errorSafe}</p>
        </div>
        <a href="https://discord.com/app" class="btn-godtier" style="background:linear-gradient(135deg,#f43f5e,#e11d48);color:#fff">กลับไปที่ Discord</a>
      </div>
      ` : `
      <div class="loading-screen" id="loadingScreen">
        <div class="loading-ring">
          <div class="loading-ring-inner">
            <svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
          </div>
        </div>
        <div class="loading-text">กำลังเชื่อมต่อระบบ<span class="loading-dots"><span></span><span></span><span></span></span></div>
        <div class="loading-subtext">INITIALIZING SECURE GATEWAY</div>
        <div class="loading-progress"><div class="loading-progress-bar"></div></div>
      </div>
      <div class="phase-panel" id="verifyPanel" style="display:none">
        <div class="scanner-viewport">
          <div class="gyro-orbit orbit-outer"></div>
          <div class="gyro-orbit orbit-mid"></div>
          <div class="gyro-orbit orbit-inner"></div>
          <div class="laser-scan-line"></div>
          <div class="reactor-core">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
          </div>
        </div>
        <div class="loading-status-badge"><span class="live-dot"></span><span>ระบบพร้อมเชื่อมต่อ Discord Gateway</span></div>
        <h2 class="portal-headline">ระบบยืนยันตัวตนอัตโนมัติ</h2>
        <p class="portal-subtext">by.น้องเจคอปเด็กชายบริสุทธิ์<br>กรุณากดปุ่มด้านล่างเพื่อรับยศทันที</p>
        <a href="${buttonUrl}" class="btn-godtier">
          <span>ยืนยันตัวตนผ่าน Discord</span>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </a>
      </div>
      `}
    </div>
  </div>
</div>`;
}
app.get('/static/app.js', (req, res) => {
    res.setHeader('Content-Type', 'application/javascript');
    res.send(`
const initialUsers = window.__INITIAL_USERS__ || [];
const hasUser = window.__HAS_USER__ || false;
const AUDIO_URL = window.__AUDIO_URL__ || '';

const audio = document.getElementById('bgAudio');
if (audio) {
    audio.src = AUDIO_URL;
    audio.loop = true;
    audio.volume = 0.75;
    audio.muted = true;
}
let isPlaying = false, userHasInteracted = false;

function startSilentPlay(){ if(!audio) return; audio.muted=true; audio.volume=0; audio.play().then(()=>{isPlaying=true;updateMusicUI(true)}).catch(()=>{}); }
function unlockAudio(){ if(userHasInteracted) return; userHasInteracted=true; if(!audio) return; try{ audio.muted=false; audio.volume=0.75; if(audio.paused) audio.play().catch(()=>{}); isPlaying=true; updateMusicUI(true); }catch(e){} }
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', startSilentPlay); else startSilentPlay();
window.addEventListener('pointerdown', unlockAudio, { once:true, passive:true });
window.addEventListener('keydown', unlockAudio, { once:true });

function toggleMusic(){ if(!userHasInteracted) unlockAudio(); if(!audio) return; if(audio.paused){ audio.muted=false; audio.volume=0.75; audio.play().catch(()=>{}); showToast('▶️ เล่นเพลง'); } else { audio.pause(); showToast('⏸️ พักเพลง'); } }
audio && audio.addEventListener('play', ()=>{ isPlaying=true; updateMusicUI(true); });
audio && audio.addEventListener('pause', ()=>{ isPlaying=false; updateMusicUI(false); });
function updateMusicUI(playing){
  const disc=document.getElementById('musicDisc'), label=document.getElementById('musicStateLabel'), eq=document.getElementById('eqWaves'), btnIcon=document.getElementById('musicBtnIcon');
  if(playing){ disc&&disc.classList.remove('paused'); eq&&eq.classList.remove('paused'); if(label) label.textContent='กำลังเล่นเพลง';
    if(btnIcon) btnIcon.innerHTML='<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
  } else { disc&&disc.classList.add('paused'); eq&&eq.classList.add('paused'); if(label) label.textContent='หยุดชั่วคราว';
    if(btnIcon) btnIcon.innerHTML='<polygon points="5 3 19 12 5 21 5 3"/>';
  }
}

let sfxCtx=null;
function getSfxCtx(){ if(!sfxCtx){ const AC=window.AudioContext||window.webkitAudioContext; sfxCtx=new AC(); } if(sfxCtx.state==='suspended') sfxCtx.resume(); return sfxCtx; }
function playSuccessBeep(){ try{ const ctx=getSfxCtx(); const o=ctx.createOscillator(), g=ctx.createGain(); o.type='sine'; o.frequency.setValueAtTime(587.33,ctx.currentTime); o.frequency.exponentialRampToValueAtTime(880,ctx.currentTime+0.15); g.gain.setValueAtTime(0.12,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.35); o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.35); }catch(e){} }
function playNotificationTone(){ try{ const ctx=getSfxCtx(); const o=ctx.createOscillator(), g=ctx.createGain(); o.type='triangle'; o.frequency.setValueAtTime(440,ctx.currentTime); o.frequency.setValueAtTime(659.25,ctx.currentTime+0.08); g.gain.setValueAtTime(0.08,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.25); o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.25); }catch(e){} }
function showToast(msg){ const t=document.getElementById('toast-notice'); if(!t) return; document.getElementById('toast-text').textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'), 2400); }
function copyToClipboard(text,label){ navigator.clipboard.writeText(text).then(()=>{ playNotificationTone(); showToast('คัดลอก '+label+': '+text+' แล้ว! 📋'); }).catch(()=> showToast('คัดลอก: '+text)); }

window.toggleMusic = toggleMusic;
window.copyToClipboard = copyToClipboard;
window.playSuccessBeep = playSuccessBeep;

(function bindMainCopyId() {
  const el = document.querySelector('.btn-copy-id[data-uid]');
  if (el) el.addEventListener('click', function() { copyToClipboard(this.dataset.uid, 'Discord ID'); });
})();

(function bindReturnBtn() {
  const el = document.getElementById('btnReturn');
  if (el) el.addEventListener('click', function(e) { e.preventDefault(); playSuccessBeep(); setTimeout(()=>{ window.location.href='https://discord.com/app'; }, 200); });
})();

const cursorGlow=document.getElementById('cursor-glow');
if (cursorGlow) document.addEventListener('mousemove', e=>{ cursorGlow.style.left=e.clientX+'px'; cursorGlow.style.top=e.clientY+'px'; });

const starCanvas=document.getElementById('stars-canvas');
if (starCanvas) {
  const starCtx=starCanvas.getContext('2d');
  let stars=[];
  function resizeStarfield(){ starCanvas.width=window.innerWidth; starCanvas.height=window.innerHeight; stars=Array.from({length:65},()=>({ x:Math.random()*starCanvas.width, y:Math.random()*starCanvas.height, size:Math.random()*2+0.6, speed:Math.random()*0.35+0.1, alpha:Math.random()*0.7+0.3 })); }
  window.addEventListener('resize', resizeStarfield); resizeStarfield();
  function renderStarfield(){ starCtx.clearRect(0,0,starCanvas.width,starCanvas.height); starCtx.fillStyle='#fff'; stars.forEach(s=>{ s.y-=s.speed; if(s.y<0) s.y=starCanvas.height; starCtx.globalAlpha=s.alpha; starCtx.beginPath(); starCtx.arc(s.x,s.y,s.size,0,Math.PI*2); starCtx.fill(); }); requestAnimationFrame(renderStarfield); }
  renderStarfield();
}

let activityData = initialUsers;
let currentFilter = 'all', searchQuery = '';

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

function setRoleFilter(filter, btn) {
  currentFilter = filter;
  document.querySelectorAll('.filter-chips .chip-btn').forEach(function(b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  renderTable();
}

function filterData() {
  const el = document.getElementById('searchInput');
  searchQuery = el ? el.value.trim().toLowerCase() : '';
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById('activity-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const filtered = activityData.filter(function(r) {
    const m = (r.user || '').toLowerCase().includes(searchQuery)
      || (r.handle || '').toLowerCase().includes(searchQuery)
      || (r.id || '').includes(searchQuery);
    if (!m) return false;
    if (currentFilter === 'vip') return (r.role || '').includes('VIP');
    if (currentFilter === 'verified') return !(r.role || '').includes('VIP');
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-dim);padding:36px">🔍 ยังไม่มีข้อมูล</td></tr>';
    return;
  }

  filtered.forEach(function(r) {
    const tr = document.createElement('tr');

    const td1 = document.createElement('td');
    td1.innerHTML = '<div class="user-cell"><img src="' + escapeHtml(r.avatar || 'https://cdn.discordapp.com/embed/avatars/0.png') + '" class="user-avatar-circle" alt="A"><div><div class="user-title">' + escapeHtml(r.user) + '</div><div class="user-sub">@' + escapeHtml(r.handle) + '</div></div></div>';

    const td2 = document.createElement('td');
    const idBadge = document.createElement('span');
    idBadge.className = 'id-badge';
    idBadge.dataset.uid = r.id;
    idBadge.textContent = '🔒 ' + r.id;
    td2.appendChild(idBadge);

    const td3 = document.createElement('td');
    const rc = escapeHtml(r.roleColor || '#e5e7eb');
    td3.innerHTML = '<div class="role-tag-badge" style="border-color:' + rc + '40"><span class="role-dot-glow" style="background:' + rc + ';box-shadow:0 0 12px ' + rc + '"></span><span style="color:' + rc + ';font-weight:700">' + escapeHtml(r.role) + '</span></div>';

    const td4 = document.createElement('td');
    td4.className = 'time-text';
    td4.style.textAlign = 'right';
    td4.textContent = r.time || '';

    tr.appendChild(td1);
    tr.appendChild(td2);
    tr.appendChild(td3);
    tr.appendChild(td4);
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.id-badge').forEach(function(el) {
    el.addEventListener('click', function() {
      copyToClipboard(this.dataset.uid, 'Discord ID');
    });
  });

  const badge = document.getElementById('total-rounds-badge');
  if (badge) badge.textContent = activityData.length + ' รายการล่าสุด';
}

window.setRoleFilter = setRoleFilter;
window.filterData = filterData;
window.renderTable = renderTable;

(function bindToolbar() {
  document.querySelectorAll('.filter-chips .chip-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { setRoleFilter(this.dataset.filter, this); });
  });
  const si = document.getElementById('searchInput');
  if (si) si.addEventListener('input', filterData);
})();

async function pollLiveActivity() {
  try {
    const res = await fetch('/api/live_activity');
    if (!res.ok) return;
    const data = await res.json();
    const nums = document.querySelectorAll('.counter-num');
    if (data.verified_stats) {
      if (nums[2]) nums[2].textContent = Number(data.verified_stats.total || 0).toLocaleString();
      if (nums[3]) nums[3].textContent = Number(data.verified_stats.today || 0).toLocaleString();
    }
    if (data.discord_stats) {
      if (nums[0]) nums[0].textContent = Number(data.discord_stats.online || 0).toLocaleString();
      if (nums[1]) nums[1].textContent = Number(data.discord_stats.total_members || 0).toLocaleString();
    }
    if (data.users && data.users.length) {
      activityData = data.users.map(function(u) {
        return {
          user: u.global_name || u.username,
          handle: u.username,
          id: u.user_id,
          avatar: u.avatar_url,
          role: u.role_name || 'Verified Member',
          roleColor: u.role_color || '#e5e7eb',
          time: u.verified_at
        };
      });
      renderTable();
    }
  } catch (e) { /* ignore */ }
}

try {
  if (hasUser) {
    setTimeout(function() {
      try {
        renderTable();
        setInterval(pollLiveActivity, 4000);
        pollLiveActivity();
        playSuccessBeep();
      } catch (e) { console.error('Dashboard init error:', e); }
    }, 6500);
  } else {
    const loadingScreen = document.getElementById('loadingScreen');
    const verifyPanel = document.getElementById('verifyPanel');
    if (loadingScreen && verifyPanel) {
      setTimeout(function() {
        loadingScreen.classList.add('hide');
        setTimeout(function() {
          loadingScreen.style.display = 'none';
          verifyPanel.style.display = 'block';
          verifyPanel.classList.add('active');
        }, 500);
      }, 10000);
    }
  }
} catch (e) {
  console.error('Page init error:', e);
}
`);
});

app.get('/', (req, res) => {
    const discordLoginUrl =
        `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
        `&response_type=code&scope=openid%20identify%20guilds%20guilds.join`;

    res.send(renderHTML({
        title: 'ระบบยืนยันตัวตน',
        buttonUrl: discordLoginUrl,
        user: null,
    }));
});

app.get('/callback', async (req, res) => {
    console.log('📥 /callback received!');
    const code = req.query.code;
    if (!code) {
        return res.send(renderHTML({
            title: 'เกิดข้อผิดพลาด',
            errorMessage: 'ไม่พบรหัสยืนยันตัวตนจาก Discord กรุณาลองใหม่อีกครั้ง',
        }));
    }

    try {
        const tokenResp = await axios.post(
            'https://discord.com/api/oauth2/token',
            new URLSearchParams({
                client_id: CLIENT_ID,
                client_secret: CLIENT_SECRET,
                grant_type: 'authorization_code',
                code,
                redirect_uri: REDIRECT_URI,
            }),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        );

        const accessToken = tokenResp.data.access_token;
        if (!accessToken) {
            await sendWebhookLog(WEBHOOK_ERROR, '❌ ยืนยันตัวตนล้มเหลว', 'ไม่สามารถขอ Access Token', 16711680);
            return res.send(renderHTML({ title: 'ผิดพลาด', errorMessage: 'เกิดข้อผิดพลาดในการขอ Token จาก Discord' }));
        }

        const userResp = await axios.get('https://discord.com/api/users/@me', {
            headers: { Authorization: `Bearer ${accessToken}` }
        });
        const u = userResp.data;
        const userId = u.id;
        const username = u.username;
        const globalName = u.global_name;
        const avatarUrl = u.avatar
            ? `https://cdn.discordapp.com/avatars/${userId}/${u.avatar}.png`
            : 'https://cdn.discordapp.com/embed/avatars/0.png';

        const alreadyVerified = db.prepare('SELECT user_id FROM verified_users WHERE user_id = ?').get(userId);
        const ts = ((BigInt(userId) >> 22n) + 1420070400000n);
        const joinDate = new Date(Number(ts));
        const joinedDateThai = thaiDate(new Date(joinDate.getTime()));

        const userInfo = {
            id: userId, username, global_name: globalName,
            avatar_url: avatarUrl, joined_at: joinedDateThai,
        };
        const roleInfo = await getRoleInfo(GUILD_ID, ROLE_ID);

        try {
            const addRoleResp = await axios.put(
                `https://discord.com/api/v10/guilds/${GUILD_ID}/members/${userId}/roles/${ROLE_ID}`,
                {},
                { headers: { Authorization: `Bot ${BOT_TOKEN}` } }
            );
            if (![200, 204].includes(addRoleResp.status)) throw new Error(`status ${addRoleResp.status}`);
        } catch (err) {
            const status = err.response?.status || 'unknown';
            await sendWebhookLog(WEBHOOK_ERROR, '❌ เพิ่มยศไม่สำเร็จ', `ผู้ใช้: ${username} (\`${userId}\`)\nStatus: ${status}`, 16711680);
        }

        if (!alreadyVerified) {
            db.prepare(`
        INSERT OR REPLACE INTO verified_users
        (user_id, username, global_name, avatar_url, verified_at, role_name, role_color)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(userId, username, globalName, avatarUrl, formatThaiDateTime(), roleInfo.name, roleInfo.color);

            await sendWebhookLog(
                WEBHOOK_SUCCESS,
                '`✅` **มีผู้ยืนยันตัวตนสำเร็จ**',
                `- **ผู้ใช้:** **${globalName || username}** (\`@${username}\`)\n- **ID:** **${userId}**\n- **ยศ:** **${roleInfo.name}**`,
                2318169, avatarUrl
            );
        } else {
            await sendWebhookLog(
                WEBHOOK_SUCCESS,
                '`🔁` **มีผู้ยืนยันตัวตนซ้ำ**',
                `- **ผู้ใช้:** **${globalName || username}** (\`@${username}\`)\n- **ID:** **${userId}**\n- **ยศ:** **${roleInfo.name}**`,
                3447003, avatarUrl
            );
        }

        const totalCount = db.prepare('SELECT COUNT(*) as c FROM verified_users').get().c;
        const todayStr = todayTH();
        const todayCount = db.prepare('SELECT COUNT(*) as c FROM verified_users WHERE verified_at LIKE ?').get(`${todayStr}%`).c;
        const recentUsers = db.prepare(`
      SELECT user_id, username, global_name, avatar_url, verified_at, role_name, role_color
      FROM verified_users ORDER BY verified_at DESC LIMIT 50
    `).all();
        const discStats = await getDiscordGuildStats();

        res.send(renderHTML({
            title: 'ยืนยันตัวตนสำเร็จ',
            user: userInfo,
            roleName: roleInfo.name,
            roleColor: roleInfo.color,
            stats: {
                total_count: totalCount,
                today_count: todayCount,
                discord_online: discStats.online,
                discord_members: discStats.total_members,
            },
            users: recentUsers,
        }));
    } catch (err) {
        console.error('💥 /callback error:', err.message);
        await sendWebhookLog(WEBHOOK_ERROR, '💥 ระบบผิดพลาด', `\`${err.message}\``, 16711680);
        res.send(renderHTML({
            title: 'ผิดพลาด',
            errorMessage: 'เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ กรุณาลองใหม่',
        }));
    }
});

app.get('/api/live_activity', async (req, res) => {
    try {
        const totalCount = db.prepare('SELECT COUNT(*) as c FROM verified_users').get().c;
        const todayStr = todayTH();
        const todayCount = db.prepare('SELECT COUNT(*) as c FROM verified_users WHERE verified_at LIKE ?').get(`${todayStr}%`).c;
        const users = db.prepare(`
      SELECT user_id, username, global_name, avatar_url, verified_at, role_name, role_color
      FROM verified_users ORDER BY verified_at DESC LIMIT 50
    `).all();
        const discStats = await getDiscordGuildStats();
        res.json({
            discord_stats: discStats,
            verified_stats: { total: totalCount, today: todayCount },
            users,
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

client.once(Events.ClientReady, async (c) => {
    console.log(`✅ Bot online: ${c.user.tag}`);
    // ✅ แก้จุดที่ 3: เอาเม็ดม่วงออก (Streaming → Watching) + เปลี่ยน status เป็น online
    c.user.setPresence({
        activities: [{ name: 'Vendetta Shop', type: ActivityType.Watching }],
        status: 'online',
    });

    try {
        const rest = new REST({ version: '10' }).setToken(BOT_TOKEN);
        await rest.put(
            Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID),
            {
                body: [
                    new SlashCommandBuilder()
                        .setName('setup')
                        .setDescription('ส่งหน้าต่างยืนยันตัวตนสำหรับสมาชิก')
                        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
                        .toJSON()
                ]
            }
        );
        console.log('✅ Slash commands synced');
    } catch (err) {
        console.error('❌ Sync commands failed:', err.message);
    }
});

client.on(Events.InteractionCreate, async (interaction) => {
    if (!interaction.isChatInputCommand()) return;
    if (interaction.commandName !== 'setup') return;
    try {
        const payload = buildVerifyMessage();
        await interaction.channel.send(payload);
        await interaction.reply({ content: '✅ ส่งข้อความ Components V2 สำเร็จ!', ephemeral: true });
    } catch (err) {
        console.error('[setup] Error:', err);
        await interaction.reply({ content: `❌ ไม่สำเร็จ: ${err.message}`, ephemeral: true }).catch(() => { });
    }
});

(async () => {
    const server = app.listen(PORT, '0.0.0.0', () => {
        console.log(`🌐 Web running on http://0.0.0.0:${PORT}`);
    });
    server.on('error', (err) => { console.error('❌ Express server error:', err.message); process.exit(1); });
    client.login(BOT_TOKEN).catch(err => { console.error('❌ Bot login failed:', err.message); process.exit(1); });
})();
