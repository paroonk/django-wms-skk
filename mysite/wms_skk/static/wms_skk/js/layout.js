$(document).ready(function () {
    /* Functions show tooltip */
    $('[data-toggle="tooltip"]').tooltip();

    /* Functions for modal form */
    var loadForm = function () {
        var btn = $(this);
        $.ajax( {
            url: btn.attr('data-url'),
            type: 'GET',
            dataType: 'json',
            beforeSend: function () {
                $('#modal-inv').modal('show');
            },
            success: function (data) {
                $('#modal-inv .modal-content').html(data.html_form);
            }
        });
    };
    var saveForm = function () {
        var form = $(this);
        $.ajax( {
            url: form.attr('action'),
            data: form.serialize(),
            type: form.attr('method'),
            dataType: 'json',
            success: function (data) {
                if (data.form_is_valid) {
                    window.location.reload();
                    $('#modal-inv').modal('hide');
                }
                else {
                    $('#modal-inv .modal-content').html(data.html_form);
                }
            }
        });
        return false;
    };

    /* Binding */
    // Create
    $('.js-create-inv').click(loadForm);
    $('#modal-inv').on('submit', '.js-inv-create-form', saveForm);

    // Update
    $('.js-update-inv').click(loadForm);
    $('#modal-inv').on('submit', '.js-inv-update-form', saveForm);

    /* Functions show agv */
    old_row = old_column = 0
    old_data = $('#layout-table tbody tr').eq(old_row).find('td').eq(old_column).text();

    setInterval(function() {
        $.ajax( {
            url: url_get_data_agv_position,
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                agv_row = data.agv_row;
                agv_col = data.agv_col;
                agv_beta = data.agv_beta;
            }
        });

        if ((agv_beta >= 0 && agv_beta < 45) || (agv_beta >= 315 && agv_beta < 360)) { agv_src = agv_left; }
        else if (agv_beta >= 45 && agv_beta < 135) { agv_src = agv_bot; }
        else if (agv_beta >= 135 && agv_beta < 225) { agv_src = agv_right; }
        else if (agv_beta >= 225 && agv_beta < 315) { agv_src = agv_top; }
    
        if (agv_col == 40) { agv_col = 39; }
        else if (agv_col == 45) { agv_col = 46; }
        if (agv_col <= 39) { columnIndex = 95 - agv_col; }
        else if (agv_col <= 45) { columnIndex = 96 - agv_col; }
        else { columnIndex = 97 - agv_col; }
        if (agv_col <= 38 && agv_row >=6 && agv_row <=7) { columnIndex -= 2; }
        else if (agv_col <= 40 && agv_row >=6 && agv_row <=7) { columnIndex -= 0; }
        else if (agv_col <= 44 && agv_row >=6 && agv_row <=7) { columnIndex -= 1; }
        if ((agv_col == 39 || agv_col == 46) && agv_row >=5 && agv_row <=7) { rowIndex = 4; }
        else { rowIndex = agv_row - 1; }

        $('#layout-table tbody tr').eq(old_row).find('td').eq(old_column).html(old_data);
        old_row = rowIndex;
        old_column = columnIndex;
        old_data = $('#layout-table tbody tr').eq(old_row).find('td').eq(old_column).text();
        var agv = "<div class='agv'><img src=" + agv_src + " style='z-index: 1;, max-width:100%; max-height:100%;'></div>"
        $('#layout-table tbody tr').eq(rowIndex).find('td').eq(columnIndex).append(agv);

//        agv_col += 1;
//        if (agv_col == 40) { agv_col = 41; }
//        if (agv_col == 45) { agv_col = 46; }
//        if (agv_col == 97) {
//            agv_col = 31;
//            agv_row += 1;
//            if (row == 21) { agv_row = 1; }
//        }

    }, 1000)

    setInterval(function() {
        if (document.hasFocus() || true) {
            $('#transfer1-table').load(url_page + ' #transfer1-table', function(){$(this).children().unwrap()});
        }
    }, 1000)

    setInterval(function() {
        if ((document.hasFocus() || true) && !($('#modal-inv').is(':visible'))) {
            location.reload()
        }
    }, 10000)

});