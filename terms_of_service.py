"""Public JANUS Terms of Service / Acceptable Use page."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

@router.get("/terms", response_class=HTMLResponse)
def terms_page():
    return HTMLResponse("""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>JANUS Terms of Service</title><style>body{font-family:Arial,sans-serif;max-width:820px;margin:40px auto;padding:0 18px;line-height:1.55;color:#171717}h1,h2{line-height:1.2}small{color:#666}</style></head><body>
<h1>JANUS Terms of Service &amp; Acceptable Use Policy</h1><p><strong>Effective: 20 August 2026</strong></p>
<p>By creating an account or using JANUS, you agree to these Terms.</p>
<h2>What JANUS is</h2><p>JANUS is an experimental AI application for conversation, persistent continuity, memory, background reflection and functional metacognition/agency features. References to cores, thought, reflection, memory, agency or sleep/wake cycles describe software architecture and functional behaviour; they are not claims that JANUS is biologically alive, sentient or phenomenally conscious.</p>
<h2>Accounts</h2><p>You are responsible for your credentials and account activity. Do not impersonate others or use accounts deceptively. Access may be suspended where reasonably necessary for security, legal compliance or protection of users and infrastructure.</p>
<h2>AI-generated information</h2><p>JANUS can be inaccurate, incomplete or unexpected. Outputs are not guaranteed facts or professional advice. Users remain responsible for decisions based on outputs, particularly in medical, legal, financial, safety-critical or other high-impact situations.</p>
<h2>Persistent memory</h2><p>JANUS may store conversation-derived memory, activity, messages and continuity information while your account exists and may perform disclosed background processing. See the Privacy Policy for data handling and retention.</p>
<h2>Acceptable use</h2><p>Do not use JANUS to violate law or others' rights, harass or exploit people, commit fraud, distribute malware, gain unauthorized access, conduct cyber abuse, deliberately disrupt the service, evade access controls, deceptively impersonate others, obtain another user's private data, or facilitate serious wrongdoing.</p>
<h2>User content</h2><p>You retain rights you already hold in content you submit. You give JANUS the limited permission necessary to process, transmit, store and transform it to operate requested features, including conversation continuity and memory.</p>
<h2>Third-party services</h2><p>JANUS may rely on Render, OpenAI, Google and transactional email services. Availability can depend on those providers, whose own terms and privacy practices may apply.</p>
<h2>Development and availability</h2><p>JANUS is under active development. Features may change, malfunction, be interrupted or be removed. Security controls and usage limits may also change as the service develops.</p>
<h2>Account deletion</h2><p>You may delete your account in the JANUS app or use the public deletion-request process if you cannot access the app.</p>
<h2>Warranty and liability</h2><p>To the extent permitted by law, JANUS is provided "as is" and "as available" without a guarantee of uninterrupted or error-free operation. Nothing here excludes rights or guarantees that cannot legally be excluded, including applicable consumer-law rights. To the extent permitted by law, the operator is not liable for indirect, incidental, special or consequential loss arising solely from use of or inability to use JANUS.</p>
<h2>Law and contact</h2><p>These Terms are intended to operate subject to applicable Australian law and mandatory consumer and privacy protections. Public support/contact details and any more specific business/operator details will be added before commercial public launch.</p>
<p><small>The repository contains the canonical, more detailed Terms of Service and Acceptable Use Policy.</small></p>
</body></html>""")
