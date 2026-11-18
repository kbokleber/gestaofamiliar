package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.time.Instant

class FilaDePontosTest {
    private fun fila(limite: Int = 10) =
        FilaDePontos(Files.createTempDirectory("fila").resolve("pontos.json").toFile(), limite)

    private fun ponto(segundosAtras: Long = 0) =
        montarPonto(-23.55, -46.63, 12f, 1.5f, 80, Instant.now().minusSeconds(segundosAtras))

    @Test
    fun enviaNaOrdemEParaNoErroDeRede() {
        val f = fila()
        f.adicionar(ponto(300).put("n", 1))
        f.adicionar(ponto(200).put("n", 2))
        f.adicionar(ponto(100).put("n", 3))
        val vistos = mutableListOf<Int>()
        val r = f.esvaziar { p ->
            vistos.add(p.getInt("n"))
            if (p.getInt("n") == 2) Resposta.TentarDepois("sem rede") else Resposta.Ok(JSONObject())
        }
        assertEquals(listOf(1, 2), vistos)
        assertEquals(1, r.enviados)
        assertEquals(2, r.pendentes)
        assertEquals("sem rede", r.erro)
        assertEquals(2, f.tamanho())

        val segunda = f.esvaziar { Resposta.Ok(JSONObject()) }
        assertEquals(2, segunda.enviados)
        assertEquals(0, f.tamanho())
    }

    @Test
    fun descartaRecusadoEParaQuandoDesconectado() {
        val f = fila()
        f.adicionar(ponto())
        f.adicionar(ponto())
        f.adicionar(ponto())
        var chamadas = 0
        val r = f.esvaziar {
            chamadas++
            if (chamadas == 1) Resposta.Recusado(400, "antiga") else Resposta.Desconectado
        }
        assertEquals(1, r.descartados)
        assertTrue(r.desconectado)
        assertEquals(2, r.pendentes)
    }

    @Test
    fun respeitaLimiteEDescartaPontoDeMaisDeUmaSemana() {
        val f = fila(limite = 3)
        repeat(5) { f.adicionar(ponto()) }
        assertEquals(3, f.tamanho())

        val g = fila()
        g.adicionar(ponto(8L * 24 * 3600))
        g.adicionar(ponto())
        var enviados = 0
        g.esvaziar { enviados++; Resposta.Ok(JSONObject()) }
        assertEquals(1, enviados)
    }

    @Test
    fun montaCorpoNoFormatoDaApi() {
        val p = montarPonto(-23.5, -46.6, null, null, 150, Instant.parse("2026-11-18T12:00:00Z"))
        assertEquals("2026-11-18T12:00:00Z", p.getString("recorded_at"))
        assertFalse(p.has("battery_level")) // fora de 0..100 não vai
        assertFalse(p.has("accuracy_m"))
    }

    @Test
    fun traduzRespostasDaApi() {
        assertTrue(ApiClient.interpretar(200, "{\"id\":1}", true) is Resposta.Ok)
        assertTrue(ApiClient.interpretar(401, "{}", true) is Resposta.Desconectado)
        assertTrue(ApiClient.interpretar(429, "{\"detail\":\"Muitas\"}", false) is Resposta.TentarDepois)
        assertTrue(ApiClient.interpretar(502, "<html>", true) is Resposta.TentarDepois)
        val recusado = ApiClient.interpretar(400, "{\"detail\":\"Código inválido ou já usado.\"}", false)
        assertEquals("Código inválido ou já usado.", (recusado as Resposta.Recusado).mensagem)
    }

    @Test
    fun normalizaEnderecoDoSite() {
        assertEquals("https://gestaofamiliar.kbosolucoes.com.br", ApiClient.normalizarEndereco(""))
        assertEquals("https://exemplo.com", ApiClient.normalizarEndereco("exemplo.com/"))
        assertEquals("https://exemplo.com", ApiClient.normalizarEndereco("https://exemplo.com/api/v1"))
    }

    @Test
    fun redeLentaNaoTravaPontoNovoNemLeituraDaTela() {
        val f = fila()
        f.adicionar(ponto(120).put("n", 1))
        val enviando = java.util.concurrent.CountDownLatch(1)
        val liberar = java.util.concurrent.CountDownLatch(1)
        val envio = Thread {
            f.esvaziar {
                enviando.countDown()
                liberar.await() // simula a rede lenta
                Resposta.Ok(JSONObject())
            }
        }
        envio.start()
        assertTrue(enviando.await(5, java.util.concurrent.TimeUnit.SECONDS))

        // Durante o envio: gravar posição nova e ler o tamanho não podem esperar a rede.
        val inicio = System.nanoTime()
        f.adicionar(ponto().put("n", 2))
        assertEquals(2, f.tamanho())
        // Um segundo envio ao mesmo tempo não começa nem espera.
        assertEquals(0, f.esvaziar { Resposta.Ok(JSONObject()) }.enviados)
        assertTrue((System.nanoTime() - inicio) < 1_000_000_000L)

        liberar.countDown()
        envio.join(5000)
        // O ponto entregue saiu; o que chegou durante o envio ficou para o próximo.
        assertEquals(1, f.tamanho())
        val restantes = mutableListOf<Int>()
        f.esvaziar { restantes.add(it.getInt("n")); Resposta.Ok(JSONObject()) }
        assertEquals(listOf(2), restantes)
    }

    @Test
    fun identificadorInternoNaoVaiParaApi() {
        val f = fila()
        f.adicionar(ponto())
        var corpo: JSONObject? = null
        f.esvaziar { corpo = it; Resposta.Ok(JSONObject()) }
        assertFalse(corpo!!.keys().asSequence().any { it.startsWith("_") })
    }

    @Test
    fun leAvisosDaRespostaEIgnoraIncompletos() {
        val corpo = JSONObject("""{"id":1,"avisos":[
            {"id":7,"titulo":"Atividades para concluir","texto":"Lição de matemática","url":"/estudos/atividades?recorte=pendentes"},
            {"id":8,"titulo":"","texto":""},
            {"titulo":"sem id"},
            {"id":9,"titulo":"Só título","texto":"x","url":null}
        ]}""")
        val avisos = lerAvisos(corpo)
        assertEquals(listOf(7, 9), avisos.map { it.id })
        assertEquals("Lição de matemática", avisos[0].texto)
        assertEquals(null, avisos[1].url)
        assertTrue(lerAvisos(JSONObject("{\"id\":1}")).isEmpty())
    }

    @Test
    fun avisoSoAbreCaminhoDoProprioSite() {
        val site = "https://gestaofamiliar.kbosolucoes.com.br"
        assertEquals("$site/estudos/atividades?recorte=pendentes", enderecoDoAviso(site, "/estudos/atividades?recorte=pendentes"))
        assertEquals(site, enderecoDoAviso(site, "https://outro-site.com/golpe"))
        assertEquals(site, enderecoDoAviso(site, "//outro-site.com"))
        assertEquals(site, enderecoDoAviso(site, null))
    }
}
