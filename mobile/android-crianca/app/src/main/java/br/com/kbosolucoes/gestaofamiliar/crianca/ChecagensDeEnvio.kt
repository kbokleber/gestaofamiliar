package br.com.kbosolucoes.gestaofamiliar.crianca

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Checklist de envio: confere, item a item, se a localização deste celular vai continuar chegando
 * à família mesmo com o app fechado. Vale para qualquer celular que envia (criança ou adulto).
 * Sem Android aqui dentro, para dar para testar sozinho.
 */

/** Ajuste do Android que resolve um item. */
enum class AjusteAndroid { GPS, LOCALIZACAO, LOCALIZACAO_SEMPRE, PRECISAO, BATERIA, ENVIO, ENTENDI_PARADA, INICIO_AUTOMATICO, REDE, NOTIFICACOES }

/**
 * OK e FALTA: o app conferiu. ATRASADO: o envio funciona, mas o último ponto é velho.
 * Os dois MANUAL: o Android não deixa o app conferir; vale o que a pessoa marcou.
 */
enum class EstadoItem { OK, FALTA, ATRASADO, MANUAL_PENDENTE, MANUAL_CONFIRMADO }

data class ItemChecklist(
    val chave: String,
    val nome: String,
    val estado: EstadoItem,
    val explicacao: String,
    val ajuste: AjusteAndroid?,
    val rotuloAjuste: String?,
) {
    val ok: Boolean get() = estado == EstadoItem.OK || estado == EstadoItem.MANUAL_CONFIRMADO
}

/** O que o app lê do Android na hora de montar o checklist. */
data class EstadoDoCelular(
    val localizacaoLigada: Boolean,
    val gpsLigado: Boolean,
    val permissaoLocalizacao: Boolean,
    val permissaoSempre: Boolean,
    val localizacaoPrecisa: Boolean,
    val semEconomiaDeBateria: Boolean,
    /** O serviço de envio está de pé agora. */
    val servicoRodando: Boolean,
    /**
     * Última vez que o serviço foi achado parado e religado depois de mais de 30 min sem envio
     * (0 = não aconteceu). paradoDesdeMs é o último envio antes da parada.
     */
    val religadoEmMs: Long,
    val paradoDesdeMs: Long,
    val ultimoEnvioMs: Long,
    val agoraMs: Long,
    val internet: Boolean,
    val notificacoes: Boolean,
    val fabricante: String,
    /** 0 = a pessoa ainda não confirmou o início automático. */
    val inicioAutomaticoConfirmadoMs: Long,
)

/** Passou disso sem enviar, o item "Envio com o app fechado" fica atrasado (o app envia a cada ~5 min). */
const val ENVIO_ATRASADO_MS = 30 * 60 * 1000L

/** Por quanto tempo a tela continua avisando de uma parada já religada (até a pessoa tocar em "Entendi"). */
const val AVISO_PARADA_MS = 24 * 60 * 60 * 1000L

/** O serviço estava parado há mais de 30 min quando foi religado: vale anotar a parada. */
fun deveAnotarParada(estavaRodando: Boolean, ultimoEnvioMs: Long, agoraMs: Long): Boolean =
    !estavaRodando && ultimoEnvioMs > 0L && agoraMs - ultimoEnvioMs > ENVIO_ATRASADO_MS

private val MARCAS_COM_INICIO_AUTOMATICO = setOf(
    "xiaomi", "redmi", "poco", "oppo", "realme", "vivo", "iqoo", "oneplus", "huawei", "honor", "meizu", "asus", "letv", "tecno", "infinix",
)

/** Marcas que têm a chave "Início automático" (o Android padrão não tem e não deixa o app conferir). */
fun precisaInicioAutomatico(fabricante: String): Boolean = fabricante.trim().lowercase(Locale.ROOT) in MARCAS_COM_INICIO_AUTOMATICO

fun ehXiaomi(fabricante: String): Boolean = fabricante.trim().lowercase(Locale.ROOT) in setOf("xiaomi", "redmi", "poco")

/** "5 min", "2 h 10 min", "3 dias". */
fun duracaoCurta(ms: Long): String {
    val minutos = (ms.coerceAtLeast(0L) / 60_000L)
    if (minutos < 1) return "menos de 1 min"
    if (minutos < 60) return "$minutos min"
    val horas = minutos / 60
    if (horas < 24) return if (minutos % 60 == 0L) "$horas h" else "$horas h ${minutos % 60} min"
    val dias = horas / 24
    return if (dias == 1L) "1 dia" else "$dias dias"
}

private fun horaCurta(millis: Long, fuso: TimeZone): String =
    SimpleDateFormat("dd/MM HH:mm", Locale("pt", "BR")).apply { timeZone = fuso }.format(Date(millis))

private fun dataCurta(millis: Long, fuso: TimeZone): String =
    SimpleDateFormat("dd/MM/yyyy", Locale("pt", "BR")).apply { timeZone = fuso }.format(Date(millis))

/** Os itens, na ordem da tela. O de início automático só aparece nas marcas que têm essa chave. */
fun checklistDeEnvio(e: EstadoDoCelular, fuso: TimeZone = TimeZone.getDefault()): List<ItemChecklist> {
    val itens = mutableListOf<ItemChecklist>()

    // 1. GPS (localização do aparelho) ligado.
    itens += if (e.localizacaoLigada) {
        ItemChecklist("gps", "Localização do celular ligada", EstadoItem.OK, "", null, null)
    } else {
        ItemChecklist(
            "gps", "Localização do celular ligada", EstadoItem.FALTA,
            "A localização do celular está desligada. Ligue em Configurações › Localização.",
            AjusteAndroid.GPS, "Ligar localização",
        )
    }

    // 2. "Permitir o tempo todo".
    itens += when {
        e.permissaoLocalizacao && e.permissaoSempre ->
            ItemChecklist("sempre", "Localização \"o tempo todo\"", EstadoItem.OK, "", null, null)
        !e.permissaoLocalizacao -> ItemChecklist(
            "sempre", "Localização \"o tempo todo\"", EstadoItem.FALTA,
            "O app não tem permissão de localização. Em Permissões › Localização, escolha \"Permitir o tempo todo\".",
            AjusteAndroid.LOCALIZACAO, "Dar permissão",
        )
        else -> ItemChecklist(
            "sempre", "Localização \"o tempo todo\"", EstadoItem.FALTA,
            "Só funciona com o app aberto. Em Permissões › Localização, escolha \"Permitir o tempo todo\".",
            AjusteAndroid.LOCALIZACAO_SEMPRE, "Abrir permissão",
        )
    }

    // 3. Precisão alta: localização precisa (permissão) e GPS ligado (não só rede).
    itens += when {
        e.localizacaoPrecisa && e.gpsLigado ->
            ItemChecklist("precisa", "Precisão alta", EstadoItem.OK, "", null, null)
        !e.localizacaoPrecisa -> ItemChecklist(
            "precisa", "Precisão alta", EstadoItem.FALTA,
            "A localização está aproximada. Em Permissões › Localização, ligue \"Usar localização precisa\".",
            AjusteAndroid.PRECISAO, "Abrir permissão",
        )
        else -> ItemChecklist(
            "precisa", "Precisão alta", EstadoItem.FALTA,
            "O GPS do celular está desligado (só rede). Em Configurações › Localização, ligue a precisão alta.",
            AjusteAndroid.GPS, "Abrir localização",
        )
    }

    // 4. Bateria sem restrição.
    itens += if (e.semEconomiaDeBateria) {
        ItemChecklist("bateria", "Bateria do app sem restrição", EstadoItem.OK, "", null, null)
    } else {
        ItemChecklist(
            "bateria", "Bateria do app sem restrição", EstadoItem.FALTA,
            "O Android pode parar o envio para economizar bateria. Escolha \"Sem restrições\".",
            AjusteAndroid.BATERIA, "Abrir ajuste",
        )
    }

    // 5. Envio funcionando com o app fechado: serviço de pé e último envio recente.
    val desde = e.agoraMs - e.ultimoEnvioMs
    itens += when {
        e.ultimoEnvioMs <= 0L -> ItemChecklist(
            "envio", "Envio com o app fechado", EstadoItem.FALTA,
            "Este celular ainda não enviou nenhuma localização. Confira os itens acima e toque em \"Enviar agora\".",
            AjusteAndroid.ENVIO, "Enviar agora",
        )
        !e.servicoRodando -> ItemChecklist(
            "envio", "Envio com o app fechado", EstadoItem.FALTA,
            "O envio está parado (último envio há ${duracaoCurta(desde)}). Confira os itens acima e toque em \"Ligar envio\".",
            AjusteAndroid.ENVIO, "Ligar envio",
        )
        e.religadoEmMs > 0L && e.agoraMs - e.religadoEmMs < AVISO_PARADA_MS -> ItemChecklist(
            "envio", "Envio com o app fechado", EstadoItem.FALTA,
            "O envio ficou parado ${duracaoCurta(e.religadoEmMs - e.paradoDesdeMs)} " +
                "(de ${horaCurta(e.paradoDesdeMs, fuso)} a ${horaCurta(e.religadoEmMs, fuso)}) e só voltou quando o app foi aberto ou o celular reiniciou. " +
                "Se o celular não ficou desligado, o Android encerrou o app: confira bateria e início automático.",
            AjusteAndroid.ENTENDI_PARADA, "Entendi",
        )
        desde > ENVIO_ATRASADO_MS -> ItemChecklist(
            "envio", "Envio com o app fechado", EstadoItem.ATRASADO,
            "O último envio foi há ${duracaoCurta(desde)}. Confira a internet e a localização, e toque em \"Enviar agora\".",
            AjusteAndroid.ENVIO, "Enviar agora",
        )
        else -> ItemChecklist(
            "envio", "Envio com o app fechado", EstadoItem.OK,
            "Último envio há ${duracaoCurta(desde)}.", null, null,
        )
    }

    // 6. Início automático: o Android não deixa conferir. Só confirmação manual, sem fingir.
    if (precisaInicioAutomatico(e.fabricante)) {
        val passos = if (ehXiaomi(e.fabricante)) {
            "Em Configurações › Apps › Gestão Familiar, ligue \"Início automático\". " +
                "Depois, nos apps recentes, segure o Gestão Familiar e toque no cadeado."
        } else {
            "Nas configurações do app (ou em Gerenciador de apps / Inicialização), permita que o Gestão Familiar inicie sozinho " +
                "e trave o app nos recentes."
        }
        itens += if (e.inicioAutomaticoConfirmadoMs > 0L) {
            ItemChecklist(
                "inicio_automatico", "Início automático", EstadoItem.MANUAL_CONFIRMADO,
                "Confirmado por você em ${dataCurta(e.inicioAutomaticoConfirmadoMs, fuso)}. O Android não deixa o app conferir.",
                AjusteAndroid.INICIO_AUTOMATICO, "Abrir ajuste",
            )
        } else {
            ItemChecklist(
                "inicio_automatico", "Início automático", EstadoItem.MANUAL_PENDENTE,
                "$passos O Android não deixa o app conferir: depois de fazer, toque em \"Já fiz\".",
                AjusteAndroid.INICIO_AUTOMATICO, "Abrir ajuste",
            )
        }
    }

    // 7. Rede ligada.
    itens += if (e.internet) {
        ItemChecklist("rede", "Internet ligada", EstadoItem.OK, "", null, null)
    } else {
        ItemChecklist(
            "rede", "Internet ligada", EstadoItem.FALTA,
            "Sem internet agora. As posições ficam guardadas e saem quando a internet voltar.",
            AjusteAndroid.REDE, "Abrir internet",
        )
    }

    // Já existia na 2.0.6: a notificação fixa mostra que o envio está ativo.
    itens += if (e.notificacoes) {
        ItemChecklist("notificacoes", "Notificação fixa", EstadoItem.OK, "", null, null)
    } else {
        ItemChecklist(
            "notificacoes", "Notificação fixa", EstadoItem.FALTA,
            "As notificações do app estão desligadas. Ligue para ver que o envio está ativo.",
            AjusteAndroid.NOTIFICACOES, "Abrir ajuste",
        )
    }
    return itens
}

/** Resumo da tela: o que ainda precisa de ação (pendente manual conta). */
fun itensQueFaltam(itens: List<ItemChecklist>): List<ItemChecklist> = itens.filter { !it.ok }

/**
 * O que vai para o site junto com a posição: só os ajustes do Android, sem dado pessoal.
 * Envio e internet o site calcula sozinho (pela hora em que o ponto chegou).
 */
fun checklistParaServidor(e: EstadoDoCelular, fuso: TimeZone = TimeZone.getDefault()): Map<String, Any?> = linkedMapOf(
    "gps" to e.localizacaoLigada,
    "sempre" to (e.permissaoLocalizacao && e.permissaoSempre),
    "precisa" to (e.localizacaoPrecisa && e.gpsLigado),
    "bateria_livre" to e.semEconomiaDeBateria,
    "inicio_automatico" to when {
        !precisaInicioAutomatico(e.fabricante) -> "nao_se_aplica"
        e.inicioAutomaticoConfirmadoMs > 0L -> "confirmado"
        else -> "pendente"
    },
    "inicio_automatico_em" to if (precisaInicioAutomatico(e.fabricante) && e.inicioAutomaticoConfirmadoMs > 0L) {
        SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).apply { timeZone = fuso }.format(Date(e.inicioAutomaticoConfirmadoMs))
    } else null,
)

/** "Último envio: dd/mm/aaaa hh:mm" no fuso do celular, ou o aviso de que nunca enviou. */
fun formatarUltimoEnvio(millis: Long, fuso: TimeZone = TimeZone.getDefault()): String {
    if (millis <= 0L) return "Ainda não enviou nenhuma localização."
    val formato = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).apply { timeZone = fuso }
    return "Último envio: ${formato.format(Date(millis))}"
}

/** Quanto tempo o histórico fica guardado, como dito ao usuário. */
fun textoHistorico(adulto: Boolean): String =
    if (adulto) "Só os adultos da família veem a sua posição. O histórico fica 7 dias e depois é apagado."
    else "Os adultos da família veem a posição e o trajeto deste celular. O histórico é apagado automaticamente pelo site."
