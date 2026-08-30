from pathlib import Path

ROOT = Path('.')
activity = ROOT / 'activity_fixed.kt'
repair = ROOT / 'pro_repair_v3.py'
if not activity.is_file():
    raise SystemExit('GITHUB_UPDATE_PATCH: activity_fixed.kt missing')

a = activity.read_text(encoding='utf-8')
marker = '// KUV_GITHUB_UPDATE_V2'
if marker not in a:
    imports = (
        'import android.app.AlertDialog\n'
        'import android.app.DownloadManager\n'
        'import android.net.Uri\n'
        'import android.os.Environment\n'
    )
    anchor_import = 'import android.content.Intent\n'
    if imports.strip() not in a:
        if anchor_import not in a:
            raise SystemExit('GITHUB_UPDATE_PATCH: Intent import anchor missing')
        a = a.replace(anchor_import, anchor_import + imports, 1)

    button = 'button("CHECK GITHUB FOR APP UPDATE"){checkForAppUpdate()};'
    anchor = 'button("REFRESH STATUS"){renderStatus()};'
    if button not in a:
        if anchor not in a:
            raise SystemExit('GITHUB_UPDATE_PATCH: UI anchor missing')
        a = a.replace(anchor, button + anchor, 1)

    fn = '''
    // KUV_GITHUB_UPDATE_V2
    private fun checkForAppUpdate(){
        status.text="Checking GitHub for verified update..."
        Thread {
            try {
                val c=(java.net.URL("https://api.github.com/repos/kunalledade959-bot/KUNAL-Universal-Video/releases/latest").openConnection() as java.net.HttpURLConnection)
                c.connectTimeout=8000
                c.readTimeout=8000
                c.setRequestProperty("Accept","application/vnd.github+json")
                c.setRequestProperty("User-Agent","Kunal-Universal-Video")
                val body=c.inputStream.bufferedReader().use{it.readText()}
                c.disconnect()
                val j=org.json.JSONObject(body)
                val tag=j.optString("tag_name","")
                val prefix="verified-apk-"
                if(!tag.startsWith(prefix)) throw IllegalStateException("No verified APK release found")
                val remote=tag.removePrefix(prefix).toLongOrNull() ?: throw IllegalStateException("Invalid verified release tag")
                val local=packageManager.getPackageInfo(packageName,0).longVersionCode
                val assets=j.optJSONArray("assets") ?: throw IllegalStateException("Verified APK assets missing")
                var url=""
                for(i in 0 until assets.length()){
                    val item=assets.getJSONObject(i)
                    if(item.optString("name").endsWith(".apk")) { url=item.optString("browser_download_url",""); break }
                }
                if(url.isBlank()) throw IllegalStateException("Verified APK asset missing")
                runOnUiThread {
                    if(remote<=local){
                        status.text="GitHub verified release $tag • app is up to date (code $local)"
                    } else {
                        AlertDialog.Builder(this)
                            .setTitle("Verified update available")
                            .setMessage("GitHub release $tag is newer than installed build $local.")
                            .setNegativeButton("Later",null)
                            .setPositiveButton("Download & Install"){_,_->downloadGitHubUpdate(url,tag)}
                            .show()
                    }
                }
            } catch(e:Exception){
                runOnUiThread{status.text="GitHub update check failed • ${e.javaClass.simpleName}: ${e.message}"}
            }
        }.start()
    }
    private fun downloadGitHubUpdate(url:String,tag:String){
        if(android.os.Build.VERSION.SDK_INT>=26 && !packageManager.canRequestPackageInstalls()){
            startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:$packageName")))
            return
        }
        val req=DownloadManager.Request(Uri.parse(url))
            .setTitle("Kunal Universal Video $tag")
            .setDescription("Verified GitHub APK update")
            .setMimeType("application/vnd.android.package-archive")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,"KUNAL_UNIVERSAL_VIDEO_$tag.apk")
        val id=getSystemService(DownloadManager::class.java).enqueue(req)
        status.text="Downloading verified GitHub update $tag..."
        Thread {
            repeat(180){
                Thread.sleep(1000)
                val q=getSystemService(DownloadManager::class.java).query(DownloadManager.Query().setFilterById(id))
                q.use {
                    if(!it.moveToFirst()) return@use
                    val s=it.getInt(it.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
                    if(s==DownloadManager.STATUS_SUCCESSFUL){
                        val u=getSystemService(DownloadManager::class.java).getUriForDownloadedFile(id)
                        if(u!=null) runOnUiThread{
                            startActivity(Intent(Intent.ACTION_VIEW,u).setDataAndType(u,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
                        }
                        return@repeat
                    }
                    if(s==DownloadManager.STATUS_FAILED) return@repeat
                }
            }
        }.start()
    }
'''
    pos = a.rfind('\n}')
    if pos < 0:
        raise SystemExit('GITHUB_UPDATE_PATCH: class end missing')
    a = a[:pos] + fn + a[pos:]
    activity.write_text(a, encoding='utf-8')

if repair.is_file():
    s = repair.read_text(encoding='utf-8')
    old = 'versionCode=3; versionName="3.0.0"'
    new = 'versionCode=(System.getenv("GITHUB_RUN_NUMBER") ?: "3").toInt(); versionName="3.${System.getenv("GITHUB_RUN_NUMBER") ?: "3"}"'
    if old in s:
        s = s.replace(old, new, 1)
    old_perm = '<uses-permission android:name="android.permission.INTERNET"/>'
    new_perm = '<uses-permission android:name="android.permission.INTERNET"/><uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>'
    if old_perm in s and 'REQUEST_INSTALL_PACKAGES' not in s:
        s = s.replace(old_perm, new_perm, 1)
    repair.write_text(s, encoding='utf-8')

print('GITHUB UPDATE PATCH: PASS')
