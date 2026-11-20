package br.com.kbosolucoes.gestaofamiliar.crianca

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.SystemClock
import android.view.MotionEvent
import android.view.View

/**
 * Botão SOS: só dispara depois de SEGURAR por 3 s (o anel enche enquanto segura).
 * Soltar antes cancela sem enviar nada. O envio em si vem depois da contagem de 5 s.
 */
@SuppressLint("ViewConstructor")
class BotaoSos(contexto: Context, private val aoSegurar: () -> Unit, private val aoSoltarCedo: () -> Unit) : View(contexto) {
    private var inicio = 0L
    private var segurando = false
    private val fundo = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(220, 38, 38) }
    private val trilho = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; color = Color.argb(90, 255, 255, 255) }
    private val anel = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; color = Color.WHITE; strokeCap = Paint.Cap.ROUND }
    private val texto = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD }
    private val area = RectF()

    init {
        contentDescription = "SOS. Segure por 3 segundos para pedir socorro."
        isClickable = true
        elevation = 12f
    }

    override fun onDraw(canvas: Canvas) {
        val r = minOf(width, height) / 2f
        val cx = width / 2f
        val cy = height / 2f
        canvas.drawCircle(cx, cy, r, fundo)
        val borda = r * 0.12f
        trilho.strokeWidth = borda
        anel.strokeWidth = borda
        area.set(cx - r + borda, cy - r + borda, cx + r - borda, cy + r - borda)
        canvas.drawArc(area, 0f, 360f, false, trilho)
        if (segurando) {
            val progresso = RegrasSos.progressoSegurar(inicio, SystemClock.uptimeMillis())
            canvas.drawArc(area, -90f, 360f * progresso, false, anel)
        }
        texto.textSize = r * 0.55f
        canvas.drawText("SOS", cx, cy + texto.textSize * 0.35f, texto)
    }

    private val passo = object : Runnable {
        override fun run() {
            if (!segurando) return
            if (RegrasSos.segurouOSuficiente(inicio, SystemClock.uptimeMillis())) {
                segurando = false
                invalidate()
                performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS)
                aoSegurar()
            } else {
                invalidate()
                postOnAnimation(this)
            }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(evento: MotionEvent): Boolean {
        when (evento.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                inicio = SystemClock.uptimeMillis()
                segurando = true
                postOnAnimation(passo)
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                if (segurando) {
                    segurando = false
                    removeCallbacks(passo)
                    invalidate()
                    aoSoltarCedo()
                }
            }
        }
        return true
    }
}
