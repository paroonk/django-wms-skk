$(document).ready(function() {
    /* Auto Calculate Form */
    // Storage
    path1 = 'form[name="storage-form"] '
    $(path1 + '#id_name_th_storage,' + path1 + '#id_qty_bag').change(function() {
        product_id = $(path1 + '#id_name_th_storage').val();
        $(path1 + '#id_product_id').val(product_id);
        $.ajax( {
            url: url_get_data_storage_form,
            type: 'POST',
            data: {
                'product_id': product_id,
            },
            success: function (data) {
                $(path1 + '#id_qty_storage').val(data.qty_storage);
                $(path1 + '#id_qty_storage_avail').val(data.qty_storage_avail);
                $(path1 + '#id_qty_pallet').val(Math.ceil($(path1 + '#id_qty_bag').val() / data.qty_limit));
            }
        });
    });
    $(path1 + '#id_name_th_storage').change();

    // Enable Select2
    $('.select2').select2({
        theme: "bootstrap4",
    });

});

setInterval(function() {
    if (document.hasFocus() || true) {
        $('#transfer1-table').load(url_page + ' #transfer1-table', function(){$(this).children().unwrap()});
        $('#plan-table').load(url_page + ' #plan-table', function(){$(this).children().unwrap()});
        $('#robot-table').load(url_page + ' #robot-table', function(){$(this).children().unwrap()});
        $('#queue1-table').load(url_page + ' #queue1-table', function(){$(this).children().unwrap()});
    }
}, 1000)