package com.montador.flashcards

import android.annotation.SuppressLint
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File

/**
 * Montador de Flashcards para Android.
 * A interface (editor, linha do tempo, estudo, exportação para o Anki) fica em assets/www;
 * aqui ficam o que só o Android faz: salvar os dados, abrir arquivos, compartilhar com o AnkiDroid
 * e o botão Voltar.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private var pendingSave: Pair<String, ByteArray>? = null

    companion object {
        private const val REQ_OPEN = 10
        private const val REQ_SAVE = 11
        private const val DATA_FILE = "flashcards.json"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = 0xFFFFFFFF.toInt()
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR

        web = WebView(this)
        setContentView(web)
        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            textZoom = 100
            cacheMode = WebSettings.LOAD_NO_CACHE
        }
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                // trechos destacados ("hl:...") e links não saem do app
                if (url.startsWith("http")) {
                    try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) } catch (_: Exception) {}
                }
                return true
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams
            ): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = callback
                val i = Intent(Intent.ACTION_GET_CONTENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                }
                return try {
                    startActivityForResult(Intent.createChooser(i, "Escolher arquivo"), REQ_OPEN); true
                } catch (e: ActivityNotFoundException) {
                    fileCallback = null; false
                }
            }
        }
        web.addJavascriptInterface(Bridge(), "Android")
        web.loadUrl("file:///android_asset/www/index.html")
    }

    inner class Bridge {
        @JavascriptInterface
        fun saveData(json: String) {
            try {
                val tmp = File(filesDir, "$DATA_FILE.tmp")
                tmp.writeText(json)
                tmp.renameTo(File(filesDir, DATA_FILE))
            } catch (_: Exception) {}
        }

        @JavascriptInterface
        fun loadData(): String {
            val f = File(filesDir, DATA_FILE)
            return if (f.exists()) f.readText() else ""
        }

        /** mode: "view" abre direto no app que sabe abrir (ex.: AnkiDroid); "send" mostra a lista de apps. */
        @JavascriptInterface
        fun shareFile(name: String, base64: String, mime: String, mode: String) {
            runOnUiThread {
                try {
                    val dir = File(cacheDir, "export").apply { mkdirs() }
                    val f = File(dir, name)
                    f.writeBytes(Base64.decode(base64, Base64.DEFAULT))
                    val uri = FileProvider.getUriForFile(this@MainActivity, "com.montador.flashcards.files", f)
                    val intent = if (mode == "view") {
                        Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime)
                    } else {
                        Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, uri)
                    }
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    try {
                        startActivity(if (mode == "view") intent else Intent.createChooser(intent, name))
                    } catch (e: ActivityNotFoundException) {
                        if (mode == "view") {
                            Toast.makeText(this@MainActivity,
                                "Nenhum app abriu o arquivo. Instale o AnkiDroid ou use Compartilhar.",
                                Toast.LENGTH_LONG).show()
                        }
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }

        /** Salva o arquivo onde a pessoa escolher (Downloads, Drive...). */
        @JavascriptInterface
        fun saveFile(name: String, base64: String, mime: String) {
            runOnUiThread {
                pendingSave = name to Base64.decode(base64, Base64.DEFAULT)
                val i = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = mime
                    putExtra(Intent.EXTRA_TITLE, name)
                }
                try { startActivityForResult(i, REQ_SAVE) } catch (_: Exception) { pendingSave = null }
            }
        }

        @JavascriptInterface
        fun isAndroid(): Boolean = true
    }

    @Deprecated("Activity result API não é usada para manter o app sem dependências extras")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        when (requestCode) {
            REQ_OPEN -> {
                val uri = data?.data
                fileCallback?.onReceiveValue(if (resultCode == RESULT_OK && uri != null) arrayOf(uri) else null)
                fileCallback = null
            }
            REQ_SAVE -> {
                val save = pendingSave
                pendingSave = null
                val uri = data?.data
                if (resultCode == RESULT_OK && uri != null && save != null) {
                    try {
                        contentResolver.openOutputStream(uri)?.use { it.write(save.second) }
                        Toast.makeText(this, "Arquivo salvo: ${save.first}", Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Toast.makeText(this, "Erro ao salvar: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
    }

    @Deprecated("Mantido para funcionar em todas as versões do Android")
    override fun onBackPressed() {
        web.evaluateJavascript("window.appBack ? String(appBack()) : 'false'") { result ->
            if (result?.contains("true") != true) {
                @Suppress("DEPRECATION")
                super.onBackPressed()
            }
        }
    }

    override fun onPause() {
        super.onPause()
        web.evaluateJavascript("window.saveNow && saveNow()", null)
    }
}
