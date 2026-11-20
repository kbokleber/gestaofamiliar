package br.com.kbosolucoes.gestaofamiliar.crianca

import android.content.Context
import android.content.Intent
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/**
 * O adulto parou de compartilhar a posição. O celular para de enviar na hora, mas o token só é
 * apagado quando o servidor confirma a revogação (200) ou já não reconhece o token (401).
 * Sem rede, fica pendente e o WorkManager tenta de novo assim que houver internet.
 */
object PararCompartilhamento {
    private const val TRABALHO = "parar-compartilhamento"
    private val trava = Any()

    /** Pede para parar. Devolve true se já concluiu no servidor; false se ficou para depois. Roda fora da tela. */
    fun pedir(contexto: Context): Boolean {
        val configuracao = Configuracao(contexto)
        if (!configuracao.compartilhandoComoAdulto) return true
        configuracao.marcarPararPendente(true)
        contexto.stopService(Intent(contexto, LocationService::class.java))
        val concluiu = tentar(contexto)
        if (!concluiu) agendar(contexto)
        return concluiu
    }

    /** Tenta concluir uma parada pendente. Devolve true quando não há mais nada pendente. */
    fun tentar(contexto: Context): Boolean = synchronized(trava) {
        val configuracao = Configuracao(contexto)
        if (!configuracao.pararPendente) return true
        val token = configuracao.token
        if (token.isNullOrBlank()) {
            configuracao.pararCompartilhamento()
            return true
        }
        val resposta = ApiClient(configuracao.site).revogarLocalizacao(token)
        if (!revogacaoConcluida(resposta)) return false
        configuracao.pararCompartilhamento()
        return true
    }

    fun agendar(contexto: Context) {
        val pedido = OneTimeWorkRequestBuilder<Trabalho>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(contexto).enqueueUniqueWork(TRABALHO, ExistingWorkPolicy.REPLACE, pedido)
    }

    class Trabalho(contexto: Context, parametros: WorkerParameters) : Worker(contexto, parametros) {
        override fun doWork(): Result = if (tentar(applicationContext)) Result.success() else Result.retry()
    }
}
