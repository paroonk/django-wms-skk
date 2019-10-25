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
                $('#modal-col').modal('show');
            },
            success: function (data) {
                $('#modal-col .modal-content').html(data.html_form);
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
                    $('#modal-col').modal('hide');
                }
                else {
                    $('#modal-col .modal-content').html(data.html_form);
                }
            }
        });
        return false;
    };

    /* Binding */
    $('.js-update-col').click(loadForm);
    $('#modal-col').on('submit', '.js-col-update-form', saveForm);

});