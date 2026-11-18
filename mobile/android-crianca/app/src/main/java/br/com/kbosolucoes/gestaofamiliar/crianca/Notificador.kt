package br.com.kbosolucoes.gestaofamiliar.crianca

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat

/** Canais e notificações do app, usados pelo serviço da criança e pelos alertas do adulto. */
object Notificador {
    const val CANAL_LOCALIZACAO = "localizacao"
    /** Canal novo da 2.0.2: o Android não deixa mudar a vibração de um canal já criado. */
    const val CANAL_LEMBRETES = "lembretes_vibrar"
    private const val CANAL_LEMBRETES_ANTIGO = "lembretes"
    /** Três toques curtos, para a criança perceber mesmo com o som baixo. */
    val VIBRACAO_LEMBRETE = longArrayOf(0, 400, 200, 400, 200, 400)
    const val CANAL_ALERTAS = "alertas"
    private const val AVISO_BASE = 1000

    fun criarCanais(contexto: Context) {
        val canais = listOf(
            NotificationChannel(
                CANAL_LOCALIZACAO, contexto.getString(R.string.canal_nome), NotificationManager.IMPORTANCE_LOW,
            ).apply { description = contexto.getString(R.string.canal_descricao) },
            NotificationChannel(
                CANAL_LEMBRETES, contexto.getString(R.string.canal_avisos_nome), NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = contexto.getString(R.string.canal_avisos_descricao)
                enableVibration(true)
                vibrationPattern = VIBRACAO_LEMBRETE
            },
            NotificationChannel(
                CANAL_ALERTAS, contexto.getString(R.string.canal_alertas_nome), NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = contexto.getString(R.string.canal_alertas_descricao) },
        )
        val gerenciador = contexto.getSystemService(NotificationManager::class.java)
        gerenciador.createNotificationChannels(canais)
        // Some da lista de canais o de lembretes sem vibração (versões até a 2.0.1).
        if (gerenciador.getNotificationChannel(CANAL_LEMBRETES_ANTIGO) != null) {
            gerenciador.deleteNotificationChannel(CANAL_LEMBRETES_ANTIGO)
        }
    }

    /** Abre o app (site dentro dele) na página do aviso. */
    fun abrirNoApp(contexto: Context, site: String, url: String?, codigo: Int): PendingIntent {
        val intent = Intent(contexto, WebActivity::class.java)
            .putExtra(WebActivity.EXTRA_ENDERECO, enderecoDoAviso(site, url))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        return PendingIntent.getActivity(
            contexto, codigo, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
    }

    fun mostrarAviso(contexto: Context, site: String, aviso: Aviso, canal: String = CANAL_LEMBRETES) {
        criarCanais(contexto)
        val numero = AVISO_BASE + aviso.id % 100_000
        contexto.getSystemService(NotificationManager::class.java).notify(
            numero,
            NotificationCompat.Builder(contexto, canal)
                .setSmallIcon(R.drawable.ic_notificacao)
                .setContentTitle(aviso.titulo)
                .setContentText(aviso.texto)
                .setStyle(NotificationCompat.BigTextStyle().bigText(aviso.texto))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setVibrate(if (canal == CANAL_LEMBRETES) VIBRACAO_LEMBRETE else null)
                .setCategory(if (canal == CANAL_ALERTAS) NotificationCompat.CATEGORY_STATUS else NotificationCompat.CATEGORY_REMINDER)
                .setContentIntent(abrirNoApp(contexto, site, aviso.url, numero))
                .setAutoCancel(true)
                .build(),
        )
    }
}
