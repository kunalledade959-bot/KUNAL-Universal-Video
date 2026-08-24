# KUNAL Universal Video automatic build diagnosis

Run: 32759496160
Commit: 4ba565918dfb46ff16c26bd661269d8b6459c364
Branch: chroma-toon-7layer-build
Job status: success

## Detected Gradle error signals
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/GalleryExporter.kt:53:44 'static field ACTION_MEDIA_SCANNER_SCAN_FILE: String' is deprecated. Deprecated in Java.
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/TargetGuideManager.kt:23:89 'field versionCode: Int' is deprecated. Deprecated in Java.

## Last 120 log lines
To honour the JVM settings for this build a single-use Daemon process will be forked. For more on this, please refer to https://docs.gradle.org/8.9/userguide/gradle_daemon.html#sec:disabling_the_daemon in the Gradle documentation.
Daemon will be stopped at the end of the build 
> Task :app:preBuild UP-TO-DATE
> Task :app:preDebugBuild UP-TO-DATE
> Task :app:mergeDebugNativeDebugMetadata NO-SOURCE
> Task :app:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :app:generateDebugResValues
> Task :app:checkDebugAarMetadata
> Task :app:mapDebugSourceSetPaths
> Task :app:generateDebugResources
> Task :app:createDebugCompatibleScreenManifests
> Task :app:extractDeepLinksDebug
> Task :app:mergeDebugResources
> Task :app:processDebugMainManifest
> Task :app:packageDebugResources
> Task :app:parseDebugLocalResources
> Task :app:processDebugManifest
> Task :app:processDebugManifestForPackage
> Task :app:javaPreCompileDebug
> Task :app:mergeDebugShaders
> Task :app:compileDebugShaders NO-SOURCE
> Task :app:generateDebugAssets UP-TO-DATE
> Task :app:mergeDebugAssets
> Task :app:compressDebugAssets
> Task :app:desugarDebugFileDependencies
> Task :app:checkDebugDuplicateClasses
> Task :app:processDebugResources
> Task :app:mergeExtDexDebug
> Task :app:mergeLibDexDebug
> Task :app:mergeDebugJniLibFolders
> Task :app:mergeDebugNativeLibs NO-SOURCE
> Task :app:stripDebugDebugSymbols NO-SOURCE
> Task :app:validateSigningDebug
> Task :app:writeDebugAppMetadata
> Task :app:writeDebugSigningConfigVersions

> Task :app:compileDebugKotlin
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/GalleryExporter.kt:53:44 'static field ACTION_MEDIA_SCANNER_SCAN_FILE: String' is deprecated. Deprecated in Java.
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/LocalBridgeService.kt:62:16 Condition is always 'true'.
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/ScreenCaptureService.kt:82:22 'constructor(): MediaRecorder' is deprecated. Deprecated in Java.
w: file:///home/runner/work/KUNAL-Universal-Video/KUNAL-Universal-Video/verification-package/KUNAL_CHROMATOON_7LAYER_GITHUB_PACKAGE/android-controller/app/src/main/java/com/kunal/universalvideo/TargetGuideManager.kt:23:89 'field versionCode: Int' is deprecated. Deprecated in Java.

> Task :app:compileDebugJavaWithJavac NO-SOURCE
> Task :app:dexBuilderDebug
> Task :app:mergeDebugGlobalSynthetics
> Task :app:processDebugJavaRes
> Task :app:mergeProjectDexDebug
> Task :app:mergeDebugJavaResource
> Task :app:packageDebug
> Task :app:createDebugApkListingFileRedirect
> Task :app:assembleDebug
gradle/actions: Writing build results to /home/runner/work/_temp/.gradle-actions/build-results/__run_4-1787594240043.json

BUILD SUCCESSFUL in 54s
33 actionable tasks: 33 executed
