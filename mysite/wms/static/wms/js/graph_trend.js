$(document).ready(function() {
    /* Date Range Picker */
    var date_format = 'D/M/YY HH:mm';

    $('input[name="date_filter"]').daterangepicker({
        maxDate: moment(),
        timePicker: true,
        timePicker24Hour: true,
        locale: {
            format: date_format,
            applyLabel: str_submit,
            cancelLabel: str_cancel,
            customRangeLabel: str_custom_range,
        },
        ranges: custom_range,
    });

    /* Responsive Chart */
    $(window).resize(function() {
        trendChart.resize();
    });
});
