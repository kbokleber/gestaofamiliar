package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Resultado de uma chamada à API, já traduzido para o que o app precisa decidir. */
sealed class Resposta {
    data class Ok(val corpo: JSONObject) : Resposta()
    /** O servidor recusou este pedido (ex.: código errado, ponto antigo). Não adianta repetir. */
    data class Recusado(val status: Int, val mensagem: String) : Resposta()
    /** Token revogado ou criança desativada: o celular precisa ser pareado de novo. */
    object Desconectado : Resposta()
    /** Sem rede, servidor fora ou muitas tentativas. Tentar de novo mais tarde. */
    data class TentarDepois(val motivo: String) : Resposta()
}

data class Pareamento(val token: String, val aparelhoId: Int, val criancaNome: String)

/**
 * Cliente das rotas do celular em /api/v1/localizacao/dispositivos.
 * Só usa HttpURLConnection e org.json, para rodar igual no Android e nos testes.
 */
class ApiClient(baseUrl: String, private val timeoutMs: Int = 20_000) {
    private val base = normalizarEndereco(baseUrl)

    fun parear(codigo: String, nomeCelular: String?): Resposta {
        val corpo = JSONObject().put("code", codigo.trim())
        if (!nomeCelular.isNullOrBlank()) corpo.put("device_label", nomeCelular.trim().take(80))
        return post("/api/v1/localizacao/dispositivos/parear", corpo, token = null)
    }

    fun enviarPosicao(token: String, ponto: JSONObject): Resposta =
        post("/api/v1/localizacao/dispositivos/posicao", ponto, token)

    private fun post(caminho: String, corpo: JSONObject, token: String?): Resposta {
        val conexao = try {
            (URL(base + caminho).openConnection() as HttpURLConnection)
        } catch (e: IOException) {
            return Resposta.TentarDepois(e.message ?: "erro de rede")
        }
        return try {
            conexao.requestMethod = "POST"
            conexao.connectTimeout = timeoutMs
            conexao.readTimeout = timeoutMs
            conexao.doOutput = true
            conexao.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            conexao.setRequestProperty("Accept", "application/json")
            if (token != null) conexao.setRequestProperty("X-Device-Token", token)
            conexao.outputStream.use { it.write(corpo.toString().toByteArray(Charsets.UTF_8)) }

            val status = conexao.responseCode
            val texto = (if (status in 200..299) conexao.inputStream else conexao.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            interpretar(status, texto, comToken = token != null)
        } catch (e: IOException) {
            Resposta.TentarDepois(e.message ?: "erro de rede")
        } finally {
            conexao.disconnect()
        }
    }

    companion object {
        const val SITE_PADRAO = "https://gestaofamiliar.kbosolucoes.com.br"

        fun normalizarEndereco(endereco: String): String {
            var limpo = endereco.trim().trimEnd('/')
            if (limpo.isEmpty()) limpo = SITE_PADRAO
            if (!limpo.startsWith("http://") && !limpo.startsWith("https://")) limpo = "https://$limpo"
            // Aceita que alguém cole o endereço da API em vez do site.
            return limpo.removeSuffix("/api/v1").removeSuffix("/api")
        }

        fun interpretar(status: Int, texto: String, comToken: Boolean): Resposta {
            val json = try { JSONObject(texto) } catch (e: Exception) { JSONObject() }
            val detalhe = json.opt("detail")
            val mensagem = if (detalhe is String) detalhe else "Erro $status no servidor."
            return when {
                status in 200..299 -> Resposta.Ok(json)
                status == 401 && comToken -> Resposta.Desconectado
                status == 429 || status == 408 || status >= 500 -> Resposta.TentarDepois(mensagem)
                else -> Resposta.Recusado(status, mensagem)
            }
        }

        fun lerPareamento(corpo: JSONObject): Pareamento = Pareamento(
            token = corpo.getString("device_token"),
            aparelhoId = corpo.optInt("device_id"),
            criancaNome = corpo.optString("crianca_nome", ""),
        )
    }
}
