$(document).ready(function () {
/******************************************************************************************************************************************************/
    /* Functions show tooltip */
    $('[data-toggle="tooltip"]').tooltip()
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
    $('.js-col-update-button').click(loadForm)
    $('#modal-id').on('submit', '.js-col-update', saveForm)
/******************************************************************************************************************************************************/
})