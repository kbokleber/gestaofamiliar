package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.util.UUID
import java.util.concurrent.locks.ReentrantLock

/**
 * Pontos ainda não entregues, num arquivo do próprio app.
 * Sem rede, os pontos ficam aqui e saem na ordem quando a conexão volta.
 * O servidor recusa pontos com mais de 7 dias, então a fila descarta os mais velhos.
 *
 * A trava do arquivo só protege leitura e gravação, que são rápidas. O envio pela rede
 * acontece fora dela: com internet lenta, a posição nova e a tela do app não ficam esperando.
 */
class FilaDePontos(private val arquivo: File, private val limite: Int = LIMITE_PADRAO) {

    fun adicionar(ponto: JSONObject) = synchronized(travaDoArquivo(arquivo)) {
        val lista = ler()
        lista.add(JSONObject(ponto.toString()).put(CAMPO_ID, UUID.randomUUID().toString()))
        while (lista.size > limite) lista.removeAt(0)
        gravar(lista)
    }

    fun tamanho(): Int = synchronized(travaDoArquivo(arquivo)) { ler().size }

    /**
     * Envia na ordem, do mais antigo ao mais novo, e para no primeiro erro de rede.
     * Ponto recusado pelo servidor é descartado; token revogado interrompe tudo.
     * Se já houver um envio em andamento, não começa outro.
     */
    fun esvaziar(enviar: (JSONObject) -> Resposta): ResultadoEnvio {
        val envio = travaDeEnvio(arquivo)
        if (!envio.tryLock()) return ResultadoEnvio(0, 0, tamanho(), desconectado = false, erro = null)
        try {
            val copia = synchronized(travaDoArquivo(arquivo)) { semVelhos(ler()) }
            val resolvidos = mutableSetOf<String>()
            var enviados = 0
            var descartados = 0
            var desconectado = false
            var erro: String? = null
            for (ponto in copia) {
                val corpo = JSONObject(ponto.toString()).apply { remove(CAMPO_ID) }
                when (val r = enviar(corpo)) {
                    is Resposta.Ok -> { resolvidos += ponto.optString(CAMPO_ID); enviados++ }
                    is Resposta.Recusado -> { resolvidos += ponto.optString(CAMPO_ID); descartados++ }
                    is Resposta.Desconectado -> { desconectado = true; break }
                    is Resposta.TentarDepois -> { erro = r.motivo; break }
                }
            }
            // Relê o arquivo: pontos que chegaram durante o envio continuam na fila.
            val pendentes = synchronized(travaDoArquivo(arquivo)) {
                val atual = semVelhos(ler())
                atual.removeAll { it.optString(CAMPO_ID) in resolvidos }
                gravar(atual)
                atual.size
            }
            return ResultadoEnvio(enviados, descartados, pendentes, desconectado, erro)
        } finally {
            envio.unlock()
        }
    }

    fun limpar() = synchronized(travaDoArquivo(arquivo)) { arquivo.delete() }

    private fun semVelhos(lista: MutableList<JSONObject>): MutableList<JSONObject> {
        val limiteIdade = Instant.now().minusSeconds(IDADE_MAXIMA_SEGUNDOS)
        lista.removeAll { p -> runCatching { Instant.parse(p.optString("recorded_at")) < limiteIdade }.getOrDefault(false) }
        // Pontos gravados antes de existir o identificador ganham um agora.
        lista.forEach { if (!it.has(CAMPO_ID)) it.put(CAMPO_ID, UUID.randomUUID().toString()) }
        return lista
    }

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
        private const val CAMPO_ID = "_fila_id"

        // Uma trava por arquivo, compartilhada entre as instâncias (serviço e tela criam as suas).
        private val travasArquivo = mutableMapOf<String, Any>()
        private val travasEnvio = mutableMapOf<String, ReentrantLock>()

        private fun travaDoArquivo(arquivo: File): Any =
            synchronized(travasArquivo) { travasArquivo.getOrPut(arquivo.absolutePath) { Any() } }

        private fun travaDeEnvio(arquivo: File): ReentrantLock =
            synchronized(travasEnvio) { travasEnvio.getOrPut(arquivo.absolutePath) { ReentrantLock() } }
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
