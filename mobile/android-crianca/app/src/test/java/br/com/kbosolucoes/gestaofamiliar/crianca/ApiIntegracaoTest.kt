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
            val conexao = java.net.URL("$url/api/v1/notificacoes/lembretes/disparar").openConnection() as java.net.HttpURLConnection
            conexao.requestMethod = "POST"
            conexao.setRequestProperty("Authorization", "Bearer $admin")
            assertEquals(200, conexao.responseCode)
            val disparo = conexao.inputStream.bufferedReader().readText()
            assertTrue("disparo: $disparo", disparo.contains("\"canal\":\"app\""))

            val comAviso = api.enviarPosicao(dados.token, montarPonto(-23.5505, -46.6333, 10f, 0f, 62, Instant.now()))
            val avisos = lerAvisos((comAviso as Resposta.Ok).corpo)
            assertEquals(1, avisos.size)
            assertEquals("Atividades para concluir", avisos[0].titulo)
            val semAviso = api.enviarPosicao(dados.token, montarPonto(-23.5505, -46.6333, 10f, 0f, 62, Instant.now().plusSeconds(2)))
            assertTrue(lerAvisos((semAviso as Resposta.Ok).corpo).isEmpty())
        }
    }
}
