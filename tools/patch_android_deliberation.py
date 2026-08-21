from pathlib import Path

p=Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s=p.read_text(encoding='utf-8')

repls=[]
repls.append((
'    private static final long SELF_ASSESS_MS=120_000L;\n',
'    private static final long SELF_ASSESS_MS=120_000L;\n    private static final long DELIBERATION_MS=60_000L;\n'))
repls.append((
'    private volatile long lastBackgroundCycleAt=0L,lastAutonomousAt=0L,lastSelfAssessAt=0L;\n',
'    private volatile long lastBackgroundCycleAt=0L,lastAutonomousAt=0L,lastSelfAssessAt=0L,lastDeliberationAt=0L;\n    private volatile String activeDeliberation="";\n    private volatile int deliberationPassCount=0;\n'))
repls.append((
'        lastDisagreementScore=prefs.getInt("core_last_disagreement_score",0);\n',
'        lastDisagreementScore=prefs.getInt("core_last_disagreement_score",0);\n        activeDeliberation=prefs.getString("core_active_deliberation","");\n        deliberationPassCount=prefs.getInt("core_deliberation_pass_count",0);\n        lastDeliberationAt=prefs.getLong("core_last_deliberation_at",0L);\n'))
repls.append((
'        if("self_assessment".equals(type))return "Consensus compared internal positions and measured unresolved disagreement. "+clean;\n',
'        if("self_assessment".equals(type))return "Consensus compared internal positions and measured unresolved disagreement. "+clean;\n        if("deliberation_started".equals(type))return "JANUS retained this as active user-directed pondering: "+clean;\n        if("deliberation_pass".equals(type))return "JANUS deliberately revisited the retained user topic. "+clean;\n'))
repls.append((
'    synchronized void ingestUserMessage(String text){\n        String clean=text==null?"":text.trim();if(clean.isEmpty())return;\n        remember("user",clean);record("interface",null,"user_topic","Local society received user topic: "+clip(clean,600));\n',
'''    private static boolean deliberationIntent(String text){
        String t=text==null?"":text.toLowerCase(Locale.ROOT).replaceAll("\\\\s+"," ").trim();
        return t.matches(".*\\\\b(mull|ponder)\\\\b.*") || t.contains("keep thinking") || t.contains("continue thinking") || t.contains("think it over") || t.contains("think that over") || t.contains("give it some thought") || t.contains("give that some thought");
    }
    private String previousUserTopic(){
        Iterator<String> it=localMemories.descendingIterator();
        while(it.hasNext()){
            String x=it.next();
            if(x.startsWith("user: ")){
                String v=x.substring(6).trim();
                if(!deliberationIntent(v))return v;
            }
        }
        return "";
    }
    private String explicitDeliberationTopic(String clean){
        String t=clean==null?"":clean.trim();
        Matcher m=Pattern.compile("(?i)(?:keep|continue)\\\\s+(?:on\\\\s+)?thinking\\\\s+about\\\\s+(.+)$").matcher(t);
        if(m.find())return m.group(1).replaceAll("[.!?]+$","").trim();
        Matcher m2=Pattern.compile("(?i)(?:mull|ponder)\\\\s+(.+?)(?:\\\\s+over)?[.!?]*$").matcher(t);
        if(m2.find()){
            String x=m2.group(1).trim();
            if(!x.matches("(?i)it|that|this|this one|that one"))return x;
        }
        return "";
    }
    synchronized void ingestUserMessage(String text){
        String clean=text==null?"":text.trim();if(clean.isEmpty())return;
        if(deliberationIntent(clean)){
            String topic=explicitDeliberationTopic(clean);
            if(topic.isEmpty())topic=previousUserTopic();
            if(!topic.isEmpty()){
                activeDeliberation=clip(topic,1200); deliberationPassCount=0; lastDeliberationAt=0L;
                record("interface",null,"deliberation_started",activeDeliberation);
            }
        }
        remember("user",clean);record("interface",null,"user_topic","Local society received user topic: "+clip(clean,600));
'''))
repls.append((
'        if(now-lastAutonomousAt>=AUTONOMOUS_PULSE_MS){autonomousPulse(now);lastAutonomousAt=now;}\n',
'        if(!activeDeliberation.isEmpty() && now-lastDeliberationAt>=DELIBERATION_MS){deliberationPulse(now);lastDeliberationAt=now;}\n        if(now-lastAutonomousAt>=AUTONOMOUS_PULSE_MS){autonomousPulse(now);lastAutonomousAt=now;}\n'))
repls.append((
'    private void autonomousPulse(long now){\n',
'''    private void deliberationPulse(long now){
        if(activeDeliberation==null||activeDeliberation.trim().isEmpty())return;
        String topic=activeDeliberation.trim();
        for(String n:SPECIALISTS){
            Core c=cores.get(n);
            if(c==null)continue;
            c.inbox.removeIf(x->x!=null && (x.contains("[feedback-only]") || x.contains("global feedback")));
            String role;
            if("evidence".equals(n))role="check support, evidence and what would discriminate alternatives";
            else if("logic".equals(n))role="test internal consistency and implications";
            else if("counterpoint".equals(n))role="look for objections, alternatives and reasons the current preference may fail";
            else if("context".equals(n))role="relate it to the wider conversation, goals and history";
            else if("memory".equals(n))role="compare it with retained continuity and prior statements";
            else if("safety".equals(n))role="check privacy, safety and claim boundaries";
            else role="seek a genuinely new but testable angle rather than restating prior conclusions";
            c.inbox.addFirst("ACTIVE USER DELIBERATION: "+topic+"; assigned role: "+role+"; pass="+(deliberationPassCount+1));
        }
        deliberationPassCount++;
        record("interface",null,"deliberation_pass","Pass "+deliberationPassCount+" on “"+clip(topic,500)+"” was promoted ahead of routine feedback and sent through all seven specialists.");
        serviceBurst(true);
    }

    private void autonomousPulse(long now){
'''))
repls.append((
'                .putLong("core_last_autonomous_at",lastAutonomousAt).putLong("core_last_self_assess_at",lastSelfAssessAt)\n                .putInt("core_last_disagreement_score",lastDisagreementScore);\n',
'                .putLong("core_last_autonomous_at",lastAutonomousAt).putLong("core_last_self_assess_at",lastSelfAssessAt)\n                .putLong("core_last_deliberation_at",lastDeliberationAt).putString("core_active_deliberation",activeDeliberation).putInt("core_deliberation_pass_count",deliberationPassCount)\n                .putInt("core_last_disagreement_score",lastDisagreementScore);\n'))
repls.append((
'                .put("autonomous_pulse_seconds",AUTONOMOUS_PULSE_MS/1000L).put("self_assess_seconds",SELF_ASSESS_MS/1000L).put("last_disagreement_score",lastDisagreementScore).put("core_cycle_api_calls",0);\n',
'                .put("autonomous_pulse_seconds",AUTONOMOUS_PULSE_MS/1000L).put("self_assess_seconds",SELF_ASSESS_MS/1000L).put("last_disagreement_score",lastDisagreementScore).put("core_cycle_api_calls",0)\n                .put("active_deliberation",activeDeliberation).put("deliberation_pass_count",deliberationPassCount).put("deliberation_interval_seconds",DELIBERATION_MS/1000L);\n'))

for old,new in repls:
    if old not in s:
        raise SystemExit('anchor not found: '+old[:100])
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('Android deliberation priority patch applied')
