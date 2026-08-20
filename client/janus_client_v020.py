import json, os, threading, tkinter as tk
from tkinter import ttk, messagebox
from urllib import request, error, parse

APP_NAME='JANUS - Global 7-3-1 v0.20'
SERVER='https://janus-global-core.onrender.com'
CFG=os.path.join(os.path.expanduser('~'),'.janus','client.json')

class API:
    def call(self,method,path,payload=None,timeout=120):
        data=None if payload is None else json.dumps(payload).encode()
        q=request.Request(SERVER+path,data=data,headers={'Content-Type':'application/json','Accept':'application/json'},method=method)
        try:
            with request.urlopen(q,timeout=timeout) as r:return json.loads(r.read().decode() or '{}')
        except error.HTTPError as e: raise RuntimeError(e.read().decode(errors='replace') or str(e))
    def get(self,screen,user): return self.call('GET','/desktop/'+screen+'?'+parse.urlencode({'username':user}),timeout=30)

def load_cfg():
    try:
        with open(CFG,encoding='utf8') as f:return json.load(f)
    except:return {}

def save_cfg(x):
    os.makedirs(os.path.dirname(CFG),exist_ok=True)
    with open(CFG,'w',encoding='utf8') as f:json.dump(x,f,indent=2)

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.api=API();self.cfg=load_cfg();self.user=self.cfg.get('profile_id') or os.environ.get('USERNAME') or 'local-user';self.pages={};self.rows={};self.timer=None
        self.auto=tk.BooleanVar(value=self.cfg.get('auto_refresh',True));self.seconds=tk.IntVar(value=int(self.cfg.get('refresh_seconds',10)))
        self.title(APP_NAME);self.geometry('1180x760');self.minsize(940,620)
        top=ttk.Frame(self,padding=10);top.pack(fill='x');ttk.Label(top,text='JANUS',font=('Segoe UI',18,'bold')).pack(side='left');ttk.Label(top,text='Global 7→3→1').pack(side='left',padx=8);self.status=tk.StringVar(value='connecting…');ttk.Label(top,textvariable=self.status).pack(side='right')
        body=ttk.Frame(self);body.pack(fill='both',expand=True);nav=ttk.Frame(body,padding=8,width=175);nav.pack(side='left',fill='y');nav.pack_propagate(False);self.content=ttk.Frame(body,padding=12);self.content.pack(side='left',fill='both',expand=True)
        for label,key in [('Home','home'),('Chat','chat'),('Messages','messages'),('Observe','observe'),('Cores','cores'),('Memory','memory'),('Activity','activity'),('Settings','settings')]:ttk.Button(nav,text=label,command=lambda k=key:self.show(k)).pack(fill='x',pady=3)
        self.build_home();self.build_chat();self.build_list('messages','Messages','Background reflections and message candidates JANUS chose to surface');self.build_list('observe','Observe','Externalizable process notes');self.build_cores();self.build_list('memory','Memory','Trace → working → episodic → core');self.build_list('activity','Activity','Conversation, reflections, decisions and system events');self.build_settings();self.show('home');self.after(100,self.health)
    def page(self,k):
        f=ttk.Frame(self.content);self.pages[k]=f;return f
    def head(self,p,title,sub=''):
        ttk.Label(p,text=title,font=('Segoe UI',18,'bold')).pack(anchor='w');
        if sub:ttk.Label(p,text=sub).pack(anchor='w',pady=(0,10))
    def build_home(self):
        p=self.page('home');self.head(p,'Home','Persistent JANUS status');self.home=tk.Text(p,state='disabled',wrap='word',font=('Segoe UI',12),padx=10,pady=10);self.home.pack(fill='both',expand=True)
    def build_chat(self):
        p=self.page('chat');self.head(p,'Conversation','Enter sends • Shift+Enter adds a line');self.chat=tk.Text(p,state='disabled',wrap='word',font=('Segoe UI',11));self.chat.pack(fill='both',expand=True);row=ttk.Frame(p);row.pack(fill='x',pady=8);self.entry=tk.Text(row,height=4,wrap='word');self.entry.pack(side='left',fill='x',expand=True);self.entry.bind('<Return>',self.enter);self.entry.bind('<Shift-Return>',self.shift);ttk.Button(row,text='Send',command=self.send).pack(side='left',fill='y',padx=8);self.say('JANUS','Connected. Ready.')
    def build_list(self,k,title,sub):
        p=self.page(k);self.head(p,title,sub);tree=ttk.Treeview(p,columns=('time','type','summary'),show='headings');
        for c,w in [('time',150),('type',170),('summary',600)]:tree.heading(c,text=c.title());tree.column(c,width=w,stretch=c=='summary')
        tree.pack(fill='both',expand=True);tree.bind('<Double-1>',lambda e,key=k:self.detail(key));self.rows[k]=[];setattr(self,k+'_tree',tree)
        if k=='messages':
            bar=ttk.Frame(p);bar.pack(fill='x',pady=6);ttk.Button(bar,text='Mark read',command=lambda:self.message_state('read')).pack(side='left');ttk.Button(bar,text='Dismiss',command=lambda:self.message_state('dismissed')).pack(side='left',padx=6)
    def build_cores(self):
        p=self.page('cores');self.head(p,'Cores','7 specialist lenses → 3 synthesis bridges → 1 JANUS voice');self.cores=tk.Text(p,state='disabled',wrap='word',font=('Segoe UI',11));self.cores.pack(fill='both',expand=True)
    def build_settings(self):
        p=self.page('settings');self.head(p,'Settings','Desktop display and live updates');ttk.Checkbutton(p,text='Auto refresh current live screen',variable=self.auto,command=self.save).pack(anchor='w',pady=8);r=ttk.Frame(p);r.pack(anchor='w');ttk.Label(r,text='Refresh interval').pack(side='left');
        for n in (5,10,15,30,60):ttk.Radiobutton(r,text=f'{n}s',value=n,variable=self.seconds,command=self.save).pack(side='left',padx=4)
        self.settings_text=tk.Text(p,height=14,state='disabled',wrap='word');self.settings_text.pack(fill='x',pady=12)
    def settext(self,w,s):w.config(state='normal');w.delete('1.0','end');w.insert('end',s);w.config(state='disabled')
    def say(self,who,text):self.chat.config(state='normal');self.chat.insert('end',f'{who}\n{text}\n\n');self.chat.config(state='disabled');self.chat.see('end')
    def enter(self,e=None):self.send();return 'break'
    def shift(self,e=None):self.entry.insert('insert','\n');return 'break'
    def send(self):
        m=self.entry.get('1.0','end').strip()
        if not m:return
        self.entry.delete('1.0','end');self.say('You',m);self.status.set('thinking…')
        self.bg(lambda:self.api.call('POST','/desktop/chat',{'profile_id':self.user,'message':m}),lambda r:(self.say('JANUS',r.get('reply','')),self.status.set('online')))
    def show(self,k):
        for p in self.pages.values():p.pack_forget()
        self.pages[k].pack(fill='both',expand=True)
        if k!='chat':self.refresh(k)
        self.schedule(k)
    def refresh(self,k):
        if k=='home':return self.bg(lambda:self.api.get('home',self.user),self.render_home)
        if k=='cores':return self.bg(lambda:self.api.get('cores',self.user),self.render_cores)
        if k=='settings':return self.bg(lambda:self.api.get('settings',self.user),self.render_settings)
        self.bg(lambda:self.api.get(k,self.user),lambda r:self.render_list(k,r))
    def render_home(self,r):
        self.settext(self.home,f"Status: {str(r.get('status','active')).upper()}\nArchitecture: {r.get('architecture','7 → 3 → 1')}\nBackground cycle: {r.get('background_interval_minutes','?')} minutes\nUnread JANUS messages: {r.get('unread_messages',0)}\n\nLatest activity:\n{(r.get('latest_activity') or {}).get('detail','No activity yet.')}")
    def render_list(self,k,r):
        tree=getattr(self,k+'_tree');tree.delete(*tree.get_children());items=r.get('items',r.get('notes',[]));self.rows[k]=items
        for i,x in enumerate(items):
            typ=x.get('event_type') or x.get('role') or 'item';state=x.get('state');typ=('NEW · ' if state=='unread' else '')+typ;txt=x.get('detail') or x.get('content') or '';tree.insert('', 'end',iid=str(i),values=(x.get('created_at','')[:19].replace('T',' '),typ,txt.replace('\n',' ')[:180]))
    def render_cores(self,r):
        s='1 INTEGRATOR\n'+(r.get('one_integrator') or {}).get('description','')+'\n\n3 BRIDGES\n'+''.join(f'• {k}: {v}\n' for k,v in (r.get('three_bridges') or {}).items())+'\n7 LENSES\n'+''.join(f'• {k}: {v}\n' for k,v in (r.get('seven_roles') or {}).items());self.settext(self.cores,s)
    def render_settings(self,r):
        s=r.get('server',{});self.settext(self.settings_text,'Global background core\n'+f"Model: {s.get('model','?')}\nBackground worker: {s.get('background_worker')}\nInterval: {s.get('interval_minutes')} min\nMemory processing: {s.get('memory_processing')}\nSelf evaluation: {s.get('self_evaluation')}\nMessage queue: {s.get('message_queue')}\nExternal access: {s.get('external_access')}")
    def detail(self,k):
        tree=getattr(self,k+'_tree');sel=tree.selection()
        if not sel:return
        x=self.rows[k][int(sel[0])];messagebox.showinfo(k.title(),x.get('detail') or x.get('content') or json.dumps(x,indent=2))
    def message_state(self,state):
        sel=self.messages_tree.selection()
        if not sel:return
        x=self.rows['messages'][int(sel[0])];self.bg(lambda:self.api.call('POST',f"/desktop/messages/{x['id']}/state",{'profile_id':self.user,'state':state}),lambda r:self.refresh('messages'))
    def save(self):self.cfg.update(profile_id=self.user,auto_refresh=self.auto.get(),refresh_seconds=self.seconds.get());save_cfg(self.cfg);self.schedule(next((k for k,p in self.pages.items() if p.winfo_ismapped()),'home'))
    def schedule(self,k):
        if self.timer:
            try:self.after_cancel(self.timer)
            except:pass
        self.timer=None
        if self.auto.get() and k in ('home','messages','observe','memory','activity'):self.timer=self.after(max(5,self.seconds.get())*1000,lambda:(self.refresh(k),self.schedule(k)))
    def bg(self,fn,done):
        def run():
            try:r=fn();self.after(0,lambda:done(r))
            except Exception as e:self.after(0,lambda:self.status.set('error: '+str(e)[:100]))
        threading.Thread(target=run,daemon=True).start()
    def health(self):self.bg(lambda:self.api.call('GET','/health',timeout=15),lambda r:self.status.set('online'))

if __name__=='__main__':App().mainloop()
