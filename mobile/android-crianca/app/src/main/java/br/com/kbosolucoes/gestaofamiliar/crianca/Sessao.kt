package br.com.kbosolucoes.gestaofamiliar.crianca

import org.json.JSONObject
import java.net.URI

/** Quem está logado no site aberto dentro do app (enviado pelo próprio site pela ponte JS). */
data class UsuarioSessao(val id: Int, val nome: String, val crianca: Boolean, val familia: Int?) {
    companion object {
        fun ler(json: String?): UsuarioSessao? {
            if (json.isNullOrBlank()) return null
            return try {
                val o = JSONObject(json)
                val id = o.optInt("id", -1)
                if (id <= 0) return null
                val familia = if (o.isNull("family_id")) null else o.optInt("family_id", -1).takeIf { it > 0 }
                UsuarioSessao(id, o.optString("nome", "").trim(), o.optBoolean("is_child", false), familia)
            } catch (e: Exception) {
                null
            }
        }
    }
}

/** O que o app faz quando alguém entra no site. */
sealed class AcaoSessao {
    object Nada : AcaoSessao()
    /** Celular já ligado a esta criança por código (versão antiga): só anota quem é. */
    object AnotarCrianca : AcaoSessao()
    /** Conecta este celular à criança logada (troca a criança anterior, se houver). */
    object ParearCrianca : AcaoSessao()
    /** Registra este celular do adulto para receber os alertas (troca o adulto anterior, se houver). */
    object RegistrarAdulto : AcaoSessao()
}

/**
 * Regras:
 * - Criança logada: o celular passa a enviar a localização dela.
 * - Adulto logado num celular que já é de uma criança (ex.: o pai conferindo algo): nada muda.
 * - Adulto no próprio celular: recebe alertas; o celular dele nunca envia localização.
 */
fun decidirSessao(
    usuario: UsuarioSessao?,
    pareadoComoCrianca: Boolean,
    criancaPareadaId: Int,
    adultoRegistradoId: Int,
): AcaoSessao {
    if (usuario == null || usuario.familia == null) return AcaoSessao.Nada
    if (usuario.crianca) {
        if (!pareadoComoCrianca) return AcaoSessao.ParearCrianca
        return when (criancaPareadaId) {
            usuario.id -> AcaoSessao.Nada
            0 -> AcaoSessao.AnotarCrianca
            else -> AcaoSessao.ParearCrianca
        }
    }
    if (pareadoComoCrianca) return AcaoSessao.Nada
    return if (adultoRegistradoId == usuario.id) AcaoSessao.Nada else AcaoSessao.RegistrarAdulto
}

/** Compara versões "2.0.0" e "2.0.10". Positivo se [a] é mais nova. Partes não numéricas valem 0. */
fun compararVersoes(a: String, b: String): Int {
    val pa = a.trim().split('.').map { it.takeWhile(Char::isDigit).toIntOrNull() ?: 0 }
    val pb = b.trim().split('.').map { it.takeWhile(Char::isDigit).toIntOrNull() ?: 0 }
    for (i in 0 until maxOf(pa.size, pb.size)) {
        val d = pa.getOrElse(i) { 0 } - pb.getOrElse(i) { 0 }
        if (d != 0) return d
    }
    return 0
}

/**
 * Endereços que abrem dentro do app: o próprio site e os subdomínios irmãos (ex.: o login em
 * auth.kbosolucoes.com.br). O resto (WhatsApp, mapas, links externos) abre fora.
 */
fun abreDentroDoApp(site: String, endereco: String): Boolean {
    val alvo = try { URI(endereco) } catch (e: Exception) { return false }
    if (alvo.scheme != "https" && alvo.scheme != "http") return false
    val hostAlvo = alvo.host?.lowercase() ?: return false
    val hostSite = try { URI(ApiClient.normalizarEndereco(site)).host?.lowercase() } catch (e: Exception) { null } ?: return false
    if (hostAlvo == hostSite) return true
    val partes = hostSite.split('.')
    // Domínio "pai" com pelo menos dois pontos (kbosolucoes.com.br), para não liberar "com.br" inteiro.
    if (partes.size < 4) return false
    val pai = partes.drop(1).joinToString(".")
    return hostAlvo.endsWith(".$pai")
}

/** A ponte com o app só atende o próprio site (nem o login, nem outros endereços). */
fun mesmoSite(site: String, endereco: String): Boolean {
    val alvo = try { URI(endereco) } catch (e: Exception) { return false }
    val base = try { URI(ApiClient.normalizarEndereco(site)) } catch (e: Exception) { return false }
    return alvo.scheme == base.scheme && alvo.host != null && alvo.host.equals(base.host, ignoreCase = true) && alvo.port == base.port
}

/**
 * Login por provedor externo (ex.: Google) na tela do Keycloak: o Google não deixa entrar dentro de apps.
 * Devolve o provedor (ex.: "google") quando [endereco] é o botão desse provedor; senão, null.
 */
fun provedorExterno(endereco: String): String? {
    val uri = try { URI(endereco) } catch (e: Exception) { return null }
    val partes = uri.path?.split('/')?.filter { it.isNotEmpty() } ?: return null
    val i = partes.indexOf("broker")
    if (i < 0 || i + 2 >= partes.size || partes[i + 2] != "login") return null
    return partes[i + 1].takeIf { it.matches(Regex("[A-Za-z0-9_.-]+")) }
}

/** O endereço do pedido de login do site (Keycloak), guardado para refazer o login no navegador. */
fun ehPedidoDeLogin(endereco: String): Boolean =
    endereco.contains("/protocol/openid-connect/auth?")

/** Abre o mesmo pedido de login no navegador, indo direto para o provedor escolhido. */
fun loginNoNavegador(pedidoDeLogin: String, provedor: String): String {
    val sem = Regex("([?&])kc_idp_hint=[^&]*&?").replace(pedidoDeLogin) { m -> m.groupValues[1] }.trimEnd('&', '?')
    val sep = if (sem.contains('?')) "&" else "?"
    return "$sem${sep}kc_idp_hint=${java.net.URLEncoder.encode(provedor, "UTF-8")}"
}

/**
 * Volta do login feito no navegador: https://<site>/app-login?retorno=<resultado> vira
 * https://<site>/app-login#<resultado>, que o site dentro do app usa para concluir o login.
 * Só aceita o endereço do próprio site.
 */
fun retornoDoLogin(site: String, endereco: String): String? {
    if (!mesmoSite(site, endereco)) return null
    val uri = try { URI(endereco) } catch (e: Exception) { return null }
    if (uri.path != CAMINHO_RETORNO_LOGIN) return null
    val retorno = uri.rawQuery?.split('&')?.firstOrNull { it.startsWith("retorno=") }?.removePrefix("retorno=")
        ?.let { java.net.URLDecoder.decode(it, "UTF-8") }
    val fragmento = retorno ?: uri.rawFragment ?: ""
    return ApiClient.normalizarEndereco(site) + CAMINHO_RETORNO_LOGIN + if (fragmento.isNotEmpty()) "#$fragmento" else ""
}

const val CAMINHO_RETORNO_LOGIN = "/app-login"
