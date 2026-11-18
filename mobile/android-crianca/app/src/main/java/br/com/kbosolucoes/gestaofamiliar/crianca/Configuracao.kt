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
    val token: String? get() = prefs.getString(TOKEN, null)
    val site: String get() = prefs.getString(SITE, ApiClient.SITE_PADRAO) ?: ApiClient.SITE_PADRAO
    val criancaNome: String get() = prefs.getString(CRIANCA, "") ?: ""
    val ultimoEnvio: Long get() = prefs.getLong(ULTIMO_ENVIO, 0L)
    val ultimoErro: String? get() = prefs.getString(ULTIMO_ERRO, null)
    val foiDesconectado: Boolean get() = prefs.getBoolean(DESCONECTADO, false)

    fun salvarPareamento(site: String, pareamento: Pareamento) {
        prefs.edit()
            .putString(SITE, site)
            .putString(TOKEN, pareamento.token)
            .putInt(APARELHO, pareamento.aparelhoId)
            .putString(CRIANCA, pareamento.criancaNome)
            .putBoolean(DESCONECTADO, false)
            .remove(ULTIMO_ERRO)
            .apply()
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

    private companion object {
        const val SITE = "site"
        const val TOKEN = "token"
        const val APARELHO = "aparelho_id"
        const val CRIANCA = "crianca_nome"
        const val ULTIMO_ENVIO = "ultimo_envio"
        const val ULTIMO_ERRO = "ultimo_erro"
        const val DESCONECTADO = "desconectado"
        const val AVISOS_CONFIRMAR = "avisos_confirmar"
        const val AVISOS_MOSTRADOS = "avisos_mostrados"
    }
}
