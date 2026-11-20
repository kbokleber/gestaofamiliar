package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.util.TimeZone

class SosTest {
    @Test
    fun soDisparaDepoisDeSegurar3Segundos() {
        assertFalse(RegrasSos.segurouOSuficiente(1_000, 3_999))
        assertTrue(RegrasSos.segurouOSuficiente(1_000, 4_000))
        assertEquals(0f, RegrasSos.progressoSegurar(1_000, 1_000), 0.001f)
        assertEquals(0.5f, RegrasSos.progressoSegurar(1_000, 2_500), 0.001f)
        assertEquals(1f, RegrasSos.progressoSegurar(1_000, 9_000), 0.001f)
    }

    @Test
    fun contagemDe5SegundosAteZero() {
        assertEquals(5, RegrasSos.segundosRestantes(10_000, 10_000))
        assertEquals(4, RegrasSos.segundosRestantes(10_000, 11_000))
        assertEquals(1, RegrasSos.segundosRestantes(10_000, 14_999))
        assertEquals(0, RegrasSos.segundosRestantes(10_000, 15_000))
        assertEquals(0, RegrasSos.segundosRestantes(10_000, 99_000))
    }

    @Test
    fun corpoComPosicaoDoMomentoOuSoBateria() {
        val momento = Instant.parse("2026-11-20T14:05:00Z")
        val completo = RegrasSos.montarCorpo(-23.55, -46.63, 8f, 40, momento)
        assertEquals(-23.55, completo.getDouble("latitude"), 0.0)
        assertEquals("2026-11-20T14:05:00Z", completo.getString("recorded_at"))
        assertEquals(40, completo.getInt("battery_level"))
        val semPosicao = RegrasSos.montarCorpo(null, null, null, 40, null)
        assertFalse(semPosicao.has("latitude"))
        assertEquals(40, semPosicao.getInt("battery_level"))
        assertFalse(RegrasSos.montarCorpo(null, null, null, 140, null).has("battery_level"))
    }

    @Test
    fun mensagensDoResultado() {
        val sp = TimeZone.getTimeZone("America/Sao_Paulo")
        val agora = 1_795_183_500_000L // 11:05 em São Paulo
        assertEquals(
            "Pedido de socorro enviado às 11:05. 2 familiares foram avisados.",
            RegrasSos.mensagemDoResultado(Resposta.Ok(JSONObject("""{"id":1,"repetido":false,"avisados":2}""")), agora, sp),
        )
        assertTrue(RegrasSos.mensagemDoResultado(Resposta.Ok(JSONObject("""{"id":1,"repetido":true,"avisados":2}""")), agora, sp).contains("já tinha sido enviado"))
        assertTrue(RegrasSos.mensagemDoResultado(Resposta.TentarDepois("sem rede"), agora, sp).contains("não foi enviado agora (sem rede)"))
        assertTrue(RegrasSos.mensagemDoResultado(Resposta.Ok(JSONObject("""{"id":1,"avisados":0}""")), agora, sp).contains("ninguém da família"))
        // S6: falha ou ninguém avisado mostram 190, 192 e 193.
        for (resposta in listOf(Resposta.TentarDepois("sem rede"), Resposta.Desconectado, Resposta.Recusado(429, "Muitos pedidos"), Resposta.Ok(JSONObject("""{"id":1,"avisados":0}""")))) {
            val texto = RegrasSos.mensagemDoResultado(resposta, agora, sp)
            assertTrue(texto, texto.contains("190") && texto.contains("192") && texto.contains("193"))
        }
        assertFalse(RegrasSos.mensagemDoResultado(Resposta.Ok(JSONObject("""{"id":1,"avisados":2}""")), agora, sp).contains("190"))
    }
}
