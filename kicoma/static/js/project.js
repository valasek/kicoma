/* Project specific Javascript goes here. */

// JavaScript to close the date picker after selecting a date
document.addEventListener('change', function (e) {
    if (e.target.type === 'date') {
        e.target.blur(); // Removes focus, which closes the picker
    }
});

// Prefill the line unit with the stock unit of the selected article (options rendered by ArticleUnitSelect)
document.addEventListener('change', function (e) {
    const select = e.target;
    if (select.tagName !== 'SELECT' || select.name !== 'article' || !select.form) {
        return;
    }
    const option = select.options[select.selectedIndex];
    const unit = select.form.elements.namedItem('unit');
    if (option && option.dataset.unit && unit) {
        unit.value = option.dataset.unit;
    }
});
