package br.com.kbosolucoes.gestaofamiliar.crianca

import android.content.Context
import androidx.core.app.NotificationManagerCompat
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/**
 * Celular do adulto: a cada ~15 minutos (o menor intervalo que o Android permite em segundo plano)
 * busca chegada/saída, bateria baixa, sem sinal e lembretes, e mostra como notificação.
 * Com o app aberto, a busca também acontece na hora.
 */
object AlertasAdulto {
    private const val TRABALHO = "alertas-adulto"
    private val trava = Any()

    fun agendar(contexto: Context) {
        val pedido = PeriodicWorkRequestBuilder<Trabalho>(15, TimeUnit.MINUTES)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(contexto).enqueueUniquePeriodicWork(TRABALHO, ExistingPeriodicWorkPolicy.UPDATE, pedido)
    }

    fun cancelar(contexto: Context) {
        WorkManager.getInstance(contexto).cancelUniqueWork(TRABALHO)
    }

    /** Busca e mostra os alertas. Devolve false se o servidor pediu para tentar mais tarde. Roda fora da tela. */
    fun buscar(contexto: Context): Boolean = synchronized(trava) {
        val configuracao = Configuracao(contexto)
        val token = configuracao.tokenAdulto ?: return true
        val notificacoes = NotificationManagerCompat.from(contexto).areNotificationsEnabled()
        val registro = configuracao.registroDeAvisosAdulto()
        val confirmando = registro.aConfirmar()
        val resposta = ApiClient(configuracao.site).avisosAdulto(token, BuildConfig.VERSION_CODE, notificacoes, confirmando)
        when (resposta) {
            is Resposta.Ok -> {
                registro.confirmados(confirmando)
                registro.processar(lerAvisos(resposta.corpo), notificacoes) {
                    // Alertas de localização apontam para /localizacao; o resto (lembretes) usa o canal de lembretes.
                    val canal = if (it.url?.startsWith("/localizacao") == true) Notificador.CANAL_ALERTAS else Notificador.CANAL_LEMBRETES
                    Notificador.mostrarAviso(contexto, configuracao.site, it, canal)
                }
                configuracao.salvarRegistroDeAvisosAdulto(registro)
                true
            }
            Resposta.Desconectado -> {
                // Revogado no site, ou o usuário deixou de ser adulto da família.
                configuracao.esquecerAdulto()
                cancelar(contexto)
                true
            }
            is Resposta.Recusado -> true
            is Resposta.TentarDepois -> false
        }
    }

    class Trabalho(contexto: Context, parametros: WorkerParameters) : Worker(contexto, parametros) {
        override fun doWork(): Result = if (buscar(applicationContext)) Result.success() else Result.retry()
    }
}
