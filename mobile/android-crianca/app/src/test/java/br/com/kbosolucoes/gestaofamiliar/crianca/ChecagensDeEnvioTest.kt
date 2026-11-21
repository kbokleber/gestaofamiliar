package br.com.kbosolucoes.gestaofamiliar.crianca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.TimeZone

class ChecagensDeEnvioTest {
    private val sp = TimeZone.getTimeZone("America/Sao_Paulo")
    private val agora = 1_795_183_500_000L // 2026-11-20 11:05 em São Paulo
    private val minuto = 60_000L
    private val hora = 60 * minuto

    /** Celular com tudo certo: Redmi, início automático confirmado ontem, enviou há 4 min. */
    private fun tudoCerto() = EstadoDoCelular(
        localizacaoLigada = true,
        gpsLigado = true,
        permissaoLocalizacao = true,
        permissaoSempre = true,
        localizacaoPrecisa = true,
        semEconomiaDeBateria = true,
        servicoRodando = true,
        religadoEmMs = 0L,
        paradoDesdeMs = 0L,
        ultimoEnvioMs = agora - 4 * minuto,
        agoraMs = agora,
        internet = true,
        notificacoes = true,
        fabricante = "Xiaomi",
        inicioAutomaticoConfirmadoMs = agora - 24 * hora,
    )

    private fun item(estado: EstadoDoCelular, chave: String) = checklistDeEnvio(estado, sp).first { it.chave == chave }

    @Test
    fun tudoCertoNoRedmiTemOs7ItensMaisNotificacaoNaOrdem() {
        val itens = checklistDeEnvio(tudoCerto(), sp)
        assertEquals(
            listOf("gps", "sempre", "precisa", "bateria", "envio", "inicio_automatico", "rede", "notificacoes"),
            itens.map { it.chave },
        )
        assertTrue(itens.all { it.ok })
        assertTrue(itensQueFaltam(itens).isEmpty())
        // Início automático nunca aparece como "OK" verificado: só como confirmado pela pessoa.
        assertEquals(EstadoItem.MANUAL_CONFIRMADO, item(tudoCerto(), "inicio_automatico").estado)
        assertTrue(item(tudoCerto(), "inicio_automatico").explicacao.contains("19/11/2026"))
        assertTrue(item(tudoCerto(), "inicio_automatico").explicacao.contains("não deixa o app conferir"))
    }

    @Test
    fun marcaSemInicioAutomaticoNaoMostraOItem() {
        val samsung = tudoCerto().copy(fabricante = "samsung", inicioAutomaticoConfirmadoMs = 0L)
        val chaves = checklistDeEnvio(samsung, sp).map { it.chave }
        assertFalse("inicio_automatico" in chaves)
        assertEquals(7, chaves.size)
        assertTrue(precisaInicioAutomatico("Redmi") && precisaInicioAutomatico(" POCO ") && precisaInicioAutomatico("OPPO"))
        assertFalse(precisaInicioAutomatico("Google"))
    }

    @Test
    fun inicioAutomaticoPendenteNaoFingeQueConferiu() {
        val pendente = item(tudoCerto().copy(inicioAutomaticoConfirmadoMs = 0L), "inicio_automatico")
        assertEquals(EstadoItem.MANUAL_PENDENTE, pendente.estado)
        assertFalse(pendente.ok)
        assertEquals(AjusteAndroid.INICIO_AUTOMATICO, pendente.ajuste)
        assertTrue(pendente.explicacao.contains("Já fiz"))
        assertTrue(pendente.explicacao.contains("Início automático"))
    }

    @Test
    fun gpsDesligadoAbreAjusteDeLocalizacao() {
        val semGps = tudoCerto().copy(localizacaoLigada = false, gpsLigado = false)
        assertEquals(EstadoItem.FALTA, item(semGps, "gps").estado)
        assertEquals(AjusteAndroid.GPS, item(semGps, "gps").ajuste)
        // Sem GPS, a precisão alta também falta e leva ao mesmo ajuste.
        assertEquals(AjusteAndroid.GPS, item(semGps, "precisa").ajuste)
    }

    @Test
    fun permissoesDeLocalizacaoLevamAoAjusteCerto() {
        val semPermissao = tudoCerto().copy(permissaoLocalizacao = false, permissaoSempre = false, localizacaoPrecisa = false)
        assertEquals(AjusteAndroid.LOCALIZACAO, item(semPermissao, "sempre").ajuste)
        val soComAppAberto = tudoCerto().copy(permissaoSempre = false)
        assertEquals(EstadoItem.FALTA, item(soComAppAberto, "sempre").estado)
        assertEquals(AjusteAndroid.LOCALIZACAO_SEMPRE, item(soComAppAberto, "sempre").ajuste)
        // Só esse item fica vermelho.
        assertEquals(listOf("sempre"), itensQueFaltam(checklistDeEnvio(soComAppAberto, sp)).map { it.chave })
    }

    @Test
    fun precisaoAproximadaPedePrecisa() {
        val aproximada = tudoCerto().copy(localizacaoPrecisa = false)
        assertEquals(EstadoItem.FALTA, item(aproximada, "precisa").estado)
        assertEquals(AjusteAndroid.PRECISAO, item(aproximada, "precisa").ajuste)
    }

    @Test
    fun bateriaComRestricao() {
        val restrita = tudoCerto().copy(semEconomiaDeBateria = false)
        assertEquals(EstadoItem.FALTA, item(restrita, "bateria").estado)
        assertEquals(AjusteAndroid.BATERIA, item(restrita, "bateria").ajuste)
    }

    @Test
    fun envioNuncaParadoAtrasadoEReligado() {
        assertEquals(EstadoItem.OK, item(tudoCerto(), "envio").estado)
        assertEquals("Último envio há 4 min.", item(tudoCerto(), "envio").explicacao)

        val nunca = item(tudoCerto().copy(ultimoEnvioMs = 0L), "envio")
        assertEquals(EstadoItem.FALTA, nunca.estado)
        assertEquals(AjusteAndroid.ENVIO, nunca.ajuste)

        val parado = item(tudoCerto().copy(servicoRodando = false, ultimoEnvioMs = agora - (5 * hora + 32 * minuto)), "envio")
        assertEquals(EstadoItem.FALTA, parado.estado)
        assertTrue(parado.explicacao.contains("5 h 32 min"))
        assertEquals("Ligar envio", parado.rotuloAjuste)

        val atrasado = item(tudoCerto().copy(ultimoEnvioMs = agora - 45 * minuto), "envio")
        assertEquals(EstadoItem.ATRASADO, atrasado.estado)
        assertFalse(atrasado.ok)
        assertTrue(atrasado.explicacao.contains("45 min"))

        // Como no caso do Guilherme: o Android parou o envio por 5 h 32 min e ele só voltou quando o app abriu.
        val religado = tudoCerto().copy(
            paradoDesdeMs = agora - 2 * hora - (5 * hora + 32 * minuto),
            religadoEmMs = agora - 2 * hora,
            ultimoEnvioMs = agora - 3 * minuto,
        )
        val aviso = item(religado, "envio")
        assertEquals(EstadoItem.FALTA, aviso.estado)
        assertEquals(AjusteAndroid.ENTENDI_PARADA, aviso.ajuste)
        assertTrue(aviso.explicacao, aviso.explicacao.contains("5 h 32 min"))
        assertTrue(aviso.explicacao, aviso.explicacao.contains("de 20/11 03:33 a 20/11 09:05"))
        // Passado 1 dia, a parada antiga deixa de ser mostrada.
        val antigo = religado.copy(religadoEmMs = agora - 25 * hora, paradoDesdeMs = agora - 30 * hora)
        assertEquals(EstadoItem.OK, item(antigo, "envio").estado)
    }

    @Test
    fun anotaParadaSoQuandoOServicoEstavaParadoHaMaisDe30Min() {
        assertTrue(deveAnotarParada(estavaRodando = false, ultimoEnvioMs = agora - 31 * minuto, agoraMs = agora))
        assertFalse(deveAnotarParada(estavaRodando = true, ultimoEnvioMs = agora - 5 * hora, agoraMs = agora))
        assertFalse(deveAnotarParada(estavaRodando = false, ultimoEnvioMs = agora - 10 * minuto, agoraMs = agora))
        assertFalse(deveAnotarParada(estavaRodando = false, ultimoEnvioMs = 0L, agoraMs = agora))
    }

    @Test
    fun semInternet() {
        val offline = item(tudoCerto().copy(internet = false), "rede")
        assertEquals(EstadoItem.FALTA, offline.estado)
        assertEquals(AjusteAndroid.REDE, offline.ajuste)
    }

    @Test
    fun oQueVaiParaOSiteSoAjustesDoAndroid() {
        val pendente = tudoCerto().copy(semEconomiaDeBateria = false, inicioAutomaticoConfirmadoMs = 0L)
        assertEquals(
            mapOf(
                "gps" to true, "sempre" to true, "precisa" to true, "bateria_livre" to false,
                "inicio_automatico" to "pendente", "inicio_automatico_em" to null,
            ),
            checklistParaServidor(pendente, sp),
        )
        assertEquals("2026-11-19", checklistParaServidor(tudoCerto(), sp)["inicio_automatico_em"])
        assertEquals("confirmado", checklistParaServidor(tudoCerto(), sp)["inicio_automatico"])
        val pixel = checklistParaServidor(tudoCerto().copy(fabricante = "Google"), sp)
        assertEquals("nao_se_aplica", pixel["inicio_automatico"])
        assertNull(pixel["inicio_automatico_em"])
    }

    @Test
    fun duracoesCurtas() {
        assertEquals("menos de 1 min", duracaoCurta(30_000L))
        assertEquals("59 min", duracaoCurta(59 * minuto))
        assertEquals("2 h", duracaoCurta(2 * hora))
        assertEquals("5 h 32 min", duracaoCurta(5 * hora + 32 * minuto))
        assertEquals("1 dia", duracaoCurta(25 * hora))
        assertEquals("3 dias", duracaoCurta(72 * hora))
    }

    @Test
    fun ultimoEnvioNoFormatoBrasileiroNoFusoDoCelular() {
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
