package br.com.kbosolucoes.gestaofamiliar.crianca

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import android.widget.Toast
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Atualização pelo próprio app: baixa o APK publicado em /app, confere o SHA-256 informado pelo
 * servidor e entrega ao instalador do Android. O Android pede confirmação (apps fora da Play Store);
 * no Android 12+, depois que o próprio app passa a ser quem instalou, ele pode atualizar sem a tela extra.
 */
object Atualizador {
    const val ACAO_RESULTADO = "br.com.kbosolucoes.gestaofamiliar.crianca.RESULTADO_ATUALIZACAO"

    sealed class Etapa {
        object Baixando : Etapa()
        object Instalando : Etapa()
        data class Falhou(val motivo: String) : Etapa()
    }

    /** Roda fora da tela. Avisa as etapas em [aoMudar]. */
    fun atualizar(contexto: Context, site: String, aoMudar: (Etapa) -> Unit) {
        val base = ApiClient.normalizarEndereco(site)
        val info = ApiClient(site).ultimaVersao()
        val esperado = (info as? Resposta.Ok)?.corpo?.optString("sha256").orEmpty().lowercase()
        if (esperado.length != 64) {
            aoMudar(Etapa.Falhou("não deu para consultar a versão nova"))
            return
        }
        aoMudar(Etapa.Baixando)
        val pasta = File(contexto.cacheDir, "atualizacao").apply { mkdirs() }
        val arquivo = File(pasta, "app.apk")
        try {
            baixar("$base/api/v1/app-android/download", arquivo)
        } catch (e: IOException) {
            arquivo.delete()
            aoMudar(Etapa.Falhou("falha no download: ${e.message ?: "sem internet"}"))
            return
        }
        if (sha256(arquivo) != esperado) {
            arquivo.delete()
            aoMudar(Etapa.Falhou("o arquivo baixado não confere com o publicado"))
            return
        }
        aoMudar(Etapa.Instalando)
        try {
            instalar(contexto, arquivo)
        } catch (e: Exception) {
            aoMudar(Etapa.Falhou("o Android recusou a instalação: ${e.message ?: "erro"}"))
        }
    }

    private fun baixar(endereco: String, destino: File) {
        val conexao = URL(endereco).openConnection() as HttpURLConnection
        try {
            conexao.connectTimeout = 20_000
            conexao.readTimeout = 60_000
            if (conexao.responseCode !in 200..299) throw IOException("erro ${conexao.responseCode}")
            conexao.inputStream.use { entrada -> destino.outputStream().use { entrada.copyTo(it) } }
        } finally {
            conexao.disconnect()
        }
    }

    fun sha256(arquivo: File): String {
        val resumo = MessageDigest.getInstance("SHA-256")
        arquivo.inputStream().use { entrada ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val lidos = entrada.read(buffer)
                if (lidos < 0) break
                resumo.update(buffer, 0, lidos)
            }
        }
        return resumo.digest().joinToString("") { "%02x".format(it) }
    }

    private fun instalar(contexto: Context, apk: File) {
        val instalador = contexto.packageManager.packageInstaller
        val parametros = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(contexto.packageName)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
            }
        }
        val id = instalador.createSession(parametros)
        instalador.openSession(id).use { sessao ->
            apk.inputStream().use { entrada ->
                sessao.openWrite("app.apk", 0, apk.length()).use { saida ->
                    entrada.copyTo(saida)
                    sessao.fsync(saida)
                }
            }
            val retorno = Intent(contexto, ResultadoAtualizacao::class.java).setAction(ACAO_RESULTADO)
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0)
            val pendente = PendingIntent.getBroadcast(contexto, id, retorno, flags)
            sessao.commit(pendente.intentSender)
        }
    }

    /** Recebe o andamento da instalação: abre a confirmação do Android ou avisa a falha. */
    class ResultadoAtualizacao : BroadcastReceiver() {
        override fun onReceive(contexto: Context, intent: Intent) {
            when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
                PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                    @Suppress("DEPRECATION")
                    val confirmar = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT) ?: return
                    contexto.startActivity(confirmar.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }
                PackageInstaller.STATUS_SUCCESS -> Unit // o app é reiniciado já na versão nova
                PackageInstaller.STATUS_FAILURE_ABORTED -> Unit // a pessoa tocou em Cancelar
                else -> {
                    val motivo = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE).orEmpty()
                    Toast.makeText(contexto, "Não foi possível atualizar o app. $motivo".trim(), Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}
