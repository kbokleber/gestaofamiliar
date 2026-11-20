package br.com.kbosolucoes.gestaofamiliar.crianca

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/** Ajuste do Android que resolve uma checagem vermelha da tela "Configurações de envio". */
enum class AjusteAndroid { LOCALIZACAO, NOTIFICACOES, LOCALIZACAO_SEMPRE, BATERIA }

data class Checagem(val nome: String, val ok: Boolean, val explicacao: String, val ajuste: AjusteAndroid)

/** As 4 checagens de "Para funcionar sempre", na ordem em que aparecem na tela. */
fun checagensDeEnvio(
    localizacao: Boolean,
    notificacao: Boolean,
    localizacaoSempre: Boolean,
    semEconomiaDeBateria: Boolean,
): List<Checagem> = listOf(
    Checagem("Localização", localizacao, "Permissão de localização negada. Em Permissões › Localização, escolha permitir.", AjusteAndroid.LOCALIZACAO),
    Checagem("Notificação fixa", notificacao, "As notificações do app estão desligadas. Ligue para ver que o envio está ativo.", AjusteAndroid.NOTIFICACOES),
    Checagem("Localização o tempo todo", localizacaoSempre, "Em Permissões › Localização, escolha \"Permitir o tempo todo\".", AjusteAndroid.LOCALIZACAO_SEMPRE),
    Checagem("Sem economia de bateria", semEconomiaDeBateria, "O Android pode parar o envio para economizar bateria. Escolha \"Sem restrições\".", AjusteAndroid.BATERIA),
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
