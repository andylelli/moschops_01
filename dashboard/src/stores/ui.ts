import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'moschops-theme'

function initialTheme(): ThemeMode {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'light' || saved === 'dark') {
    return saved
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    theme: initialTheme() as ThemeMode,
    environment: 'demo',
    strategy: 'daily-breakout-5-10',
  }),
  actions: {
    applyTheme() {
      document.documentElement.setAttribute('data-theme', this.theme)
      localStorage.setItem(THEME_KEY, this.theme)
    },
    toggleTheme() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
      this.applyTheme()
    },
  },
})
