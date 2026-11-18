package br.com.kbosolucoes.gestaofamiliar.crianca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.nio.file.Files
import java.time.Instant

/**
 * Conversa com uma API de verdade. Só roda quando GF_API_URL e GF_CODIGO estão definidos,
 * por exemplo contra a API local de teste. Nunca aponte para produção sem combinar antes.
 */
class ApiIntegracaoTest {
    @Test
    fun pareiaEnviaPontosERecusaTokenFalso() {
        val url = System.getenv("GF_API_URL")
        val codigo = System.getenv("GF_CODIGO")
        assumeTrue(!url.isNullOrBlank() && !codigo.isNullOrBlank())

        val api = ApiClient(url!!)
        val pareado = api.parear(codigo!!, "Teste automático")
        assertTrue("pareamento: $pareado", pareado is Resposta.Ok)
        val dados = ApiClient.lerPareamento((pareado as Resposta.Ok).corpo)

        // Mesmo código de novo: recusado, sem repetir.
        assertTrue(api.parear(codigo, null) is Resposta.Recusado)

        val fila = FilaDePontos(Files.createTempDirectory("fila").resolve("p.json").toFile())
        fila.adicionar(montarPonto(-23.5505, -46.6333, 10f, 0f, 64, Instant.now().minusSeconds(120)))
        fila.adicionar(montarPonto(-23.5510, -46.6340, 10f, 1.2f, 63, Instant.now().minusSeconds(60)))
        val r = fila.esvaziar { api.enviarPosicao(dados.token, it) }
        assertEquals(2, r.enviados)
        assertEquals(0, r.pendentes)

        assertTrue(api.enviarPosicao("token-falso-com-mais-de-vinte-caracteres", montarPonto(0.0, 0.0, null, null, null, Instant.now())) is Resposta.Desconectado)

        // Lembrete: com GF_TOKEN_ADMIN, dispara o lembrete pelo site e confere que chega neste celular.
        val admin = System.getenv("GF_TOKEN_ADMIN")
        if (!admin.isNullOrBlank()) {
            fun comoApp(confirmar: List<Int> = emptyList(), segundos: Long = 0) =
                montarPonto(-23.5505, -46.6333, 10f, 0f, 62, Instant.now().minusSeconds(30 - segundos))
                    .put("app_versao", 3).put("notificacoes", true).put("avisos_recebidos", org.json.JSONArray(confirmar))
            // O app novo se anuncia antes do disparo, como faz a cada envio.
            assertTrue(api.enviarPosicao(dados.token, comoApp()) is Resposta.Ok)
            val conexao = java.net.URL("$url/api/v1/notificacoes/lembretes/disparar").openConnection() as java.net.HttpURLConnection
            conexao.requestMethod = "POST"
            conexao.setRequestProperty("Authorization", "Bearer $admin")
            assertEquals(200, conexao.responseCode)
            val disparo = conexao.inputStream.bufferedReader().readText()
            assertTrue("disparo: $disparo", disparo.contains("\"canal\":\"app\""))

            val comAviso = api.enviarPosicao(dados.token, comoApp(segundos = 2))
            val avisos = lerAvisos((comAviso as Resposta.Ok).corpo)
            assertEquals(1, avisos.size)
            assertEquals("Atividades para concluir", avisos[0].titulo)
            // Sem confirmar, volta; confirmado, some.
            val deNovo = api.enviarPosicao(dados.token, comoApp(segundos = 4))
            assertEquals(avisos[0].id, lerAvisos((deNovo as Resposta.Ok).corpo).single().id)
            val confirmado = api.enviarPosicao(dados.token, comoApp(listOf(avisos[0].id), segundos = 6))
            assertTrue(lerAvisos((confirmado as Resposta.Ok).corpo).isEmpty())
        }
    }

    /**
     * App 2.0: criança logada conecta o celular sem código; o adulto com o app recebe o alerta de bateria.
     * Precisa de GF_API_URL, GF_LOGIN_CRIANCA e GF_LOGIN_ADULTO (tokens de login da API local).
     */
    @Test
    fun criancaLogadaConectaEAdultoRecebeAlerta() {
        val url = System.getenv("GF_API_URL")
        val crianca = System.getenv("GF_LOGIN_CRIANCA")
        val adulto = System.getenv("GF_LOGIN_ADULTO")
        assumeTrue(!url.isNullOrBlank() && !crianca.isNullOrBlank() && !adulto.isNullOrBlank())
        val api = ApiClient(url!!)

        // Login da criança não registra celular de adulto; o do adulto não conecta localização.
        assertTrue(api.registrarAdulto(crianca!!, "x", 4) is Resposta.Recusado)
        assertTrue(api.parearMe(adulto!!, "x", null) is Resposta.Recusado)
        assertTrue(api.parearMe("login-invalido", "x", null) is Resposta.Recusado)

        val registro = api.registrarAdulto(adulto, "Celular do adulto", 4)
        assertTrue("registro: $registro", registro is Resposta.Ok)
        val tokenAdulto = (registro as Resposta.Ok).corpo.getString("device_token")

        val pareado = api.parearMe(crianca, "Celular da criança", null)
        assertTrue("parear-me: $pareado", pareado is Resposta.Ok)
        val dados = ApiClient.lerPareamento((pareado as Resposta.Ok).corpo)
        assertTrue(dados.criancaId > 0)
        assertTrue(api.enviarPosicao(dados.token, montarPonto(-23.60, -46.70, 10f, 0f, 60, Instant.now().minusSeconds(90))) is Resposta.Ok)
        assertTrue(api.enviarPosicao(dados.token, montarPonto(-23.60, -46.70, 10f, 0f, 12, Instant.now().minusSeconds(30))) is Resposta.Ok)

        val primeira = api.avisosAdulto(tokenAdulto, 4, true, emptyList())
        assertTrue("avisos: $primeira", primeira is Resposta.Ok)
        val alertas = lerAvisos((primeira as Resposta.Ok).corpo)
        val bateria = alertas.firstOrNull { it.texto.contains("12%") }
        assertTrue("alertas: $alertas", bateria != null)
        assertEquals("/localizacao", bateria!!.url)

        // Confirmado: não vem de novo.
        val segunda = api.avisosAdulto(tokenAdulto, 4, true, alertas.map { it.id }) as Resposta.Ok
        assertTrue(lerAvisos(segunda.corpo).none { it.id == bateria.id })

        // Troca de criança no mesmo celular revoga o token anterior.
        val trocado = api.parearMe(crianca, "Celular da criança", dados.token)
        assertTrue(trocado is Resposta.Ok)
        assertTrue(api.enviarPosicao(dados.token, montarPonto(0.0, 0.0, null, null, null, Instant.now())) is Resposta.Desconectado)

        assertTrue(api.revogarAdulto(tokenAdulto) is Resposta.Ok)
        assertTrue(api.avisosAdulto(tokenAdulto, 4, true, emptyList()) is Resposta.Desconectado)

        val versao = api.ultimaVersao()
        assertTrue("ultima: $versao", versao is Resposta.Ok || (versao is Resposta.Recusado && versao.status == 404))
    }
}
