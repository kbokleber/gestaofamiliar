package br.com.kbosolucoes.gestaofamiliar.crianca

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.ActivityNotFoundException
import android.content.ContentValues
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.Settings
import android.util.Base64
import android.view.Gravity
import android.view.View
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.FileProvider
import java.io.File
import java.util.concurrent.Executors

/**
 * Tela principal: o site do Gestão Familiar dentro do app, com o mesmo login e as mesmas funções
 * para adultos e crianças. Por baixo, o app cuida do que o navegador não faz sozinho:
 * - criança logada: conecta o celular e envia localização e bateria (LocationService);
 * - adulto logado: recebe chegada/saída, bateria baixa e "sem sinal" como notificação;
 * - envio e download de arquivos, botão voltar e aviso de versão nova.
 */
class WebActivity : Activity() {
    private lateinit var configuracao: Configuracao
    private lateinit var web: WebView
    private lateinit var faixas: LinearLayout
    private lateinit var carregando: ProgressBar
    private lateinit var erro: LinearLayout
    private val fundo = Executors.newSingleThreadExecutor()
    private var escolhaDeArquivo: ValueCallback<Array<Uri>>? = null

    /** Página aberta agora (só a ponte do próprio site é atendida). Atualizada na thread da tela. */
    @Volatile private var paginaAtual: String = ""
    private var versaoNova: String? = null
    /** Criança para quem já disseram "não" à troca nesta abertura do app (não pergunta de novo a cada página). */
    @Volatile private var trocaRecusadaPara = 0
    /** Último pedido de login do Keycloak aberto aqui (para refazer no navegador quando for pelo Google). */
    private var pedidoDeLogin: String? = null
    private var versaoConferidaEm = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configuracao = Configuracao(this)
        Notificador.criarCanais(this)
        montarTela()
        configurarWeb()
        if (savedInstanceState != null) web.restoreState(savedInstanceState)
        val retorno = intent?.dataString?.let { retornoDoLogin(configuracao.site, it) }
        if (retorno != null) web.loadUrl(retorno)
        else if (web.url == null) web.loadUrl(enderecoInicial(intent))
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val retorno = intent.dataString?.let { retornoDoLogin(configuracao.site, it) }
        if (retorno != null) abrir(retorno)
        else intent.getStringExtra(EXTRA_ENDERECO)?.let { abrir(it) }
    }

    override fun onResume() {
        super.onResume()
        web.onResume()
        if (configuracao.pareado) LocationService.iniciar(this)
        if (configuracao.tokenAdulto != null) fundo.execute { AlertasAdulto.buscar(applicationContext) }
        conferirVersao()
        desenharFaixas()
    }

    override fun onPause() {
        web.onPause()
        CookieManager.getInstance().flush()
        super.onPause()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    override fun onDestroy() {
        fundo.shutdown()
        web.destroy()
        super.onDestroy()
    }

    @Deprecated("Mantido para o botão voltar em todas as versões do Android")
    override fun onBackPressed() {
        if (erro.visibility == View.VISIBLE) {
            @Suppress("DEPRECATION") super.onBackPressed()
        } else if (web.canGoBack()) {
            web.goBack()
        } else {
            @Suppress("DEPRECATION") super.onBackPressed()
        }
    }

    // ------------------------------------------------------------ tela

    private fun montarTela() {
        faixas = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        carregando = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        web = WebView(this)
        erro = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(24), dp(24), dp(24), dp(24))
            visibility = View.GONE
            addView(TextView(context).apply {
                text = "Sem conexão com o Gestão Familiar"
                textSize = 20f
                setTypeface(typeface, Typeface.BOLD)
                setTextColor(Color.rgb(17, 24, 39))
                gravity = Gravity.CENTER
            })
            addView(TextView(context).apply {
                text = "Confira a internet e tente de novo. A localização continua sendo guardada e é enviada quando a conexão voltar."
                textSize = 15f
                setTextColor(Color.rgb(75, 85, 99))
                gravity = Gravity.CENTER
                setPadding(0, dp(8), 0, dp(16))
            })
            addView(Button(context).apply {
                text = "Tentar de novo"
                isAllCaps = false
                setOnClickListener {
                    erro.visibility = View.GONE
                    web.visibility = View.VISIBLE
                    web.reload()
                }
            })
            addView(Button(context).apply {
                text = "Configurações do celular"
                isAllCaps = false
                setOnClickListener { abrirConfiguracoes() }
            })
        }
        val raiz = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(faixas, LinearLayout.LayoutParams(-1, -2))
            addView(carregando, LinearLayout.LayoutParams(-1, dp(3)))
            addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
            addView(erro, LinearLayout.LayoutParams(-1, 0, 1f))
        }
        setContentView(raiz)
    }

    /** Faixas no topo, só quando há algo a resolver. */
    private fun desenharFaixas() {
        faixas.removeAllViews()
        if (configuracao.pareado && (!configuracao.temLocalizacao() || !configuracao.temLocalizacaoSempre())) {
            faixa("Falta liberar a localização neste celular. Toque para ajustar.", alerta = true) { abrirConfiguracoes() }
        } else if (configuracao.foiDesconectado && !configuracao.pareado) {
            faixa("Este celular foi desconectado da família. Entre de novo com a conta da criança.", alerta = true) { abrirConfiguracoes() }
        }
        if (configuracao.tokenAdulto != null && !NotificationManagerCompat.from(this).areNotificationsEnabled()) {
            faixa("Ative as notificações para receber os alertas da família.", alerta = true) { pedirNotificacoes() }
        }
        versaoNova?.let { v ->
            faixa("Nova versão do app ($v). Toque para atualizar.", alerta = false) {
                abrirFora(ApiClient.normalizarEndereco(configuracao.site) + "/app")
            }
        }
    }

    private fun faixa(texto: String, alerta: Boolean, acao: () -> Unit) {
        faixas.addView(TextView(this).apply {
            text = texto
            textSize = 14f
            setTextColor(if (alerta) Color.rgb(146, 64, 14) else Color.WHITE)
            setBackgroundColor(if (alerta) Color.rgb(254, 243, 199) else Color.rgb(124, 58, 237))
            setPadding(dp(14), dp(10), dp(14), dp(10))
            setOnClickListener { acao() }
        }, LinearLayout.LayoutParams(-1, -2))
    }

    // ------------------------------------------------------------ navegador

    @SuppressLint("SetJavaScriptEnabled", "JavascriptInterface")
    private fun configurarWeb() {
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true)
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            @Suppress("DEPRECATION")
            databaseEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            // Zoom com dois dedos (pinça), como no Chrome; sem os botões +/- do Android por cima.
            setSupportZoom(true)
            builtInZoomControls = true
            displayZoomControls = false
            userAgentString = "$userAgentString $MARCA_USER_AGENT${BuildConfig.VERSION_NAME}"
        }
        web.addJavascriptInterface(Ponte(), "GFAppNativo")
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, pedido: WebResourceRequest): Boolean {
                val endereco = pedido.url.toString()
                // Google e outros provedores não deixam entrar dentro de apps: o login segue no navegador
                // e volta para o app por /app-login.
                val provedor = provedorExterno(endereco)
                val pedidoAtual = pedidoDeLogin
                if (provedor != null && pedidoAtual != null) {
                    abrirFora(loginNoNavegador(pedidoAtual, provedor))
                    return true
                }
                if (ehPedidoDeLogin(endereco)) pedidoDeLogin = endereco
                if (abreDentroDoApp(configuracao.site, endereco)) return false
                abrirFora(endereco)
                return true
            }

            override fun doUpdateVisitedHistory(view: WebView, url: String?, recarregou: Boolean) {
                paginaAtual = url.orEmpty()
            }

            override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
                paginaAtual = url.orEmpty()
                if (url != null && ehPedidoDeLogin(url)) pedidoDeLogin = url
            }

            override fun onReceivedError(view: WebView, pedido: WebResourceRequest, falha: WebResourceError) {
                if (pedido.isForMainFrame) {
                    web.visibility = View.GONE
                    erro.visibility = View.VISIBLE
                }
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, progresso: Int) {
                carregando.progress = progresso
                carregando.visibility = if (progresso in 1..99) View.VISIBLE else View.GONE
            }

            override fun onShowFileChooser(
                view: WebView,
                retorno: ValueCallback<Array<Uri>>,
                parametros: FileChooserParams,
            ): Boolean {
                escolhaDeArquivo?.onReceiveValue(null)
                escolhaDeArquivo = retorno
                val escolher = parametros.createIntent().apply {
                    if (parametros.mode == FileChooserParams.MODE_OPEN_MULTIPLE) putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                }
                return try {
                    startActivityForResult(escolher, PEDIDO_ARQUIVO)
                    true
                } catch (e: ActivityNotFoundException) {
                    escolhaDeArquivo = null
                    false
                }
            }
        }
        web.setDownloadListener { url, userAgent, disposicao, tipo, _ -> baixar(url, userAgent, disposicao, tipo) }
    }

    @Deprecated("startActivityForResult é o caminho simples numa Activity sem AndroidX")
    override fun onActivityResult(codigo: Int, resultado: Int, dados: Intent?) {
        if (codigo == PEDIDO_ARQUIVO) {
            val arquivos = if (resultado == RESULT_OK && dados != null) {
                dados.clipData?.let { lista -> Array(lista.itemCount) { lista.getItemAt(it).uri } }
                    ?: WebChromeClient.FileChooserParams.parseResult(resultado, dados)
            } else null
            escolhaDeArquivo?.onReceiveValue(arquivos)
            escolhaDeArquivo = null
            return
        }
        @Suppress("DEPRECATION") super.onActivityResult(codigo, resultado, dados)
    }

    private fun enderecoInicial(intent: Intent?): String {
        val pedido = intent?.getStringExtra(EXTRA_ENDERECO)
        return if (pedido != null && abreDentroDoApp(configuracao.site, pedido)) pedido
        else ApiClient.normalizarEndereco(configuracao.site) + "/"
    }

    private fun abrir(endereco: String) {
        if (!abreDentroDoApp(configuracao.site, endereco)) return
        erro.visibility = View.GONE
        web.visibility = View.VISIBLE
        web.loadUrl(endereco)
    }

    private fun abrirFora(endereco: String) {
        val intent = if (endereco.startsWith("intent:")) {
            runCatching { Intent.parseUri(endereco, Intent.URI_INTENT_SCHEME) }.getOrNull()?.apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
                component = null
                selector = null
            }
        } else {
            Intent(Intent.ACTION_VIEW, Uri.parse(endereco))
        } ?: return
        try {
            startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(this, "Nenhum app do celular abre este link.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun abrirConfiguracoes() = startActivity(Intent(this, ConfiguracaoActivity::class.java))

    // ------------------------------------------------------------ downloads

    /** Links comuns (ex.: o APK em /app). Arquivos gerados pelo site chegam pela ponte (salvarArquivo). */
    private fun baixar(url: String, userAgent: String, disposicao: String?, tipo: String?) {
        if (!url.startsWith("https://") && !url.startsWith("http://")) {
            Toast.makeText(this, "Não foi possível baixar este arquivo.", Toast.LENGTH_SHORT).show()
            return
        }
        val nome = URLUtil.guessFileName(url, disposicao, tipo)
        val pedido = DownloadManager.Request(Uri.parse(url))
            .setTitle(nome)
            .setMimeType(tipo)
            .addRequestHeader("User-Agent", userAgent)
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, nome)
        CookieManager.getInstance().getCookie(url)?.let { pedido.addRequestHeader("Cookie", it) }
        try {
            getSystemService(DownloadManager::class.java).enqueue(pedido)
            Toast.makeText(this, "Baixando $nome…", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            abrirFora(url)
        }
    }

    private fun salvarArquivo(conteudo: ByteArray, nome: String, tipo: String) {
        val nomeSeguro = nome.replace(Regex("[\\\\/:*?\"<>|\\p{Cntrl}]"), "_").trim().ifBlank { "arquivo" }.take(120)
        val tipoSeguro = tipo.ifBlank { "application/octet-stream" }
        val endereco: Uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val valores = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, nomeSeguro)
                put(MediaStore.Downloads.MIME_TYPE, tipoSeguro)
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, valores)
                ?: throw IllegalStateException("sem acesso a Downloads")
            contentResolver.openOutputStream(uri)?.use { it.write(conteudo) }
            contentResolver.update(uri, ContentValues().apply { put(MediaStore.Downloads.IS_PENDING, 0) }, null, null)
            uri
        } else {
            // Android 8 e 9: guarda na área do app e abre/compartilha pelo FileProvider (sem pedir permissão de armazenamento).
            val pasta = File(cacheDir, "arquivos").apply { mkdirs() }
            val arquivo = File(pasta, nomeSeguro)
            arquivo.writeBytes(conteudo)
            FileProvider.getUriForFile(this, "$packageName.arquivos", arquivo)
        }
        runOnUiThread {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Toast.makeText(this, "Salvo em Downloads: $nomeSeguro", Toast.LENGTH_LONG).show()
            }
            val ver = Intent(Intent.ACTION_VIEW).setDataAndType(endereco, tipoSeguro).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            try {
                startActivity(Intent.createChooser(ver, nomeSeguro))
            } catch (e: ActivityNotFoundException) {
                // salvo; só não há app para abrir este tipo
            }
        }
    }

    // ------------------------------------------------------------ ponte com o site

    private inner class Ponte {
        @JavascriptInterface
        fun salvarArquivo(base64: String, nome: String, tipo: String) {
            if (!mesmoSite(configuracao.site, paginaAtual)) return
            fundo.execute {
                try {
                    salvarArquivo(Base64.decode(base64, Base64.DEFAULT), nome, tipo)
                } catch (e: Exception) {
                    runOnUiThread { Toast.makeText(this@WebActivity, "Não foi possível salvar o arquivo.", Toast.LENGTH_LONG).show() }
                }
            }
        }

        @JavascriptInterface
        fun sessao(token: String, usuarioJson: String) {
            if (!mesmoSite(configuracao.site, paginaAtual)) return
            if (token.isBlank()) return // saiu: a criança continua conectada e o adulto continua recebendo alertas
            val usuario = UsuarioSessao.ler(usuarioJson) ?: return
            fundo.execute { tratarSessao(token, usuario) }
        }
    }

    private fun tratarSessao(login: String, usuario: UsuarioSessao) {
        val api = ApiClient(configuracao.site)
        val acao = decidirSessao(usuario, configuracao.pareado, configuracao.criancaId, configuracao.adultoId)
        when (acao) {
            AcaoSessao.Nada -> if (configuracao.tokenAdulto != null && !configuracao.pareado) AlertasAdulto.agendar(applicationContext)
            AcaoSessao.AnotarCrianca -> configuracao.anotarCrianca(usuario.id, usuario.nome)
            AcaoSessao.ParearCrianca -> parearCrianca(login)
            AcaoSessao.ConfirmarTrocaDeAdulto -> if (trocaRecusadaPara != usuario.id) runOnUiThread { confirmarTroca(login, usuario) }
            AcaoSessao.RegistrarAdulto -> {
                val resposta = api.registrarAdulto(login, Build.MODEL, BuildConfig.VERSION_CODE)
                if (resposta is Resposta.Ok) {
                    val novo = resposta.corpo.optString("device_token")
                    if (novo.isNotBlank()) {
                        configuracao.tokenAdulto?.let { api.revogarAdulto(it) }
                        configuracao.salvarAdulto(configuracao.site, novo, usuario.id, usuario.nome)
                        AlertasAdulto.agendar(applicationContext)
                        runOnUiThread {
                            desenharFaixas()
                            if (!NotificationManagerCompat.from(this).areNotificationsEnabled()) pedirNotificacoes()
                        }
                    }
                }
            }
        }
    }

    /** Liga este celular à criança logada. Roda fora da tela. */
    private fun parearCrianca(login: String, avisarFalha: Boolean = false) {
        val api = ApiClient(configuracao.site)
        val resposta = api.parearMe(login, Build.MODEL, configuracao.token)
        if (resposta !is Resposta.Ok) {
            // Ex.: o login venceu enquanto a pergunta ficou aberta. Vale de novo na próxima entrada.
            if (avisarFalha) runOnUiThread {
                Toast.makeText(this, "Não deu para trocar agora. Saia e entre de novo com a conta da criança.", Toast.LENGTH_LONG).show()
            }
            return
        }
        // Celular passa a ser da criança: deixa de receber alertas de adulto.
        configuracao.tokenAdulto?.let { api.revogarAdulto(it) }
        configuracao.esquecerAdulto()
        AlertasAdulto.cancelar(applicationContext)
        configuracao.salvarPareamento(configuracao.site, ApiClient.lerPareamento(resposta.corpo))
        runOnUiThread {
            desenharFaixas()
            if (configuracao.temLocalizacao() && configuracao.temLocalizacaoSempre()) {
                LocationService.iniciar(this, enviarAgora = true)
            } else {
                Toast.makeText(this, "Celular conectado. Agora libere a localização.", Toast.LENGTH_LONG).show()
                abrirConfiguracoes()
            }
        }
    }

    /** Criança entrou no celular de um adulto: só troca se alguém confirmar. */
    private fun confirmarTroca(login: String, crianca: UsuarioSessao) {
        if (isFinishing || isDestroyed) return
        val adulto = configuracao.adultoNome.ifBlank { "um adulto" }
        val nome = crianca.nome.ifBlank { "a criança" }
        AlertDialog.Builder(this)
            .setTitle("Este celular é de $adulto")
            .setMessage(
                "Ele recebe os alertas da família. Transformar no celular de $nome? " +
                    "Ele passa a enviar a localização de $nome e $adulto deixa de receber os alertas aqui.",
            )
            .setPositiveButton("Transformar") { _, _ -> fundo.execute { parearCrianca(login, avisarFalha = true) } }
            .setNegativeButton("Não, manter") { _, _ -> trocaRecusadaPara = crianca.id }
            .setOnCancelListener { trocaRecusadaPara = crianca.id }
            .show()
    }

    private fun pedirNotificacoes() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !configuracao.temNotificacao()) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), PEDIDO_NOTIFICACAO)
        } else {
            val ajustes = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            runCatching { startActivity(ajustes) }
        }
    }

    override fun onRequestPermissionsResult(codigo: Int, permissoes: Array<out String>, resultados: IntArray) {
        super.onRequestPermissionsResult(codigo, permissoes, resultados)
        desenharFaixas()
    }

    // ------------------------------------------------------------ versão nova

    private fun conferirVersao() {
        val agora = System.currentTimeMillis()
        if (agora - versaoConferidaEm < INTERVALO_VERSAO_MS) return
        versaoConferidaEm = agora
        fundo.execute {
            val resposta = ApiClient(configuracao.site).ultimaVersao()
            val publicada = (resposta as? Resposta.Ok)?.corpo?.optString("versao").orEmpty()
            if (publicada.isNotBlank() && compararVersoes(publicada, BuildConfig.VERSION_NAME) > 0) {
                runOnUiThread {
                    versaoNova = publicada
                    desenharFaixas()
                }
            }
        }
    }

    private fun dp(valor: Int) = (valor * resources.displayMetrics.density).toInt()

    companion object {
        const val EXTRA_ENDERECO = "endereco"
        const val MARCA_USER_AGENT = "GestaoFamiliarApp/"
        private const val PEDIDO_ARQUIVO = 20
        private const val PEDIDO_NOTIFICACAO = 21
        private const val INTERVALO_VERSAO_MS = 60 * 60 * 1000L
    }
}
