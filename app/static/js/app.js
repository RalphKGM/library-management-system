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
