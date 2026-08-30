from pathlib import Path
import re

ROOT=Path('.')
activity=ROOT/'activity_fixed.kt'
repair=ROOT/'pro_repair_v3.py'
if not activity.is_file(): raise SystemExit('GITHUB_UPDATE_PATCH: activity_fixed.kt missing')
a=activity.read_text(encoding='utf-8')
marker='// KUV_GITHUB_UPDATE_V1'
if marker not in a:
    a=a.replace('import android.content.Intent\n','import android.content.Intent\nimport android.app.AlertDialog\nimport android.app.DownloadManager\nimport android.net.Uri\nimport android.os.Environment\n',1)
    button='button("CHECK GITHUB FOR APP UPDATE"){checkForAppUpdate()};'
    anchor='button("REFRESH STATUS"){renderStatus()};'
    if anchor not in a: raise SystemExit('GITHUB_UPDATE_PATCH: UI anchor missing')
    a=a.replace(anchor,button+anchor,1)
    fn=r'''\n    // KUV_GITHUB_UPDATE_V1\n    private fun checkForAppUpdate(){\n        status.text="Checking GitHub for verified update..."\n        Thread {\n            try {\n                val c=(java.net.URL("https://api.github.com/repos/kunalledade959-bot/KUNAL-Universal-Video/releases/latest").openConnection() as java.net.HttpURLConnection)\n                c.connectTimeout=8000; c.readTimeout=8000; c.setRequestProperty("Accept","application/vnd.github+json"); c.setRequestProperty("User-Agent","Kunal-Universal-Video")\n                val body=c.inputStream.bufferedReader().use{it.readText()}; c.disconnect()\n                val j=org.json.JSONObject(body); val tag=j.optString("tag_name","")\n                val m=Regex("verified-apk-(\\d+)").matchEntire(tag) ?: throw IllegalStateException("No verified APK release found")\n                val remote=m.groupValues[1].toLong(); val local=packageManager.getPackageInfo(packageName,0).longVersionCode\n                val asset=j.optJSONArray("assets")?.let{arr->(0 until arr.length()).map{arr.getJSONObject(it)}.firstOrNull{it.optString("name").endsWith(".apk")}}\n                val url=asset?.optString("browser_download_url","") ?: throw IllegalStateException("Verified APK asset missing")\n                runOnUiThread {\n                    if(remote<=local){ status.text="GitHub verified release $tag • app is up to date (code $local)" }\n                    else {\n                        AlertDialog.Builder(this).setTitle("Verified update available").setMessage("GitHub release $tag is newer than installed build $local.").setNegativeButton("Later",null).setPositiveButton("Download & Install"){_,_->downloadGitHubUpdate(url,tag)}.show()\n                    }\n                }\n            } catch(e:Exception){ runOnUiThread{status.text="GitHub update check failed • ${e.javaClass.simpleName}: ${e.message}"} }\n        }.start()\n    }\n    private fun downloadGitHubUpdate(url:String,tag:String){\n        if(android.os.Build.VERSION.SDK_INT>=26 && !packageManager.canRequestPackageInstalls()){\n            startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:$packageName"))); return\n        }\n        val req=DownloadManager.Request(Uri.parse(url)).setTitle("Kunal Universal Video $tag").setDescription("Verified GitHub APK update").setMimeType("application/vnd.android.package-archive").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,"KUNAL_UNIVERSAL_VIDEO_$tag.apk")\n        val id=getSystemService(DownloadManager::class.java).enqueue(req)\n        status.text="Downloading verified GitHub update $tag..."\n        Thread { repeat(180){ Thread.sleep(1000); val q=getSystemService(DownloadManager::class.java).query(DownloadManager.Query().setFilterById(id)); q.use { if(!it.moveToFirst()) return@use; val s=it.getInt(it.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS)); if(s==DownloadManager.STATUS_SUCCESSFUL){ val u=getSystemService(DownloadManager::class.java).getUriForDownloadedFile(id); if(u!=null) runOnUiThread{startActivity(Intent(Intent.ACTION_VIEW,u).setDataAndType(u,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))}; return@repeat }; if(s==DownloadManager.STATUS_FAILED) return@repeat } } }.start()\n    }\n'''
    pos=a.rfind('\n}')
    if pos<0: raise SystemExit('GITHUB_UPDATE_PATCH: class end missing')
    a=a[:pos]+fn+a[pos:]
activity.write_text(a,encoding='utf-8')

if repair.is_file():
    s=repair.read_text(encoding='utf-8')
    # Keep Android updates monotonic: verified-apk-N maps to versionCode N.
    s=s.replace('versionCode=3; versionName="3.0.0"','versionCode=(System.getenv("GITHUB_RUN_NUMBER") ?: "3").toInt(); versionName="3.${System.getenv("GITHUB_RUN_NUMBER") ?: "3"}"',1)
    old='<uses-permission android:name="android.permission.INTERNET"/>'
    if old in s and 'REQUEST_INSTALL_PACKAGES' not in s:
        s=s.replace(old,old+'<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>',1)
    repair.write_text(s,encoding='utf-8')

print('GITHUB UPDATE PATCH: PASS')
