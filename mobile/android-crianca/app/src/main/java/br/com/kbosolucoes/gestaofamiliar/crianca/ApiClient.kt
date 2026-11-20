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

data class Pareamento(val token: String, val aparelhoId: Int, val criancaNome: String, val criancaId: Int = 0)

/**
 * Cliente das rotas do celular (/api/v1/localizacao/dispositivos e /api/v1/app-android).
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

    /** Criança logada no site dentro do app: conecta o celular sem código. */
    fun parearMe(login: String, nomeCelular: String?, tokenAnterior: String?): Resposta {
        val corpo = JSONObject()
        if (!nomeCelular.isNullOrBlank()) corpo.put("device_label", nomeCelular.trim().take(80))
        if (!tokenAnterior.isNullOrBlank()) corpo.put("token_anterior", tokenAnterior)
        return chamar("POST", "/api/v1/localizacao/dispositivos/parear-me", corpo, mapOf("Authorization" to "Bearer $login"), comToken = false)
    }

    /** Adulto logado: registra o celular para receber alertas. Devolve device_token e device_id. */
    /** O adulto logado passa a compartilhar a posição deste celular (app 2.0.5+). */
    fun parearAdulto(login: String, nomeCelular: String?, tokenAnterior: String?): Resposta {
        val corpo = JSONObject().put("device_label", nomeCelular ?: "")
        if (!tokenAnterior.isNullOrBlank()) corpo.put("token_anterior", tokenAnterior)
        return chamar("POST", "/api/v1/localizacao/dispositivos/parear-adulto", corpo, mapOf("Authorization" to "Bearer $login"), comToken = false)
    }

    /** Este celular para de enviar a posição (o token de posição deixa de valer). */
    fun revogarLocalizacao(token: String): Resposta =
        post("/api/v1/localizacao/dispositivos/revogar-me", JSONObject(), token)

    fun registrarAdulto(login: String, nomeCelular: String?, versao: Int): Resposta {
        val corpo = JSONObject().put("app_versao", versao)
        if (!nomeCelular.isNullOrBlank()) corpo.put("device_label", nomeCelular.trim().take(80))
        return chamar("POST", "/api/v1/app-android/dispositivos/registrar", corpo, mapOf("Authorization" to "Bearer $login"), comToken = false)
    }

    /** Busca os alertas do adulto e confirma os já mostrados. */
    fun avisosAdulto(token: String, versao: Int, notificacoes: Boolean, recebidos: List<Int>): Resposta {
        val corpo = JSONObject()
            .put("app_versao", versao)
            .put("notificacoes", notificacoes)
            .put("avisos_recebidos", org.json.JSONArray(recebidos))
        return post("/api/v1/app-android/dispositivos/avisos", corpo, token)
    }

    fun revogarAdulto(token: String): Resposta =
        post("/api/v1/app-android/dispositivos/revogar-me", JSONObject(), token)

    /** Versão mais recente publicada (rota pública). */
    fun ultimaVersao(): Resposta = chamar("GET", "/api/v1/app-android/ultima", null, emptyMap(), comToken = false)

    private fun post(caminho: String, corpo: JSONObject, token: String?): Resposta =
        chamar("POST", caminho, corpo, if (token != null) mapOf("X-Device-Token" to token) else emptyMap(), comToken = token != null)

    private fun chamar(metodo: String, caminho: String, corpo: JSONObject?, cabecalhos: Map<String, String>, comToken: Boolean): Resposta {
        val conexao = try {
            (URL(base + caminho).openConnection() as HttpURLConnection)
        } catch (e: IOException) {
            return Resposta.TentarDepois(e.message ?: "erro de rede")
        }
        return try {
            conexao.requestMethod = metodo
            conexao.connectTimeout = timeoutMs
            conexao.readTimeout = timeoutMs
            conexao.setRequestProperty("Accept", "application/json")
            cabecalhos.forEach { (nome, valor) -> conexao.setRequestProperty(nome, valor) }
            if (corpo != null) {
                conexao.doOutput = true
                conexao.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conexao.outputStream.use { it.write(corpo.toString().toByteArray(Charsets.UTF_8)) }
            }

            val status = conexao.responseCode
            val texto = (if (status in 200..299) conexao.inputStream else conexao.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            interpretar(status, texto, comToken = comToken)
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
            criancaId = corpo.optInt("crianca_id", 0),
        )
    }
}
