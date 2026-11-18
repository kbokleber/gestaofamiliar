package br.com.kbosolucoes.gestaofamiliar.crianca

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Volta a compartilhar a localização depois que o celular liga ou o app é atualizado. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(contexto: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED -> {
                val configuracao = Configuracao(contexto)
                // Sem "permitir o tempo todo", o Android não deixa ligar o serviço em segundo plano.
                if (configuracao.temLocalizacaoSempre()) {
                    runCatching { LocationService.iniciar(contexto) }
                }
            }
        }
    }
}
