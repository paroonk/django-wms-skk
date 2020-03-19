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

    var rowIndex = [], columnIndex = [], row, col
    row = 0
    for (agv_row = 0; agv_row <= 22; agv_row++) {
        rowIndex[agv_row] = []
        columnIndex[agv_row] = []
        col = 1
        for (agv_col = 77; agv_col >= 0; agv_col--) {

            // Find Row
            rowIndex[agv_row][agv_col] = row
            if (agv_row == 6) {
                if (agv_col == 9) { rowIndex[agv_row][agv_col] -= 1 }         // Robot #2 Offset
                else if (agv_col == 12) { rowIndex[agv_row][agv_col] -= 1 }   // Robot #1 Offset
                // else if (agv_col == 15) { rowIndex[agv_row][agv_col] -= 1 }   // Robot #3 Offset
            }

            // Find Column
            columnIndex[agv_row][agv_col] = col
            if (agv_row == 6) {
                if (agv_col == 9) { columnIndex[agv_row][agv_col] = columnIndex[agv_row - 1][agv_col] }          // Robot #2 Offset
                else if (agv_col == 12) { columnIndex[agv_row][agv_col] = columnIndex[agv_row - 1][agv_col] }    // Robot #1 Offset
                // else if (agv_col == 15) { columnIndex[agv_row][agv_col] = columnIndex[agv_row - 1][agv_col] }    // Robot #3 Offset
            }

            // Update col
            if (agv_col == 77 || agv_col == 1) {}

            else if (agv_col >= 9 && agv_col <= 10 && agv_row == 4) {}      // Robot #2 Offset
            else if (agv_col >= 12 && agv_col <= 13 && agv_row == 4) {}     // Robot #1 Offset
            // else if (agv_col >= 15 && agv_col <= 16 && agv_row == 4) {}     // Robot #3 Offset

            else if (agv_col == 9 && agv_row == 6) {}       // Robot #2 Offset
            else if (agv_col == 12 && agv_row == 6) {}      // Robot #1 Offset
            // else if (agv_col == 15 && agv_row == 6) {}      // Robot #3 Offset
            else { col++ }
        }
        // Update row
        if (agv_row == 0 || agv_row == 21) {}
        else { row++ }
    }

    // for (i = 0; i < 21; i++) {
    //     for (j = 1; j < 77; j++) {
    //         $('#layout-table tbody tr').eq(i).find('td').eq(j).text(i + "," + j)
    //     }
    // }
    // console.log(rowIndex, columnIndex)
    
    var old_column = [], old_row = [], old_data = []
    var agv, agv_src
    function update_agv_robot() {
        $.ajax({
            url: api_agvrobotstatus,
            type: 'GET',
            success: function (response) {
                $.each(response.robot_status, function (key, value) {
                    $('#robotQty' + value.robot_no).html(value.qty_act)
                })

                $.each(response.agv_status, function (key, value) {
                    if (value.agv_direction == 'L') { agv_src = agv_left }
                    else if (value.agv_direction == 'B') { agv_src = agv_bot }
                    else if (value.agv_direction == 'R') { agv_src = agv_right }
                    else if (value.agv_direction == 'T') { agv_src = agv_top }

                    $('#layout-table tbody tr').eq(old_row[value.id]).find('td').eq(old_column[value.id]).html(old_data[value.id])
                    old_column[value.id] = columnIndex[value.agv_row][value.agv_col]
                    old_row[value.id] = rowIndex[value.agv_row][value.agv_col]
                    old_data[value.id] = $('#layout-table tbody tr').eq(rowIndex[value.agv_row][value.agv_col]).find('td').eq(columnIndex[value.agv_row][value.agv_col]).text()
                    agv = "<div class='agv' data-toggle='tooltip' title='AGV #" + value.id + "'><img src=" + agv_src + " style='z-index:" + value.id + ";max-width:100%;max-height:100%'></div>"
                    $('#layout-table tbody tr').eq(rowIndex[value.agv_row][value.agv_col]).find('td').eq(columnIndex[value.agv_row][value.agv_col]).append(agv)
                })
                $('.agv').tooltip()
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