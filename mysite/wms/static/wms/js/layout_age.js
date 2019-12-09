$(document).ready(function () {
/******************************************************************************************************************************************************/
    /* Functions show tooltip */
    $('[data-toggle="tooltip"]').tooltip()
/******************************************************************************************************************************************************/
    /* Date Range Picker */
    var date_format = 'D/M/Y HH:mm:ss'
/******************************************************************************************************************************************************/
    /* Functions for modal form */
    var loadForm = function () {
        var btn = $(this)
        $.ajax( {
            url: btn.attr('data-url'),
            type: 'GET',
            beforeSend: function () {
                $('#modal-id').modal('show')
            },
            success: function (response) {
                $('#modal-id .modal-content').html(response.html_form)

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
        $.ajax( {
            url: form.attr('action'),
            type: form.attr('method'),
            data: form.serialize(),
            success: function (response) {
                if (response.form_is_valid) {
                    window.location.reload()
                    $('#modal-id').modal('hide')
                }
                else {
                    $('#modal-id .modal-content').html(response.html_form)
                }
            }
        })
        return false
    }
/******************************************************************************************************************************************************/
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
/******************************************************************************************************************************************************/
})