package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject

/** Aviso que o servidor manda junto com a resposta do envio da localização (ex.: lembrete de atividades). */
data class Aviso(
    val id: Int,
    val titulo: String,
    val texto: String,
    val url: String?,
    /** App 2.0.9+: "padrao" ou "mp3" toca como alarme; null = só notificação. */
    val som: String? = null,
    val volume: String? = null,
)

/** Pedido de alarme do aviso: qual som e que fração do volume de alarme usar. */
data class PedidoDeAlarme(val som: String, val fracaoVolume: Float)

/** Só sons conhecidos tocam; volume desconhecido vira médio. */
fun pedidoDeAlarme(aviso: Aviso): PedidoDeAlarme? {
    val som = aviso.som ?: return null
    if (som != "padrao" && som != "mp3") return null
    val fracao = if (aviso.volume == "alto") 0.9f else 0.6f
    return PedidoDeAlarme(som, fracao)
}

private fun JSONObject.textoOuNulo(campo: String): String? =
    if (isNull(campo)) null else optString(campo).trim().takeIf { it.isNotEmpty() && it != "null" }

/** Lê o campo "avisos" da resposta de POST /dispositivos/posicao. Ignora itens incompletos. */
fun lerAvisos(corpo: JSONObject): List<Aviso> {
    val lista = corpo.optJSONArray("avisos") ?: return emptyList()
    return (0 until lista.length()).mapNotNull { i ->
        val item = lista.optJSONObject(i) ?: return@mapNotNull null
        val id = item.optInt("id", -1)
        val titulo = item.optString("titulo").trim()
        val texto = item.optString("texto").trim()
        if (id < 0 || (titulo.isEmpty() && texto.isEmpty())) return@mapNotNull null
        val url = item.optString("url").trim().takeIf { it.isNotEmpty() && it != "null" }
        Aviso(id, titulo.ifEmpty { "Gestão Familiar" }, texto, url, item.textoOuNulo("som"), item.textoOuNulo("volume"))
    }
}

/** Endereço completo para abrir ao tocar no aviso: só caminhos do próprio site. */
fun enderecoDoAviso(site: String, url: String?): String {
    val base = ApiClient.normalizarEndereco(site)
    if (url.isNullOrBlank() || !url.startsWith("/") || url.startsWith("//")) return base
    return base + url
}
