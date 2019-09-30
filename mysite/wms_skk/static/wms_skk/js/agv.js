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

    // Retrieval
    path2 = 'form[name="retrieval-form"] '
    $(path2 + '#id_name_th_retrieve,' + path2 + '#id_qty_bag').change(function() {
        product_id = $(path2 + '#id_name_th_retrieve').val();
        qty_bag = $(path2 + '#id_qty_bag').val();
        $(path2 + '#id_product_id').val(product_id);
        $.ajax( {
            url: url_get_data_retrieval_form,
            type: 'POST',
            data: {
                'product_id': product_id,
                'qty_bag': qty_bag,
            },
            success: function (data) {
                $(path2 + '#id_inv_bag').val(data.inv_bag);
                $(path2 + '#id_avail_inv_bag').val(data.avail_inv_bag);
                $(path2 + '#id_buffer_space').val(data.buffer_space);
                $(path2 + '#id_qty_act_bag').val(data.qty_act_bag);
                $(path2 + '#id_qty_act_pallet').val(data.qty_act_pallet);
                $(path2 + '#id_retrieve_list').val(data.retrieve_list);
                $(path2 + '#id_buffer_list').val(data.buffer_list);
            }
        });
    });
    $(path2 + '#id_name_th_retrieve').change();
    
    // Move
    path3 = 'form[name="move-form"] '
    $(path3 + '#id_move_from,' + path3 + '#id_move_to').change(function() {
        move_from = $(path3 + '#id_move_from').val();
        move_to = $(path3 + '#id_move_to').val();
        $.ajax( {
            url: url_get_data_move_form,
            type: 'POST',
            data: {
                'move_from': move_from,
                'move_to': move_to,
            },
            success: function (data) {
                $(path3 + '#id_name_th').val(data.name_th);
                $(path3 + '#id_product_id').val(data.product_id);
                $(path3 + '#id_qty_bag').val(data.qty_bag);
                $(path3 + '#id_lot_name').val(data.lot_name);
                $(path3 + '#id_storage_for').val(data.storage_for);
            }
        });
    });
    $(path3 + '#id_move_from').change();

    // Enable Select2
    $('.select2').select2({
        theme: "bootstrap4",
    });

});

setInterval(function() {
    if (document.hasFocus() || true) {
        $('#transfer1-table').load(url_page + ' #transfer1-table', function(){$(this).children().unwrap()});
        $('#plan-table').load(url_page + ' #plan-table', function(){$(this).children().unwrap()});
        $('#queue1-table').load(url_page + ' #queue1-table', function(){$(this).children().unwrap()});
    }
}, 1000)
