function agv_to_home(url, agv_no) {
    var card_no=$('#ca_no').val();
    $("#register").attr('href', window.location.href+'?body=EDS'+card_no);
}

$(document).ready(function() {
    // Enable Select2
    $('.select2').select2({
        theme: "bootstrap4",
    });

    // Manual Transfeer
    path = 'form[name="manualtransfer-form"] '
    $(path + '#id_agv_no').change(function() {
        agv_no = $(path + '#id_agv_no').val();
        $('#agv_to_home').attr('href', url_agv_to_home.replace('/0/', '/' + agv_no + '/'));
    });
    $(path + '#id_agv_no').change();

});

setInterval(function() {
    if (document.hasFocus() || true) {
        $('.refresh').each(function(i, e) {
            $(e).load(url_page + ' .refresh:eq(' + i + ')', function(){$(this).children().unwrap()});
        });
    }
}, 1000)