export const MENUS = [
  { key: 'dashboard', label: 'Dashboard', href: '/' },
  { key: 'saude', label: 'Saúde', href: '/healthcare/members' },
  { key: 'manutencao', label: 'Manutenção', href: '/maintenance/equipment' },
  { key: 'financas', label: 'Finanças', href: '/finance' },
  { key: 'estudos', label: 'Estudos', href: '/estudos/painel' },
] as const

export type MenuKey = (typeof MENUS)[number]['key']

type MenuUser = {
  is_superuser?: boolean
  is_child?: boolean
  allowed_menus?: string[] | null
} | null | undefined

export function visibleMenuKeys(user: MenuUser): MenuKey[] {
  if (!user) return []
  if (user.is_superuser || user.allowed_menus == null) {
    return MENUS.map((menu) => menu.key)
  }
  return MENUS.map((menu) => menu.key).filter((key) => user.allowed_menus?.includes(key))
}

export function canSeeMenu(user: MenuUser, menu: MenuKey): boolean {
  return visibleMenuKeys(user).includes(menu)
}

export function firstAllowedPath(user: MenuUser): string {
  const keys = visibleMenuKeys(user)
  const match = MENUS.find((menu) => keys.includes(menu.key))
  if (!match) return '/sem-menu'
  if (user?.is_child && match.key === 'estudos') return '/estudos/atividades'
  return match.href
}

/** Tela inicial depois do login. Filho entra em Atividades, não no Painel. */
export function entradaAposLogin(user: MenuUser): string {
  if (user?.is_child && canSeeMenu(user, 'estudos')) return '/estudos/atividades'
  return firstAllowedPath(user)
}
