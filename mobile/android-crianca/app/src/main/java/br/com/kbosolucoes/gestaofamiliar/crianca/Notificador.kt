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
    /** 2.0.9: lembrete com alarme. O canal fica sem som: quem toca é o [Alarme], no volume de alarme. */
    const val CANAL_LEMBRETES_ALARME = "lembretes_alarme"
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
                CANAL_LEMBRETES_ALARME, contexto.getString(R.string.canal_alarme_nome), NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = contexto.getString(R.string.canal_alarme_descricao)
                setSound(null, null)
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

    /** Botão "Parar" e o gesto de dispensar a notificação param o alarme. */
    private fun pararAlarme(contexto: Context, codigo: Int): PendingIntent = PendingIntent.getBroadcast(
        contexto, codigo, Intent(contexto, Alarme.PararReceiver::class.java),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    fun mostrarAviso(contexto: Context, site: String, aviso: Aviso, canalPedido: String = CANAL_LEMBRETES) {
        criarCanais(contexto)
        val numero = AVISO_BASE + aviso.id % 100_000
        // Alertas de localização nunca tocam alarme; lembretes com som pedido usam o canal sem som + Alarme.
        val alarme = if (canalPedido == CANAL_ALERTAS) null else pedidoDeAlarme(aviso)
        val canal = if (alarme != null) CANAL_LEMBRETES_ALARME else canalPedido
        val construtor = NotificationCompat.Builder(contexto, canal)
                .setSmallIcon(R.drawable.ic_notificacao)
                .setContentTitle(aviso.titulo)
                .setContentText(aviso.texto)
                .setStyle(NotificationCompat.BigTextStyle().bigText(aviso.texto))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setVibrate(if (canal == CANAL_ALERTAS) null else VIBRACAO_LEMBRETE)
                .setCategory(if (canal == CANAL_ALERTAS) NotificationCompat.CATEGORY_STATUS else NotificationCompat.CATEGORY_REMINDER)
                .setContentIntent(abrirNoApp(contexto, site, aviso.url, numero))
                .setAutoCancel(true)
        if (alarme != null) {
            construtor
                .addAction(0, contexto.getString(R.string.parar_alarme), pararAlarme(contexto, numero))
                .setDeleteIntent(pararAlarme(contexto, numero + 1))
        }
        contexto.getSystemService(NotificationManager::class.java).notify(numero, construtor.build())
        if (alarme != null) Alarme.tocar(contexto, alarme)
    }
}
