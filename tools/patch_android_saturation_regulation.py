from pathlib import Path
import re

p=Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s=p.read_text(encoding='utf-8')

if 'lastSaturationAt' not in s:
    s=s.replace('    private volatile int lastDisagreementScore=0;\n','    private volatile int lastDisagreementScore=0;\n    private volatile long lastSaturationAt=0L;\n',1)
    anchor='        lastDisagreementScore=prefs.getInt("core_last_disagreement_score",0);\n'
    if anchor not in s: raise SystemExit('missing saturation load anchor')
    s=s.replace(anchor,anchor+'        lastSaturationAt=prefs.getLong("core_last_saturation_at",0L);\n',1)

pattern=re.compile(r'    private void selfAssess\(long now\)\{.*?\n    \}\n\n    private void serviceBurst',re.S)
replacement=r'''    private void selfAssess(long now){
        String[][] pairs={{"evidence","counterpoint"},{"logic","novelty"},{"context","safety"},{"left_hemisphere","right_hemisphere"},{"consensus","interface"}};
        int disagree=0;StringBuilder details=new StringBuilder();
        for(String[] p:pairs){Core a=cores.get(p[0]),b=cores.get(p[1]);int delta=Math.abs(a.activeDirection-b.activeDirection);if(delta>0)disagree++;if(details.length()>0)details.append("; ");details.append(p[0]).append("/").append(p[1]).append(" d=").append(delta);}
        lastDisagreementScore=disagree;
        double grounding=(cores.get("evidence").cycles+cores.get("logic").cycles+cores.get("memory").cycles+cores.get("novelty").cycles)/4.0;
        double integration=(cores.get("counterpoint").cycles+cores.get("consensus").cycles+cores.get("interface").cycles)/3.0;
        double imbalance=integration/Math.max(1.0,grounding);
        long off=0,total=0;
        for(String n:new String[]{"counterpoint","left_hemisphere","right_hemisphere","consensus","interface"}){Core c=cores.get(n);for(int i=0;i<8;i++)total+=c.fano[i];for(int i=4;i<8;i++)off+=c.fano[i];}
        double exploratory=total>0?(double)off/total:0.0;
        boolean saturated=integration>=12.0 && (imbalance>=1.80 || exploratory>=0.45);
        String summary="Local self-assessment: "+disagree+" of "+pairs.length+" comparison pairs differ in active Fano direction ("+details+"). Integration/grounding="+String.format(Locale.US,"%.2f",imbalance)+"; exploratory pressure="+String.format(Locale.US,"%.2f",exploratory)+".";
        if(saturated && now-lastSaturationAt>=600_000L){
            lastSaturationAt=now;
            int removed=0;
            for(String n:new String[]{"counterpoint","left_hemisphere","right_hemisphere","consensus","interface"}){
                Core c=cores.get(n);Iterator<String> it=c.inbox.iterator();while(it.hasNext()){String x=it.next();String low=x==null?"":x.toLowerCase(Locale.ROOT);if(low.contains("[feedback-only]")||low.contains("global feedback")||low.contains("self-assessment")){it.remove();removed++;}}
            }
            String topic=(activeDeliberation!=null&&!activeDeliberation.trim().isEmpty())?activeDeliberation.trim():"the current unresolved retained task";
            remember("regulation","Saturation checkpoint: "+clip(topic,900)+". Integration/grounding="+String.format(Locale.US,"%.2f",imbalance)+", exploratory="+String.format(Locale.US,"%.2f",exploratory)+". Resume only with fresh evidence, a falsifiable test, a new constraint, or a genuinely new route rather than another summary.");
            cores.get("evidence").inbox.addFirst("SATURATION ESCAPE: find a concrete observation, source, measurement, or discriminating test for: "+topic);
            cores.get("logic").inbox.addFirst("SATURATION ESCAPE: reduce this to one explicit claim and derive a checkable consequence; reject unexplained parameter fitting: "+topic);
            cores.get("memory").inbox.addFirst("SATURATION ESCAPE: identify what information is actually missing from the retained task rather than restating prior summaries: "+topic);
            cores.get("novelty").inbox.addFirst("SATURATION ESCAPE: generate one genuinely new but testable route, not a paraphrase of the existing argument: "+topic);
            cores.get("safety").inbox.addFirst("SATURATION ESCAPE: preserve boundaries between measured fact, derivation, coincidence/fitting, and speculation: "+topic);
            summary+=" Saturation escape executed: retained a compact checkpoint, removed "+removed+" recursive queue item(s), reduced critique/integration input, and redirected the next pass toward fresh grounding.";
            record("consensus",null,"self_assessment",summary);
            serviceBurst(true);
            return;
        }
        record("consensus",null,"self_assessment",summary+(saturated?" Saturation is still present, but the correction cooldown is active so JANUS will wait for new evidence instead of repeatedly correcting itself.":" Grounding/integration balance remains within the current correction threshold."));
        if(disagree>0 && !saturated){
            String task=summary+" Re-examine current topic once; Evidence should seek support, Logic consistency, Counterpoint alternatives, and Consensus should preserve unresolved disagreement if it cannot be narrowed.";
            cores.get("evidence").inbox.addLast(task);cores.get("logic").inbox.addLast(task);cores.get("counterpoint").inbox.addLast(task);cores.get("consensus").inbox.addLast(task);
            serviceBurst(true);
        }
    }

    private void serviceBurst'''
s2,n=pattern.subn(replacement,s,count=1)
if n!=1: raise SystemExit('could not replace Android selfAssess for saturation regulation')
s=s2

# Persist the cooldown. Deliberation patches may already have extended this chain.
needle='.putInt("core_last_disagreement_score",lastDisagreementScore);'
if needle not in s: raise SystemExit('missing saturation persist anchor')
s=s.replace(needle,'.putLong("core_last_saturation_at",lastSaturationAt)\n                '+needle,1)

for token in ['SATURATION ESCAPE','Integration/grounding=','core_last_saturation_at','Saturation checkpoint']:
    if token not in s: raise SystemExit('saturation patch verification failed: '+token)

p.write_text(s,encoding='utf-8')
print('Android saturation escape regulation verified')
