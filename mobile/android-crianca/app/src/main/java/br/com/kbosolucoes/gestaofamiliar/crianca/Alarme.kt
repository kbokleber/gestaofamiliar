package br.com.kbosolucoes.gestaofamiliar.crianca

import android.content.BroadcastReceiver
import android.content.ContentResolver
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.util.Log
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.math.ceil

/**
 * Toca o lembrete como alarme (2.0.9): no volume de ALARME do celular, que toca mesmo no
 * silencioso e na vibração. Por no máximo [DURACAO_MAXIMA_MS]; o botão "Parar" da notificação
 * interrompe antes. O volume de alarme volta ao valor anterior quando o som acaba.
 *
 * Som "mp3": arquivo res/raw/lembrete_mp3 (quando existir no app); sem ele, usa o toque padrão.
 */
object Alarme {
    const val DURACAO_MAXIMA_MS = 10_000L
    private const val TAG = "Alarme"
    private const val RECURSO_MP3 = "lembrete_mp3"

    private val principal = Handler(Looper.getMainLooper())
    private val trava = Any()
    private var tocador: MediaPlayer? = null
    private var volumeAnterior: Int? = null
    private var terminou = CountDownLatch(0)
    private val pararPorTempo = Runnable { pararAgora() }
    private var gerenciador: AudioManager? = null

    /** Volume alvo no fluxo de alarme, de 1 ao máximo do celular. */
    fun volumeAlvo(maximo: Int, fracao: Float): Int =
        ceil(maximo * fracao.coerceIn(0f, 1f)).toInt().coerceIn(1, maxOf(1, maximo))

    fun tocar(contexto: Context, pedido: PedidoDeAlarme) {
        val app = contexto.applicationContext
        synchronized(trava) {
            pararAgora()
            val fonte = fonte(app, pedido.som) ?: return
            val audio = app.getSystemService(AudioManager::class.java)
            gerenciador = audio
            val alvo = volumeAlvo(audio.getStreamMaxVolume(AudioManager.STREAM_ALARM), pedido.fracaoVolume)
            val atual = audio.getStreamVolume(AudioManager.STREAM_ALARM)
            if (atual != alvo) {
                // Alguns celulares recusam mudar o volume no "Não perturbe": toca no volume que estiver.
                runCatching { audio.setStreamVolume(AudioManager.STREAM_ALARM, alvo, 0) }
                    .onSuccess { volumeAnterior = atual }
                    .onFailure { Log.w(TAG, "Volume de alarme não alterado", it) }
            }
            try {
                val novo = MediaPlayer()
                novo.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build(),
                )
                novo.setDataSource(app, fonte)
                novo.isLooping = true
                novo.setWakeMode(app, PowerManager.PARTIAL_WAKE_LOCK)
                novo.setOnErrorListener { _, _, _ -> pararAgora(); true }
                novo.prepare()
                novo.start()
                tocador = novo
                terminou = CountDownLatch(1)
                principal.postDelayed(pararPorTempo, DURACAO_MAXIMA_MS)
            } catch (e: Exception) {
                Log.w(TAG, "Não foi possível tocar o alarme", e)
                pararAgora()
            }
        }
    }

    fun parar() = pararAgora()

    /** Bloqueia até o alarme acabar (ou o tempo dado), para o trabalho em segundo plano não encerrar o processo antes. */
    fun esperarTerminar(limiteMs: Long) {
        runCatching { terminou.await(limiteMs, TimeUnit.MILLISECONDS) }
    }

    fun tocando(): Boolean = synchronized(trava) { tocador != null }

    private fun pararAgora() {
        synchronized(trava) {
            principal.removeCallbacks(pararPorTempo)
            tocador?.let { atual ->
                runCatching { atual.stop() }
                runCatching { atual.release() }
            }
            tocador = null
            volumeAnterior?.let { anterior ->
                runCatching { gerenciador?.setStreamVolume(AudioManager.STREAM_ALARM, anterior, 0) }
            }
            volumeAnterior = null
            terminou.countDown()
        }
    }

    private fun fonte(contexto: Context, som: String): Uri? {
        if (som == "mp3") {
            val id = contexto.resources.getIdentifier(RECURSO_MP3, "raw", contexto.packageName)
            if (id != 0) return Uri.parse("${ContentResolver.SCHEME_ANDROID_RESOURCE}://${contexto.packageName}/$id")
        }
        return RingtoneManager.getActualDefaultRingtoneUri(contexto, RingtoneManager.TYPE_NOTIFICATION)
            ?: RingtoneManager.getActualDefaultRingtoneUri(contexto, RingtoneManager.TYPE_ALARM)
            ?: Settings.System.DEFAULT_NOTIFICATION_URI
    }

    /** Botão "Parar" e dispensar a notificação. */
    class PararReceiver : BroadcastReceiver() {
        override fun onReceive(contexto: Context, intent: Intent) {
            parar()
        }
    }
}
