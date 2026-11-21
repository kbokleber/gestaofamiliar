package br.com.kbosolucoes.gestaofamiliar.crianca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.TimeZone

class AtualizacaoTest {
    @Test
    fun versaoMaiorNoSiteFicaDisponivelQualquerQueSejaONumero() {
        assertEquals(EstadoAtualizacao.Disponivel("2.0.6", "2.0.7"), decidirAtualizacao("2.0.6", "2.0.7", null))
        assertEquals(EstadoAtualizacao.Disponivel("2.0.8", "2.0.10"), decidirAtualizacao("2.0.8", "2.0.10", null))
        assertEquals(EstadoAtualizacao.Disponivel("2.0.8", "3.0"), decidirAtualizacao("2.0.8", "3.0", null))
        assertEquals(EstadoAtualizacao.Disponivel("2.0.8", "2.1.0"), decidirAtualizacao("2.0.8", " 2.1.0 ", null))
    }

    @Test
    fun igualOuMenorNoSiteEJaAtualizado() {
        assertEquals(EstadoAtualizacao.JaAtualizado("2.0.8", "2.0.8"), decidirAtualizacao("2.0.8", "2.0.8", null))
        // Site com versão mais antiga (ex.: publicação desfeita): nunca oferece "voltar".
        assertEquals(EstadoAtualizacao.JaAtualizado("2.0.8", "2.0.7"), decidirAtualizacao("2.0.8", "2.0.7", null))
    }

    @Test
    fun respostaVaziaOuErroViraFalhaComMotivo() {
        assertEquals(EstadoAtualizacao.Falhou("sem conexão com o site (timeout)"), decidirAtualizacao("2.0.8", null, "sem conexão com o site (timeout)"))
        assertTrue(decidirAtualizacao("2.0.8", "", null) is EstadoAtualizacao.Falhou)
        assertTrue(decidirAtualizacao("2.0.8", null, null) is EstadoAtualizacao.Falhou)
        assertTrue(decidirAtualizacao("2.0.8", "beta", null) is EstadoAtualizacao.Falhou)
    }

    @Test
    fun motivoDeCadaRespostaDoSite() {
        assertEquals(null, motivoDaFalhaDeVersao(Resposta.Ok(org.json.JSONObject())))
        assertEquals("nenhuma versão publicada no site", motivoDaFalhaDeVersao(Resposta.Recusado(404, "Nenhuma versão do app foi enviada ainda.")))
        assertEquals("sem conexão com o site (timeout)", motivoDaFalhaDeVersao(Resposta.TentarDepois("timeout")))
    }

    @Test
    fun textosDoBloco() {
        assertEquals("Você já tem a versão mais nova (2.0.8).", textoAtualizacao(EstadoAtualizacao.JaAtualizado("2.0.8", "2.0.8")))
        assertEquals("Versão 2.0.9 disponível. Você tem a 2.0.8.", textoAtualizacao(EstadoAtualizacao.Disponivel("2.0.8", "2.0.9")))
        assertTrue(textoAtualizacao(EstadoAtualizacao.Falhou("sem conexão com o site (x)")).startsWith("Não deu para consultar a atualização: sem conexão"))
        assertEquals("Consultando o site...", textoAtualizacao(EstadoAtualizacao.Consultando))
        val sp = TimeZone.getTimeZone("America/Sao_Paulo")
        assertEquals("Última consulta: 20/11 11:05", textoUltimaConsulta(1_795_183_500_000L, sp))
        assertEquals("Ainda não consultou.", textoUltimaConsulta(0L, sp))
    }

    @Test
    fun consultaACadaAberturaNoMaximo1VezPorMinutoEOBotaoSempre() {
        val agora = 1_795_183_500_000L
        assertTrue(deveConsultarVersao(agora, 0L, forcar = false))
        assertTrue(deveConsultarVersao(agora, agora - 61_000L, forcar = false))
        assertFalse(deveConsultarVersao(agora, agora - 10_000L, forcar = false))
        assertTrue(deveConsultarVersao(agora, agora - 10_000L, forcar = true))
    }
}
