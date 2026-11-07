plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Versão: a mesma do programa do Windows (montador/__init__.py)
val appVersion: String = Regex("__version__ = \"([^\"]+)\"")
    .find(rootProject.file("../montador/__init__.py").readText())!!.groupValues[1]
val parts = appVersion.split(".").map { it.toInt() }

android {
    namespace = "com.montador.flashcards"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.montador.flashcards"
        minSdk = 24
        targetSdk = 34
        versionCode = parts[0] * 10000 + parts[1] * 100 + parts[2]
        versionName = appVersion
    }

    // A chave de assinatura NÃO fica no repositório: vem do ambiente (segredo do GitHub ou gerada no build).
    val ksPath = System.getenv("MONTADOR_KEYSTORE")
    signingConfigs {
        if (ksPath != null) {
            create("montador") {
                storeFile = file(ksPath)
                storePassword = System.getenv("MONTADOR_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("MONTADOR_KEY_ALIAS") ?: "montador"
                keyPassword = System.getenv("MONTADOR_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (ksPath != null) signingConfigs.getByName("montador")
                            else signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core:1.13.1")
}
