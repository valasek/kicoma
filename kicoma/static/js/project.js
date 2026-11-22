/* Project specific Javascript goes here. */

// JavaScript to close the date picker after selecting a date
document.addEventListener('change', function (e) {
    if (e.target.type === 'date') {
        e.target.blur(); // Removes focus, which closes the picker
    }
});

// Show a recent unit change of the selected article (options rendered by ArticleUnitSelect)
function showUnitChangeNotice(select) {
    const notice = select.form && select.form.querySelector('.js-unit-change-notice');
    if (!notice) {
        return;
    }
    const option = select.options[select.selectedIndex];
    const text = (option && option.dataset.unitChangeNotice) || '';
    notice.textContent = text;
    notice.hidden = !text;
}

document.querySelectorAll('select[name="article"]').forEach(showUnitChangeNotice);

// Prefill the line unit with the stock unit of the selected article (options rendered by ArticleUnitSelect)
document.addEventListener('change', function (e) {
    const select = e.target;
    if (select.tagName !== 'SELECT' || select.name !== 'article' || !select.form) {
        return;
    }
    showUnitChangeNotice(select);
    if (select.dataset.unitPrefill === 'off') {
        return;
    }
    const option = select.options[select.selectedIndex];
    const unit = select.form.elements.namedItem('unit');
    if (option && option.dataset.unit && unit) {
        unit.value = option.dataset.unit;
    }
});

// Ask before saving a line whose unit differs from the article's stock unit
document.addEventListener('submit', function (e) {
    const form = e.target;
    const select = form.elements.namedItem('article');
    const unit = form.elements.namedItem('unit');
    if (!select || !unit || !select.dataset || !select.dataset.unitMismatchMessage) {
        return;
    }
    const option = select.options[select.selectedIndex];
    if (!option || !option.dataset.unit || !unit.value || unit.value === option.dataset.unit) {
        return;
    }
    const message = select.dataset.unitMismatchMessage
        .replace('{unit}', unit.value)
        .replace('{stock_unit}', option.dataset.unit);
    if (!window.confirm(message)) {
        e.preventDefault();
    }
});
