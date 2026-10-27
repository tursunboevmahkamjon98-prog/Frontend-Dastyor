import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.dastyor.dastyor"
    // Pinned above Flutter's own default (34) — file_picker's
    // flutter_plugin_android_lifecycle dependency requires compiling
    // against API 36+.
    compileSdk = 36
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // Required by flutter_local_notifications (uses Java 8+ APIs the
        // device's own SDK may not natively support pre-API 26).
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.dastyor.dastyor"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        // Pinned below Flutter's own default (36) — Android 16's new
        // "Local Network Protection" blocks apps that TARGET api 36 from
        // reaching private/local IPs (127.0.0.1, 192.168.x.x, adb reverse,
        // etc.) unless a new local-network permission is declared AND
        // granted at runtime. Since this app's whole dev workflow talks to
        // a LAN/loopback dev backend, targeting 34 sidesteps that
        // restriction entirely instead of chasing the new permission.
        targetSdk = 34
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // Release signing. The keystore and its passwords live in
    // android/key.properties, which is NOT in the repository — see
    // android/key.properties.example. Without that file the build falls
    // back to the debug key, so a fresh clone still builds.
    signingConfigs {
        create("release") {
            val props = Properties()
            val propsFile = rootProject.file("key.properties")
            if (propsFile.exists()) {
                propsFile.inputStream().use { props.load(it) }
                storeFile = rootProject.file(props.getProperty("storeFile"))
                storePassword = props.getProperty("storePassword")
                keyAlias = props.getProperty("keyAlias")
                keyPassword = props.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            val keyed = rootProject.file("key.properties").exists()
            signingConfig = if (keyed) signingConfigs.getByName("release")
                            else signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

dependencies {
    // Pairs with isCoreLibraryDesugaringEnabled above — required by
    // flutter_local_notifications, the flag alone isn't enough.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}

flutter {
    source = "../.."
}
