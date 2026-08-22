from pathlib import Path

java = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
s = java.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global s
    if old not in s:
        raise SystemExit('Android attachment patch pattern missing: ' + old[:90])
    s = s.replace(old, new, 1)


replace_once(
    'import android.content.Intent;\n',
    'import android.content.Intent;\nimport android.database.Cursor;\n'
)
replace_once(
    'import android.net.Uri;\n',
    'import android.net.Uri;\nimport android.provider.OpenableColumns;\nimport android.util.Base64;\n'
)
replace_once(
    'import java.io.BufferedReader;\n',
    'import java.io.BufferedReader;\nimport java.io.ByteArrayOutputStream;\nimport java.io.InputStream;\n'
)
replace_once(
    '    private static final int RC_GOOGLE_COMPAT = 731;\n',
    '    private static final int RC_GOOGLE_COMPAT = 731;\n    private static final int RC_FILE_PICKER = 732;\n    private static final int MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024;\n'
)

insert_methods = r'''
    private void startFilePicker() {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("*/*");
            startActivityForResult(intent, RC_FILE_PICKER);
        } catch (Exception e) {
            deliverFilePickerError("Unable to open the file picker: " + e.getMessage());
        }
    }

    private String displayName(Uri uri) {
        String name = "attachment";
        Cursor cursor = null;
        try {
            cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null);
            if (cursor != null && cursor.moveToFirst()) {
                int i = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (i >= 0 && cursor.getString(i) != null && !cursor.getString(i).isBlank()) name = cursor.getString(i);
            }
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
        return name;
    }

    private byte[] readAttachment(Uri uri) throws Exception {
        try (InputStream input = getContentResolver().openInputStream(uri); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            if (input == null) throw new IllegalArgumentException("The selected file could not be opened.");
            byte[] buffer = new byte[32768];
            int total = 0, n;
            while ((n = input.read(buffer)) >= 0) {
                total += n;
                if (total > MAX_ATTACHMENT_BYTES) throw new IllegalArgumentException("JANUS currently accepts files up to 8 MiB.");
                out.write(buffer, 0, n);
            }
            if (total == 0) throw new IllegalArgumentException("Empty files are not supported.");
            return out.toByteArray();
        }
    }

    private void deliverFilePickerError(String message) {
        final String js = "if(window.__janusFilePickError)window.__janusFilePickError(" + quote(message == null ? "File selection failed." : message) + ")";
        runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
    }

    private void deliverPickedFile(Uri uri) {
        pool.submit(() -> {
            try {
                byte[] bytes = readAttachment(uri);
                String mime = getContentResolver().getType(uri);
                if (mime == null || mime.isBlank()) mime = "application/octet-stream";
                JSONObject item = new JSONObject();
                item.put("filename", displayName(uri));
                item.put("mime_type", mime);
                item.put("data_base64", Base64.encodeToString(bytes, Base64.NO_WRAP));
                final String js = "if(window.__janusFilePicked)window.__janusFilePicked(JSON.parse(" + quote(item.toString()) + "))";
                runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
            } catch (Exception e) {
                deliverFilePickerError(e.getMessage());
            }
        });
    }

'''
replace_once(
    '    private void startGoogleSignIn() { requestGoogleCredential(false); }\n\n',
    '    private void startGoogleSignIn() { requestGoogleCredential(false); }\n\n' + insert_methods
)

old_on_result = '''        super.onActivityResult(requestCode, resultCode, data);\n        if (requestCode != RC_GOOGLE_COMPAT) return;\n'''
new_on_result = '''        super.onActivityResult(requestCode, resultCode, data);\n        if (requestCode == RC_FILE_PICKER) {\n            if (resultCode == RESULT_OK && data != null && data.getData() != null) deliverPickedFile(data.getData());\n            else deliverFilePickerError("File selection was cancelled.");\n            return;\n        }\n        if (requestCode != RC_GOOGLE_COMPAT) return;\n'''
replace_once(old_on_result, new_on_result)
replace_once(
    '        @JavascriptInterface public void googleSignIn() { runOnUiThread(MainActivity.this::startGoogleSignIn); }\n',
    '        @JavascriptInterface public void googleSignIn() { runOnUiThread(MainActivity.this::startGoogleSignIn); }\n        @JavascriptInterface public void pickFile() { runOnUiThread(MainActivity.this::startFilePicker); }\n'
)
java.write_text(s, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def hreplace(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android attachment HTML patch pattern missing: ' + old[:100])
    h = h.replace(old, new, 1)

hreplace(
    '.sendbar button,.action{border:0;border-radius:9px;background:#222;color:#fff;padding:9px 12px}',
    '.sendbar button,.action{border:0;border-radius:9px;background:#222;color:#fff;padding:9px 12px}.attachment-strip{position:fixed;bottom:calc(var(--safe) + var(--nav) + 74px);left:10px;right:10px;z-index:17;display:flex;gap:6px;overflow-x:auto;padding:4px}.attachment-chip{white-space:nowrap;border:1px solid #ccc;background:#fff;border-radius:14px;padding:6px 9px;font-size:12px}.attachment-chip button{border:0;background:transparent;padding:0 0 0 6px;color:#555}'
)
hreplace(
    '<div id="chat" class="view active"><h2>Chat</h2><div id="chatlog" class="chat"></div><div class="sendbar"><textarea id="composer" placeholder="Message JANUS"></textarea><button onclick="sendChat()">Send</button></div></div>',
    '<div id="chat" class="view active"><h2>Chat</h2><div id="chatlog" class="chat"></div><div id="attachmentStrip" class="attachment-strip hidden"></div><div class="sendbar"><button id="attachBtn" class="secondary" onclick="pickAttachment()" title="Attach file">＋</button><textarea id="composer" placeholder="Message JANUS"></textarea><button onclick="sendChat()">Send</button></div></div>'
)
hreplace(
    "let profile='',token=localStorage.janusToken||'',accountId=localStorage.janusAccountId||'',seq=0,pending={},timer=null,observeMode='all',lastObserveKey='';const main=",
    "let profile='',token=localStorage.janusToken||'',accountId=localStorage.janusAccountId||'',seq=0,pending={},timer=null,observeMode='all',lastObserveKey='',pendingAttachments=[];const main="
)

old_send = "async function sendChat(){let m=composer.value.trim();if(!m)return;composer.value='';addMsg('You',m);setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);setStatus('Interface active');refresh('messages')}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}composer.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat()}});"
new_send = "function renderAttachments(){if(!pendingAttachments.length){attachmentStrip.innerHTML='';attachmentStrip.classList.add('hidden');return}attachmentStrip.classList.remove('hidden');attachmentStrip.innerHTML=pendingAttachments.map((x,i)=>'<span class=\"attachment-chip\">📎 '+esc(x.filename||'file')+'<button onclick=\"removeAttachment('+i+')\">×</button></span>').join('')}function removeAttachment(i){pendingAttachments.splice(i,1);renderAttachments()}function pickAttachment(){if(pendingAttachments.length>=4){addMsg('System','Up to 4 files can be attached to one Chat turn.');return}setStatus('Choose a file');Android.pickFile()}window.__janusFilePickError=function(msg){if(String(msg||'').toLowerCase().indexOf('cancel')<0)addMsg('System',msg||'File selection failed.');setStatus('Interface active')};window.__janusFilePicked=async function(file){setStatus('Uploading attachment');try{let r=await api('POST','/files/upload',file);if(r&&r.file){pendingAttachments.push(r.file);renderAttachments();setStatus('Attachment ready')}else throw new Error('Server did not confirm the upload.')}catch(e){addMsg('System','Attachment upload failed. '+e.message);setStatus('Interface active')}};async function sendChat(){let m=composer.value.trim(),atts=pendingAttachments.slice();if(!m&&!atts.length)return;if(!m)m='Please assess the attached file or files.';composer.value='';let shown=m+(atts.length?'\\n\\n'+atts.map(x=>'[Attached: '+(x.filename||'file')+']').join('\\n'):'');addMsg('You',shown);pendingAttachments=[];renderAttachments();setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,attachment_ids:atts.map(x=>x.id),local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);setStatus('Interface active');refresh('messages')}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}composer.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat()}});"
hreplace(old_send, new_send)
hreplace(
    "function googleComingSoon(){authMessage.textContent='Google sign-in is configured through the JANUS account system.'}function logout(){token='';accountId='';profile='';",
    "function googleComingSoon(){authMessage.textContent='Google sign-in is configured through the JANUS account system.'}function logout(){pendingAttachments=[];renderAttachments();token='';accountId='';profile='';"
)
html.write_text(h, encoding='utf-8')
print('Applied Android file attachment picker/upload/chat patch')
