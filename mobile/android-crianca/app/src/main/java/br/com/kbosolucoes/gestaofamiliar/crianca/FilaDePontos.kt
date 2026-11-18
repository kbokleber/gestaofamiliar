package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant

/**
 * Pontos ainda não entregues, num arquivo do próprio app.
 * Sem rede, os pontos ficam aqui e saem na ordem quando a conexão volta.
 * O servidor recusa pontos com mais de 7 dias, então a fila descarta os mais velhos.
 */
class FilaDePontos(private val arquivo: File, private val limite: Int = LIMITE_PADRAO) {
    private val trava = Any()

    fun adicionar(ponto: JSONObject) = synchronized(trava) {
        val lista = ler()
        lista.add(ponto)
        while (lista.size > limite) lista.removeAt(0)
        gravar(lista)
    }

    fun tamanho(): Int = synchronized(trava) { ler().size }

    /**
     * Envia na ordem, do mais antigo ao mais novo, e para no primeiro erro de rede.
     * Ponto recusado pelo servidor é descartado; token revogado interrompe tudo.
     */
    fun esvaziar(enviar: (JSONObject) -> Resposta): ResultadoEnvio = synchronized(trava) {
        val lista = ler()
        val limiteIdade = Instant.now().minusSeconds(IDADE_MAXIMA_SEGUNDOS)
        lista.removeAll { p -> runCatching { Instant.parse(p.optString("recorded_at")) < limiteIdade }.getOrDefault(false) }
        var enviados = 0
        var descartados = 0
        var desconectado = false
        var erro: String? = null
        while (lista.isNotEmpty()) {
            when (val r = enviar(lista[0])) {
                is Resposta.Ok -> { lista.removeAt(0); enviados++ }
                is Resposta.Recusado -> { lista.removeAt(0); descartados++ }
                is Resposta.Desconectado -> { desconectado = true; break }
                is Resposta.TentarDepois -> { erro = r.motivo; break }
            }
        }
        gravar(lista)
        ResultadoEnvio(enviados, descartados, lista.size, desconectado, erro)
    }

    fun limpar() = synchronized(trava) { arquivo.delete() }

    private fun ler(): MutableList<JSONObject> {
        if (!arquivo.exists()) return mutableListOf()
        return try {
            val array = JSONArray(arquivo.readText(Charsets.UTF_8))
            MutableList(array.length()) { array.getJSONObject(it) }
        } catch (e: Exception) {
            mutableListOf() // arquivo corrompido: melhor recomeçar do que travar o envio
        }
    }

    private fun gravar(lista: List<JSONObject>) {
        val temporario = File(arquivo.parentFile, arquivo.name + ".tmp")
        temporario.writeText(JSONArray(lista).toString(), Charsets.UTF_8)
        if (!temporario.renameTo(arquivo)) {
            arquivo.writeText(JSONArray(lista).toString(), Charsets.UTF_8)
            temporario.delete()
        }
    }

    companion object {
        /** Uma semana de pontos a cada 5 minutos. */
        const val LIMITE_PADRAO = 2016
        const val IDADE_MAXIMA_SEGUNDOS = 7L * 24 * 3600 - 600
    }
}

data class ResultadoEnvio(
    val enviados: Int,
    val descartados: Int,
    val pendentes: Int,
    val desconectado: Boolean,
    val erro: String?,
)

/** Monta o corpo de POST /dispositivos/posicao. */
fun montarPonto(
    latitude: Double,
    longitude: Double,
    precisaoM: Float?,
    velocidadeMps: Float?,
    bateria: Int?,
    momento: Instant,
): JSONObject {
    val ponto = JSONObject()
        .put("latitude", latitude)
        .put("longitude", longitude)
        .put("recorded_at", momento.toString())
    if (precisaoM != null) ponto.put("accuracy_m", precisaoM.toDouble())
    if (velocidadeMps != null) ponto.put("speed_mps", velocidadeMps.toDouble())
    if (bateria != null && bateria in 0..100) ponto.put("battery_level", bateria)
    return ponto
}
