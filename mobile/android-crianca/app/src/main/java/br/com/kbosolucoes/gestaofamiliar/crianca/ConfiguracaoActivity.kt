package br.com.kbosolucoes.gestaofamiliar.crianca

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Configurações do celular da criança: mostra, passo a passo, o que falta liberar para a
 * localização funcionar sempre. Também permite conectar com o código do site (alternativa
 * a entrar no app com a conta da criança).
 */
class ConfiguracaoActivity : Activity() {
    private lateinit var configuracao: Configuracao
    private lateinit var raiz: LinearLayout
    private var pareando = false
    private var atualizacao: EstadoAtualizacao = EstadoAtualizacao.NaoConsultado
    private var progressoAtualizacao: String? = null
    private var aguardandoPermissaoInstalar = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configuracao = Configuracao(this)
        LocationService.criarCanal(this)
        raiz = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
        }
        setContentView(ScrollView(this).apply { addView(raiz) })
    }

    override fun onResume() {
        super.onResume()
        desenhar()
        if (configuracao.pareado) LocationService.iniciar(this)
        if (configuracao.pararPendente) Thread {
            if (PararCompartilhamento.tentar(applicationContext)) runOnUiThread { desenhar() }
        }.start()
        if (aguardandoPermissaoInstalar && packageManager.canRequestPackageInstalls()) {
            aguardandoPermissaoInstalar = false
            atualizarApp()
        } else if (atualizacao == EstadoAtualizacao.NaoConsultado) {
            verificarAtualizacao()
        }
    }

    override fun onRequestPermissionsResult(codigo: Int, permissoes: Array<out String>, resultados: IntArray) {
        super.onRequestPermissionsResult(codigo, permissoes, resultados)
        desenhar()
        if (configuracao.pareado) LocationService.iniciar(this, enviarAgora = true)
    }

    private fun desenhar() {
        raiz.removeAllViews()
        titulo("Configurações de envio")
        val adulto = configuracao.compartilhandoComoAdulto || (!configuracao.pareado && configuracao.tokenAdulto != null)
        texto(
            if (adulto) {
                "Neste celular você recebe os alertas da família. Se quiser, também pode compartilhar a sua localização: " +
                    "só os adultos da família veem, e as crianças nunca."
            } else {
                "Este app envia a localização e a bateria deste celular para a família, a cada 5 minutos, e mostra os lembretes de atividades. " +
                    "Ele não grava áudio, não vê a tela, as fotos nem as mensagens. " +
                    "O botão SOS envia nome, posição e bateria só para os familiares escolhidos; a posição do SOS fica 7 dias e o registro, 30 dias."
            },
            cinza = true,
        )
        if (configuracao.pareado) {
            configuracao.marcarChecklistMostrado()
            telaPareado()
        } else {
            // Adulto no próprio celular: primeiro a opção de compartilhar; o código continua disponível embaixo.
            if (configuracao.tokenAdulto != null) telaAdulto()
            telaParear()
        }
        telaAtualizacao()
    }

    // ------------------------------------------------------------ atualização do app

    /** Versão instalada × publicada no site. Nenhum número fixo: a publicada vem sempre do /ultima. */
    private fun telaAtualizacao() {
        subtitulo("Atualização do app")
        texto("Versão instalada: ${BuildConfig.VERSION_NAME}", cinza = true)
        texto(progressoAtualizacao ?: textoAtualizacao(atualizacao))
        texto(textoUltimaConsulta(configuracao.ultimaConsultaVersao), cinza = true)
        val disponivel = atualizacao as? EstadoAtualizacao.Disponivel
        if (disponivel != null) {
            botao("Atualizar para a ${disponivel.publicada}") { atualizarApp() }
        }
        botao(if (atualizacao == EstadoAtualizacao.Consultando) "Consultando..." else "Verificar atualização") {
            verificarAtualizacao()
        }
    }

    private fun verificarAtualizacao() {
        if (atualizacao == EstadoAtualizacao.Consultando) return
        atualizacao = EstadoAtualizacao.Consultando
        progressoAtualizacao = null
        desenhar()
        Thread {
            val estado = Atualizador.consultar(configuracao.site)
            configuracao.anotarConsultaVersao()
            runOnUiThread {
                atualizacao = estado
                desenhar()
            }
        }.start()
    }

    /** Baixa e instala a versão publicada (o Android pede a confirmação). */
    private fun atualizarApp() {
        if (progressoAtualizacao?.endsWith("...") == true) return
        if (!packageManager.canRequestPackageInstalls()) {
            aguardandoPermissaoInstalar = true
            android.widget.Toast.makeText(this, "Permita que o Gestão Familiar instale a atualização e volte.", android.widget.Toast.LENGTH_LONG).show()
            runCatching { startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))) }
            return
        }
        Thread {
            Atualizador.atualizar(applicationContext, configuracao.site) { etapa ->
                runOnUiThread {
                    progressoAtualizacao = when (etapa) {
                        Atualizador.Etapa.Baixando -> "Baixando a versão nova..."
                        Atualizador.Etapa.Instalando -> "Instalando... confirme na tela do Android."
                        is Atualizador.Etapa.Falhou -> "Não deu para atualizar (${etapa.motivo}). Toque em \"Atualizar\" para tentar de novo."
                    }
                    desenhar()
                }
            }
        }.start()
    }

    // ------------------------------------------------------------ adulto

    /** Adulto no próprio celular, ainda sem compartilhar: explica e leva para a tela principal ligar. */
    private fun telaAdulto() {
        if (configuracao.foiDesconectado && configuracao.perfil == Configuracao.PERFIL_ADULTO) {
            aviso("O compartilhamento da sua localização foi desligado no site.")
        }
        subtitulo("Compartilhar a minha localização")
        texto(WebActivity.TEXTO_COMPARTILHAR, cinza = true)
        botao("Compartilhar a minha localização") {
            configuracao.pedirCompartilhar(true)
            finish() // a tela principal mostra a confirmação, com a conta que está logada
        }
    }

    // ------------------------------------------------------------ pareamento

    private fun telaParear() {
        if (configuracao.foiDesconectado) {
            aviso("Este celular foi desconectado da família. Peça um código novo para um adulto.")
        }
        subtitulo("Ligar este celular")
        texto("O jeito mais fácil: a criança entra no app com a conta dela e o celular se conecta sozinho.", cinza = true)
        texto("Ou use um código: no site, um adulto abre Localização › Celulares e toca em \"Gerar código\".", cinza = true)

        val site = campo("Endereço do site", configuracao.site, InputType.TYPE_TEXT_VARIATION_URI)
        val codigo = campo("Código (ex.: ABCD-2345)", "", InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS)
        val nome = campo("Nome deste celular (opcional)", Build.MODEL ?: "", InputType.TYPE_TEXT_FLAG_CAP_WORDS)
        val mensagem = texto("", cinza = true)

        botao(if (pareando) "Conectando..." else "Conectar à família") {
            if (pareando) return@botao
            val codigoDigitado = codigo.text.toString().trim()
            if (codigoDigitado.length < 8) {
                mensagem.text = "Digite o código de 8 letras e números que aparece no site."
                return@botao
            }
            pareando = true
            mensagem.text = "Conectando..."
            val endereco = ApiClient.normalizarEndereco(site.text.toString())
            Thread {
                val resposta = ApiClient(endereco).parear(codigoDigitado, nome.text.toString())
                runOnUiThread {
                    pareando = false
                    when (resposta) {
                        is Resposta.Ok -> {
                            configuracao.salvarPareamento(endereco, ApiClient.lerPareamento(resposta.corpo))
                            desenhar()
                            pedirLocalizacao()
                        }
                        is Resposta.Recusado -> mensagem.text = resposta.mensagem
                        is Resposta.TentarDepois -> mensagem.text = "Não deu para falar com o site agora: ${resposta.motivo}. Confira a internet e tente de novo."
                        Resposta.Desconectado -> mensagem.text = "Código não aceito."
                    }
                }
            }.start()
        }
    }

    // ------------------------------------------------------------ pareado

    private fun telaPareado() {
        val adulto = configuracao.compartilhandoComoAdulto
        val nome = configuracao.criancaNome.ifBlank { if (adulto) "você" else "criança" }
        subtitulo(if (adulto) "Compartilhando a localização de $nome" else "Conectado como $nome")

        subtitulo("Checklist de envio")
        val itens = checklistDeEnvio(configuracao.estadoDoCelular(servicoRodando = LocationService.rodando))
        val faltam = itensQueFaltam(itens)
        if (faltam.isEmpty()) {
            texto("Tudo certo: a localização deve continuar chegando com o app fechado.")
        } else {
            aviso(
                if (faltam.size == 1) "Falta 1 item para o envio funcionar sempre, mesmo com o app fechado."
                else "Faltam ${faltam.size} itens para o envio funcionar sempre, mesmo com o app fechado.",
            )
        }
        for (item in itens) {
            val extra: Pair<String, () -> Unit>? = when (item.estado) {
                EstadoItem.MANUAL_PENDENTE -> "Já fiz" to {
                    configuracao.confirmarInicioAutomatico(true)
                    desenhar()
                }
                EstadoItem.MANUAL_CONFIRMADO -> "Desfazer" to {
                    configuracao.confirmarInicioAutomatico(false)
                    desenhar()
                }
                else -> null
            }
            passo(item, extra) { item.ajuste?.let { abrirAjuste(it) } }
        }

        subtitulo("Envio")
        texto(formatarUltimoEnvio(configuracao.ultimoEnvio))
        val pendentes = configuracao.fila().tamanho()
        if (pendentes > 0) texto("$pendentes ${if (pendentes == 1) "posição esperando" else "posições esperando"} a internet voltar.", cinza = true)
        configuracao.ultimoErro?.let { texto("Último problema: $it", cinza = true) }
        botao("Enviar agora") {
            LocationService.iniciar(this, enviarAgora = true)
            raiz.postDelayed({ desenhar() }, 4000)
        }
        texto(textoHistorico(adulto), cinza = true)
        if (adulto && configuracao.pararPendente) {
            aviso("O envio já parou neste celular. Falta avisar o site: o app conclui sozinho assim que tiver internet.")
        } else if (adulto) {
            botao("Parar de compartilhar") {
                Thread {
                    val concluiu = PararCompartilhamento.pedir(applicationContext)
                    runOnUiThread {
                        if (!concluiu) {
                            android.widget.Toast.makeText(
                                this,
                                "Parou de enviar. Sem internet agora: o app avisa o site assim que conectar.",
                                android.widget.Toast.LENGTH_LONG,
                            ).show()
                        }
                        desenhar()
                    }
                }.start()
            }
        } else {
            texto("Para desligar, um adulto revoga este celular no site.", cinza = true)
        }
        botao("Voltar ao app") { finish() }
    }

    // ------------------------------------------------------------ permissões

    /** Leva direto à tela do Android que resolve aquela checagem. */
    private fun abrirAjuste(ajuste: AjusteAndroid) {
        val detalhesDoApp = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
        when (ajuste) {
            AjusteAndroid.GPS -> runCatching { startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS)) }
                .onFailure { runCatching { startActivity(detalhesDoApp) } }
            // Android 12+: pedir a permissão de novo mostra a troca de "aproximada" para "precisa".
            AjusteAndroid.PRECISAO -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) pedirLocalizacao()
                else runCatching { startActivity(detalhesDoApp) }.onFailure { pedirLocalizacao() }
            AjusteAndroid.ENVIO -> {
                LocationService.iniciar(this, enviarAgora = true)
                raiz.postDelayed({ desenhar() }, 4000)
            }
            AjusteAndroid.ENTENDI_PARADA -> {
                configuracao.esquecerParada()
                desenhar()
            }
            AjusteAndroid.INICIO_AUTOMATICO -> abrirInicioAutomatico(detalhesDoApp)
            AjusteAndroid.REDE -> {
                val painel = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) Intent(Settings.Panel.ACTION_INTERNET_CONNECTIVITY)
                    else Intent(Settings.ACTION_WIRELESS_SETTINGS)
                runCatching { startActivity(painel) }.onFailure { runCatching { startActivity(Intent(Settings.ACTION_SETTINGS)) } }
            }
            AjusteAndroid.LOCALIZACAO -> runCatching { startActivity(detalhesDoApp) }.onFailure { pedirLocalizacao() }
            AjusteAndroid.NOTIFICACOES -> {
                val notificacoes = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
                runCatching { startActivity(notificacoes) }.onFailure { runCatching { startActivity(detalhesDoApp) } }
            }
            // Android 10 mostra a opção "o tempo todo" no próprio diálogo; do 11 em diante só nos ajustes do app.
            AjusteAndroid.LOCALIZACAO_SEMPRE ->
                if (Build.VERSION.SDK_INT == Build.VERSION_CODES.Q && configuracao.temLocalizacao()) pedirLocalizacaoSempre()
                else runCatching { startActivity(detalhesDoApp) }.onFailure { pedirLocalizacaoSempre() }
            AjusteAndroid.BATERIA -> pedirSemEconomia()
        }
    }

    /** Tela de "Início automático" da marca, quando existe; senão, os ajustes do app. O app não consegue ler o resultado. */
    private fun abrirInicioAutomatico(detalhesDoApp: Intent) {
        val candidatos = listOf(
            ComponentName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity"),
            ComponentName("com.coloros.safecenter", "com.coloros.safecenter.permission.startup.StartupAppListActivity"),
            ComponentName("com.oppo.safe", "com.oppo.safe.permission.startup.StartupAppListActivity"),
            ComponentName("com.vivo.permissionmanager", "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"),
            ComponentName("com.huawei.systemmanager", "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity"),
        )
        for (componente in candidatos) {
            if (runCatching { startActivity(Intent().setComponent(componente)) }.isSuccess) return
        }
        runCatching { startActivity(detalhesDoApp) }
    }

    private fun pedirLocalizacao() {
        requestPermissions(
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
            PEDIDO_LOCALIZACAO,
        )
    }

    private fun pedirLocalizacaoSempre() {
        if (!configuracao.temLocalizacao()) {
            pedirLocalizacao()
            return
        }
        // No Android 10 abre um diálogo; do 11 em diante o sistema leva à tela de configurações do app.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION), PEDIDO_SEMPRE)
        }
    }

    @SuppressLint("BatteryLife")
    private fun pedirSemEconomia() {
        val pedido = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName"))
        val lista = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        runCatching { startActivity(pedido) }.onFailure { runCatching { startActivity(lista) } }
    }

    // ------------------------------------------------------------ componentes simples

    private fun titulo(t: String) = TextView(this).apply {
        text = t
        textSize = 26f
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(ROXO)
        raiz.addView(this)
    }

    private fun subtitulo(t: String) = TextView(this).apply {
        text = t
        textSize = 19f
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(Color.rgb(17, 24, 39))
        setPadding(0, dp(20), 0, dp(6))
        raiz.addView(this)
    }

    private fun texto(t: String, cinza: Boolean = false) = TextView(this).apply {
        text = t
        textSize = 15f
        setTextColor(if (cinza) Color.rgb(75, 85, 99) else Color.rgb(17, 24, 39))
        setPadding(0, dp(4), 0, dp(4))
        raiz.addView(this)
    }

    private fun aviso(t: String) = TextView(this).apply {
        text = t
        textSize = 15f
        setTextColor(Color.rgb(146, 64, 14))
        setBackgroundColor(Color.rgb(254, 243, 199))
        setPadding(dp(12), dp(10), dp(12), dp(10))
        raiz.addView(this, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(12) })
    }

    private fun campo(rotulo: String, valor: String, tipo: Int): EditText {
        texto(rotulo)
        return EditText(this).apply {
            setText(valor)
            inputType = InputType.TYPE_CLASS_TEXT or tipo
            isSingleLine = true
            textSize = 17f
            raiz.addView(this, LinearLayout.LayoutParams(-1, -2))
        }
    }

    private fun botao(rotulo: String, acao: () -> Unit) = Button(this).apply {
        text = rotulo
        isAllCaps = false
        textSize = 17f
        setTextColor(Color.WHITE)
        setBackgroundColor(ROXO)
        setOnClickListener { acao() }
        raiz.addView(this, LinearLayout.LayoutParams(-1, dp(52)).apply { topMargin = dp(16) })
    }

    private fun passo(item: ItemChecklist, extra: Pair<String, () -> Unit>?, acao: () -> Unit) {
        val linha = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(8), 0, dp(8))
        }
        val textos = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val (marca, cor, sufixo) = when (item.estado) {
            EstadoItem.OK -> Triple("✓ ", Color.rgb(21, 128, 61), "")
            EstadoItem.MANUAL_CONFIRMADO -> Triple("✓ ", Color.rgb(21, 128, 61), " (confirmado por você)")
            EstadoItem.FALTA -> Triple("✗ ", Color.rgb(185, 28, 28), "")
            EstadoItem.ATRASADO -> Triple("! ", Color.rgb(180, 83, 9), " (atrasado)")
            EstadoItem.MANUAL_PENDENTE -> Triple("? ", Color.rgb(180, 83, 9), " (confirmação manual)")
        }
        textos.addView(TextView(this).apply {
            text = marca + item.nome + sufixo
            textSize = 16f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(cor)
        })
        if (item.explicacao.isNotBlank()) textos.addView(TextView(this).apply {
            text = item.explicacao
            textSize = 14f
            setTextColor(Color.rgb(75, 85, 99))
        })
        linha.addView(textos, LinearLayout.LayoutParams(0, -2, 1f))
        val botoes = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        if (item.estado != EstadoItem.OK && item.rotuloAjuste != null) botoes.addView(Button(this).apply {
            text = item.rotuloAjuste
            isAllCaps = false
            setOnClickListener { acao() }
        })
        if (extra != null) botoes.addView(Button(this).apply {
            text = extra.first
            isAllCaps = false
            setOnClickListener { extra.second() }
        })
        if (botoes.childCount > 0) linha.addView(botoes)
        raiz.addView(linha)
        raiz.addView(View(this).apply { setBackgroundColor(Color.rgb(229, 231, 235)) }, LinearLayout.LayoutParams(-1, dp(1)))
    }

    private fun dp(valor: Int) = (valor * resources.displayMetrics.density).toInt()

    private companion object {
        val ROXO = Color.rgb(124, 58, 237)
        const val PEDIDO_LOCALIZACAO = 1
        const val PEDIDO_SEMPRE = 2
    }
}
