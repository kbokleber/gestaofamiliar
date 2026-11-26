package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AlarmeTest {
    private fun avisos(json: String) = lerAvisos(JSONObject(json))

    @Test
    fun avisoSemSomOuComNullSoNotifica() {
        val lista = avisos("""{"avisos":[{"id":1,"titulo":"T","texto":"x"},{"id":2,"titulo":"T","texto":"y","som":null,"volume":null}]}""")
        assertEquals(listOf<String?>(null, null), lista.map { it.som })
        lista.forEach { assertNull(pedidoDeAlarme(it)) }
    }

    @Test
    fun somConhecidoViraAlarmeComVolume() {
        val lista = avisos("""{"avisos":[{"id":1,"titulo":"T","texto":"x","som":"padrao","volume":"alto"},{"id":2,"titulo":"T","texto":"y","som":"mp3","volume":"medio"},{"id":3,"titulo":"T","texto":"z","som":"mp3"}]}""")
        assertEquals(PedidoDeAlarme("padrao", 0.9f), pedidoDeAlarme(lista[0]))
        assertEquals(PedidoDeAlarme("mp3", 0.6f), pedidoDeAlarme(lista[1]))
        assertEquals(PedidoDeAlarme("mp3", 0.6f), pedidoDeAlarme(lista[2]))
    }

    @Test
    fun somDesconhecidoOuDesligadoNaoToca() {
        val lista = avisos("""{"avisos":[{"id":1,"titulo":"T","texto":"x","som":"desligado"},{"id":2,"titulo":"T","texto":"y","som":"sirene","volume":"alto"}]}""")
        lista.forEach { assertNull(pedidoDeAlarme(it)) }
    }

    @Test
    fun volumeAlvoFicaEntreUmEOMaximo() {
        assertEquals(5, Alarme.volumeAlvo(7, 0.6f))
        assertEquals(7, Alarme.volumeAlvo(7, 0.9f))
        assertEquals(1, Alarme.volumeAlvo(7, 0f))
        assertEquals(1, Alarme.volumeAlvo(0, 0.9f))
        assertEquals(14, Alarme.volumeAlvo(15, 0.9f))
    }

    @Test
    fun duracaoMaximaEhDezSegundos() {
        assertEquals(10_000L, Alarme.DURACAO_MAXIMA_MS)
    }
}
