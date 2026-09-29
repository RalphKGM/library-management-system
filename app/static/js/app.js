const toggle = document.querySelector('.nav-toggle')
const nav = document.querySelector('#primary-nav')
if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true'
    toggle.setAttribute('aria-expanded', String(!open))
    nav.classList.toggle('is-open', !open)
  })
}

document.querySelectorAll('[data-table-filter]').forEach(filterInput => {
  const filterTable = filterInput.closest('.staff-card, .admin-panel')?.querySelector('[data-filter-table]')
  if (!filterTable) return
  filterInput.addEventListener('input', () => {
    const value = filterInput.value.trim().toLowerCase()
    filterTable.querySelectorAll('tbody tr').forEach(row => {
      row.hidden = value && !row.textContent.toLowerCase().includes(value)
    })
  })
})

const dashboardClock = document.querySelector('[data-dashboard-clock]')
if (dashboardClock) {
  const updateClock = () => {
    const now = new Date()
    dashboardClock.dateTime = now.toISOString()
    dashboardClock.textContent = new Intl.DateTimeFormat(undefined, {
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit'
    }).format(now)
  }
  updateClock()
  window.setInterval(updateClock, 60000)
}

const themeChoices = document.querySelectorAll('[data-theme-choice]')
const allowedThemes = ['rose', 'charcoal', 'coastal', 'orchid', 'midnight']
function setTheme(theme) {
  const chosen = allowedThemes.includes(theme) ? theme : 'rose'
  document.documentElement.dataset.theme = chosen
  themeChoices.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.themeChoice === chosen))
  })
  try { localStorage.setItem('library-theme', chosen) } catch (_) {}
}
let savedTheme = 'rose'
try { savedTheme = localStorage.getItem('library-theme') || 'rose' } catch (_) {}
setTheme(savedTheme)
themeChoices.forEach(button => button.addEventListener('click', () => setTheme(button.dataset.themeChoice)))

function dismissFlash(flash) {
  flash.classList.add('is-leaving')
  window.setTimeout(() => flash.remove(), 250)
}
document.querySelectorAll('.flash').forEach(flash => {
  const timer = window.setTimeout(() => dismissFlash(flash), 7000)
  flash.querySelector('.flash-close')?.addEventListener('click', () => {
    window.clearTimeout(timer)
    dismissFlash(flash)
  })
})
