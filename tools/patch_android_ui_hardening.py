from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android UI hardening patch pattern missing: ' + old[:140])
    h = h.replace(old, new, 1)

# Add a theme-safe variable layer without rewriting the mature base stylesheet.
style_end = '</style></head><body>'
theme_css = r'''
<style id="janusThemeLayer">
:root{
  --janus-bg:#ffffff;--janus-surface:#ffffff;--janus-soft:#eeeeee;--janus-text:#171717;
  --janus-muted:#666666;--janus-border:#d7d7d7;--janus-accent:#222222;--janus-accent-text:#ffffff;
  --janus-user:#dcecff;--janus-danger:#9b1c1c;
}
html[data-theme="dark"]{color-scheme:dark;--janus-bg:#121212;--janus-surface:#1d1d1d;--janus-soft:#292929;--janus-text:#f2f2f2;--janus-muted:#b7b7b7;--janus-border:#424242;--janus-user:#24364b;--janus-accent-text:#ffffff}
html[data-theme="system"]{color-scheme:light dark}
@media(prefers-color-scheme:dark){html[data-theme="system"]{--janus-bg:#121212;--janus-surface:#1d1d1d;--janus-soft:#292929;--janus-text:#f2f2f2;--janus-muted:#b7b7b7;--janus-border:#424242;--janus-user:#24364b;--janus-accent-text:#ffffff}}
html,body{background:var(--janus-bg)!important;color:var(--janus-text)!important}.top,.nav,.sendbar,.login{background:var(--janus-surface)!important;color:var(--janus-text)!important;border-color:var(--janus-border)!important}.card,.options button,.filters button,.login input,.login select,.sendbar textarea,input,select,textarea{background:var(--janus-surface)!important;color:var(--janus-text)!important;border-color:var(--janus-border)!important}.janus{background:var(--janus-soft)!important}.user{background:var(--janus-user)!important}.system{background:var(--janus-surface)!important;color:var(--janus-muted)!important}.small,.status,.thought-label,.technical{color:var(--janus-muted)!important}.nav button{background:var(--janus-surface)!important;color:var(--janus-text)!important}.nav button.on,.filters button.on,.action,.badge,.new-thoughts{background:var(--janus-accent)!important;color:var(--janus-accent-text)!important}.secondary{background:var(--janus-soft)!important;color:var(--janus-text)!important}.item,.top,.nav,.sendbar,.card{border-color:var(--janus-border)!important}.error{color:var(--janus-danger)!important}.theme-row{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:9px}.theme-row label{display:block}.theme-row select,.theme-row input[type="color"]{width:100%;min-height:42px;margin-top:4px;border:1px solid var(--janus-border);border-radius:9px}.theme-preview{height:10px;border-radius:7px;background:var(--janus-accent);margin-top:8px}.theme-note{margin-top:8px}
@media(max-width:430px){.theme-row{grid-template-columns:1fr}}
</style>
'''
replace_once(style_end, '</style>' + theme_css + '</head><body>')

server_settings = '<div id="serverSettings" class="card"></div>'
theme_panel = '''<div class="card" id="themeSettings"><b>Interface theme</b><p class="small">Stored on this device. Theme choices do not change JANUS cognition or server state.</p><div class="theme-row"><label>Appearance<select id="themeMode" onchange="saveThemeSettings()"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><label>Accent colour<input id="themeAccent" type="color" value="#222222" onchange="saveThemeSettings()"></label></div><div class="theme-row"><label>User message colour<input id="themeUser" type="color" value="#dcecff" onchange="saveThemeSettings()"></label><label>Surface tint<input id="themeSurface" type="color" value="#ffffff" onchange="saveThemeSettings()"></label></div><div class="theme-preview"></div><div class="theme-note small">Readable text contrast is selected automatically for the accent. Reset returns to JANUS defaults.</div><button class="action secondary" style="margin-top:9px" onclick="resetThemeSettings()">Reset theme</button></div>'''
replace_once(server_settings, theme_panel + server_settings)

js = r'''
function validHex(v,fallback){return /^#[0-9a-fA-F]{6}$/.test(String(v||''))?String(v):fallback}
function contrastText(hex){let h=validHex(hex,'#222222').slice(1),r=parseInt(h.slice(0,2),16),g=parseInt(h.slice(2,4),16),b=parseInt(h.slice(4,6),16);return ((r*299+g*587+b*114)/1000)>150?'#111111':'#ffffff'}
function themeDefaults(mode){let dark=mode==='dark'||(mode==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);return {surface:dark?'#1d1d1d':'#ffffff',user:dark?'#24364b':'#dcecff'}}
function applyThemeSettings(){
  let mode=localStorage.janusThemeMode||'system',accent=validHex(localStorage.janusThemeAccent,'#222222'),defs=themeDefaults(mode),surface=validHex(localStorage.janusThemeSurface,defs.surface),user=validHex(localStorage.janusThemeUser,defs.user),root=document.documentElement;
  root.dataset.theme=mode;root.style.setProperty('--janus-accent',accent);root.style.setProperty('--janus-accent-text',contrastText(accent));root.style.setProperty('--janus-surface',surface);root.style.setProperty('--janus-user',user);
  if(document.getElementById('themeMode'))themeMode.value=mode;if(document.getElementById('themeAccent'))themeAccent.value=accent;if(document.getElementById('themeSurface'))themeSurface.value=surface;if(document.getElementById('themeUser'))themeUser.value=user;
}
function saveThemeSettings(){localStorage.janusThemeMode=themeMode.value;localStorage.janusThemeAccent=themeAccent.value;localStorage.janusThemeSurface=themeSurface.value;localStorage.janusThemeUser=themeUser.value;applyThemeSettings()}
function resetThemeSettings(){['janusThemeMode','janusThemeAccent','janusThemeSurface','janusThemeUser'].forEach(k=>localStorage.removeItem(k));applyThemeSettings()}
applyThemeSettings();
try{if(window.matchMedia){window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if((localStorage.janusThemeMode||'system')==='system')applyThemeSettings()})}}catch(e){}
'''
replace_once('</script>', js + '\n</script>')

html.write_text(h, encoding='utf-8')
print('Applied Android Phase 3 theme/UI hardening patch')
