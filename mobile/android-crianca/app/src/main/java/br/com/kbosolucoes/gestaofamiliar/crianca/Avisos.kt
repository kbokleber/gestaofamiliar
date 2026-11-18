package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject

/** Aviso que o servidor manda junto com a resposta do envio da localização (ex.: lembrete de atividades). */
data class Aviso(val id: Int, val titulo: String, val texto: String, val url: String?)

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
        Aviso(id, titulo.ifEmpty { "Gestão Familiar" }, texto, url)
    }
}

/** Endereço completo para abrir ao tocar no aviso: só caminhos do próprio site. */
fun enderecoDoAviso(site: String, url: String?): String {
    val base = ApiClient.normalizarEndereco(site)
    if (url.isNullOrBlank() || !url.startsWith("/") || url.startsWith("//")) return base
    return base + url
}
