package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import java.text.SimpleDateFormat
import java.time.Instant
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/** Regras do botão SOS, sem Android, para dar para testar sozinho. */
object RegrasSos {
    /** Não há central: quando o SOS falha ou ninguém é avisado, mostrar os números de emergência. */
    const val EMERGENCIA = "Em emergência, ligue 190 (Polícia), 192 (SAMU) ou 193 (Bombeiros)."

    /** Segurar o botão por 3 s para começar; soltar antes não faz nada. */
    const val SEGURAR_MS = 3_000L
    /** Depois, 5 s de contagem com "Cancelar" antes de enviar. */
    const val CONTAGEM_S = 5

    fun progressoSegurar(inicioMs: Long, agoraMs: Long): Float =
        ((agoraMs - inicioMs).toFloat() / SEGURAR_MS).coerceIn(0f, 1f)

    fun segurouOSuficiente(inicioMs: Long, agoraMs: Long): Boolean = agoraMs - inicioMs >= SEGURAR_MS

    /** Segundos que faltam na contagem (5, 4, ... 0). Em 0, envia. */
    fun segundosRestantes(inicioContagemMs: Long, agoraMs: Long): Int {
        val passados = ((agoraMs - inicioContagemMs).coerceAtLeast(0L) / 1000L).toInt()
        return (CONTAGEM_S - passados).coerceAtLeast(0)
    }

    /** Corpo de POST /localizacao/dispositivos/sos. Sem posição do momento, o servidor usa a última. */
    fun montarCorpo(latitude: Double?, longitude: Double?, precisaoM: Float?, bateria: Int?, momento: Instant?): JSONObject {
        val corpo = JSONObject()
        if (latitude != null && longitude != null) {
            corpo.put("latitude", latitude).put("longitude", longitude)
            if (precisaoM != null) corpo.put("accuracy_m", precisaoM.toDouble())
            if (momento != null) corpo.put("recorded_at", momento.toString())
        }
        if (bateria != null && bateria in 0..100) corpo.put("battery_level", bateria)
        return corpo
    }

    /** Texto que aparece depois de tentar enviar. */
    fun mensagemDoResultado(resposta: Resposta, agoraMs: Long, fuso: TimeZone = TimeZone.getDefault()): String {
        val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).apply { timeZone = fuso }.format(Date(agoraMs))
        return when (resposta) {
            is Resposta.Ok -> {
                if (resposta.corpo.optBoolean("repetido", false)) {
                    "Seu pedido de socorro já tinha sido enviado. A família já foi avisada."
                } else {
                    val n = resposta.corpo.optInt("avisados", 0)
                    if (n > 0) "Pedido de socorro enviado às $hora. ${if (n == 1) "1 familiar foi avisado" else "$n familiares foram avisados"}."
                    else "Pedido de socorro registrado às $hora, mas ninguém da família foi avisado. Ligue para um familiar. $EMERGENCIA"
                }
            }
            Resposta.Desconectado -> "Este celular foi desconectado da família. O pedido não foi enviado. Ligue para um familiar. $EMERGENCIA"
            is Resposta.Recusado -> "O pedido não foi aceito: ${resposta.mensagem}. Ligue para um familiar. $EMERGENCIA"
            is Resposta.TentarDepois -> "O pedido não foi enviado agora (${resposta.motivo}). Tente de novo ou ligue para um familiar. $EMERGENCIA"
        }
    }
}
