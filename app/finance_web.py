"""ORXYZ wallet and operator control prototype pages.

These surfaces are deliberately staged: they model the bandwidth-reward flow
without claiming cash redemption or guaranteed financial returns.
"""
from fastapi.responses import HTMLResponse


def wallet_page() -> HTMLResponse:
    return HTMLResponse("""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ORXYZ Wallet</title>
<style>
:root{--bg:#f4f5f2;--ink:#0d0f10;--card:#fff;--muted:#777e83;--line:#dfe2dd;--lime:#d8ff45}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif}
.shell{max-width:1120px;margin:auto;padding:24px}.nav{display:flex;justify-content:space-between;align-items:center}.brand{font-weight:900;letter-spacing:-.05em;font-size:24px}.pill{background:#fff;border:1px solid var(--line);padding:8px 12px;border-radius:999px;font-size:12px}
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:24px;padding:56px 0 30px}.hero h1{font-size:clamp(48px,7vw,80px);line-height:.92;letter-spacing:-.065em;margin:8px 0 18px}.hero p{color:var(--muted);font-size:17px;line-height:1.6;max-width:620px}
.card{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:24px}.wallet{background:#111;color:#fff}.eyebrow{font-size:11px;letter-spacing:.14em;font-weight:800;color:#7f8500}.bal{font-size:56px;font-weight:900;letter-spacing:-.05em;margin:28px 0}.bal span{font-size:18px;color:var(--lime)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.stat{background:#1a1d1f;border:1px solid #2c3033;border-radius:14px;padding:12px}.stat small{display:block;color:#92999f}.stat b{display:block;margin-top:5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}.row{display:flex;justify-content:space-between;gap:20px;padding:14px 0;border-bottom:1px solid var(--line)}.row:last-child{border-bottom:0}
label{display:flex;justify-content:space-between;font-size:13px;font-weight:700;margin:13px 0 7px}input{width:100%;accent-color:#111}.btn{border:0;border-radius:12px;background:#111;color:white;font-weight:800;padding:12px 16px;cursor:pointer}.btn.lime{background:var(--lime);color:#111;width:100%;margin-top:18px}
.products{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.product{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px}.product .emoji{font-size:36px}.product h3{margin:12px 0 6px}.price{font-weight:900;font-size:22px}.muted{color:var(--muted);font-size:12px;line-height:1.5}.notice{margin-top:14px;font-size:12px;font-weight:700}
@media(max-width:760px){.hero,.grid{grid-template-columns:1fr}.products{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style></head>
<body><div class="shell">
<div class="nav"><div class="brand">ORXYZ</div><div class="pill">User Wallet • Prototype</div></div>
<section class="hero"><div><div class="eyebrow">EARN • STACK • SPEND</div><h1>Your contribution becomes useful value.</h1><p>Opt in to contribute bandwidth. ORXYZ tracks verified GB and the real revenue associated with it, then credits a small disclosed reward share as spendable ORXYZ.</p></div>
<div class="card wallet"><small>Spendable ORXYZ</small><div class="bal"><span id="balance">8.420</span> <span>ORXYZ</span></div><div class="stats"><div class="stat"><small>Pending</small><b id="pending">0.108</b></div><div class="stat"><small>GB verified</small><b id="gbStat">120 GB</b></div><div class="stat"><small>Reward rate</small><b id="rateStat">5%</b></div></div><button class="btn lime" onclick="claim()">Claim verified reward</button><div class="notice" id="walletNotice"></div></div></section>
<div class="grid"><section class="card"><h2>Bandwidth earning</h2>
<label>Verified GB <b><span id="gbLabel">120</span> GB</b></label><input id="gb" type="range" min="10" max="1000" step="10" value="120">
<label>Revenue per GB <b>$<span id="priceLabel">0.018</span></b></label><input id="price" type="range" min="0.005" max="0.05" step="0.001" value="0.018">
<label>Reward share <b><span id="rateLabel">5</span>%</b></label><input id="rate" type="range" min="1" max="15" value="5">
<p class="muted">Demo assumptions only. Actual bandwidth demand and payout economics would require real network partners, compliance, anti-abuse controls and auditable metering.</p></section>
<section class="card"><h2>How your reward stacks</h2><div class="row"><span>Verified revenue</span><b>$<span id="revenue">2.16</span></b></div><div class="row"><span>Your ORXYZ reward</span><b><span id="earned">0.108</span> ORXYZ</b></div><div class="row"><span>Network / settlement pool</span><b>$<span id="reserve">2.05</span></b></div><div class="row"><span>Formula</span><b>revenue × reward %</b></div></section></div>
<h2>Spend ORXYZ</h2><div class="products"><div class="product"><div class="emoji">🔌</div><h3>USB-C Cable</h3><div class="price">3.25 ORXYZ</div><button class="btn" onclick="buy('USB-C Cable',3.25)">Buy</button></div><div class="product"><div class="emoji">✨</div><h3>AI Credits</h3><div class="price">5 ORXYZ</div><button class="btn" onclick="buy('AI Credits',5)">Buy</button></div><div class="product"><div class="emoji">☕</div><h3>Coffee Reward</h3><div class="price">2.75 ORXYZ</div><button class="btn" onclick="buy('Coffee Reward',2.75)">Buy</button></div></div>
<p class="muted" style="margin:28px 0">ORXYZ shown here is a closed-loop prototype reward unit, not a bank deposit, guaranteed investment return, or currently redeemable currency.</p>
</div><script>
let bal=8.42,pending=0;const gb=document.getElementById('gb'),price=document.getElementById('price'),rate=document.getElementById('rate');
function calc(){const g=+gb.value,p=+price.value,r=+rate.value,rev=g*p,e=rev*r/100;pending=e;gbLabel.textContent=g;priceLabel.textContent=p.toFixed(3);rateLabel.textContent=r;revenue.textContent=rev.toFixed(2);earned.textContent=e.toFixed(3);reserve.textContent=(rev-e).toFixed(2);pendingEl();gbStat.textContent=g+' GB';rateStat.textContent=r+'%'}
function pendingEl(){document.getElementById('pending').textContent=pending.toFixed(3)}
function draw(){document.getElementById('balance').textContent=bal.toFixed(3);pendingEl()}
function claim(){if(pending<=0)return;bal+=pending;pending=0;draw();walletNotice.textContent='Verified reward added to your spendable ORXYZ balance.'}
function buy(name,cost){if(bal<cost){walletNotice.textContent='Not enough ORXYZ for '+name+'.';return}bal-=cost;draw();walletNotice.textContent=name+' purchased in this prototype.'}
[gb,price,rate].forEach(x=>x.addEventListener('input',calc));calc();draw();
</script></body></html>""")


def control_page() -> HTMLResponse:
    return HTMLResponse("""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ORXYZ Control Center</title>
<style>
:root{--bg:#080a0c;--panel:#111519;--line:#252c31;--text:#f5f7f5;--muted:#8e979e;--lime:#d8ff45}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif}.shell{max-width:1180px;margin:auto;padding:24px}.nav{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:20px}.brand{font-weight:900;font-size:22px}.tag{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:8px 11px}.title{padding:48px 0 26px}.title h1{font-size:48px;letter-spacing:-.05em;margin:0 0 10px}.title p{color:var(--muted);max-width:720px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric,.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px}.metric small{display:block;color:var(--muted)}.metric b{display:block;margin-top:8px;font-size:26px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.panel h2{font-size:18px;margin-top:0}.row{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:13px 0;border-bottom:1px solid var(--line)}.row:last-child{border-bottom:0}.row span{color:var(--muted);font-size:13px}input[type=range]{width:100%;accent-color:var(--lime)}button{border:0;border-radius:10px;padding:10px 13px;font-weight:800;cursor:pointer}.primary{background:var(--lime);color:#111}.danger{background:#3a1719;color:#ffb9bd}.good{color:#a8e6b5}.warn{color:#f3d28a}.token{width:100%;background:#090c0e;color:white;border:1px solid var(--line);border-radius:10px;padding:11px}.muted{color:var(--muted);font-size:11px;line-height:1.5}.switch{display:flex;gap:8px;align-items:center}.dot{width:9px;height:9px;border-radius:50%;background:#7ee095}.table{width:100%;border-collapse:collapse;font-size:12px}.table th,.table td{text-align:left;padding:11px 6px;border-bottom:1px solid var(--line)}.table th{color:var(--muted)}@media(max-width:800px){.metrics{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}@media(max-width:520px){.metrics{grid-template-columns:1fr}}
</style></head><body><div class="shell">
<div class="nav"><div class="brand">ORXYZ Control</div><div class="tag">Operator Surface • Staged</div></div>
<div class="title"><h1>Network Control Center</h1><p>Manage the prototype reward economics, monitor bandwidth activity, and keep the system fail-closed before any real settlement is enabled.</p></div>
<div class="metrics"><div class="metric"><small>Active earners</small><b>128</b></div><div class="metric"><small>Verified GB today</small><b>4,820</b></div><div class="metric"><small>Pool revenue</small><b>$86.76</b></div><div class="metric"><small>ORXYZ credited</small><b>4.338</b></div></div>
<div class="grid"><section class="panel"><h2>Reward economics</h2><div class="row"><span>Reward share</span><b><span id="rr">5</span>%</b></div><input id="rewardRate" type="range" min="1" max="15" value="5"><div class="row"><span>Minimum verified GB</span><b>1 GB</b></div><div class="row"><span>Reward release</span><div class="switch"><span class="dot"></span><b class="good">staged</b></div></div><button class="primary" onclick="save()">Save prototype settings</button><p id="saved" class="muted"></p></section>
<section class="panel"><h2>Safety controls</h2><div class="row"><span>Live cash redemption</span><b class="warn">OFF</b></div><div class="row"><span>External transfers</span><b class="warn">OFF</b></div><div class="row"><span>Auto reward release</span><b class="warn">OFF</b></div><div class="row"><span>Bandwidth fraud review</span><b class="good">ON</b></div><button class="danger" onclick="freezeAll()">Freeze reward issuance</button><p id="freezeMsg" class="muted"></p></section>
<section class="panel"><h2>Operator authentication</h2><input class="token" type="password" id="opsToken" placeholder="Bearer token (not stored server-side by this page)"><p class="muted">Protected /ops API calls require the configured ORXYZ operator token. Keep secrets out of GitHub and browser URLs.</p><button onclick="checkHealth()">Check system health</button><pre id="health" class="muted"></pre></section>
<section class="panel"><h2>Recent earning activity</h2><table class="table"><thead><tr><th>User</th><th>GB</th><th>Revenue</th><th>Reward</th></tr></thead><tbody><tr><td>user-0182</td><td>42.1</td><td>$0.76</td><td>0.038 ORXYZ</td></tr><tr><td>user-0094</td><td>18.7</td><td>$0.34</td><td>0.017 ORXYZ</td></tr><tr><td>user-0201</td><td>64.3</td><td>$1.16</td><td>0.058 ORXYZ</td></tr></tbody></table></section></div>
<p class="muted" style="margin:24px 0">This control center currently models network controls; production reward issuance should be persisted in a durable ledger with authenticated users, auditable metering, anti-Sybil controls, and explicit settlement rules.</p>
</div><script>
const slider=document.getElementById('rewardRate');slider.oninput=()=>rr.textContent=slider.value;
function save(){saved.textContent='Prototype reward settings updated in this browser session.'}
function freezeAll(){freezeMsg.textContent='Prototype issuance frozen locally. Production requires a server-side kill switch.'}
async function checkHealth(){try{const r=await fetch('/health');const d=await r.json();health.textContent=JSON.stringify(d,null,2)}catch(e){health.textContent='Health check failed.'}}
</script></body></html>""")
