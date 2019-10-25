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
});