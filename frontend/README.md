# Frontend - Sistema Familiar

Interface moderna e responsiva construída com React, TypeScript e TailwindCSS.

## 🚀 Quick Start

\`\`\`bash
# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview do build
npm run preview
\`\`\`

## 🛠️ Tecnologias

- **React 18** - UI Library
- **TypeScript** - Type Safety
- **Vite** - Build Tool
- **TailwindCSS** - CSS Framework
- **React Router** - Navegação
- **Axios** - HTTP Client
- **Zustand** - State Management
- **React Query** - Server State
- **Lucide React** - Ícones
- **Vite PWA** - Progressive Web App

## 📁 Estrutura

\`\`\`
src/
├── components/          # Componentes reutilizáveis
│   └── Layout.tsx      # Layout com sidebar
├── lib/                # Utilitários
│   ├── api.ts          # Cliente Axios
│   └── utils.ts        # Helpers
├── pages/              # Páginas
│   ├── Dashboard.tsx
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── healthcare/
│   └── maintenance/
├── services/           # Serviços de API
│   └── authService.ts
├── stores/             # Zustand stores
│   └── authStore.ts
├── App.tsx             # Rotas principais
├── main.tsx            # Entry point
└── index.css           # Estilos globais
\`\`\`

## 🎨 Componentes

### Layout
Sidebar responsivo com navegação para todas as seções.

### Autenticação
- Login page
- Register page
- Protected routes

### Dashboard
Visão geral com estatísticas e ações rápidas.

### Healthcare Pages
- Family Members
- Appointments
- Medications

### Maintenance Pages
- Equipment
- Maintenance Orders

## 🔧 Customização

### Cores (Tailwind)
Edite `tailwind.config.js` para mudar o tema:

\`\`\`js
theme: {
  extend: {
    colors: {
      primary: 'your-color',
      // ...
    }
  }
}
\`\`\`

### API URL
Configure em `.env.local`:

\`\`\`
VITE_API_URL=http://localhost:8001/api/v1
\`\`\`

## 📱 PWA

O app é uma Progressive Web App:

- ✅ Instalável
- ✅ Funciona offline
- ✅ Ícone na tela inicial

Para customizar o manifest, edite `vite.config.ts`.

## 🚀 Build

\`\`\`bash
npm run build
\`\`\`

Arquivos gerados em `dist/`. Sirva com:

\`\`\`bash
npm install -g serve
serve -s dist
\`\`\`

## 🔐 Autenticação

O token JWT é armazenado no localStorage via Zustand:

\`\`\`typescript
import { useAuthStore } from './stores/authStore'

const { user, token, isAuthenticated, setAuth, logout } = useAuthStore()
\`\`\`

## 📡 Fazendo Requisições

Use o cliente API configurado:

\`\`\`typescript
import api from '@/lib/api'

const response = await api.get('/endpoint')
\`\`\`

O token é automaticamente adicionado nos headers.

