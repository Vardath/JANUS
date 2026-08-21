from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')

# 1) Natural explicit completion. Keep processing the user's completion message normally,
# but stop carrying the prior deliberation into future autonomous cycles.
old = '''    synchronized void ingestUserMessage(String text){
        String clean=text==null?"":text.trim();if(clean.isEmpty())return;
        if(deliberationIntent(clean)){
'''
new = '''    private static boolean deliberationStopIntent(String text){
        String t=text==null?"":text.toLowerCase(Locale.ROOT).replaceAll("\\s+"," ").trim();
        return t.contains("stop pondering") || t.contains("stop thinking about") || t.contains("you can stop thinking") || t.contains("don't keep thinking") || t.contains("do not keep thinking") || t.contains("done pondering");
    }
    synchronized void ingestUserMessage(String text){
        String clean=text==null?"":text.trim();if(clean.isEmpty())return;
        if(deliberationStopIntent(clean) && activeDeliberation!=null && !activeDeliberation.isEmpty()){
            String finished=activeDeliberation;
            activeDeliberation=""; deliberationPassCount=0; lastDeliberationAt=0L;
            record("interface",null,"deliberation_completed","Stopped retained user-directed pondering: "+clip(finished,500));
        }
        if(deliberationIntent(clean)){
'''
if old not in s:
    raise SystemExit('ingestUserMessage deliberation anchor not found')
s = s.replace(old, new, 1)

# 2) Human-readable completion event.
old = '        if("deliberation_pass".equals(type))return "JANUS deliberately revisited the retained user topic. "+clean;\n'
new = old + '        if("deliberation_completed".equals(type))return "JANUS stopped carrying the delegated pondering task. "+clean;\n'
if old not in s:
    raise SystemExit('deliberation event externalization anchor not found')
s = s.replace(old, new, 1)

# 3) While a delegated deliberation is active, it owns the autonomous slot. Generic
# memory-resurfacing and self-assessment are deliberately suppressed so they cannot
# become the primary topic and re-create a self-referential feedback loop.
old = '''        if(!activeDeliberation.isEmpty() && now-lastDeliberationAt>=DELIBERATION_MS){deliberationPulse(now);lastDeliberationAt=now;}
        if(now-lastAutonomousAt>=AUTONOMOUS_PULSE_MS){autonomousPulse(now);lastAutonomousAt=now;}
        if(now-lastSelfAssessAt>=SELF_ASSESS_MS){selfAssess(now);lastSelfAssessAt=now;}
'''
new = '''        if(activeDeliberation!=null && !activeDeliberation.isEmpty()){
            if(now-lastDeliberationAt>=DELIBERATION_MS){deliberationPulse(now);lastDeliberationAt=now;}
            // Keep generic autonomous/self-assessment clocks current without running them;
            // the user-delegated task remains the primary autonomous work item.
            lastAutonomousAt=now; lastSelfAssessAt=now;
        }else{
            if(now-lastAutonomousAt>=AUTONOMOUS_PULSE_MS){autonomousPulse(now);lastAutonomousAt=now;}
            if(now-lastSelfAssessAt>=SELF_ASSESS_MS){selfAssess(now);lastSelfAssessAt=now;}
        }
'''
if old not in s:
    raise SystemExit('tick deliberation scheduler anchor not found')
s = s.replace(old, new, 1)

# 4) Replace the deliberation pass body. Clear only stale feedback/self-reference from
# every queue, preserve unrelated/user work, then inject the delegated task into all
# seven specialists at the head of their queues.
start = s.find('    private void deliberationPulse(long now){')
end = s.find('\n    private void autonomousPulse(long now){', start)
if start < 0 or end < 0:
    raise SystemExit('deliberationPulse boundaries not found')
replacement = '''    private void deliberationPulse(long now){
        if(activeDeliberation==null||activeDeliberation.trim().isEmpty())return;
        String topic=activeDeliberation.trim();
        for(Core q:cores.values()){
            q.inbox.removeIf(x->x!=null && (x.contains("[feedback-only]") || x.contains("global feedback") || x.contains("self-assessment") || x.contains("self assessment")));
        }
        for(String n:SPECIALISTS){
            Core c=cores.get(n);
            if(c==null)continue;
            String role;
            if("evidence".equals(n))role="check support, evidence, examples, and what would discriminate alternatives";
            else if("logic".equals(n))role="test internal consistency, implications, and decision criteria";
            else if("counterpoint".equals(n))role="seek objections, alternatives, and reasons the current preference could fail";
            else if("context".equals(n))role="relate it to the user's actual question, goals, history, and surrounding conversation";
            else if("memory".equals(n))role="compare it with retained continuity and prior relevant statements without merely repeating them";
            else if("safety".equals(n))role="check privacy, safety, claim boundaries, and unintended consequences";
            else role="seek a genuinely new, useful, testable angle rather than summarizing prior output";
            c.inbox.addFirst("PRIMARY USER DELIBERATION: "+topic+"; assigned role: "+role+"; pass="+(deliberationPassCount+1)+"; routine telemetry is supporting context only");
        }
        deliberationPassCount++;
        record("interface",null,"deliberation_pass","Primary deliberation pass "+deliberationPassCount+" on “"+clip(topic,500)+"” replaced routine autonomous/self-assessment work and was sent through all seven specialists.");
        serviceBurst(true);
    }
'''
s = s[:start] + replacement + s[end:]

required = [
    'PRIMARY USER DELIBERATION:',
    'routine telemetry is supporting context only',
    'lastAutonomousAt=now; lastSelfAssessAt=now;',
    'deliberationStopIntent',
    'deliberation_completed',
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('primary deliberation verification missing: '+repr(missing))

p.write_text(s, encoding='utf-8')
print('Android primary deliberation scheduler patch applied and verified')
