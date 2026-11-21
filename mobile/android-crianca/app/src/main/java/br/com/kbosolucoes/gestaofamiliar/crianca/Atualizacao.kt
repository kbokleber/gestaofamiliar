package br.com.kbosolucoes.gestaofamiliar.crianca

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Atualização dinâmica do app: a versão publicada vem sempre do servidor (/app-android/ultima).
 * Nenhum número de versão fica fixo aqui; a instalada vem do próprio APK (BuildConfig).
 * Sem Android aqui dentro, para dar para testar sozinho.
 */
sealed class EstadoAtualizacao {
    /** Ainda não consultou nesta abertura. */
    object NaoConsultado : EstadoAtualizacao()
    object Consultando : EstadoAtualizacao()
    data class JaAtualizado(val instalada: String, val publicada: String) : EstadoAtualizacao()
    data class Disponivel(val instalada: String, val publicada: String) : EstadoAtualizacao()
    data class Falhou(val motivo: String) : EstadoAtualizacao()
}

/** Ao abrir ou voltar ao app, consulta de novo se passou disso (o botão "Verificar" consulta sempre). */
const val INTERVALO_CONSULTA_VERSAO_MS = 60 * 1000L

fun deveConsultarVersao(agoraMs: Long, ultimaConsultaMs: Long, forcar: Boolean): Boolean =
    forcar || ultimaConsultaMs <= 0L || agoraMs - ultimaConsultaMs >= INTERVALO_CONSULTA_VERSAO_MS

/**
 * Decide a partir do que o servidor respondeu. [publicada] é o campo "versao" do /ultima (null se não veio);
 * [erro] é o motivo quando a consulta falhou (sem rede, servidor fora, nenhuma versão publicada).
 */
fun decidirAtualizacao(instalada: String, publicada: String?, erro: String?): EstadoAtualizacao {
    if (erro != null) return EstadoAtualizacao.Falhou(erro)
    val versao = publicada?.trim().orEmpty()
    if (versao.isEmpty() || !versao.first().isDigit()) return EstadoAtualizacao.Falhou("o site não informou a versão publicada")
    return if (compararVersoes(versao, instalada) > 0) EstadoAtualizacao.Disponivel(instalada, versao)
    else EstadoAtualizacao.JaAtualizado(instalada, versao)
}

/** Texto do bloco "Atualização do app" em Configurações de envio. */
fun textoAtualizacao(estado: EstadoAtualizacao): String = when (estado) {
    EstadoAtualizacao.NaoConsultado -> "Toque em \"Verificar atualização\" para conferir se há versão nova."
    EstadoAtualizacao.Consultando -> "Consultando o site..."
    is EstadoAtualizacao.JaAtualizado -> "Você já tem a versão mais nova (${estado.instalada})."
    is EstadoAtualizacao.Disponivel -> "Versão ${estado.publicada} disponível. Você tem a ${estado.instalada}."
    is EstadoAtualizacao.Falhou -> "Não deu para consultar a atualização: ${estado.motivo}. Confira a internet e tente de novo."
}

/** "Última consulta: dd/mm hh:mm" no fuso do celular. */
fun textoUltimaConsulta(millis: Long, fuso: TimeZone = TimeZone.getDefault()): String {
    if (millis <= 0L) return "Ainda não consultou."
    return "Última consulta: " + SimpleDateFormat("dd/MM HH:mm", Locale("pt", "BR")).apply { timeZone = fuso }.format(Date(millis))
}

/** Motivo legível de uma resposta que não foi Ok. */
fun motivoDaFalhaDeVersao(resposta: Resposta): String? = when (resposta) {
    is Resposta.Ok -> null
    is Resposta.Recusado -> if (resposta.status == 404) "nenhuma versão publicada no site" else resposta.mensagem
    is Resposta.TentarDepois -> "sem conexão com o site (${resposta.motivo})"
    Resposta.Desconectado -> "o site recusou a consulta"
}
