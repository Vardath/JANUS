from pathlib import Path
import re

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')

if 'private static String fanoOrientationName(int d)' not in s:
    pattern = re.compile(r'    private String think\(Core c\)\{.*?\n    \}\n\n    private synchronized void send', re.S)
    replacement = r'''    private static String fanoOrientationName(int d){
        switch(d){
            case 1:return "grounding"; case 2:return "structure"; case 3:return "synthesis";
            case 4:return "alternative"; case 5:return "continuity"; case 6:return "novelty";
            case 7:return "boundary"; default:return "neutral";
        }
    }
    private static String fanoDirective(int d){
        switch(d){
            case 1:return "prioritize concrete support, observations, sources, measurements and explicit assumptions";
            case 2:return "prioritize causal structure, constraints, consistency and relations among parts";
            case 3:return "seek a coherent synthesis showing how supported pieces fit together";
            case 4:return "generate a serious alternative, counterfactual or failure mode before accepting the current view";
            case 5:return "use temporal, historical and memory continuity; compare the present state with what persisted before";
            case 6:return "seek a non-obvious but testable analogy, connection or new line of inquiry";
            case 7:return "stress uncertainty, scope, safety and epistemic boundaries; separate known, inferred and speculative claims";
            default:return "stay conservative and do not add unsupported interpretation";
        }
    }
    private static int fanoDirectionFromText(String text){
        Matcher m=Pattern.compile("\\bFano\\s+d([0-7])\\b",Pattern.CASE_INSENSITIVE).matcher(text==null?"":text);
        return m.find()?Integer.parseInt(m.group(1)):0;
    }
    private static int fanoCompletion(List<String> inputs){
        int a=0,b=0;
        for(String t:inputs){int d=fanoDirectionFromText(t);if(d==0)continue;if(a==0)a=d;else if(d!=a){b=d;break;}}
        return a!=0&&b!=0?((a^b)&7):0;
    }
    private static String fanoReadableState(String raw){
        Matcher m=Pattern.compile("Fano d([0-7])=([^;]+);.*?pressure=([a-z]+)",Pattern.CASE_INSENSITIVE).matcher(raw==null?"":raw);
        if(!m.find())return "";
        return "Fano orientation: "+m.group(2)+" (d"+m.group(1)+"); "+m.group(3)+" processing pressure is dominant.";
    }
    private static String fanoFocus(List<String> inputs,int d){
        if(inputs==null||inputs.isEmpty())return "maintenance / retained state";
        String[] markers;
        switch(d){
            case 1:markers=new String[]{"evidence","source","observed","recorded","measured","fact","data","support","verified"};break;
            case 2:markers=new String[]{"because","therefore","causal","structure","constraint","consistent","logic","relation","mechanism"};break;
            case 3:markers=new String[]{"combine","together","synthesis","integrate","shared","pattern","fit","connect"};break;
            case 4:markers=new String[]{"alternative","counter","however","but","fails","wrong","coincidence","instead","other"};break;
            case 5:markers=new String[]{"memory","history","before","previous","retained","continuity","earlier","persist"};break;
            case 6:markers=new String[]{"novel","new","unusual","analogy","curious","explore","unexpected","hypothesis"};break;
            case 7:markers=new String[]{"uncertain","unknown","boundary","safety","privacy","risk","speculative","tentative","claim"};break;
            default:return clip(inputs.get(0),320);
        }
        int best=0,bestScore=-1,bestBreadth=-1;
        for(int i=0;i<inputs.size();i++){
            String low=inputs.get(i).toLowerCase(Locale.ROOT);int score=0;for(String w:markers)if(low.contains(w))score++;
            int breadth=d==6?terms(low).size():0;
            if(score>bestScore||(score==bestScore&&breadth>bestBreadth)){best=i;bestScore=score;bestBreadth=breadth;}
        }
        return clip(inputs.get(best),320);
    }

    private String think(Core c){
        List<String> inputs=new ArrayList<>();while(!c.inbox.isEmpty()&&inputs.size()<8)inputs.add(c.inbox.pollFirst());
        fanoIngest(c,inputs);
        boolean integrating=Arrays.asList("left_hemisphere","right_hemisphere","consensus","interface").contains(c.name);
        int completion=integrating?fanoCompletion(inputs):0;
        if(completion>0){c.fano[completion]+=2;long max=-1;int idx=0;for(int i=0;i<8;i++)if(c.fano[i]>max){max=c.fano[i];idx=i;}c.activeDirection=idx;}
        long line=c.fano[1]+c.fano[2]+c.fano[3],off=c.fano[4]+c.fano[5]+c.fano[6]+c.fano[7],total=Math.max(1,c.fano[0]+line+off);
        double conservative=(double)c.fano[0]/total,coherent=(double)line/total,exploratory=(double)off/total;
        String pressure=conservative>=coherent&&conservative>=exploratory?"conservative":coherent>=exploratory?"coherent":"exploratory";
        String topic=fanoFocus(inputs,c.activeDirection);
        String roleNote;
        switch(c.name){
            case "evidence": roleNote="grounding check: separate recorded support from inference"; break;
            case "logic": roleNote="consistency check: look for incompatible assumptions or causal gaps"; break;
            case "counterpoint": roleNote="challenge: search for alternatives, coincidence and failure modes"; break;
            case "context": roleNote="context check: relate the topic to prior goals, history and environment"; break;
            case "memory": roleNote="continuity check: compare with retained local topics and unfinished work"; break;
            case "safety": roleNote="boundary check: privacy, security and harmful failure modes"; break;
            case "novelty": roleNote="connection search: look for an unusual but testable relation"; break;
            case "left_hemisphere": roleNote="analytic synthesis of evidence/logic/counterpoint inputs"; break;
            case "right_hemisphere": roleNote="contextual synthesis of context/memory/novelty inputs"; break;
            case "consensus": roleNote="integration: combine hemispheres while preserving unresolved disagreement"; break;
            default: roleNote="interface update: expose only a concise externalizable state";
        }
        String out=c.name+": "+roleNote+"; Fano d"+c.activeDirection+"="+fanoOrientationName(c.activeDirection)+"; control="+fanoDirective(c.activeDirection)+"; pressure="+pressure+" ("+String.format(Locale.US,"%.2f/%.2f/%.2f",conservative,coherent,exploratory)+"); 1|3|4="+c.fano[0]+"|"+line+"|"+off+(completion>0?"; line-completion=d"+completion:"")+"; topic="+topic+"; processed "+inputs.size()+" peer inputs";
        if(("memory".equals(c.name)||"novelty".equals(c.name)||"consensus".equals(c.name))&&!inputs.isEmpty())remember("core:"+c.name,out);
        return out;
    }

    private synchronized void send'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit('Could not structurally replace Android think() for Fano semantics')
    s = s2

old = '            return topic.isEmpty()?base:base+" Current focus: "+topic+".";\n'
new = '            String visible=topic.isEmpty()?base:base+" Current focus: "+topic+"."; String fs=fanoReadableState(raw); return fs.isEmpty()?visible:visible+" "+fs;\n'
if old in s:
    s = s.replace(old, new, 1)
elif 'fanoReadableState(raw)' not in s:
    raise SystemExit('Could not patch readable Observe Fano state')

required = [
    'fanoOrientationName', 'fanoDirective', 'fanoFocus', 'fanoCompletion',
    'fanoReadableState(raw)', 'control=', 'pressure=', 'line-completion=d'
]
for token in required:
    if token not in s:
        raise SystemExit('Fano semantic patch verification failed: '+token)

p.write_text(s, encoding='utf-8')
print('Operational Android Fano semantics verified')
