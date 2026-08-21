from pathlib import Path

p = Path('android/app/src/main/assets/index.html')
s = p.read_text(encoding='utf-8')
marker = "let profile='',token=localStorage.janusToken||'',accountId=localStorage.janusAccountId||'',seq=0,pending={},timer=null,observeMode='all',lastObserveKey='';"
guard = """(function(){let legacyLocalEvidence=null;Object.defineProperty(window,'janusLocalEvidence',{configurable:false,get:function(){return function(p){if(p==='observe')return;if(legacyLocalEvidence)return legacyLocalEvidence(p);};},set:function(fn){legacyLocalEvidence=fn;}});})();\n"""
if guard.strip() not in s:
    if marker not in s:
        raise SystemExit('Observe guard insertion point not found')
    s = s.replace(marker, guard + marker, 1)
    p.write_text(s, encoding='utf-8')
print('Observe legacy override guard verified')