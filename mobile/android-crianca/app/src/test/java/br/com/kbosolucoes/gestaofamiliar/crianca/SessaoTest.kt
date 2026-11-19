package br.com.kbosolucoes.gestaofamiliar.crianca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessaoTest {
    private val gui = UsuarioSessao(16, "Guilherme", crianca = true, familia = 1)
    private val pai = UsuarioSessao(1, "Kleber", crianca = false, familia = 1)

    @Test
    fun leUsuarioEnviadoPeloSite() {
        assertEquals(gui, UsuarioSessao.ler("""{"id":16,"nome":"Guilherme","is_child":true,"family_id":1}"""))
        assertEquals(null, UsuarioSessao.ler("""{"id":3,"nome":"X","is_child":false,"family_id":null}""")?.familia)
        assertNull(UsuarioSessao.ler(""))
        assertNull(UsuarioSessao.ler("não é json"))
        assertNull(UsuarioSessao.ler("""{"nome":"sem id"}"""))
    }

    @Test
    fun criancaConectaOCelularSozinha() {
        assertEquals(AcaoSessao.ParearCrianca, decidirSessao(gui, pareadoComoCrianca = false, criancaPareadaId = 0, adultoRegistradoId = 0))
        assertEquals(AcaoSessao.Nada, decidirSessao(gui, true, 16, 0))
        // Pareado por código na versão antiga (sem id): só anota, não cria outro pareamento.
        assertEquals(AcaoSessao.AnotarCrianca, decidirSessao(gui, true, 0, 0))
        // Celular era da Giovana: passa para o Guilherme.
        assertEquals(AcaoSessao.ParearCrianca, decidirSessao(gui, true, 17, 0))
        // Criança no celular de um adulto: só troca depois de confirmar na tela.
        assertEquals(AcaoSessao.ConfirmarTrocaDeAdulto, decidirSessao(gui, false, 0, 1))
    }

    @Test
    fun adultoRecebeAlertasMasNuncaViraCelularMonitorado() {
        assertEquals(AcaoSessao.RegistrarAdulto, decidirSessao(pai, false, 0, 0))
        assertEquals(AcaoSessao.Nada, decidirSessao(pai, false, 0, 1))
        assertEquals(AcaoSessao.RegistrarAdulto, decidirSessao(pai, false, 0, 2))
        // Adulto entrando no celular da criança: nada muda (continua enviando a localização dela).
        assertEquals(AcaoSessao.Nada, decidirSessao(pai, true, 16, 0))
        // Sem família ou sem login: nada.
        assertEquals(AcaoSessao.Nada, decidirSessao(pai.copy(familia = null), false, 0, 0))
        assertEquals(AcaoSessao.Nada, decidirSessao(null, false, 0, 0))
    }

    @Test
    fun comparaVersoes() {
        assertTrue(compararVersoes("2.0.1", "2.0.0") > 0)
        assertTrue(compararVersoes("2.0.10", "2.0.9") > 0)
        assertTrue(compararVersoes("1.9", "2.0.0") < 0)
        assertEquals(0, compararVersoes("2.0", "2.0.0"))
        assertEquals(0, compararVersoes("2.0.0", "2.0.0"))
    }

    @Test
    fun soOSiteEOLoginAbremDentroDoApp() {
        val site = "https://gestaofamiliar.kbosolucoes.com.br"
        assertTrue(abreDentroDoApp(site, "https://gestaofamiliar.kbosolucoes.com.br/estudos"))
        assertTrue(abreDentroDoApp(site, "https://auth.kbosolucoes.com.br/realms/x/protocol/openid-connect/auth?a=1"))
        assertFalse(abreDentroDoApp(site, "https://wa.me/5511999999999"))
        assertFalse(abreDentroDoApp(site, "https://outro.com.br/"))
        assertFalse(abreDentroDoApp(site, "https://kbosolucoes.com.br.golpe.com/"))
        assertFalse(abreDentroDoApp(site, "tel:11999999999"))
        assertFalse(abreDentroDoApp("https://app.exemplo.com", "https://outra.exemplo.com/"))
    }

    @Test
    fun ponteSoAtendeOProprioSite() {
        val site = "https://gestaofamiliar.kbosolucoes.com.br"
        assertTrue(mesmoSite(site, "https://gestaofamiliar.kbosolucoes.com.br/localizacao"))
        assertTrue(mesmoSite(site, "https://GestaoFamiliar.kbosolucoes.com.br/"))
        assertFalse(mesmoSite(site, "https://auth.kbosolucoes.com.br/"))
        assertFalse(mesmoSite(site, "http://gestaofamiliar.kbosolucoes.com.br/"))
        assertFalse(mesmoSite(site, ""))
    }

    @Test
    fun guardaIdDaCriancaDoPareamento() {
        val corpo = org.json.JSONObject("""{"device_token":"t","device_id":5,"crianca_id":16,"crianca_nome":"Guilherme"}""")
        assertEquals(Pareamento("t", 5, "Guilherme", 16), ApiClient.lerPareamento(corpo))
    }

    @Test
    fun loginPeloGoogleVaiParaONavegadorEVoltaAoApp() {
        val site = "https://gestaofamiliar.kbosolucoes.com.br"
        val pedido = "https://auth.kbosolucoes.com.br/realms/familia/protocol/openid-connect/auth?client_id=gestaofamiliar" +
            "&redirect_uri=https%3A%2F%2Fgestaofamiliar.kbosolucoes.com.br%2Fapp-login&state=abc&code_challenge=x"
        assertTrue(ehPedidoDeLogin(pedido))
        assertFalse(ehPedidoDeLogin("https://auth.kbosolucoes.com.br/realms/familia/login-actions/authenticate?x=1"))

        assertEquals("google", provedorExterno("https://auth.kbosolucoes.com.br/realms/familia/broker/google/login?client_id=g&tab_id=t"))
        assertNull(provedorExterno("https://auth.kbosolucoes.com.br/realms/familia/broker/google/endpoint?state=x"))
        assertNull(provedorExterno("https://auth.kbosolucoes.com.br/realms/familia/protocol/openid-connect/auth?x=1"))

        assertEquals("$pedido&kc_idp_hint=google", loginNoNavegador(pedido, "google"))
        assertEquals("$pedido&kc_idp_hint=google", loginNoNavegador("$pedido&kc_idp_hint=github", "google"))

        // Volta do navegador: o resultado vai depois do # para o site concluir o login dentro do app.
        assertEquals(
            "$site/app-login#state=abc&code=123",
            retornoDoLogin(site, "$site/app-login?retorno=state%3Dabc%26code%3D123"),
        )
        assertEquals("$site/app-login#state=abc&code=1", retornoDoLogin(site, "$site/app-login#state=abc&code=1"))
        assertNull(retornoDoLogin(site, "https://golpe.com/app-login?retorno=x"))
        assertNull(retornoDoLogin(site, "$site/outra?retorno=x"))
    }

    @Test
    fun atualizadorConfereOArquivoBaixado() {
        val arquivo = java.io.File.createTempFile("apk", ".bin")
        arquivo.writeText("abc")
        // SHA-256 de "abc"
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", Atualizador.sha256(arquivo))
        arquivo.delete()
    }
}
