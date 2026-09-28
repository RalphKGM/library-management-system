const toggle = document.querySelector('.nav-toggle')
const nav = document.querySelector('#primary-nav')
if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true'
    toggle.setAttribute('aria-expanded', String(!open))
    nav.classList.toggle('is-open', !open)
  })
}

const filterInput = document.querySelector('[data-table-filter]')
const filterTable = document.querySelector('[data-filter-table]')
if (filterInput && filterTable) {
  filterInput.addEventListener('input', () => {
    const value = filterInput.value.trim().toLowerCase()
    filterTable.querySelectorAll('tbody tr').forEach(row => {
      row.hidden = value && !row.textContent.toLowerCase().includes(value)
    })
  })
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
