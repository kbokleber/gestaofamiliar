import { useEffect, type ReactNode } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Circle, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { corBateria, type Lugar } from './api'

/** Centro usado quando ainda não há nenhum ponto nem lugar: São Paulo. */
export const CENTRO_PADRAO: [number, number] = [-23.55, -46.63]

type Ponto = [number, number]

function Enquadrar({ pontos, chave }: { pontos: Ponto[]; chave: string }) {
  const mapa = useMap()
  useEffect(() => {
    if (pontos.length === 0) return
    if (pontos.length === 1) {
      mapa.setView(pontos[0], Math.max(mapa.getZoom(), 15))
      return
    }
    mapa.fitBounds(L.latLngBounds(pontos), { padding: [30, 30], maxZoom: 17 })
    // Reenquadra só quando o conjunto muda de verdade (a chave), não a cada atualização.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapa, chave])
  return null
}

function CliqueNoMapa({ onClique }: { onClique: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (evento) => onClique(evento.latlng.lat, evento.latlng.lng),
  })
  return null
}

interface MapaBaseProps {
  pontos: Ponto[]
  chaveEnquadramento: string
  altura?: string
  onClique?: (lat: number, lng: number) => void
  children?: ReactNode
}

/** Mapa do OpenStreetMap. O z-0 isola as camadas do Leaflet para não cobrirem os modais. */
export function MapaBase({ pontos, chaveEnquadramento, altura = 'h-80', onClique, children }: MapaBaseProps) {
  return (
    <div className={`relative z-0 w-full overflow-hidden rounded-lg border border-gray-200 ${altura}`}>
      <MapContainer center={pontos[0] ?? CENTRO_PADRAO} zoom={13} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <Enquadrar pontos={pontos} chave={chaveEnquadramento} />
        {onClique && <CliqueNoMapa onClique={onClique} />}
        {children}
      </MapContainer>
    </div>
  )
}

export function CirculosLugares({ lugares }: { lugares: Lugar[] }) {
  return (
    <>
      {lugares.map((lugar) => (
        <Circle
          key={lugar.id}
          center={[lugar.latitude, lugar.longitude]}
          radius={lugar.raio_m}
          pathOptions={{ color: '#7c3aed', weight: 2, fillOpacity: 0.12 }}
        >
          <Tooltip direction="top">{lugar.nome}</Tooltip>
        </Circle>
      ))}
    </>
  )
}

function escaparHtml(texto: string): string {
  return texto.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] || c)
}

/** Marcador da criança: apelido (ou início do nome) e a bateria logo abaixo, com a cor do nível. */
export function iconeCrianca(nome: string, bateria: number | null, apelido?: string | null, adulto = false): L.DivIcon {
  // Sem apelido, duas letras: irmãos com a mesma inicial não ficam iguais no mapa.
  const letras = nome.trim().slice(0, 2) || '?'
  const rotulo = apelido?.trim() || letras[0].toUpperCase() + letras.slice(1).toLowerCase()
  const inicial = escaparHtml(rotulo)
  const fonte = rotulo.length <= 2 ? 15 : rotulo.length === 3 ? 13 : 10
  const cor = corBateria(bateria).hex
  const textoBateria = bateria == null ? '—' : `${bateria}%`
  return L.divIcon({
    className: '',
    iconSize: [44, 58],
    iconAnchor: [22, 22],
    tooltipAnchor: [0, -22],
    html: `
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px">
        <div style="width:40px;height:40px;border-radius:9999px;background:${adulto ? '#0f766e' : '#7c3aed'};color:#fff;font-weight:700;font-size:${fonte}px;line-height:1;text-align:center;overflow:hidden;display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${inicial}</div>
        <div style="background:${cor};color:#fff;font-size:12px;font-weight:700;padding:0 6px;border-radius:9999px;box-shadow:0 1px 3px rgba(0,0,0,.3)">${textoBateria}</div>
      </div>`,
  })
}

/** Bolinha simples para início, fim, paradas e o ponto escolhido no cadastro. */
export function iconeBolinha(cor: string, rotulo = ''): L.DivIcon {
  return L.divIcon({
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    html: `<div style="width:24px;height:24px;border-radius:9999px;background:${cor};color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4)">${escaparHtml(rotulo)}</div>`,
  })
}
