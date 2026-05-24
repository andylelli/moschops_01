import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'moschops-theme'
const ENVIRONMENT_KEY = 'moschops-environment'
const STRATEGY_KEY = 'moschops-strategy'
const ROLE_KEY = 'moschops-role'
const DATASET_KEY = 'moschops-dataset-profile'
const START_DATE_KEY = 'moschops-start-date'
const END_DATE_KEY = 'moschops-end-date'

function initialTheme(): ThemeMode {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'light' || saved === 'dark') {
    return saved
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function loadString(key: string, fallback: string): string {
  const value = localStorage.getItem(key)
  return value ?? fallback
}

function isoDateDaysAgo(days: number): string {
  const now = new Date()
  now.setUTCDate(now.getUTCDate() - days)
  return now.toISOString().slice(0, 10)
}

function initialStartDate(): string {
  return loadString(START_DATE_KEY, isoDateDaysAgo(30))
}

function initialEndDate(): string {
  return loadString(END_DATE_KEY, new Date().toISOString().slice(0, 10))
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    theme: initialTheme() as ThemeMode,
    environment: loadString(ENVIRONMENT_KEY, 'demo'),
    strategy: loadString(STRATEGY_KEY, 'daily-breakout-5-10'),
    operatorRole: loadString(ROLE_KEY, 'analyst'),
    datasetProfile: loadString(DATASET_KEY, 'rolling-90d'),
    startDate: initialStartDate(),
    endDate: initialEndDate(),
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
    persistContext() {
      localStorage.setItem(ENVIRONMENT_KEY, this.environment)
      localStorage.setItem(STRATEGY_KEY, this.strategy)
      localStorage.setItem(ROLE_KEY, this.operatorRole)
      localStorage.setItem(DATASET_KEY, this.datasetProfile)
      localStorage.setItem(START_DATE_KEY, this.startDate)
      localStorage.setItem(END_DATE_KEY, this.endDate)
    },
  },
})
