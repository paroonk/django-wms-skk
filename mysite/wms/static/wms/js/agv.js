$(document).ready(function () {
    /************************************************************************************************************************************************/
    // Refresh AgvProductionPlan
    function update_agvproductionplan() {
        $.ajax({
            url: api_agvproductionplan,
            type: 'GET',
            success: function (response) {
                render_agvproductionplan(response)
            }
        })
    }
    update_agvproductionplan()
    setInterval(update_agvproductionplan, 1000)

    // Refresh RobotQueue
    function update_robotqueue() {
        $.ajax({
            url: api_robotqueue,
            type: 'GET',
            success: function (response) {
                render_robotqueue(response)
            }
        })
    }
    update_robotqueue()
    setInterval(update_robotqueue, 1000)

    // Refresh AgvQueue
    function update_agvqueue() {
        $.ajax({
            url: api_agvqueue,
            type: 'GET',
            success: function (response) {
                render_agvqueue(response)
            }
        })
    }
    update_agvqueue()
    setInterval(update_agvqueue, 1000)

    // Refresh AgvTransfer
    function update_agvtransfer() {
        $.ajax({
            url: api_agvtransfer,
            type: 'GET',
            success: function (response) {
                render_agvtransfer(response)
            }
        })
    }
    update_agvtransfer()
    setInterval(update_agvtransfer, 1000)
    /************************************************************************************************************************************************/
    /* Auto Calculate Form */
    // Storage
    path1 = 'form[name="storage-form"] '
    $(path1 + '#id_product_name_storage,' + path1 + '#id_qty_bag').change(function () {
        $.ajax({
            url: url_get_data_storage_form,
            type: 'GET',
            data: {
                'product_name_storage': $(path1 + '#id_product_name_storage').val(),
            },
            beforeSend: function (response) {
                $(path1 + 'button[type="submit"]').attr("disabled", true)
            },
            success: function (response) {
                $(path1 + '#id_qty_storage').val(response.qty_storage)
                $(path1 + '#id_qty_storage_avail').val(response.qty_storage_avail)
                $(path1 + '#id_qty_pallet').val(Math.ceil($(path1 + '#id_qty_bag').val() / response.qty_limit))
                $(path1 + 'button[type="submit"]').attr("disabled", false)
            }
        })
    })
    $(path1 + '#id_product_name_storage').change()

    // Retrieval
    path2 = 'form[name="retrieval-form"] '
    $(path2 + '#id_product_name_retrieve,' + path2 + '#id_qty_bag').change(function () {
        $.ajax({
            url: url_get_data_retrieval_form,
            type: 'GET',
            data: {
                'product_name_retrieve': $(path2 + '#id_product_name_retrieve').val(),
                'qty_bag': $(path2 + '#id_qty_bag').val(),
            },
            beforeSend: function (response) {
                $(path2 + 'button[type="submit"]').attr("disabled", true)
            },
            success: function (response) {
                $(path2 + '#id_inv_bag').val(response.inv_bag)
                $(path2 + '#id_avail_inv_bag').val(response.avail_inv_bag)
                $(path2 + '#id_buffer_space').val(response.buffer_space)
                $(path2 + '#id_qty_act_bag').val(response.qty_act_bag)
                $(path2 + '#id_qty_act_pallet').val(response.qty_act_pallet)
                $(path2 + '#id_retrieve_list').val(response.retrieve_list)
                $(path2 + '#id_buffer_list').val(response.buffer_list)
                $(path2 + 'button[type="submit"]').attr("disabled", false)
            }
        })
    })
    $(path2 + '#id_product_name_retrieve').change()

    // Move
    path3 = 'form[name="move-form"] '
    $(path3 + '#id_move_from,' + path3 + '#id_move_to').change(function () {
        $.ajax({
            url: url_get_data_move_form,
            type: 'GET',
            data: {
                'move_from': $(path3 + '#id_move_from').val(),
                'move_to': $(path3 + '#id_move_to').val(),
            },
            beforeSend: function (response) {
                $(path3 + 'button[type="submit"]').attr("disabled", true)
            },
            success: function (response) {
                $(path3 + '#id_product_name_move').val(response.product_name_move)
                $(path3 + '#id_qty_bag').val(response.qty_bag)
                $(path3 + '#id_lot_name').val(response.lot_name)
                $(path3 + '#id_storage_for').val(response.storage_for)
                $(path3 + 'button[type="submit"]').attr("disabled", false)
            }
        })
    })
    $(path3 + '#id_move_from').change()
    /************************************************************************************************************************************************/
    // Enable Select2
    $('.select2').select2({
        theme: "bootstrap4",
        language: lang,
    })
    /************************************************************************************************************************************************/
})
