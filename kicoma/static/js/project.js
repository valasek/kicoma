/* Project specific Javascript goes here. */

// JavaScript to close the date picker after selecting a date
const dateInput = document.querySelector('input[type="date"]');

dateInput.addEventListener('change', function() {
    this.blur(); // Removes focus, which closes the picker
});
