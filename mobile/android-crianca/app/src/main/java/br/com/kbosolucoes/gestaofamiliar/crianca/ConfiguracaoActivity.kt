package br.com.kbosolucoes.gestaofamiliar.crianca

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
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
import androidx.core.app.NotificationManagerCompat

/**
 * Configurações do celular da criança: mostra, passo a passo, o que falta liberar para a
 * localização funcionar sempre. Também permite conectar com o código do site (alternativa
 * a entrar no app com a conta da criança).
 */
class ConfiguracaoActivity : Activity() {
    private lateinit var configuracao: Configuracao
    private lateinit var raiz: LinearLayout
    private var pareando = false

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
            telaPareado()
        } else {
            // Adulto no próprio celular: primeiro a opção de compartilhar; o código continua disponível embaixo.
            if (configuracao.tokenAdulto != null) telaAdulto()
            telaParear()
        }
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

        subtitulo("Para funcionar sempre")
        val checagens = checagensDeEnvio(
            localizacao = configuracao.temLocalizacao(),
            notificacao = NotificationManagerCompat.from(this).areNotificationsEnabled(),
            localizacaoSempre = configuracao.temLocalizacaoSempre(),
            semEconomiaDeBateria = configuracao.semEconomiaDeBateria(),
        )
        for (checagem in checagens) {
            passo(checagem.nome, checagem.ok, checagem.explicacao, "Abrir ajuste") { abrirAjuste(checagem.ajuste) }
        }
        if (configuracao.temLocalizacao() && !configuracao.temLocalizacaoPrecisa()) {
            aviso("A localização está aproximada. Para mostrar \"está em Casa\" com segurança, ative \"Localização precisa\" nas configurações do app.")
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

    private fun passo(nome: String, ok: Boolean, explicacao: String, rotulo: String, acao: () -> Unit) {
        val linha = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(8), 0, dp(8))
        }
        val textos = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        textos.addView(TextView(this).apply {
            text = (if (ok) "✓ " else "✗ ") + nome
            textSize = 16f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(if (ok) Color.rgb(21, 128, 61) else Color.rgb(185, 28, 28))
        })
        if (!ok) textos.addView(TextView(this).apply {
            text = explicacao
            textSize = 14f
            setTextColor(Color.rgb(75, 85, 99))
        })
        linha.addView(textos, LinearLayout.LayoutParams(0, -2, 1f))
        if (!ok) linha.addView(Button(this).apply {
            text = rotulo
            isAllCaps = false
            setOnClickListener { acao() }
        })
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
