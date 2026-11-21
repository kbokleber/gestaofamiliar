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
import android.widget.FrameLayout
import android.os.BatteryManager
import android.os.Handler
import android.os.Looper
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import java.io.File
import java.time.Instant
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

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
    /** Texto da faixa enquanto atualiza (ex.: "Baixando..."); null = convite para atualizar. */
    private var estadoAtualizacao: String? = null
    /** Foi às configurações liberar "instalar apps": ao voltar, segue com a atualização. */
    private var aguardandoPermissaoInstalar = false
    /** Criança para quem já disseram "não" à troca nesta abertura do app (não pergunta de novo a cada página). */
    @Volatile private var trocaRecusadaPara = 0
    // Login e usuário do site aberto agora (só em memória): servem para o adulto ligar o compartilhamento.
    @Volatile private var loginAtual: String? = null
    @Volatile private var usuarioAtual: UsuarioSessao? = null
    private var dialogoCompartilhar: AlertDialog? = null
    private lateinit var botaoSos: BotaoSos
    private var dialogoSos: AlertDialog? = null
    private val relogio = Handler(Looper.getMainLooper())
    /** Último pedido de login do Keycloak aberto aqui (para refazer no navegador quando for pelo Google). */
    private var pedidoDeLogin: String? = null
    private var versaoConferidaEm = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configuracao = Configuracao(this)
        Notificador.criarCanais(this)
        // APK de uma atualização anterior: já instalado (ou desistido), não precisa ocupar espaço.
        fundo.execute { java.io.File(cacheDir, "atualizacao").deleteRecursively() }
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
        // Checklist de envio: abre sozinho uma vez por pareamento (inclusive para quem atualizou da 2.0.6).
        if (configuracao.pareado && !configuracao.checklistMostrado) abrirConfiguracoes()
        if (configuracao.tokenAdulto != null) fundo.execute { AlertasAdulto.buscar(applicationContext) }
        if (configuracao.pararPendente) fundo.execute { PararCompartilhamento.tentar(applicationContext) }
        conferirVersao()
        // Voltou da tela de configurações, onde o adulto tocou em "Compartilhar minha localização".
        if (configuracao.pedidoDeCompartilhar && loginAtual != null) explicarCompartilhamento()
        desenharFaixas()
        // Voltou da tela do Android sem atualizar (cancelou, falhou ou saiu no meio): libera tentar de novo.
        if (estadoAtualizacao?.startsWith("Instalando") == true) {
            estadoAtualizacao = "A atualização não foi concluída. Toque para tentar de novo."
        }
        if (aguardandoPermissaoInstalar && packageManager.canRequestPackageInstalls()) {
            aguardandoPermissaoInstalar = false
            iniciarAtualizacao()
        }
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
        // Botão SOS por cima do site, no canto de baixo: só no celular que compartilha a localização.
        botaoSos = BotaoSos(
            this,
            aoSegurar = { comecarContagemSos() },
            aoSoltarCedo = { Toast.makeText(this, "Para pedir socorro, segure o SOS por 3 segundos.", Toast.LENGTH_SHORT).show() },
        )
        val moldura = FrameLayout(this).apply {
            addView(raiz, FrameLayout.LayoutParams(-1, -1))
            addView(botaoSos, FrameLayout.LayoutParams(dp(72), dp(72), Gravity.BOTTOM or Gravity.END).apply {
                setMargins(0, 0, dp(16), dp(24))
            })
        }
        setContentView(moldura)
        atualizarBotaoSos()
    }

    private fun atualizarBotaoSos() {
        if (!::botaoSos.isInitialized) return
        botaoSos.visibility = if (configuracao.pareado && !configuracao.pararPendente) View.VISIBLE else View.GONE
    }

    // ------------------------------------------------------------ SOS

    /** Segurou 3 s: contagem de 5 s com "Cancelar". Só envia se ninguém cancelar. */
    private fun comecarContagemSos() {
        if (isFinishing || isDestroyed || dialogoSos?.isShowing == true) return
        val inicio = System.currentTimeMillis()
        val texto = TextView(this).apply {
            textSize = 22f
            gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(Color.rgb(185, 28, 28))
            setPadding(dp(24), dp(24), dp(24), dp(8))
        }
        val cancelado = AtomicBoolean(false)
        val dialogo = AlertDialog.Builder(this)
            .setTitle("Pedir socorro")
            .setView(texto)
            .setCancelable(false)
            .setNegativeButton("CANCELAR") { _, _ -> cancelado.set(true) }
            .create()
        dialogoSos = dialogo
        val passo = object : Runnable {
            override fun run() {
                if (cancelado.get() || !dialogo.isShowing) return
                val restam = RegrasSos.segundosRestantes(inicio, System.currentTimeMillis())
                if (restam > 0) {
                    texto.text = "Enviando o SOS em $restam…\n\nToque em CANCELAR se foi sem querer."
                    relogio.postDelayed(this, 200)
                } else {
                    dialogo.dismiss()
                    enviarSos()
                }
            }
        }
        dialogo.setOnDismissListener { relogio.removeCallbacks(passo) }
        dialogo.show()
        dialogo.getButton(AlertDialog.BUTTON_NEGATIVE)?.apply { textSize = 18f }
        passo.run()
    }

    /** Pega a posição do momento (até 8 s) e envia; sem posição, o servidor usa a última conhecida. */
    @SuppressLint("MissingPermission")
    private fun enviarSos() {
        val token = configuracao.token
        if (token.isNullOrBlank()) {
            mostrarResultadoSos(Resposta.Desconectado)
            return
        }
        Toast.makeText(this, "Enviando o pedido de socorro…", Toast.LENGTH_SHORT).show()
        val enviado = AtomicBoolean(false)
        fun mandar(local: android.location.Location?) {
            if (!enviado.compareAndSet(false, true)) return
            val gerenciador = getSystemService(BATTERY_SERVICE) as BatteryManager
            val bateria = gerenciador.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY).takeIf { it in 0..100 }
            val corpo = RegrasSos.montarCorpo(
                local?.latitude, local?.longitude, local?.takeIf { it.hasAccuracy() }?.accuracy, bateria,
                local?.let { Instant.ofEpochMilli(it.time) },
            )
            fundo.execute {
                val resposta = ApiClient(configuracao.site).enviarSos(token, corpo)
                runOnUiThread { mostrarResultadoSos(resposta) }
            }
        }
        if (configuracao.temLocalizacao()) {
            val cancelar = CancellationTokenSource()
            LocationServices.getFusedLocationProviderClient(this)
                .getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, cancelar.token)
                .addOnSuccessListener { mandar(it) }
                .addOnFailureListener { mandar(null) }
            relogio.postDelayed({ cancelar.cancel(); mandar(null) }, 8_000)
        } else {
            mandar(null)
        }
    }

    private fun mostrarResultadoSos(resposta: Resposta) {
        if (isFinishing || isDestroyed) return
        AlertDialog.Builder(this)
            .setTitle(if (resposta is Resposta.Ok) "SOS enviado" else "SOS não enviado")
            .setMessage(RegrasSos.mensagemDoResultado(resposta, System.currentTimeMillis()))
            .setPositiveButton("OK", null)
            .show()
    }

    /** Faixas no topo, só quando há algo a resolver. */
    private fun desenharFaixas() {
        atualizarBotaoSos()
        faixas.removeAllViews()
        if (configuracao.pareado && (!configuracao.temLocalizacao() || !configuracao.temLocalizacaoSempre())) {
            faixa("Falta liberar a localização neste celular. Toque para ajustar.", alerta = true) { abrirConfiguracoes() }
        } else if (configuracao.foiDesconectado && !configuracao.pareado) {
            val texto = if (configuracao.perfil == Configuracao.PERFIL_ADULTO) {
                "O compartilhamento da sua localização foi desligado no site. Toque para ver."
            } else {
                "Este celular foi desconectado da família. Entre de novo com a conta da criança."
            }
            faixa(texto, alerta = true) { abrirConfiguracoes() }
        }
        if (deveOferecerCompartilhar(
                adultoRegistrado = configuracao.tokenAdulto != null,
                pareadoComoCrianca = configuracao.pareadoComoCrianca,
                compartilhandoComoAdulto = configuracao.compartilhandoComoAdulto,
                dispensadaAte = configuracao.ofertaDispensadaAte,
                agora = System.currentTimeMillis(),
            ) && loginAtual != null
        ) {
            faixa("Compartilhar a sua localização com os adultos da família? Toque para saber mais.", alerta = false) {
                explicarCompartilhamento()
            }
        }
        if (configuracao.tokenAdulto != null && !NotificationManagerCompat.from(this).areNotificationsEnabled()) {
            faixa("Ative as notificações para receber os alertas da família.", alerta = true) { pedirNotificacoes() }
        }
        versaoNova?.let { v ->
            val texto = estadoAtualizacao ?: "Nova versão do app ($v). Toque para atualizar."
            faixa(texto, alerta = false) { iniciarAtualizacao() }
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

        /** Item "Configurações de envio" do menu do site (app 2.0.5+). Não envia nada: só abre a tela do celular. */
        @JavascriptInterface
        fun abrirConfiguracoesDeEnvio() {
            if (!mesmoSite(configuracao.site, paginaAtual)) return
            runOnUiThread { abrirConfiguracoes() }
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
        loginAtual = login
        usuarioAtual = usuario
        // Outro adulto entrou num celular que compartilha a posição de um adulto: o anterior para de compartilhar.
        if (devePararDeCompartilhar(configuracao.compartilhandoComoAdulto, configuracao.criancaId, usuario)) {
            pararCompartilhamento()
        }
        // Celular de adulto: o que recebe alertas ou o que compartilha a posição de um adulto (pergunta antes de trocar).
        val adultoDoCelular = configuracao.adultoId.takeIf { it != 0 }
            ?: (if (configuracao.compartilhandoComoAdulto) configuracao.criancaId else 0)
        val acao = decidirSessao(usuario, configuracao.pareadoComoCrianca, configuracao.criancaId, adultoDoCelular)
        when (acao) {
            AcaoSessao.Nada -> if (configuracao.tokenAdulto != null && !configuracao.pareadoComoCrianca) AlertasAdulto.agendar(applicationContext)
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
        runOnUiThread {
            desenharFaixas()
            if (configuracao.pedidoDeCompartilhar && !usuario.crianca) explicarCompartilhamento()
        }
    }

    // ------------------------------------------------------------ adulto compartilhando a posição

    /** Explica o que é compartilhado antes de pedir qualquer permissão. */
    private fun explicarCompartilhamento() {
        if (isFinishing || isDestroyed || dialogoCompartilhar?.isShowing == true) return
        val usuario = usuarioAtual
        val login = loginAtual
        if (usuario == null || login == null || usuario.crianca || configuracao.pareadoComoCrianca) {
            configuracao.pedirCompartilhar(false)
            return
        }
        configuracao.pedirCompartilhar(false)
        dialogoCompartilhar = AlertDialog.Builder(this)
            .setTitle("Compartilhar a sua localização")
            .setMessage(TEXTO_COMPARTILHAR)
            .setPositiveButton("Compartilhar") { _, _ -> fundo.execute { comecarCompartilhamento(login) } }
            .setNegativeButton("Agora não") { _, _ ->
                configuracao.dispensarOferta(System.currentTimeMillis() + OFERTA_PAUSA_MS)
                desenharFaixas()
            }
            .show()
    }

    /** Liga este celular à posição do adulto logado. Roda fora da tela. */
    private fun comecarCompartilhamento(login: String) {
        val resposta = ApiClient(configuracao.site).parearAdulto(login, Build.MODEL, configuracao.token)
        if (resposta !is Resposta.Ok) {
            val motivo = when (resposta) {
                is Resposta.Recusado -> resposta.mensagem
                is Resposta.TentarDepois -> "Não deu para falar com o site agora. Confira a internet e tente de novo."
                else -> "Saia e entre de novo no app e tente outra vez."
            }
            runOnUiThread { Toast.makeText(this, motivo, Toast.LENGTH_LONG).show() }
            return
        }
        configuracao.salvarPareamento(configuracao.site, ApiClient.lerPareamento(resposta.corpo), Configuracao.PERFIL_ADULTO)
        runOnUiThread {
            desenharFaixas()
            if (configuracao.temLocalizacao() && configuracao.temLocalizacaoSempre()) {
                LocationService.iniciar(this, enviarAgora = true)
                Toast.makeText(this, "Pronto. Os adultos da família já veem você no mapa.", Toast.LENGTH_LONG).show()
                if (!configuracao.checklistMostrado) abrirConfiguracoes()
            } else {
                Toast.makeText(this, "Falta liberar a localização \"o tempo todo\".", Toast.LENGTH_LONG).show()
                abrirConfiguracoes()
            }
        }
    }

    /** Para de enviar a posição do adulto (os alertas continuam). Sem rede, conclui depois. Roda fora da tela. */
    private fun pararCompartilhamento() {
        PararCompartilhamento.pedir(applicationContext)
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
                if (!configuracao.checklistMostrado) abrirConfiguracoes()
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

    /** Baixa e instala a versão nova pelo próprio app; o Android pede a confirmação. */
    private fun iniciarAtualizacao() {
        if (estadoAtualizacao != null && estadoAtualizacao!!.endsWith("...")) return // já em andamento
        if (!packageManager.canRequestPackageInstalls()) {
            aguardandoPermissaoInstalar = true
            Toast.makeText(this, "Permita que o Gestão Familiar instale a atualização e volte ao app.", Toast.LENGTH_LONG).show()
            val ajustes = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))
            runCatching { startActivity(ajustes) }.onFailure { abrirFora(ApiClient.normalizarEndereco(configuracao.site) + "/app") }
            return
        }
        fundo.execute {
            Atualizador.atualizar(applicationContext, configuracao.site) { etapa ->
                runOnUiThread {
                    estadoAtualizacao = when (etapa) {
                        Atualizador.Etapa.Baixando -> "Baixando a versão nova..."
                        Atualizador.Etapa.Instalando -> "Instalando... confirme na tela do Android."
                        is Atualizador.Etapa.Falhou -> "Não deu para atualizar (${etapa.motivo}). Toque para tentar de novo."
                    }
                    desenharFaixas()
                }
            }
        }
    }

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
        private const val OFERTA_PAUSA_MS = 30L * 24 * 60 * 60 * 1000

        const val TEXTO_COMPARTILHAR =
            "O que é compartilhado: a posição deste celular a cada 5 minutos e a bateria.\n\n" +
                "Quem vê: só os adultos da família com acesso à Localização. As crianças nunca veem.\n\n" +
                "Por quanto tempo: o histórico fica guardado 7 dias e depois é apagado.\n\n" +
                "Você não recebe nem gera alertas de chegada e saída.\n\n" +
                "SOS: se você usar o botão SOS, seu nome, posição e bateria vão só para os familiares escolhidos. A posição do SOS fica guardada 7 dias e o registro do SOS, 30 dias.\n\n" +
                "Para desligar: Configurações do app › Parar de compartilhar, ou Revogar no site.\n\n" +
                "Depois, o Android vai pedir a localização. Escolha \"Permitir o tempo todo\"."
    }
}
