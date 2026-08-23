from pathlib import Path

java = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
s = java.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global s
    if old not in s:
        raise SystemExit('Android artifact export patch pattern missing: ' + old[:100])
    s = s.replace(old, new, 1)

# This patch is intentionally applied after the attachment patch, which already
# introduces InputStream and the file-picker onActivityResult branch.
replace_once(
    'import android.provider.OpenableColumns;\n',
    'import android.provider.OpenableColumns;\nimport android.content.ContentValues;\nimport android.provider.MediaStore;\n'
)
replace_once(
    'import androidx.work.WorkManager;\n',
    'import androidx.work.WorkManager;\nimport androidx.core.content.FileProvider;\n'
)
replace_once(
    'import java.io.ByteArrayOutputStream;\n',
    'import java.io.ByteArrayOutputStream;\nimport java.io.File;\nimport java.io.FileOutputStream;\n'
)
replace_once(
    '    private static final int RC_FILE_PICKER = 732;\n',
    '    private static final int RC_FILE_PICKER = 732;\n    private static final int RC_ARTIFACT_EXPORT = 733;\n'
)
replace_once(
    '    private final ExecutorService pool = Executors.newCachedThreadPool();\n',
    '    private final ExecutorService pool = Executors.newCachedThreadPool();\n    private String pendingArtifactFileId = "";\n    private String pendingArtifactName = "JANUS-artifact.md";\n    private String pendingArtifactMime = "text/markdown";\n'
)

methods = r'''
    private String accessToken() {
        String token = getSharedPreferences("janus", MODE_PRIVATE).getString("access_token", "");
        return token == null ? "" : token;
    }

    private byte[] downloadArtifactBytes(String fileId) throws Exception {
        if (fileId == null || fileId.isBlank()) throw new IllegalArgumentException("Artifact file is unavailable.");
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(SERVER + "/files/" + java.net.URLEncoder.encode(fileId, "UTF-8") + "/download").openConnection();
            c.setRequestMethod("GET");
            c.setConnectTimeout(20000);
            c.setReadTimeout(120000);
            String token = accessToken();
            if (!token.isBlank()) c.setRequestProperty("Authorization", "Bearer " + token);
            int code = c.getResponseCode();
            if (code >= 400) throw new IllegalStateException("JANUS could not export this artifact (HTTP " + code + ").");
            try (InputStream input = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[32768]; int n;
                while ((n = input.read(buffer)) >= 0) out.write(buffer, 0, n);
                return out.toByteArray();
            }
        } finally { if (c != null) c.disconnect(); }
    }

    private void artifactResult(boolean ok, String message) {
        final String js = "if(window.__janusArtifactExportResult)window.__janusArtifactExportResult(" + ok + "," + quote(message == null ? "" : message) + ")";
        runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
    }

    private void startArtifactExport(String fileId, String filename, String mime) {
        pendingArtifactFileId = fileId == null ? "" : fileId;
        pendingArtifactName = filename == null || filename.isBlank() ? "JANUS-artifact.md" : filename;
        pendingArtifactMime = mime == null || mime.isBlank() ? "application/octet-stream" : mime;
        try {
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType(pendingArtifactMime);
            intent.putExtra(Intent.EXTRA_TITLE, pendingArtifactName);
            startActivityForResult(intent, RC_ARTIFACT_EXPORT);
        } catch (Exception e) { artifactResult(false, "Unable to open Android export: " + e.getMessage()); }
    }

    private void finishArtifactExport(Uri destination) {
        final String fileId = pendingArtifactFileId;
        pool.submit(() -> {
            try {
                byte[] bytes = downloadArtifactBytes(fileId);
                try (OutputStream out = getContentResolver().openOutputStream(destination, "w")) {
                    if (out == null) throw new IllegalStateException("Android could not open the selected destination.");
                    out.write(bytes);
                }
                artifactResult(true, "Artifact exported successfully.");
            } catch (Exception e) { artifactResult(false, e.getMessage()); }
        });
    }

    private void shareArtifact(String fileId, String filename, String mime) {
        final String safeName = (filename == null || filename.isBlank()) ? "JANUS-artifact.md" : filename.replaceAll("[\\/]+", "-");
        final String safeMime = (mime == null || mime.isBlank()) ? "application/octet-stream" : mime;
        pool.submit(() -> {
            try {
                byte[] bytes = downloadArtifactBytes(fileId);
                File dir = new File(getCacheDir(), "shared_artifacts");
                if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Could not prepare Android share storage.");
                File out = new File(dir, safeName);
                try (FileOutputStream stream = new FileOutputStream(out)) { stream.write(bytes); }
                Uri uri = FileProvider.getUriForFile(MainActivity.this, getPackageName() + ".fileprovider", out);
                runOnUiThread(() -> {
                    try {
                        Intent send = new Intent(Intent.ACTION_SEND);
                        send.setType(safeMime);
                        send.putExtra(Intent.EXTRA_STREAM, uri);
                        send.putExtra(Intent.EXTRA_SUBJECT, safeName);
                        send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        startActivity(Intent.createChooser(send, "Share JANUS artifact"));
                        artifactResult(true, "Android share sheet opened.");
                    } catch (Exception e) { artifactResult(false, "Unable to share artifact: " + e.getMessage()); }
                });
            } catch (Exception e) { artifactResult(false, e.getMessage()); }
        });
    }

'''
replace_once(
    '    private void startFilePicker() {\n',
    methods + '    private void startFilePicker() {\n'
)

old_result = '''        if (requestCode == RC_FILE_PICKER) {\n            if (resultCode == RESULT_OK && data != null && data.getData() != null) deliverPickedFile(data.getData());\n            else deliverFilePickerError("File selection was cancelled.");\n            return;\n        }\n'''
new_result = old_result + '''        if (requestCode == RC_ARTIFACT_EXPORT) {\n            if (resultCode == RESULT_OK && data != null && data.getData() != null) finishArtifactExport(data.getData());\n            else artifactResult(false, "Artifact export was cancelled.");\n            return;\n        }\n'''
replace_once(old_result, new_result)
replace_once(
    '        @JavascriptInterface public void pickFile() { runOnUiThread(MainActivity.this::startFilePicker); }\n',
    '        @JavascriptInterface public void pickFile() { runOnUiThread(MainActivity.this::startFilePicker); }\n        @JavascriptInterface public void exportArtifact(String fileId, String filename, String mime) { runOnUiThread(() -> startArtifactExport(fileId, filename, mime)); }\n        @JavascriptInterface public void shareArtifact(String fileId, String filename, String mime) { shareArtifact(fileId, filename, mime); }\n'
)
# Avoid Java resolving the Bridge method recursively.
s = s.replace('        @JavascriptInterface public void shareArtifact(String fileId, String filename, String mime) { shareArtifact(fileId, filename, mime); }',
              '        @JavascriptInterface public void shareArtifact(String fileId, String filename, String mime) { MainActivity.this.shareArtifact(fileId, filename, mime); }')
java.write_text(s, encoding='utf-8')

manifest = Path('android/app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8')
provider = '''        <provider android:name="androidx.core.content.FileProvider" android:authorities="${applicationId}.fileprovider" android:exported="false" android:grantUriPermissions="true">\n            <meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/file_paths" />\n        </provider>\n'''
if '.fileprovider' not in m:
    m = m.replace('    </application>', provider + '    </application>')
manifest.write_text(m, encoding='utf-8')

xml_dir = Path('android/app/src/main/res/xml')
xml_dir.mkdir(parents=True, exist_ok=True)
(xml_dir / 'file_paths.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>\n<paths xmlns:android="http://schemas.android.com/apk/res/android">\n    <cache-path name="shared_artifacts" path="shared_artifacts/" />\n</paths>\n''', encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
old = "<button class=\"action\" onclick=\"useArtifactInChat('+Number(a.id)+')\">Use in Chat</button>"
new = old + "<button class=\"action secondary\" onclick=\"exportArtifactNative('+Number(a.id)+')\">Download / Export</button><button class=\"action secondary\" onclick=\"shareArtifactNative('+Number(a.id)+')\">Share</button>"
if old not in h:
    raise SystemExit('Android artifact export HTML detail pattern missing')
h = h.replace(old, new, 1)

js = r'''
window.__janusArtifactExportResult=function(ok,msg){setStatus('Interface active');if(!ok&&String(msg||'').toLowerCase().indexOf('cancel')<0)alert(msg||'Artifact export failed.');};
async function artifactNativeInfo(id){let r=await api('GET','/artifacts/'+encodeURIComponent(id));let a=r.artifact||{};if(!a.file_id||!a.available)throw new Error('Artifact file is unavailable.');return a}
async function exportArtifactNative(id){try{let a=await artifactNativeInfo(id);setStatus('Choose export location');Android.exportArtifact(String(a.file_id),String(a.original_name||a.title||'JANUS-artifact.md'),String(a.mime_type||'application/octet-stream'))}catch(e){alert('Could not export artifact. '+e.message)}}
async function shareArtifactNative(id){try{let a=await artifactNativeInfo(id);setStatus('Preparing share');Android.shareArtifact(String(a.file_id),String(a.original_name||a.title||'JANUS-artifact.md'),String(a.mime_type||'application/octet-stream'))}catch(e){alert('Could not share artifact. '+e.message)}}
'''
if '</script>' not in h:
    raise SystemExit('Android artifact export script terminator missing')
h = h.replace('</script>', js + '\n</script>', 1)
html.write_text(h, encoding='utf-8')
print('Applied native Android artifact export/share patch')
