/* Project specific Javascript goes here. */

// JavaScript to close the date picker after selecting a date
document.addEventListener('change', function(e) {
    if (e.target.type === 'date') {
        e.target.blur(); // Removes focus, which closes the picker
    }
});
