package br.com.kbosolucoes.gestaofamiliar.crianca

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.location.Location
import android.os.BatteryManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import org.json.JSONArray
import java.time.Instant
import java.util.concurrent.Executors
import java.util.concurrent.RejectedExecutionException

/**
 * Serviço em primeiro plano: pega a localização a cada ~5 minutos, junta a bateria
 * e envia para o Gestão Familiar. Sem rede, guarda na fila e manda depois.
 * A notificação fixa deixa claro, no próprio celular, que a localização está sendo compartilhada.
 */
class LocationService : Service() {
    private val rede = Executors.newSingleThreadExecutor()
    private val cliente by lazy { LocationServices.getFusedLocationProviderClient(this) }
    private lateinit var configuracao: Configuracao

    private val retorno = object : LocationCallback() {
        override fun onLocationResult(resultado: LocationResult) {
            resultado.locations.forEach { guardar(it) }
            enviarPendentes()
        }
    }

    override fun onCreate() {
        super.onCreate()
        configuracao = Configuracao(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!configuracao.pareado || !configuracao.temLocalizacao() || configuracao.pararPendente) {
            stopSelf()
            return START_NOT_STICKY
        }
        criarCanal(this)
        val tipo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION else 0
        try {
            ServiceCompat.startForeground(this, NOTIFICACAO_ID, notificacao(), tipo)
        } catch (e: Exception) {
            // Algumas versões do Android recusam iniciar em primeiro plano (ex.: sem permissão
            // "o tempo todo" e com o app fechado). Melhor parar do que fechar o app com erro.
            stopSelf()
            return START_NOT_STICKY
        }
        iniciarAtualizacoes()
        if (intent?.action == ACAO_ENVIAR_AGORA) pedirPosicaoAgora()
        return START_STICKY
    }

    @SuppressLint("MissingPermission")
    private fun iniciarAtualizacoes() {
        val prioridade = if (configuracao.temLocalizacaoPrecisa()) Priority.PRIORITY_HIGH_ACCURACY else Priority.PRIORITY_BALANCED_POWER_ACCURACY
        val pedido = LocationRequest.Builder(prioridade, INTERVALO_MS)
            .setMinUpdateIntervalMillis(INTERVALO_MINIMO_MS)
            .setWaitForAccurateLocation(false)
            .build()
        cliente.removeLocationUpdates(retorno)
        cliente.requestLocationUpdates(pedido, retorno, Looper.getMainLooper())
    }

    @SuppressLint("MissingPermission")
    private fun pedirPosicaoAgora() {
        cliente.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
            .addOnSuccessListener { local -> if (local != null) guardar(local); enviarPendentes() }
            .addOnFailureListener { enviarPendentes() }
    }

    private fun guardar(local: Location) {
        val ponto = montarPonto(
            latitude = local.latitude,
            longitude = local.longitude,
            precisaoM = if (local.hasAccuracy()) local.accuracy else null,
            velocidadeMps = if (local.hasSpeed()) local.speed else null,
            bateria = bateria(),
            momento = Instant.ofEpochMilli(local.time),
        )
        configuracao.fila().adicionar(ponto)
    }

    private fun enviarPendentes() {
        // Uma posição pedida pelo "Enviar agora" pode chegar depois que o serviço parou.
        if (rede.isShutdown) return
        try {
            rede.execute { enviarAgora() }
        } catch (e: RejectedExecutionException) {
            // serviço já encerrado: o ponto continua na fila e sai no próximo envio
        }
    }

    private fun enviarAgora() {
        val token = configuracao.token ?: return
        val api = ApiClient(configuracao.site)
        val notificacoes = NotificationManagerCompat.from(this).areNotificationsEnabled()
        val registro = configuracao.registroDeAvisos()
        val resultado = configuracao.fila().esvaziar { ponto ->
            // Junto com a posição: versão do app, notificações liberadas e avisos já mostrados.
            val confirmando = registro.aConfirmar()
            ponto.put("app_versao", BuildConfig.VERSION_CODE)
                .put("notificacoes", notificacoes)
                .put("avisos_recebidos", JSONArray(confirmando))
            val resposta = api.enviarPosicao(token, ponto)
            if (resposta is Resposta.Ok) {
                registro.confirmados(confirmando)
                // Lembretes e outros avisos vêm na resposta; o servidor reenvia até confirmarmos.
                registro.processar(lerAvisos(resposta.corpo), notificacoes) { mostrarAviso(it) }
            }
            resposta
        }
        configuracao.salvarRegistroDeAvisos(registro)
        configuracao.registrarEnvio(resultado)
        if (resultado.desconectado) {
            val adulto = configuracao.compartilhandoComoAdulto
            configuracao.marcarDesconectado()
            avisarDesconectado(adulto)
            ContextCompat.getMainExecutor(this).execute { pararServico() }
        }
    }

    private fun bateria(): Int? {
        val gerenciador = getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val nivel = gerenciador.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        return if (nivel in 0..100) nivel else null
    }

    private fun notificacao(): Notification {
        val abrir = PendingIntent.getActivity(
            this, 0, Intent(this, ConfiguracaoActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        val nome = configuracao.criancaNome.ifBlank { "este celular" }
        val adulto = configuracao.compartilhandoComoAdulto
        return NotificationCompat.Builder(this, CANAL_ID)
            .setSmallIcon(R.drawable.ic_notificacao)
            .setContentTitle(if (adulto) "Sua localização está compartilhada" else "Localização compartilhada com a família")
            .setContentText(if (adulto) "Só os adultos da família veem. Toque para desligar." else "Gestão Familiar está acompanhando $nome.")
            .setOngoing(true)
            .setSilent(true)
            .setContentIntent(abrir)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun mostrarAviso(aviso: Aviso) = Notificador.mostrarAviso(this, configuracao.site, aviso)

    private fun avisarDesconectado(adulto: Boolean) {
        val gerenciador = getSystemService(NotificationManager::class.java)
        val abrir = PendingIntent.getActivity(
            this, 1, Intent(this, ConfiguracaoActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        gerenciador.notify(
            NOTIFICACAO_DESCONECTADO_ID,
            NotificationCompat.Builder(this, CANAL_ID)
                .setSmallIcon(R.drawable.ic_notificacao)
                .setContentTitle(if (adulto) "Compartilhamento desligado" else "Celular desconectado da família")
                .setContentText(
                    if (adulto) "Sua localização deixou de ser compartilhada. Ligue de novo no app, se quiser."
                    else "Entre de novo no app com a sua conta ou peça um código novo para um adulto.",
                )
                .setContentIntent(abrir)
                .setAutoCancel(true)
                .build(),
        )
    }

    private fun pararServico() {
        cliente.removeLocationUpdates(retorno)
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        cliente.removeLocationUpdates(retorno)
        rede.shutdown()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACAO_ENVIAR_AGORA = "br.com.kbosolucoes.gestaofamiliar.crianca.ENVIAR_AGORA"
        private const val CANAL_ID = Notificador.CANAL_LOCALIZACAO
        private const val NOTIFICACAO_ID = 10
        private const val NOTIFICACAO_DESCONECTADO_ID = 11
        private const val INTERVALO_MS = 5 * 60 * 1000L
        private const val INTERVALO_MINIMO_MS = 2 * 60 * 1000L

        fun criarCanal(contexto: Context) = Notificador.criarCanais(contexto)

        /** Liga o serviço se o celular está pareado e tem permissão de localização. */
        fun iniciar(contexto: Context, enviarAgora: Boolean = false) {
            val configuracao = Configuracao(contexto)
            if (!configuracao.pareado || !configuracao.temLocalizacao() || configuracao.pararPendente) return
            val intent = Intent(contexto, LocationService::class.java)
            if (enviarAgora) intent.action = ACAO_ENVIAR_AGORA
            ContextCompat.startForegroundService(contexto, intent)
        }
    }
}
