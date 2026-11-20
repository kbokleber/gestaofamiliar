package br.com.kbosolucoes.gestaofamiliar.crianca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.TimeZone

class ChecagensDeEnvioTest {
    @Test
    fun quatroChecagensNaOrdemComOAjusteCerto() {
        val tudoVerde = checagensDeEnvio(true, true, true, true)
        assertEquals(listOf("Localização", "Notificação fixa", "Localização o tempo todo", "Sem economia de bateria"), tudoVerde.map { it.nome })
        assertTrue(tudoVerde.all { it.ok })
        assertEquals(
            listOf(AjusteAndroid.LOCALIZACAO, AjusteAndroid.NOTIFICACOES, AjusteAndroid.LOCALIZACAO_SEMPRE, AjusteAndroid.BATERIA),
            tudoVerde.map { it.ajuste },
        )
        // Criança sem "o tempo todo": só essa fica vermelha, e o botão leva ao ajuste dela.
        val vermelha = checagensDeEnvio(true, true, false, true).filter { !it.ok }
        assertEquals(listOf(AjusteAndroid.LOCALIZACAO_SEMPRE), vermelha.map { it.ajuste })
    }

    @Test
    fun ultimoEnvioNoFormatoBrasileiroNoFusoDoCelular() {
        val sp = TimeZone.getTimeZone("America/Sao_Paulo")
        // 2026-11-20T14:05:00Z = 11:05 em São Paulo.
        assertEquals("Último envio: 20/11/2026 11:05", formatarUltimoEnvio(1_795_183_500_000L, sp))
        assertEquals("Ainda não enviou nenhuma localização.", formatarUltimoEnvio(0L, sp))
    }

    @Test
    fun historicoDoAdultoDiz7Dias() {
        assertTrue(textoHistorico(adulto = true).contains("7 dias"))
        assertTrue(!textoHistorico(adulto = false).contains("7 dias"))
    }
}
