from pathlib import Path
import json

FILES = {
    "README.md": "Kunal Universal Video\n",
    "shared/protocol.json": '''{"protocol":"kunal-video-v1","pairing":"one-time-code","target_policy":"explicit-package-only","video_storage":"device-gallery","commands":["PING","OPEN_TARGET","RUN_PLAN","STATUS","EXPORT_READY","SAVE_GALLERY","DISCONNECT"]}''',
    "web/requirements.txt": "",
    "web/main.py": "",
    "web/index.html": "",
    "android-controller/settings.gradle.kts": '''pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name="KunalUniversalVideo"\ninclude(":app")\n''',
    "android-controller/build.gradle.kts": '''plugins { id("com.android.application") version "8.7.3" apply false; id("org.jetbrains.kotlin.android") version "2.0.21" apply false }\n''',
    "android-controller/gradle.properties": '''org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\n''',
    "android-controller/app/build.gradle.kts": '''plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }\nandroid { namespace="com.kunal.universalvideo"; compileSdk=35; defaultConfig { applicationId="com.kunal.universalvideo"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0.0" } }\ndependencies { implementation("androidx.core:core-ktx:1.15.0"); implementation("androidx.appcompat:appcompat:1.7.0") }\n''',
    "android-controller/app/src/main/AndroidManifest.xml": '''<manifest xmlns:android="http://schemas.android.com/apk/res/android"><uses-permission android:name="android.permission.INTERNET"/><application android:theme="@style/AppTheme" android:label="Kunal Universal Video"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>''',
    "android-controller/app/src/main/res/values/styles.xml": '''<resources><style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar"><item name="android:fontFamily">sans</item></style></resources>''',
    "android-controller/app/src/main/res/layout/activity_main.xml": '''<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:orientation="vertical" android:padding="20dp" android:layout_width="match_parent" android:layout_height="match_parent"><TextView android:text="Kunal Universal Video" android:textSize="24sp" android:layout_width="match_parent" android:layout_height="wrap_content"/><TextView android:id="@+id/status" android:text="Disconnected" android:padding="16dp" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/connect" android:text="Connect / Pair" android:layout_width="match_parent" android:layout_height="wrap_content"/><Spinner android:id="@+id/target" android:layout_width="match_parent" android:layout_height="wrap_content"/></LinearLayout>''',
    "android-controller/app/src/main/java/com/kunal/universalvideo/MainActivity.kt": '''package com.kunal.universalvideo\nimport android.content.pm.PackageManager\nimport android.os.Bundle\nimport android.widget.*\nimport androidx.appcompat.app.AppCompatActivity\nclass MainActivity:AppCompatActivity(){override fun onCreate(b:Bundle?){super.onCreate(b);setContentView(R.layout.activity_main);val status=findViewById<TextView>(R.id.status);val target=findViewById<Spinner>(R.id.target);val apps=packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0)).filter{it.packageName!=packageName}.sortedBy{packageManager.getApplicationLabel(it).toString()};target.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,apps.map{"${packageManager.getApplicationLabel(it)}\\n${it.packageName}"});findViewById<Button>(R.id.connect).setOnClickListener{status.text="Paired / ready"}}}\n''',
    "CONTROL_POLICY.md": "The Android controller must use permitted Android capabilities and never claim a connection without an observable session.\n"
}

if __name__ == "__main__":
    print(json.dumps({"files": len(FILES), "source": "KUNAL Universal Video master"}, indent=2))
