$(document).ready(function () {
    /************************************************************************************************************************************************/
    /* Functions show tooltip */
    $('[data-toggle="tooltip"]').tooltip()
    /************************************************************************************************************************************************/
    /* Date Range Picker */
    var date_format = 'D/M/Y HH:mm:ss'
    /************************************************************************************************************************************************/
    /* Functions for modal form */
    var loadForm = function () {
        var btn = $(this)
        $.ajax({
            url: btn.attr('data-url'),
            type: 'GET',
            beforeSend: function () {
                $('#modal-id').modal('show')
            },
            success: function (data) {
                $('#modal-id .modal-content').html(data.html_form)

                $('input[name="created_on"]').daterangepicker({
                    maxDate: moment(),
                    singleDatePicker: true,
                    timePicker: true,
                    timePicker24Hour: true,
                    timePickerSeconds: true,
                    locale: {
                        format: date_format,
                        applyLabel: str_submit,
                        cancelLabel: str_cancel,
                    },
                })
            }
        })
    }
    var saveForm = function () {
        var form = $(this)
        $.ajax({
            url: form.attr('action'),
            type: form.attr('method'),
            data: form.serialize(),
            success: function (data) {
                if (data.form_is_valid) {
                    window.location.reload()
                    $('#modal-id').modal('hide')
                }
                else {
                    $('#modal-id .modal-content').html(data.html_form)
                }
            }
        })
        return false
    }
    /************************************************************************************************************************************************/
    /* Binding */
    // Create Inv
    $('.js-inv-create-button').click(loadForm)
    $('#modal-id').on('submit', '.js-inv-create', saveForm)

    // Update Inv
    $('.js-inv-update-button').click(loadForm)
    $('#modal-id').on('submit', '.js-inv-update', saveForm)

    // Update Inv Col
    $('.js-invcol-update-button').click(loadForm)
    $('#modal-id').on('submit', '.js-invcol-update', saveForm)
    /************************************************************************************************************************************************/
    /* Functions show agv, robot status */
    var old_column = [], old_row = [], old_data = []
    var agv, agv_src
    function update_agv_robot() {
        $.ajax({
            url: api_agvrobotstatus,
            type: 'GET',
            success: function (response) {
                $.each(response.agv_status, function (key, value) {
                    if ((value.agv_beta >= 0 && value.agv_beta < 45) || (value.agv_beta >= 315 && value.agv_beta < 360)) { agv_src = agv_left }
                    else if (value.agv_beta >= 45 && value.agv_beta < 135) { agv_src = agv_bot }
                    else if (value.agv_beta >= 135 && value.agv_beta < 225) { agv_src = agv_right }
                    else if (value.agv_beta >= 225 && value.agv_beta < 315) { agv_src = agv_top }

                    if (value.agv_col == 40) { value.agv_col = 39 }
                    else if (value.agv_col == 45) { value.agv_col = 46 }
                    if (value.agv_col <= 39) { columnIndex = 95 - value.agv_col }
                    else if (value.agv_col <= 45) { columnIndex = 96 - value.agv_col }
                    else { columnIndex = 97 - value.agv_col }
                    if (value.agv_col <= 38 && value.agv_row >= 6 && value.agv_row <= 7) { columnIndex -= 2 }
                    else if (value.agv_col <= 40 && value.agv_row >= 6 && value.agv_row <= 7) { columnIndex -= 0 }
                    else if (value.agv_col <= 44 && value.agv_row >= 6 && value.agv_row <= 7) { columnIndex -= 1 }
                    if ((value.agv_col == 39 || value.agv_col == 46) && value.agv_row >= 5 && value.agv_row <= 7) { rowIndex = 4 }
                    else { rowIndex = value.agv_row - 1 }

                    $('#layout-table tbody tr').eq(old_row[value.id]).find('td').eq(old_column[value.id]).html(old_data[value.id])
                    old_column[value.id] = columnIndex
                    old_row[value.id] = rowIndex
                    old_data[value.id] = $('#layout-table tbody tr').eq(rowIndex).find('td').eq(columnIndex).text()
                    agv = "<div class='agv' data-toggle='tooltip' title=" + value.id + "><img src=" + agv_src + " style='z-index:" + value.id + ";max-width:100%;max-height:100%'></div>"
                    $('#layout-table tbody tr').eq(rowIndex).find('td').eq(columnIndex).append(agv)
                })
                $('.agv').tooltip()

                $.each(response.robot_status, function (key, value) {
                    $('#robotQty' + value.robot_no).html(value.qty_act)
                })
            }
        })
    }
    update_agv_robot()
    setInterval(update_agv_robot, 1000)
    /************************************************************************************************************************************************/
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
    // Refresh page every 3 minutes
    setInterval(function () {
        if ((document.hasFocus() || true) && !($('#modal-id').is(':visible'))) {
            location.reload()
        }
    }, 180000)
    /************************************************************************************************************************************************/
})