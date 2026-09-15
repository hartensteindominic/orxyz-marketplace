"""Public ORXYZ Trade Desk pages.

The browser never receives supplier cost, connected-account IDs, or release
controls. Buyers can only check out against a server-side approved quote code.
"""
from html import escape

from fastapi.responses import HTMLResponse


def trade_desk_page(*, checkout_enabled: bool) -> HTMLResponse:
    status = "Checkout live" if checkout_enabled else "Checkout staged"
    status_class = "live" if checkout_enabled else "staged"
    button_label = "Open secure checkout" if checkout_enabled else "Checkout not enabled yet"
    disabled = "" if checkout_enabled else "disabled"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <meta name=\"color-scheme\" content=\"dark\" />
  <title>ORXYZ Trade Desk</title>
  <meta name=\"description\" content=\"Secure quote checkout for approved ORXYZ industrial supply transactions.\" />
  <style>
    :root {{ --bg:#06080d; --panel:#0f131d; --line:#242b39; --text:#f6f8fb; --muted:#98a2b3; --cyan:#74e5e0; --violet:#a78bfa; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; color:var(--text); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif; background:radial-gradient(circle at 78% 4%,rgba(89,106,255,.18),transparent 29rem),radial-gradient(circle at 10% 34%,rgba(66,220,210,.08),transparent 24rem),linear-gradient(180deg,#06080d,#090c13 55%,#06080d); }}
    a {{ color:inherit; }}
    .shell {{ width:min(1120px,calc(100% - 36px)); margin:0 auto; }}
    header {{ padding:28px 0; border-bottom:1px solid rgba(255,255,255,.08); }}
    .brand {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
    .logo {{ font-weight:850; letter-spacing:.16em; font-size:16px; }}
    .badge {{ padding:8px 11px; border:1px solid var(--line); border-radius:999px; font-size:12px; color:#cbd3df; background:rgba(255,255,255,.03); }}
    .badge.live::before,.badge.staged::before {{ content:\"\"; display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; }}
    .badge.live::before {{ background:#76e4b5; box-shadow:0 0 14px rgba(118,228,181,.65); }}
    .badge.staged::before {{ background:#f2c16b; box-shadow:0 0 14px rgba(242,193,107,.45); }}
    main {{ padding:76px 0 90px; }}
    .hero {{ display:grid; grid-template-columns:minmax(0,1.05fr) minmax(340px,.8fr); gap:56px; align-items:center; }}
    .eyebrow {{ color:#aab3c2; font-size:11px; letter-spacing:.14em; text-transform:uppercase; font-weight:750; }}
    h1 {{ margin:18px 0 22px; font-size:clamp(52px,7vw,84px); line-height:.95; letter-spacing:-.06em; }}
    h1 span {{ display:block; color:#8e98aa; }}
    .lead {{ max-width:650px; color:var(--muted); font-size:18px; line-height:1.65; }}
    .points {{ display:flex; flex-wrap:wrap; gap:9px; margin-top:24px; }}
    .point {{ padding:8px 11px; border:1px solid rgba(255,255,255,.09); border-radius:999px; color:#9da7b8; font-size:11px; }}
    .card {{ border:1px solid var(--line); border-radius:28px; padding:28px; background:linear-gradient(160deg,rgba(255,255,255,.055),rgba(255,255,255,.018)); box-shadow:0 32px 70px rgba(0,0,0,.28); }}
    .card h2 {{ margin:0 0 10px; font-size:25px; letter-spacing:-.03em; }}
    .card p {{ margin:0 0 22px; color:var(--muted); line-height:1.55; font-size:14px; }}
    label {{ display:block; margin:14px 0 7px; color:#cbd3df; font-size:12px; font-weight:700; }}
    input {{ width:100%; min-height:48px; padding:0 14px; border:1px solid #2a3241; border-radius:13px; background:#0a0e16; color:white; font:inherit; outline:none; }}
    input:focus {{ border-color:#6fc9d2; box-shadow:0 0 0 3px rgba(111,201,210,.12); }}
    button {{ width:100%; min-height:50px; margin-top:18px; border:0; border-radius:999px; background:#f7f9fc; color:#080b11; font-weight:800; cursor:pointer; }}
    button:disabled {{ cursor:not-allowed; opacity:.46; }}
    .fine {{ margin-top:14px!important; font-size:11px!important; color:#717d90!important; }}
    .error {{ min-height:20px; margin-top:12px; color:#ffb3b3; font-size:12px; }}
    .rails {{ margin-top:78px; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .rail {{ border:1px solid var(--line); border-radius:22px; padding:24px; background:rgba(255,255,255,.025); }}
    .rail b {{ display:block; margin-bottom:9px; font-size:17px; }}
    .rail span {{ color:var(--muted); font-size:13px; line-height:1.6; }}
    footer {{ padding:30px 0 42px; border-top:1px solid rgba(255,255,255,.07); color:#778194; font-size:11px; line-height:1.6; }}
    @media (max-width:820px) {{ .hero {{ grid-template-columns:1fr; }} main {{ padding-top:52px; }} .rails {{ grid-template-columns:1fr; margin-top:52px; }} }}
  </style>
</head>
<body>
<header><div class=\"shell brand\"><div class=\"logo\">ORXYZ</div><div class=\"badge {status_class}\">{escape(status)}</div></div></header>
<main>
  <div class=\"shell\">
    <section class=\"hero\">
      <div>
        <div class=\"eyebrow\">Secure industrial trade checkout</div>
        <h1>Approved quote.<span>Controlled settlement.</span></h1>
        <p class=\"lead\">Buyers pay ORXYZ against a locked commercial quote. ORXYZ validates payment and the supplier purchase order before the supplier portion is released under the configured trade rail.</p>
        <div class=\"points\"><span class=\"point\">Quote price locked server-side</span><span class=\"point\">Supplier cost stays private</span><span class=\"point\">Direct shipment supported</span></div>
      </div>
      <div class=\"card\">
        <h2>Pay an ORXYZ quote</h2>
        <p>Use the quote code and buyer email shown on your approved ORXYZ quotation. Browser fields cannot change supplier cost or ORXYZ margin.</p>
        <form id=\"checkout-form\">
          <label for=\"quote\">Quote code</label>
          <input id=\"quote\" name=\"quote\" autocomplete=\"off\" placeholder=\"ORXYZ-Q-...\" required />
          <label for=\"email\">Buyer email</label>
          <input id=\"email\" name=\"email\" type=\"email\" autocomplete=\"email\" placeholder=\"buyer@company.com\" required />
          <button type=\"submit\" {disabled}>{escape(button_label)}</button>
          <div id=\"error\" class=\"error\" role=\"alert\"></div>
        </form>
        <p class=\"fine\">Payment does not change product specifications, Incoterms, warranty, lead time, taxes, duties, or other terms stated in the approved quote / PO documents.</p>
      </div>
    </section>
    <section class=\"rails\">
      <div class=\"rail\"><b>ORXYZ Instant</b><span>For specifically approved lower-risk Connect transactions. A supplier split can occur automatically only when the supplier is eligible, onboarded, and the quote authorizes that release mode.</span></div>
      <div class=\"rail\"><b>ORXYZ Trade</b><span>Default for custom or higher-value industrial orders. Buyer payment and supplier payout are separated so ORXYZ can verify the order and PO before funds move to the supplier.</span></div>
    </section>
  </div>
</main>
<footer><div class=\"shell\">ORXYZ · Buffalo, New York · Secure quote checkout for approved business transactions. Payment processing is provided by Stripe when live checkout is enabled. Supplier payout timing depends on the approved quote, payment status, supplier rail, and ORXYZ release controls.</div></footer>
<script>
  const form = document.getElementById('checkout-form');
  const error = document.getElementById('error');
  form?.addEventListener('submit', async (event) => {{
    event.preventDefault();
    error.textContent = '';
    const button = form.querySelector('button');
    button.disabled = true;
    const quote_id = document.getElementById('quote').value.trim();
    const buyer_email = document.getElementById('email').value.trim();
    try {{
      const res = await fetch('/checkout', {{ method:'POST', headers:{{'content-type':'application/json'}}, body:JSON.stringify({{quote_id,buyer_email}}) }});
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Checkout could not be created.');
      if (!data.url) throw new Error('Checkout URL was not returned.');
      window.location.assign(data.url);
    }} catch (e) {{
      error.textContent = e?.message || 'Checkout could not be created.';
      button.disabled = {str(not checkout_enabled).lower()};
    }}
  }});
</script>
</body>
</html>"""
    return HTMLResponse(html)


def result_page(*, success: bool) -> HTMLResponse:
    title = "Payment received" if success else "Checkout cancelled"
    body = (
        "Stripe has returned you to ORXYZ. Payment confirmation and supplier release are handled server-side; retain your quote and PO records."
        if success
        else "No supplier payout is triggered by a cancelled checkout. You can return to the trade desk when you are ready."
    )
    html = f"""<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)} · ORXYZ</title><body style=\"margin:0;min-height:100vh;display:grid;place-items:center;background:#06080d;color:#f7f8fb;font-family:system-ui,sans-serif\"><main style=\"width:min(680px,calc(100% - 36px));padding:34px;border:1px solid #252c39;border-radius:26px;background:#0f131d\"><div style=\"font-weight:850;letter-spacing:.16em\">ORXYZ</div><h1 style=\"font-size:44px;letter-spacing:-.04em;margin:34px 0 16px\">{escape(title)}</h1><p style=\"color:#98a2b3;line-height:1.7\">{escape(body)}</p><a href=\"/\" style=\"display:inline-block;margin-top:16px;color:#f7f8fb\">Return to trade desk →</a></main></body></html>"""
    return HTMLResponse(html)
