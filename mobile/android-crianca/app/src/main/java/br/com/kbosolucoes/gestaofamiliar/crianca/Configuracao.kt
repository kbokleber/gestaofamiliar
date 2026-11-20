package br.com.kbosolucoes.gestaofamiliar.crianca

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.PowerManager
import androidx.core.content.ContextCompat
import java.io.File

/**
 * Dados do pareamento, guardados só neste aparelho (área privada do app, sem backup).
 * O token nunca sai daqui, a não ser no cabeçalho X-Device-Token das chamadas à API.
 */
class Configuracao(private val contexto: Context) {
    private val prefs = contexto.getSharedPreferences("pareamento", Context.MODE_PRIVATE)

    val pareado: Boolean get() = !token.isNullOrBlank()
    /** De quem é a posição que este celular envia. Quem veio do 2.0.4 não tem o campo: é criança. */
    val perfil: String get() = prefs.getString(PERFIL, PERFIL_CRIANCA) ?: PERFIL_CRIANCA
    /** Envia a localização de uma criança (o uso de sempre). */
    val pareadoComoCrianca: Boolean get() = pareado && perfil != PERFIL_ADULTO
    /** O adulto escolheu compartilhar a própria posição com os adultos da família. */
    val compartilhandoComoAdulto: Boolean get() = pareado && perfil == PERFIL_ADULTO
    /** Até quando a faixa "Compartilhar minha localização" fica escondida (o adulto tocou em "Agora não"). */
    val ofertaDispensadaAte: Long get() = prefs.getLong(OFERTA_DISPENSADA_ATE, 0L)
    /** O adulto parou de compartilhar, mas o servidor ainda não confirmou (sem rede): não envia e tenta de novo. */
    val pararPendente: Boolean get() = prefs.getBoolean(PARAR_PENDENTE, false)
    /** O adulto pediu, na tela de configurações, para começar a compartilhar (o app faz isso na tela principal). */
    val pedidoDeCompartilhar: Boolean get() = prefs.getBoolean(PEDIR_COMPARTILHAR, false)
    val token: String? get() = prefs.getString(TOKEN, null)
    val site: String get() = prefs.getString(SITE, ApiClient.SITE_PADRAO) ?: ApiClient.SITE_PADRAO
    val criancaNome: String get() = prefs.getString(CRIANCA, "") ?: ""
    /** 0 = pareado por código numa versão antiga, sem saber o id da criança. */
    val criancaId: Int get() = prefs.getInt(CRIANCA_ID, 0)

    // Celular de adulto: token só para buscar alertas (nunca envia localização).
    val tokenAdulto: String? get() = prefs.getString(TOKEN_ADULTO, null)
    val adultoId: Int get() = if (tokenAdulto.isNullOrBlank()) 0 else prefs.getInt(ADULTO_ID, 0)
    val adultoNome: String get() = prefs.getString(ADULTO_NOME, "") ?: ""
    val ultimoEnvio: Long get() = prefs.getLong(ULTIMO_ENVIO, 0L)
    val ultimoErro: String? get() = prefs.getString(ULTIMO_ERRO, null)
    val foiDesconectado: Boolean get() = prefs.getBoolean(DESCONECTADO, false)

    fun salvarPareamento(site: String, pareamento: Pareamento, perfil: String = PERFIL_CRIANCA) {
        prefs.edit()
            .putString(SITE, site)
            .putString(PERFIL, perfil)
            .remove(PEDIR_COMPARTILHAR)
            .remove(PARAR_PENDENTE)
            .putString(TOKEN, pareamento.token)
            .putInt(APARELHO, pareamento.aparelhoId)
            .putString(CRIANCA, pareamento.criancaNome)
            .putInt(CRIANCA_ID, pareamento.criancaId)
            .putBoolean(DESCONECTADO, false)
            .remove(ULTIMO_ERRO)
            .apply()
    }

    fun anotarCrianca(id: Int, nome: String) {
        val editor = prefs.edit().putInt(CRIANCA_ID, id)
        if (nome.isNotBlank()) editor.putString(CRIANCA, nome)
        editor.apply()
    }

    fun salvarAdulto(site: String, token: String, usuarioId: Int, nome: String = "") {
        prefs.edit()
            .putString(SITE, site)
            .putString(TOKEN_ADULTO, token)
            .putInt(ADULTO_ID, usuarioId)
            .putString(ADULTO_NOME, nome)
            .remove(AVISOS_ADULTO_CONFIRMAR)
            .remove(AVISOS_ADULTO_MOSTRADOS)
            .apply()
    }

    /** O adulto parou de compartilhar: apaga o token de posição e a fila (os alertas continuam). */
    fun pararCompartilhamento() {
        prefs.edit().remove(TOKEN).remove(APARELHO).remove(CRIANCA).remove(CRIANCA_ID)
            .remove(PERFIL).remove(ULTIMO_ERRO).remove(PARAR_PENDENTE).putBoolean(DESCONECTADO, false).apply()
        fila().limpar()
    }

    fun marcarPararPendente(pendente: Boolean) {
        prefs.edit().putBoolean(PARAR_PENDENTE, pendente).apply()
    }

    fun dispensarOferta(ate: Long) {
        prefs.edit().putLong(OFERTA_DISPENSADA_ATE, ate).apply()
    }

    fun pedirCompartilhar(pedir: Boolean) {
        prefs.edit().putBoolean(PEDIR_COMPARTILHAR, pedir).apply()
    }

    fun esquecerAdulto() {
        prefs.edit().remove(TOKEN_ADULTO).remove(ADULTO_ID).remove(ADULTO_NOME).apply()
    }

    fun registroDeAvisosAdulto(): RegistroDeAvisos =
        RegistroDeAvisos.ler(prefs.getString(AVISOS_ADULTO_CONFIRMAR, null), prefs.getString(AVISOS_ADULTO_MOSTRADOS, null))

    fun salvarRegistroDeAvisosAdulto(registro: RegistroDeAvisos) {
        val (confirmar, mostrados) = registro.serializar()
        prefs.edit().putString(AVISOS_ADULTO_CONFIRMAR, confirmar).putString(AVISOS_ADULTO_MOSTRADOS, mostrados).apply()
    }

    /** O adulto revogou no site: apaga o token e a fila; o celular precisa de um código novo. */
    fun marcarDesconectado() {
        prefs.edit().remove(TOKEN).putBoolean(DESCONECTADO, true).apply()
        fila().limpar()
    }

    fun registrarEnvio(resultado: ResultadoEnvio) {
        val editor = prefs.edit()
        if (resultado.enviados > 0) editor.putLong(ULTIMO_ENVIO, System.currentTimeMillis())
        if (resultado.erro != null) editor.putString(ULTIMO_ERRO, resultado.erro) else editor.remove(ULTIMO_ERRO)
        editor.apply()
    }

    fun registroDeAvisos(): RegistroDeAvisos =
        RegistroDeAvisos.ler(prefs.getString(AVISOS_CONFIRMAR, null), prefs.getString(AVISOS_MOSTRADOS, null))

    fun salvarRegistroDeAvisos(registro: RegistroDeAvisos) {
        val (confirmar, mostrados) = registro.serializar()
        prefs.edit().putString(AVISOS_CONFIRMAR, confirmar).putString(AVISOS_MOSTRADOS, mostrados).apply()
    }

    fun fila() = FilaDePontos(File(contexto.filesDir, "pontos-pendentes.json"))

    fun temLocalizacao(): Boolean =
        concedida(Manifest.permission.ACCESS_FINE_LOCATION) || concedida(Manifest.permission.ACCESS_COARSE_LOCATION)

    fun temLocalizacaoPrecisa(): Boolean = concedida(Manifest.permission.ACCESS_FINE_LOCATION)

    fun temLocalizacaoSempre(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.Q || concedida(Manifest.permission.ACCESS_BACKGROUND_LOCATION)

    fun temNotificacao(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || concedida(Manifest.permission.POST_NOTIFICATIONS)

    fun semEconomiaDeBateria(): Boolean {
        val energia = contexto.getSystemService(Context.POWER_SERVICE) as PowerManager
        return energia.isIgnoringBatteryOptimizations(contexto.packageName)
    }

    private fun concedida(permissao: String) =
        ContextCompat.checkSelfPermission(contexto, permissao) == PackageManager.PERMISSION_GRANTED

    companion object {
        const val PERFIL_CRIANCA = "crianca"
        const val PERFIL_ADULTO = "adulto"
        private const val PERFIL = "perfil"
        private const val OFERTA_DISPENSADA_ATE = "oferta_compartilhar_dispensada_ate"
        private const val PEDIR_COMPARTILHAR = "pedir_compartilhar"
        private const val PARAR_PENDENTE = "parar_compartilhamento_pendente"
        private const val SITE = "site"
        private const val TOKEN = "token"
        private const val APARELHO = "aparelho_id"
        private const val CRIANCA = "crianca_nome"
        private const val CRIANCA_ID = "crianca_id"
        private const val TOKEN_ADULTO = "token_adulto"
        private const val ADULTO_ID = "adulto_id"
        private const val ADULTO_NOME = "adulto_nome"
        private const val AVISOS_ADULTO_CONFIRMAR = "avisos_adulto_confirmar"
        private const val AVISOS_ADULTO_MOSTRADOS = "avisos_adulto_mostrados"
        private const val ULTIMO_ENVIO = "ultimo_envio"
        private const val ULTIMO_ERRO = "ultimo_erro"
        private const val DESCONECTADO = "desconectado"
        private const val AVISOS_CONFIRMAR = "avisos_confirmar"
        private const val AVISOS_MOSTRADOS = "avisos_mostrados"
    }
}
