$(document).ready(function() {
    // Enable Select2
    $('.select2').select2({
        theme: "bootstrap4",
    });

});

setInterval(function() {
    if (document.hasFocus() || true) {
        $('.refresh').each(function(i, e) {
            $(e).load(url_page + ' .refresh:eq(' + i + ')', function(){$(this).children().unwrap()});
        });
    }
}, 1000)
