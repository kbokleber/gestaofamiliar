package br.com.kbosolucoes.gestaofamiliar.crianca

/**
 * Controla a confirmação dos avisos: o servidor reenvia cada aviso até o app confirmar.
 * - [aConfirmar]: avisos já mostrados, que vão no próximo envio como avisos_recebidos.
 * - [mostrados]: últimos avisos mostrados, para não tocar de novo quando o servidor reenviar.
 */
class RegistroDeAvisos(aConfirmar: Collection<Int> = emptyList(), mostrados: Collection<Int> = emptyList()) {
    private val pendentesDeConfirmacao = LinkedHashSet(aConfirmar)
    private val recentes = ArrayDeque(mostrados)

    fun aConfirmar(): List<Int> = pendentesDeConfirmacao.toList()
    fun mostrados(): List<Int> = recentes.toList()

    /** O servidor recebeu estes ids como confirmados: não precisam ir de novo. */
    fun confirmados(ids: Collection<Int>) {
        pendentesDeConfirmacao.removeAll(ids.toSet())
    }

    /**
     * Mostra os avisos novos e marca para confirmar. Com as notificações bloqueadas, não mostra
     * nem confirma: o servidor percebe (notificacoes=false) e passa a usar o navegador.
     */
    fun processar(avisos: List<Aviso>, notificacoesLiberadas: Boolean, mostrar: (Aviso) -> Unit) {
        if (!notificacoesLiberadas) return
        for (aviso in avisos) {
            if (aviso.id !in recentes) {
                mostrar(aviso)
                recentes.addLast(aviso.id)
                while (recentes.size > LIMITE_RECENTES) recentes.removeFirst()
            }
            pendentesDeConfirmacao.add(aviso.id)
        }
    }

    fun serializar(): Pair<String, String> =
        pendentesDeConfirmacao.joinToString(",") to recentes.joinToString(",")

    companion object {
        const val LIMITE_RECENTES = 100

        fun ler(aConfirmar: String?, mostrados: String?): RegistroDeAvisos =
            RegistroDeAvisos(numeros(aConfirmar), numeros(mostrados))

        private fun numeros(texto: String?): List<Int> =
            texto.orEmpty().split(',').mapNotNull { it.trim().toIntOrNull() }
    }
}
